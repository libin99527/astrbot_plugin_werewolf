"""命令处理基类"""
import re
from typing import TYPE_CHECKING, Optional
from astrbot.api.event import AstrMessageEvent
from astrbot.core.message.components import At

if TYPE_CHECKING:
    from ..services import GameManager


class BaseCommandHandler:
    """命令处理基类"""

    def __init__(self, game_manager: "GameManager"):
        self.game_manager = game_manager
        self.message_service = game_manager.message_service

    def get_at_user(self, event: AstrMessageEvent) -> str:
        """获取消息中@的第一个用户ID"""
        for seg in event.get_messages():
            if isinstance(seg, At):
                return str(seg.qq)
        return ""

    def get_target_user(self, event: AstrMessageEvent) -> str:
        """获取目标用户ID（支持@、编号和QQ号）"""
        # 方式1：从@中提取
        target = self.get_at_user(event)
        if target:
            return target

        # 方式2：从消息文本中提取数字
        for seg in event.get_messages():
            if hasattr(seg, 'text'):
                match = re.search(r'\b(\d+)\b', seg.text)
                if match:
                    return match.group(1)

        return ""

    def get_player_name(self, event: AstrMessageEvent) -> str:
        """获取玩家昵称"""
        try:
            player_name = None

            # 方法1：从unified_msg_origin获取
            if hasattr(event, 'unified_msg_origin') and event.unified_msg_origin:
                msg_origin = event.unified_msg_origin
                if hasattr(msg_origin, 'sender') and msg_origin.sender:
                    sender = msg_origin.sender
                    player_name = getattr(sender, 'card', None) or getattr(sender, 'nickname', None)

            # 方法2：从event.sender获取
            if not player_name and hasattr(event, 'sender'):
                sender = event.sender
                if isinstance(sender, dict):
                    player_name = sender.get('card') or sender.get('nickname') or sender.get('name')
                else:
                    player_name = getattr(sender, 'card', None) or getattr(sender, 'nickname', None)

            # 方法3：使用message_obj
            if not player_name and hasattr(event, 'message_obj'):
                msg_obj = event.message_obj
                if hasattr(msg_obj, 'sender'):
                    sender = msg_obj.sender
                    player_name = getattr(sender, 'card', None) or getattr(sender, 'nickname', None)

            # 兜底
            if not player_name:
                player_id = event.get_sender_id()
                player_name = f"玩家{player_id[-4:]}"

            return player_name
        except Exception:
            player_id = event.get_sender_id()
            return f"玩家{player_id[-4:]}"
