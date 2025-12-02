"""禁言管理服务"""
from typing import TYPE_CHECKING
from astrbot.api import logger

if TYPE_CHECKING:
    from ..models import GameRoom


class BanService:
    """禁言管理服务"""

    @staticmethod
    async def ban_player(room: "GameRoom", player_id: str) -> bool:
        """禁言玩家"""
        if not room.bot:
            return False

        try:
            duration = 86400 * room.config.ban_duration_days
            await room.bot.set_group_ban(
                group_id=int(room.group_id),
                user_id=int(player_id),
                duration=duration
            )
            room.banned_player_ids.add(player_id)
            logger.info(f"[狼人杀] 已禁言玩家 {player_id}")
            return True
        except Exception as e:
            logger.error(f"[狼人杀] 禁言玩家 {player_id} 失败: {e}")
            return False

    @staticmethod
    async def unban_player(room: "GameRoom", player_id: str) -> bool:
        """解除禁言"""
        if not room.bot:
            return False

        try:
            await room.bot.set_group_ban(
                group_id=int(room.group_id),
                user_id=int(player_id),
                duration=0
            )
            room.banned_player_ids.discard(player_id)
            logger.info(f"[狼人杀] 已解除禁言 {player_id}")
            return True
        except Exception as e:
            logger.error(f"[狼人杀] 解除禁言 {player_id} 失败: {e}")
            return False

    @staticmethod
    async def unban_all_players(room: "GameRoom") -> None:
        """解除所有禁言"""
        for player_id in list(room.banned_player_ids):
            await BanService.unban_player(room, player_id)
        room.banned_player_ids.clear()

    @staticmethod
    async def set_group_whole_ban(room: "GameRoom", enable: bool) -> bool:
        """设置全员禁言"""
        if not room.bot:
            return False

        try:
            await room.bot.set_group_whole_ban(
                group_id=int(room.group_id),
                enable=enable
            )
            logger.info(f"[狼人杀] 全员禁言状态: {enable}")
            return True
        except Exception as e:
            logger.error(f"[狼人杀] 设置全员禁言失败: {e}")
            return False

    @staticmethod
    async def set_temp_admin(room: "GameRoom", player_id: str) -> bool:
        """设置临时管理员（用于发言）"""
        if not room.bot:
            return False

        try:
            await room.bot.set_group_admin(
                group_id=int(room.group_id),
                user_id=int(player_id),
                enable=True
            )
            room.temp_admin_ids.add(player_id)
            logger.info(f"[狼人杀] 已设置临时管理员 {player_id}")
            return True
        except Exception as e:
            logger.error(f"[狼人杀] 设置临时管理员 {player_id} 失败: {e}")
            return False

    @staticmethod
    async def remove_temp_admin(room: "GameRoom", player_id: str) -> bool:
        """取消临时管理员"""
        if not room.bot:
            return False

        try:
            await room.bot.set_group_admin(
                group_id=int(room.group_id),
                user_id=int(player_id),
                enable=False
            )
            room.temp_admin_ids.discard(player_id)
            logger.info(f"[狼人杀] 已取消临时管理员 {player_id}")
            return True
        except Exception as e:
            logger.error(f"[狼人杀] 取消临时管理员 {player_id} 失败: {e}")
            return False

    @staticmethod
    async def clear_temp_admins(room: "GameRoom") -> None:
        """清除所有临时管理员"""
        for player_id in list(room.temp_admin_ids):
            await BanService.remove_temp_admin(room, player_id)
        room.temp_admin_ids.clear()

    @staticmethod
    async def set_group_card(room: "GameRoom", player_id: str, card: str) -> bool:
        """设置群昵称"""
        if not room.bot:
            return False

        try:
            await room.bot.set_group_card(
                group_id=int(room.group_id),
                user_id=int(player_id),
                card=card
            )
            logger.info(f"[狼人杀] 已将玩家 {player_id} 群昵称改为 {card}")
            return True
        except Exception as e:
            logger.error(f"[狼人杀] 修改玩家 {player_id} 群昵称失败: {e}")
            return False

    @staticmethod
    async def set_player_numbers(room: "GameRoom") -> None:
        """将所有玩家群昵称改为编号"""
        for player in room.players.values():
            new_card = f"{player.number}号"
            await BanService.set_group_card(room, player.id, new_card)

    @staticmethod
    async def restore_player_cards(room: "GameRoom") -> None:
        """恢复所有玩家原始群昵称"""
        for player in room.players.values():
            if player.original_card:
                await BanService.set_group_card(room, player.id, player.original_card)
