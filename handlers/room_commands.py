"""房间管理命令"""
import re
from typing import TYPE_CHECKING, AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from .base import BaseCommandHandler
from ..models import GamePhase, AIPlayerConfig
from ..utils import cmd

if TYPE_CHECKING:
    from ..services import GameManager


class RoomCommandHandler(BaseCommandHandler):
    """房间管理命令处理器"""

    # AI玩家名称黑名单（避免与命令冲突）
    AI_NAME_BLACKLIST = {"加入房间", "创建房间", "开始游戏", "结束游戏", "投票", "办掉", "验人", "救人", "毒人", "开枪", "房间"}

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
            f"💡 使用 {cmd('加入房间')} 来参与游戏\n"
            f"🤖 使用 {cmd('（机器人名字）加入')} 让AI玩家加入\n"
            f"👥 {config.total_players}人齐全后，房主使用 {cmd('开始游戏')}"
        )

    async def join_room(self, event: AstrMessageEvent) -> AsyncGenerator:
        """加入房间"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("⚠️ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result(f"❌ 当前群未创建房间！请使用 {cmd('创建房间')}")
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
            f"如未收到私聊，请使用：{cmd('查角色')}\n\n"
            f"🐺 狼人请私聊使用：{cmd('办掉')} 编号\n"
            f"🔮 预言家请等待狼人行动完成后使用：{cmd('验人')} 编号\n"
            "⏰ 剩余时间：2分钟"
        )

        # 开始游戏
        await self.game_manager.start_game(room)

        # 进入狼人行动阶段（会根据是否有人类狼人决定处理逻辑）
        from ..phases import NightWolfPhase
        wolf_phase = NightWolfPhase(self.game_manager)
        await wolf_phase.on_enter(room)

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

    async def ai_join_room(self, event: AstrMessageEvent) -> AsyncGenerator:
        """AI玩家加入房间"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("⚠️ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result(f"❌ 当前群未创建房间！请使用 {cmd('创建房间')}")
            return

        if room.phase != GamePhase.WAITING:
            yield event.plain_result("❌ 游戏已开始，无法加入！")
            return

        if room.is_full:
            yield event.plain_result(f"❌ 房间已满（{room.player_count}/{self.game_manager.config.total_players}）！")
            return

        # 从消息中提取AI名称
        message_text = event.message_str.strip()
        # 匹配 /xxx加入 或 xxx加入 格式
        match = re.match(r'^[/／]?(.+?)加入$', message_text)
        if not match:
            yield event.plain_result(f"❌ 无法识别AI名称！\n使用格式：{cmd('小咪加入')}")
            return

        ai_name = match.group(1).strip()

        # 验证名称
        if not ai_name:
            yield event.plain_result("❌ AI名称不能为空！")
            return

        if len(ai_name) > 10:
            yield event.plain_result("❌ AI名称不能超过10个字符！")
            return

        if ai_name in self.AI_NAME_BLACKLIST:
            yield event.plain_result(f"❌ '{ai_name}' 是保留名称，请换一个！")
            return

        # 检查是否已有同名AI
        ai_player_id = f"ai_{ai_name}"
        if room.is_player_in_room(ai_player_id):
            yield event.plain_result(f"⚠️ AI玩家 {ai_name} 已经在游戏中了！")
            return

        # 创建AI玩家配置（使用全局配置的模型）
        ai_config = AIPlayerConfig(
            name=ai_name,
            model_id=self.game_manager.config.ai_player_model
        )

        # 添加AI玩家
        ai_player = self.game_manager.add_ai_player(room, ai_name, ai_config)

        yield event.plain_result(
            f"{ai_player.name} 加入游戏！\n\n"
            f"当前人数：{room.player_count}/{self.game_manager.config.total_players}"
        )

    async def kick_ai_player(self, event: AstrMessageEvent) -> AsyncGenerator:
        """踢出AI玩家"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有创建的房间！")
            return

        if room.phase != GamePhase.WAITING:
            yield event.plain_result("❌ 游戏已开始，无法踢出玩家！")
            return

        # 获取要踢出的AI名称
        target_str = ""
        for seg in event.get_messages():
            if hasattr(seg, 'text'):
                # 提取命令后的参数
                text = seg.text.strip()
                match = re.match(r'^[/／]?踢出AI\s*(.*)$', text)
                if match:
                    target_str = match.group(1).strip()
                    break

        if not target_str:
            # 列出所有AI玩家
            ai_players = [p for p in room.players.values() if p.is_ai]
            if not ai_players:
                yield event.plain_result("❌ 当前房间没有AI玩家！")
                return

            ai_list = "\n".join([f"  • {p.name}" for p in ai_players])
            yield event.plain_result(
                f"❌ 请指定要踢出的AI名称！\n\n"
                f"当前AI玩家：\n{ai_list}\n\n"
                f"使用格式：{cmd('踢出AI')} 小咪"
            )
            return

        # 查找AI玩家
        ai_player_id = f"ai_{target_str}"
        player = room.get_player(ai_player_id)

        if not player:
            yield event.plain_result(f"❌ 未找到AI玩家：{target_str}")
            return

        if not player.is_ai:
            yield event.plain_result(f"❌ {target_str} 不是AI玩家！")
            return

        # 移除玩家
        del room.players[ai_player_id]

        yield event.plain_result(
            f"✅ AI玩家 {target_str} 已被踢出！\n\n"
            f"当前人数：{room.player_count}/{self.game_manager.config.total_players}"
        )
