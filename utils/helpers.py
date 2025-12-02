"""工具函数"""
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Player, GameRoom


def format_player_list(players: List["Player"], exclude_ids: Optional[List[str]] = None) -> str:
    """格式化玩家列表"""
    exclude_ids = exclude_ids or []
    lines = []
    for p in players:
        if p.id not in exclude_ids:
            lines.append(f"  • {p.display_name}")
    return "\n".join(lines)


def parse_target(target_str: str, room: "GameRoom") -> Optional[str]:
    """解析目标玩家ID"""
    return room.parse_target(target_str)
