"""夜晚-预言家验人阶段"""
import random
from typing import TYPE_CHECKING
from astrbot.api import logger

from .base import BasePhase
from ..models import GamePhase

if TYPE_CHECKING:
    from ..models import GameRoom


class NightSeerPhase(BasePhase):
    """预言家验人阶段"""

    @property
    def name(self) -> str:
        return "预言家验人阶段"

    @property
    def timeout_seconds(self) -> int:
        return self.game_manager.config.timeout_seer

    def _is_current_phase(self, room: "GameRoom") -> bool:
        return room.phase == GamePhase.NIGHT_SEER

    async def on_enter(self, room: "GameRoom") -> None:
        """进入预言家验人阶段"""
        room.phase = GamePhase.NIGHT_SEER
        room.seer_checked = False

        seer = room.get_seer()

        # 如果游戏中没有预言家角色，直接跳过
        if not seer:
            logger.info(f"[狼人杀] 群 {room.group_id} 没有预言家角色，跳过预言家阶段")
            await self._enter_witch_phase(room)
            return

        # 发送群提示
        await self.message_service.announce_seer_phase(room)

        # 给预言家发私聊通知
        await self._notify_seer(room)

        # 计算等待时间（预言家已死则随机短时间）
        if seer.is_alive:
            wait_time = self.timeout_seconds
        else:
            wait_time = random.uniform(
                self.game_manager.config.timeout_dead_min,
                self.game_manager.config.timeout_dead_max
            )

        # 启动定时器
        await self.start_timer(room, wait_time)

    async def _notify_seer(self, room: "GameRoom") -> None:
        """通知预言家"""
        seer = room.get_seer()
        if not seer or not seer.is_alive:
            return

        # 获取存活玩家列表
        alive_players = room.get_alive_players()
        player_list = "\n".join([
            f"  {p.number}号 - {p.display_name}"
            for p in alive_players if p.id != seer.id
        ])

        prompt = (
            f"🔮 预言家验人阶段\n\n"
            f"轮到你行动了！请选择一名玩家查验身份。\n\n"
            f"📋 可查验的玩家：\n{player_list}\n\n"
            f"💡 使用命令：/验人 编号\n"
            f"例如：/验人 3"
        )

        await self.message_service.send_private_message(room, seer.id, prompt)
        logger.info(f"[狼人杀] 已通知预言家 {seer.id} 验人")

    async def on_timeout(self, room: "GameRoom") -> None:
        """预言家验人超时"""
        room.seer_checked = True

        # 只有预言家存活时才发送超时提示
        if room.is_seer_alive():
            await self.message_service.announce_timeout(room, "预言家验人")

        # 进入女巫阶段
        await self._enter_witch_phase(room)

    async def on_checked(self, room: "GameRoom") -> None:
        """预言家验人完成"""
        room.cancel_timer()
        room.seer_checked = True
        await self._enter_witch_phase(room)

    async def _enter_witch_phase(self, room: "GameRoom") -> None:
        """进入女巫行动阶段"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.enter_witch_phase(room)
