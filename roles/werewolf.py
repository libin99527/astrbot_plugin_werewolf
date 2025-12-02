"""狼人角色"""
from typing import List, TYPE_CHECKING
from .base import BaseRole

if TYPE_CHECKING:
    from ..models import Player, GameRoom, Role


class WerewolfRole(BaseRole):
    """狼人角色"""

    @property
    def role_type(self) -> "Role":
        from ..models import Role
        return Role.WEREWOLF

    @property
    def name(self) -> str:
        return "狼人"

    @property
    def emoji(self) -> str:
        return "🐺"

    @property
    def description(self) -> str:
        return "每晚可以与队友商量后选择杀死一名玩家"

    @property
    def goal(self) -> str:
        return "消灭所有好人"

    def get_role_info(self, player: "Player", room: "GameRoom") -> str:
        """获取狼人角色信息"""
        # 找到队友
        werewolves = room.get_werewolves()
        teammates = [w for w in werewolves if w.id != player.id]

        # 队友信息
        teammate_info = ""
        if teammates:
            teammate_names = ", ".join([t.display_name for t in teammates])
            teammate_info = f"\n\n🤝 你的队友：{teammate_names}"

        # 可选目标（非狼人）
        other_players = [p for p in room.players.values() if not p.is_werewolf]
        players_list = self.format_player_list(other_players)

        return (
            f"🎭 游戏开始！你的角色是：\n\n"
            f"{self.emoji} {self.name}\n\n"
            f"你的目标：{self.goal}！{teammate_info}\n\n"
            f"📋 可选目标列表：\n{players_list}\n\n"
            f"💡 夜晚私聊使用命令：\n"
            f"  /办掉 编号 - 投票办掉目标\n"
            f"  /密谋 消息 - 与队友交流\n"
            f"示例：/办掉 1"
        )

    def get_night_commands(self) -> List[str]:
        return ["/办掉 编号", "/密谋 消息"]
