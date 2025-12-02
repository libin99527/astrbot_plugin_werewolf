"""房间管理命令"""
from typing import TYPE_CHECKING, AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from .base import BaseCommandHandler
from ..models import GamePhase

if TYPE_CHECKING:
    from ..services import GameManager


class RoomCommandHandler(BaseCommandHandler):
    """房间管理命令处理器"""

    async def create_room(self, event: AstrMessageEvent) -> AsyncGenerator:
        """创建房间"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("⚠️ 请在群聊中使用此命令！")
            return

        if self.game_manager.room_exists(group_id):
            yield event.plain_result("❌ 当前群已存在游戏房间！请先结束现有游戏。")
            return

        # 创建房间
        room = self.game_manager.create_room(
            group_id=group_id,
            creator_id=event.get_sender_id(),
            msg_origin=event.unified_msg_origin,
            bot=event.bot
        )

        config = self.game_manager.config
        yield event.plain_result(
            f"✅ 狼人杀房间创建成功！\n\n"
            f"📋 游戏规则：\n"
            f"• {config.total_players}人局（{config.werewolf_count}狼人 + {config.god_count}神 + {config.villager_count}平民）\n"
            f"• 神职：{config.get_role_description()}\n"
            f"• 夜晚：狼人办掉 → 预言家验人 → 女巫行动\n"
            f"• 白天：遗言 → 发言 → 投票放逐\n"
            f"• 遗言规则：第一晚被狼杀有遗言，投票放逐有遗言，被毒无遗言\n"
            f"• 猎人：被狼杀或投票放逐可开枪，被毒不能开枪\n"
            f"• 游戏结束后生成AI复盘报告\n\n"
            f"💡 使用 /加入房间 来参与游戏\n"
            f"👥 {config.total_players}人齐全后，房主使用 /开始游戏"
        )

    async def join_room(self, event: AstrMessageEvent) -> AsyncGenerator:
        """加入房间"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("⚠️ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群未创建房间！请使用 /创建房间")
            return

        if room.phase != GamePhase.WAITING:
            yield event.plain_result("❌ 游戏已开始，无法加入！")
            return

        player_id = event.get_sender_id()
        if room.is_player_in_room(player_id):
            yield event.plain_result("⚠️ 你已经在游戏中了！")
            return

        if room.is_full:
            yield event.plain_result(f"❌ 房间已满（{room.player_count}/{self.game_manager.config.total_players}）！")
            return

        # 获取玩家昵称
        player_name = self.get_player_name(event)

        # 加入房间
        self.game_manager.add_player(room, player_id, player_name)

        yield event.plain_result(
            f"✅ 成功加入游戏！\n\n"
            f"当前人数：{room.player_count}/{self.game_manager.config.total_players}"
        )

    async def start_game(self, event: AstrMessageEvent) -> AsyncGenerator:
        """开始游戏"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有创建的房间！")
            return

        # 验证房主
        if event.get_sender_id() != room.creator_id:
            yield event.plain_result("⚠️ 只有房主才能开始游戏！")
            return

        # 验证人数
        if room.player_count != self.game_manager.config.total_players:
            yield event.plain_result(
                f"❌ 人数不足！当前 {room.player_count}/{self.game_manager.config.total_players} 人"
            )
            return

        if room.phase != GamePhase.WAITING:
            yield event.plain_result("❌ 游戏已经开始！")
            return

        # 公告游戏开始
        yield event.plain_result(
            "🌙 游戏开始！天黑请闭眼...\n\n"
            "角色已分配完毕！\n\n"
            "机器人正在私聊告知各位身份...\n"
            "如未收到私聊，请使用：/查角色\n\n"
            "🐺 狼人请私聊使用：/办掉 编号\n"
            "🔮 预言家请等待狼人行动完成后使用：/验人 编号\n"
            "⏰ 剩余时间：2分钟"
        )

        # 开始游戏
        await self.game_manager.start_game(room)

        # 启动狼人阶段定时器
        from ..phases import NightWolfPhase
        wolf_phase = NightWolfPhase(self.game_manager)
        await wolf_phase.start_timer(room)

    async def end_game(self, event: AstrMessageEvent) -> AsyncGenerator:
        """强制结束游戏"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有进行中的游戏！")
            return

        if event.get_sender_id() != room.creator_id:
            yield event.plain_result("⚠️ 只有房主才能结束游戏！")
            return

        await self.game_manager.cleanup_room(group_id)
        yield event.plain_result("✅ 游戏已强制结束！")
