"""角色层"""
from .base import BaseRole
from .werewolf import WerewolfRole
from .seer import SeerRole
from .witch import WitchRole, WitchState
from .hunter import HunterRole, HunterState, HunterDeathType
from .villager import VillagerRole
from .factory import RoleFactory

__all__ = [
    "BaseRole",
    "WerewolfRole",
    "SeerRole",
    "WitchRole",
    "WitchState",
    "HunterRole",
    "HunterState",
    "HunterDeathType",
    "VillagerRole",
    "RoleFactory",
]
