"""白天发言阶段"""
from typing import TYPE_CHECKING
from astrbot.api import logger

from .base import BasePhase
from ..models import GamePhase
from ..services import BanService

if TYPE_CHECKING:
    from ..models import GameRoom


class DaySpeakingPhase(BasePhase):
    """白天发言阶段"""

    @property
    def name(self) -> str:
        return "发言阶段"

    @property
    def timeout_seconds(self) -> int:
        return self.game_manager.config.timeout_speaking

    def _is_current_phase(self, room: "GameRoom") -> bool:
        return room.phase in (GamePhase.DAY_SPEAKING, GamePhase.DAY_PK)

    async def on_enter(self, room: "GameRoom") -> None:
        """进入发言阶段"""
        room.phase = GamePhase.DAY_SPEAKING

        # 设置发言顺序（按编号排序）
        alive_players = room.get_alive_players()
        alive_players.sort(key=lambda p: p.number)
        room.speaking_state.order = [p.id for p in alive_players]
        room.speaking_state.current_index = 0

        # 确保全群禁言
        await BanService.set_group_whole_ban(room, True)

        # 开始第一个人发言
        await self._next_speaker(room)

    async def on_timeout(self, room: "GameRoom") -> None:
        """发言超时"""
        current_speaker_id = room.speaking_state.current_speaker_id
        if current_speaker_id:
            # 取消管理员
            await BanService.remove_temp_admin(room, current_speaker_id)

            # 发送超时提示
            player = room.get_player(current_speaker_id)
            if player:
                await self.message_service.send_group_message(
                    room, f"⏰ {player.display_name} 发言超时！自动进入下一位。"
                )

        # 下一位
        room.speaking_state.current_index += 1
        await self._next_speaker(room)

    async def on_finish_speaking(self, room: "GameRoom") -> None:
        """发言完毕"""
        room.cancel_timer()

        current_speaker_id = room.speaking_state.current_speaker_id
        if current_speaker_id:
            # 记录发言
            self._record_speech(room, current_speaker_id)
            # 取消管理员
            await BanService.remove_temp_admin(room, current_speaker_id)

        # 下一位
        room.speaking_state.current_index += 1

        if room.phase == GamePhase.DAY_PK:
            await self._next_pk_speaker(room)
        else:
            await self._next_speaker(room)

    def _record_speech(self, room: "GameRoom", player_id: str) -> None:
        """记录发言内容"""
        player = room.get_player(player_id)
        if not player:
            return

        speech_list = room.speaking_state.current_speech
        if speech_list:
            full_speech = " ".join(speech_list)
            if len(full_speech) > 200:
                full_speech = full_speech[:200] + "..."

            phase_tag = "💬PK发言" if room.phase == GamePhase.DAY_PK else "💬发言"
            room.log(f"{phase_tag}：{player.display_name} - {full_speech}")
        else:
            phase_tag = "💬PK发言" if room.phase == GamePhase.DAY_PK else "💬发言"
            room.log(f"{phase_tag}：{player.display_name} - [未捕获到文字内容]")

        # 清空缓存
        room.speaking_state.current_speech.clear()

    async def _next_speaker(self, room: "GameRoom") -> None:
        """下一个发言者"""
        speaking = room.speaking_state

        # 检查是否所有人都发言完毕
        if speaking.current_index >= len(speaking.order):
            await self._enter_vote_phase(room)
            return

        # 获取当前发言者
        current_id = speaking.order[speaking.current_index]
        speaking.current_speaker_id = current_id
        speaking.current_speech.clear()

        # 设为临时管理员
        await BanService.set_temp_admin(room, current_id)

        # 发送提示
        player = room.get_player(current_id)
        if player:
            await self.message_service.send_group_at_message(
                room, player,
                f" 现在轮到你发言\n\n"
                f"⏰ 发言时间：2分钟\n"
                f"💡 发言完毕后请使用：/发言完毕\n\n"
                f"进度：{speaking.current_index + 1}/{len(speaking.order)}"
            )

        # 启动定时器
        await self.start_timer(room)

    async def _next_pk_speaker(self, room: "GameRoom") -> None:
        """下一个PK发言者"""
        speaking = room.speaking_state
        pk_players = room.vote_state.pk_players

        # 检查是否所有PK玩家都发言完毕
        if speaking.current_index >= len(pk_players):
            await self._enter_pk_vote(room)
            return

        # 获取当前PK发言者
        current_id = pk_players[speaking.current_index]
        speaking.current_speaker_id = current_id
        speaking.current_speech.clear()

        # 设为临时管理员
        await BanService.set_temp_admin(room, current_id)

        # 发送提示
        player = room.get_player(current_id)
        if player:
            await self.message_service.send_group_at_message(
                room, player,
                f" PK发言：现在轮到你发言\n\n"
                f"⏰ 发言时间：2分钟\n"
                f"💡 发言完毕后请使用：/发言完毕\n\n"
                f"进度：{speaking.current_index + 1}/{len(pk_players)}"
            )

        # 启动定时器
        await self.start_timer(room)

    async def enter_pk_phase(self, room: "GameRoom", pk_player_ids: list) -> None:
        """进入PK发言阶段"""
        room.phase = GamePhase.DAY_PK
        room.vote_state.pk_players = pk_player_ids
        room.speaking_state.current_index = 0
        room.vote_state.is_pk_vote = False

        # 发送PK开始提示
        pk_names = []
        for pid in pk_player_ids:
            player = room.get_player(pid)
            if player:
                pk_names.append(player.display_name)

        await self.message_service.announce_pk_start(room, pk_names)

        # 开启全群禁言
        await BanService.set_group_whole_ban(room, True)

        # 开始第一个PK发言者
        await self._next_pk_speaker(room)

    async def _enter_vote_phase(self, room: "GameRoom") -> None:
        """进入投票阶段"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.enter_vote_phase(room)

    async def _enter_pk_vote(self, room: "GameRoom") -> None:
        """进入PK投票"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.enter_pk_vote_phase(room)
