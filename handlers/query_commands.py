"""查询命令处理"""
import os
from typing import TYPE_CHECKING, AsyncGenerator
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .base import BaseCommandHandler
from ..models import GamePhase, Role
from ..roles import RoleFactory

if TYPE_CHECKING:
    from ..services import GameManager


class QueryCommandHandler(BaseCommandHandler):
    """查询命令处理器"""

    def __init__(self, game_manager: "GameManager"):
        super().__init__(game_manager)
        # 使用 AstrBot 数据目录下的临时文件夹
        self.tmp_dir = os.path.join(get_astrbot_data_path(), "werewolf_temp")
        os.makedirs(self.tmp_dir, exist_ok=True)

    async def check_role(self, event: AstrMessageEvent) -> AsyncGenerator:
        """查看角色（返回文本）"""
        player_id = event.get_sender_id()

        if not event.is_private_chat():
            yield event.plain_result("⚠️ 请私聊机器人使用此命令！")
            return

        _, room = self.game_manager.get_room_by_player(player_id)
        if not room:
            yield event.plain_result("❌ 你没有参与任何游戏！")
            return

        player = room.get_player(player_id)
        if not player or not player.role:
            yield event.plain_result("❌ 游戏尚未开始，角色还未分配！")
            return

        # 使用文本输出角色信息
        role_info = RoleFactory.get_role_info(player.role, player, room)
        yield event.plain_result(f"🎭 你的角色是：\n\n{role_info}")

    async def show_status(self, event: AstrMessageEvent) -> AsyncGenerator:
        """显示游戏状态（返回文本）"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有进行中的游戏！")
            return

        # 构建状态文本
        status_text = (
            f"📊 游戏状态\n\n"
            f"阶段：{room.phase.value}\n"
            f"天数：第 {room.day_count} 天\n"
            f"存活人数：{room.alive_count}/{room.player_count}\n\n"
            f"玩家列表：\n"
        )

        for p in room.players:
            status_icon = "✅" if p.is_alive else "💀"
            status_text += f"  {status_icon} {p.number}号 - {p.nickname or f'玩家{p.number}'}\n"

        yield event.plain_result(status_text)

    async def show_help(self, event: AstrMessageEvent) -> AsyncGenerator:
        """显示帮助（返回菜单图片）"""
        config = self.game_manager.config

        # 尝试生成菜单图片
        try:
            from ..draw import draw_menu_image

            image = draw_menu_image(config.total_players)
            output_path = os.path.join(self.tmp_dir, "werewolf_menu.png")
            image.save(output_path)

            yield event.image_result(output_path)
        except Exception as e:
            logger.warning(f"[狼人杀] 生成菜单图片失败: {e}，降级为文本")
            # 降级到文本菜单
            help_text = (
                "📖 狼人杀游戏 - 命令列表\n\n"
                "基础命令：\n"
                "  /创建房间 - 创建游戏房间\n"
                "  /加入房间 - 加入房间\n"
                "  /开始游戏 - 开始游戏（房主）\n"
                "  /查角色 - 查看角色（私聊）\n"
                "  /游戏状态 - 查看游戏状态\n"
                "  /结束游戏 - 结束游戏（房主）\n\n"
                f"游戏命令（使用编号1-{config.total_players}）：\n"
                "  /办掉 编号 - 狼人夜晚办掉（如：/办掉 1）\n"
                "  /密谋 消息 - 狼人与队友交流\n"
                "  /验人 编号 - 预言家查验（如：/验人 3）\n"
                "  /毒人 编号 - 女巫使用毒药（如：/毒人 5）\n"
                "  /救人 - 女巫使用解药\n"
                "  /不操作 - 女巫不使用道具\n"
                "  /开枪 编号 - 猎人开枪带走（如：/开枪 2）\n"
                "  /发言完毕 - 发言说完\n"
                "  /遗言完毕 - 遗言说完\n"
                "  /投票 编号 - 白天投票放逐（如：/投票 2）\n"
                "  /开始投票 - 跳过发言直接投票（房主）\n\n"
                "游戏规则：\n"
                f"• {config.total_players}人局：{config.werewolf_count}狼人 + {config.god_count}神 + {config.villager_count}平民\n"
                f"• 使用编号（1-{config.total_players}号）代替QQ号\n"
                "• 遗言规则：第一晚被狼杀有遗言，投票放逐有遗言，被毒无遗言\n"
                "• 猎人：被狼杀或投票放逐可开枪，被毒不能开枪\n"
                f"• 游戏结束后{'生成AI复盘报告' if config.enable_ai_review else '不生成AI复盘'}\n"
                "• 狼人胜利：好人 ≤ 狼人 或 神职全灭\n"
                "• 好人胜利：狼人全部出局"
            )
            yield event.plain_result(help_text)
