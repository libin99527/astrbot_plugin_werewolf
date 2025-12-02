"""阶段基类"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
import asyncio
from astrbot.api import logger

if TYPE_CHECKING:
    from ..models import GameRoom
    from ..services import GameManager


class BasePhase(ABC):
    """游戏阶段基类"""

    def __init__(self, game_manager: "GameManager"):
        self.game_manager = game_manager
        self.message_service = game_manager.message_service

    @property
    @abstractmethod
    def name(self) -> str:
        """阶段名称"""
        pass

    @property
    @abstractmethod
    def timeout_seconds(self) -> int:
        """超时时间（秒）"""
        pass

    @abstractmethod
    async def on_enter(self, room: "GameRoom") -> None:
        """进入阶段时调用"""
        pass

    @abstractmethod
    async def on_timeout(self, room: "GameRoom") -> None:
        """超时时调用"""
        pass

    async def start_timer(self, room: "GameRoom", timeout: float = None) -> None:
        """启动定时器"""
        timeout = timeout or self.timeout_seconds
        task = asyncio.create_task(self._timer_task(room, timeout))
        room.set_timer(task)

    async def _timer_task(self, room: "GameRoom", timeout: float) -> None:
        """定时器任务"""
        try:
            await asyncio.sleep(timeout)

            # 检查房间是否还存在
            if room.group_id not in self.game_manager.rooms:
                return

            # 检查阶段是否匹配（避免跨阶段误触发）
            if not self._is_current_phase(room):
                return

            logger.info(f"[狼人杀] 群 {room.group_id} {self.name}超时")
            await self.on_timeout(room)

        except asyncio.CancelledError:
            logger.info(f"[狼人杀] 群 {room.group_id} {self.name}定时器已取消")
        except Exception as e:
            logger.error(f"[狼人杀] {self.name}超时处理失败: {e}")

    @abstractmethod
    def _is_current_phase(self, room: "GameRoom") -> bool:
        """检查当前是否是本阶段"""
        pass
