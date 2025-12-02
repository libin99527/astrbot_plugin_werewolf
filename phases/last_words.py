"""遗言阶段"""
from typing import TYPE_CHECKING
from astrbot.api import logger

from .base import BasePhase
from ..models import GamePhase
from ..services import BanService

if TYPE_CHECKING:
    from ..models import GameRoom


class LastWordsPhase(BasePhase):
    """遗言阶段"""

    @property
    def name(self) -> str:
        return "遗言阶段"

    @property
    def timeout_seconds(self) -> int:
        return self.game_manager.config.timeout_speaking

    def _is_current_phase(self, room: "GameRoom") -> bool:
        return room.phase == GamePhase.LAST_WORDS

    async def on_enter(self, room: "GameRoom") -> None:
        """进入遗言阶段"""
        room.phase = GamePhase.LAST_WORDS

        # 检查是否有被杀玩家
        if not room.last_killed_id:
            await self._finish_last_words(room)
            return

        killed_player = room.get_player(room.last_killed_id)
        if not killed_player:
            await self._finish_last_words(room)
            return

        # 清空发言缓存
        room.speaking_state.current_speech.clear()

        # 开启全群禁言
        await BanService.set_group_whole_ban(room, True)

        # 设置被杀玩家为临时管理员
        await BanService.set_temp_admin(room, killed_player.id)

        # 发送遗言提示
        await self.message_service.send_group_at_message(
            room, killed_player,
            f" 现在请你留遗言\n\n"
            f"⏰ 遗言时间：2分钟\n"
            f"💡 遗言完毕后请使用：/遗言完毕"
        )

        # 启动定时器
        await self.start_timer(room)

    async def on_timeout(self, room: "GameRoom") -> None:
        """遗言超时"""
        if room.last_killed_id:
            # 取消管理员
            await BanService.remove_temp_admin(room, room.last_killed_id)
            # 禁言
            await BanService.ban_player(room, room.last_killed_id)

        # 确保全员禁言
        await BanService.set_group_whole_ban(room, True)

        # 发送超时提示
        await self.message_service.announce_timeout(room, "遗言")

        await self._finish_last_words(room)

    async def on_finish(self, room: "GameRoom") -> None:
        """遗言完毕"""
        room.cancel_timer()

        # 记录遗言
        self._record_last_words(room)

        if room.last_killed_id:
            # 取消管理员
            await BanService.remove_temp_admin(room, room.last_killed_id)
            # 禁言
            await BanService.ban_player(room, room.last_killed_id)

        # 确保全员禁言
        await BanService.set_group_whole_ban(room, True)

        await self._finish_last_words(room)

    def _record_last_words(self, room: "GameRoom") -> None:
        """记录遗言内容"""
        if not room.last_killed_id:
            return

        player = room.get_player(room.last_killed_id)
        if not player:
            return

        speech_list = room.speaking_state.current_speech
        if speech_list:
            full_speech = " ".join(speech_list)
            if len(full_speech) > 200:
                full_speech = full_speech[:200] + "..."
            room.log(f"💀遗言：{player.display_name} - {full_speech}")
        else:
            room.log(f"💀遗言：{player.display_name} - [未捕获到文字内容]")

        # 清空缓存
        room.speaking_state.current_speech.clear()

    async def _finish_last_words(self, room: "GameRoom") -> None:
        """结束遗言阶段"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)

        if room.last_words_from_vote:
            # 来自投票放逐，进入夜晚
            room.last_words_from_vote = False
            room.end_first_night()
            await phase_manager.enter_night_phase(room)
        else:
            # 来自夜晚被杀，进入发言阶段
            room.last_killed_id = None
            room.end_first_night()
            await phase_manager.enter_speaking_phase(room)
