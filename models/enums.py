"""游戏枚举定义"""
from enum import Enum


class GamePhase(Enum):
    """游戏阶段"""
    WAITING = "等待中"
    NIGHT_WOLF = "夜晚-狼人行动"
    NIGHT_SEER = "夜晚-预言家验人"
    NIGHT_WITCH = "夜晚-女巫行动"
    LAST_WORDS = "遗言阶段"
    DAY_SPEAKING = "白天发言"
    DAY_VOTE = "白天投票"
    DAY_PK = "PK发言"
    FINISHED = "已结束"


class Role(Enum):
    """角色枚举"""
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"

    @property
    def display_name(self) -> str:
        """获取角色显示名称"""
        names = {
            Role.WEREWOLF: "狼人",
            Role.SEER: "预言家",
            Role.WITCH: "女巫",
            Role.HUNTER: "猎人",
            Role.VILLAGER: "平民",
        }
        return names.get(self, "未知")

    @property
    def emoji(self) -> str:
        """获取角色emoji"""
        emojis = {
            Role.WEREWOLF: "🐺",
            Role.SEER: "🔮",
            Role.WITCH: "💊",
            Role.HUNTER: "🔫",
            Role.VILLAGER: "👤",
        }
        return emojis.get(self, "❓")

    @property
    def is_god(self) -> bool:
        """是否是神职"""
        return self in (Role.SEER, Role.WITCH, Role.HUNTER)

    @property
    def is_werewolf(self) -> bool:
        """是否是狼人"""
        return self == Role.WEREWOLF

    @property
    def is_good(self) -> bool:
        """是否是好人阵营"""
        return self != Role.WEREWOLF
