"""角色基类"""
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Player, GameRoom, Role


class BaseRole(ABC):
    """角色基类"""

    @property
    @abstractmethod
    def role_type(self) -> "Role":
        """角色类型"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """角色名称"""
        pass

    @property
    @abstractmethod
    def emoji(self) -> str:
        """角色emoji"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """角色描述"""
        pass

    @property
    @abstractmethod
    def goal(self) -> str:
        """角色目标"""
        pass

    @abstractmethod
    def get_role_info(self, player: "Player", room: "GameRoom") -> str:
        """获取角色信息文本（用于游戏开始时私聊）"""
        pass

    @abstractmethod
    def get_night_commands(self) -> List[str]:
        """获取夜晚可用命令"""
        pass

    def format_player_list(self, players: List["Player"], exclude_ids: Optional[List[str]] = None) -> str:
        """格式化玩家列表"""
        exclude_ids = exclude_ids or []
        lines = []
        for p in players:
            if p.id not in exclude_ids:
                lines.append(f"  • {p.display_name}")
        return "\n".join(lines)
