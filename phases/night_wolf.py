"""夜晚-狼人行动阶段"""
import random
from typing import TYPE_CHECKING
from astrbot.api import logger

from .base import BasePhase
from ..models import GamePhase

if TYPE_CHECKING:
    from ..models import GameRoom


class NightWolfPhase(BasePhase):
    """狼人行动阶段"""

    @property
    def name(self) -> str:
        return "狼人行动阶段"

    @property
    def timeout_seconds(self) -> int:
        return self.game_manager.config.timeout_wolf

    def _is_current_phase(self, room: "GameRoom") -> bool:
        return room.phase == GamePhase.NIGHT_WOLF

    async def on_enter(self, room: "GameRoom") -> None:
        """进入狼人行动阶段"""
        room.phase = GamePhase.NIGHT_WOLF
        room.seer_checked = False
        room.vote_state.clear_night_votes()

        # 启动定时器
        await self.start_timer(room)

    async def on_timeout(self, room: "GameRoom") -> None:
        """狼人行动超时"""
        await self.message_service.announce_timeout(room, "狼人行动")

        if room.vote_state.night_votes:
            # 有投票，处理
            await self._finish_and_next(room)
        else:
            # 无投票，记录日志，直接进入预言家阶段
            room.log("🐺 狼人超时：未投票，今晚无人被刀")
            await self._enter_seer_phase(room)

    async def on_all_voted(self, room: "GameRoom") -> None:
        """所有狼人投票完成"""
        room.cancel_timer()
        await self._finish_and_next(room)

    async def _finish_and_next(self, room: "GameRoom") -> None:
        """完成狼人阶段，进入下一阶段"""
        # 处理投票结果
        await self.game_manager.process_night_kill(room)

        # 检查游戏是否结束
        if await self.game_manager.check_and_handle_victory(room):
            return

        # 进入预言家阶段
        await self._enter_seer_phase(room)

    async def _enter_seer_phase(self, room: "GameRoom") -> None:
        """进入预言家验人阶段"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.enter_seer_phase(room)
