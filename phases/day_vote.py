"""白天投票阶段"""
from typing import TYPE_CHECKING, Dict, List
from astrbot.api import logger

from .base import BasePhase
from ..models import GamePhase, Role
from ..roles import HunterDeathType
from ..services import BanService

if TYPE_CHECKING:
    from ..models import GameRoom


class DayVotePhase(BasePhase):
    """白天投票阶段"""

    @property
    def name(self) -> str:
        return "投票阶段"

    @property
    def timeout_seconds(self) -> int:
        return self.game_manager.config.timeout_vote

    def _is_current_phase(self, room: "GameRoom") -> bool:
        return room.phase == GamePhase.DAY_VOTE

    async def on_enter(self, room: "GameRoom") -> None:
        """进入投票阶段"""
        room.phase = GamePhase.DAY_VOTE
        room.vote_state.day_votes.clear()

        # 发送投票开始消息
        await self.message_service.announce_vote_start(room)

        # 解除全群禁言
        await BanService.set_group_whole_ban(room, False)

        # 启动定时器（带30秒提醒）
        await self._start_vote_timer(room)

    async def enter_pk_vote(self, room: "GameRoom") -> None:
        """进入PK投票"""
        room.phase = GamePhase.DAY_VOTE
        room.vote_state.is_pk_vote = True
        room.vote_state.day_votes.clear()

        # 发送PK投票提示
        pk_names = []
        for pid in room.vote_state.pk_players:
            player = room.get_player(pid)
            if player:
                pk_names.append(player.display_name)

        await self.message_service.announce_pk_vote_start(room, pk_names)

        # 解除全群禁言
        await BanService.set_group_whole_ban(room, False)

        # 启动定时器
        await self._start_vote_timer(room)

    async def _start_vote_timer(self, room: "GameRoom") -> None:
        """启动带30秒提醒的投票定时器"""
        import asyncio

        async def vote_timer():
            try:
                timeout = self.timeout_seconds

                # 如果超过30秒，先等待到剩余30秒
                if timeout > 30:
                    await asyncio.sleep(timeout - 30)

                    if room.group_id not in self.game_manager.rooms:
                        return
                    if room.phase != GamePhase.DAY_VOTE:
                        return

                    # 发送30秒提醒
                    voted = len(room.vote_state.day_votes)
                    total = room.alive_count
                    await self.message_service.announce_vote_reminder(room, voted, total)

                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(timeout)

                if room.group_id not in self.game_manager.rooms:
                    return
                if room.phase != GamePhase.DAY_VOTE:
                    return

                await self.on_timeout(room)

            except asyncio.CancelledError:
                logger.info(f"[狼人杀] 群 {room.group_id} 投票定时器已取消")
            except Exception as e:
                logger.error(f"[狼人杀] 投票超时处理失败: {e}")

        task = asyncio.create_task(vote_timer())
        room.set_timer(task)

    async def on_timeout(self, room: "GameRoom") -> None:
        """投票超时"""
        voted = len(room.vote_state.day_votes)
        total = room.alive_count

        await self.message_service.send_group_message(
            room, f"⏰ 投票超时！已有 {voted}/{total} 人投票，自动结算。"
        )

        if room.vote_state.day_votes:
            await self._process_vote_result(room)
        else:
            # 无人投票，进入下一夜晚
            room.log("📊 投票超时：无人投票，本轮无人出局")
            await self._enter_night(room)

    async def on_all_voted(self, room: "GameRoom") -> None:
        """所有人投票完成"""
        room.cancel_timer()
        await self._process_vote_result(room)

    async def _process_vote_result(self, room: "GameRoom") -> None:
        """处理投票结果"""
        # 先统计投票，用于生成图片
        votes = room.vote_state.day_votes
        vote_counts: Dict[str, int] = {}
        voters_map: Dict[str, List[str]] = {}  # target_id -> [voter_names]

        for voter_id, target_id in votes.items():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
            voter = room.get_player(voter_id)
            if voter:
                if target_id not in voters_map:
                    voters_map[target_id] = []
                voters_map[target_id].append(voter.display_name)

        # 处理投票结果
        exiled_id, is_tie = await self.game_manager.process_day_vote(room)

        if is_tie:
            # 平票情况 - 发送投票结果图片（无人被放逐）
            is_pk = room.vote_state.is_pk_vote
            await self.message_service.announce_vote_result(
                room, vote_counts, voters_map, None, is_pk
            )

            if not is_pk:
                # 第一次平票，进入PK
                from .day_speaking import DaySpeakingPhase
                speaking_phase = DaySpeakingPhase(self.game_manager)
                await speaking_phase.enter_pk_phase(room, room.vote_state.pk_players)
            else:
                # PK后仍平票，无人出局
                room.log("📊 PK投票结果：仍然平票，本轮无人出局")
                await self._enter_night(room)
            return

        if not exiled_id:
            await self._enter_night(room)
            return

        # 有人被放逐
        exiled_player = room.get_player(exiled_id)
        if not exiled_player:
            return

        # 记录日志
        is_pk = room.vote_state.is_pk_vote
        room.log(f"📊 {'PK' if is_pk else ''}投票结果：{exiled_player.display_name} 被放逐")

        # 发送投票结果
        await self.message_service.announce_vote_result(
            room, vote_counts, voters_map, exiled_player.display_name, is_pk
        )

        # 公告放逐结果
        await self.message_service.announce_exile(room, exiled_player.display_name, is_pk)

        # 检查是否是猎人
        if exiled_player.role == Role.HUNTER:
            room.hunter_state.pending_shot_player_id = exiled_id
            room.hunter_state.death_type = HunterDeathType.VOTE
            await self._wait_for_hunter_shot(room)
            return

        # 检查游戏是否结束
        if await self.game_manager.check_and_handle_victory(room):
            return

        # 进入遗言阶段
        room.last_killed_id = exiled_id
        room.last_words_from_vote = True
        await self._enter_last_words(room)

    async def _wait_for_hunter_shot(self, room: "GameRoom") -> None:
        """等待猎人开枪"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.wait_for_hunter_shot(room, "vote")

    async def _enter_last_words(self, room: "GameRoom") -> None:
        """进入遗言阶段"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.enter_last_words_phase(room)

    async def _enter_night(self, room: "GameRoom") -> None:
        """进入夜晚"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.enter_night_phase(room)
