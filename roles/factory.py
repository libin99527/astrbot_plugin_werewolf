"""角色工厂"""
from typing import Dict, Type, TYPE_CHECKING
from .base import BaseRole
from .werewolf import WerewolfRole
from .seer import SeerRole
from .witch import WitchRole
from .hunter import HunterRole
from .villager import VillagerRole

if TYPE_CHECKING:
    from ..models import Role


class RoleFactory:
    """角色工厂"""

    _role_classes: Dict["Role", Type[BaseRole]] = {}
    _instances: Dict["Role", BaseRole] = {}

    @classmethod
    def _init_role_classes(cls) -> None:
        """初始化角色类映射"""
        if cls._role_classes:
            return

        from ..models import Role

        cls._role_classes = {
            Role.WEREWOLF: WerewolfRole,
            Role.SEER: SeerRole,
            Role.WITCH: WitchRole,
            Role.HUNTER: HunterRole,
            Role.VILLAGER: VillagerRole,
        }

    @classmethod
    def get(cls, role: "Role") -> BaseRole:
        """获取角色实例（单例）"""
        cls._init_role_classes()

        if role not in cls._instances:
            role_class = cls._role_classes.get(role)
            if role_class:
                cls._instances[role] = role_class()
            else:
                raise ValueError(f"未知角色类型: {role}")

        return cls._instances[role]

    @classmethod
    def get_role_info(cls, role: "Role", player: "Player", room: "GameRoom") -> str:
        """获取角色信息文本"""
        from ..models import Player, GameRoom
        role_instance = cls.get(role)
        return role_instance.get_role_info(player, room)
