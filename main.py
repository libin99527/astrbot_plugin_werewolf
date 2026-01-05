"""
狼人杀游戏插件
游戏规则：9人局（3狼人 + 3神 + 3平民）
神职：预言家 + 女巫 + 猎人
流程：创建房间 → 分配角色 → 夜晚（狼人办掉→预言家验人→女巫行动） → 白天投票 → 判断胜负
"""
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.star.filter.permission import PermissionType

from .models import GameConfig
from .services import GameManager
from .handlers import (
    RoomCommandHandler,
    NightCommandHandler,
    DayCommandHandler,
    QueryCommandHandler,
)
from .utils import set_command_prefix


@register("astrbot_plugin_werewolf", "miao", "狼人杀游戏（3狼3神3平民+AI复盘+AI玩家）", "v3.0.2")
class WerewolfPlugin(Star):
    """狼人杀插件"""

    def __init__(self, context: Context, config: dict = None, *args, **kwargs):
        super().__init__(context)
        self.context = context

        # 从 AstrBot 配置读取命令前缀
        self._init_command_prefix()

        # 加载配置
        config = config or {}
        self.game_config = self._load_config(config)

        # 初始化游戏管理器
        self.game_manager = GameManager(context, self.game_config)

        # 初始化命令处理器
        self.room_handler = RoomCommandHandler(self.game_manager)
        self.night_handler = NightCommandHandler(self.game_manager)
        self.day_handler = DayCommandHandler(self.game_manager)
        self.query_handler = QueryCommandHandler(self.game_manager)

        # 日志
        self._log_startup()

    def _init_command_prefix(self) -> None:
        """从 AstrBot 配置读取命令前缀"""
        try:
            astrbot_config = self.context.get_config()
            wake_prefixes = astrbot_config.get("wake_prefix", ["/"])
            # 使用第一个前缀作为命令前缀
            prefix = wake_prefixes[0] if wake_prefixes else "/"
            set_command_prefix(prefix)
            logger.debug(f"[狼人杀] 命令前缀设置为: {prefix}")
        except Exception as e:
            logger.warning(f"[狼人杀] 读取命令前缀失败，使用默认值 '/': {e}")
            set_command_prefix("/")

    def _load_config(self, config: dict) -> GameConfig:
        """加载并验证配置"""
        game_config = GameConfig.from_dict(config)

        if not game_config.validate():
            logger.warning(
                f"[狼人杀] 角色配置不匹配！使用默认配置：9人局（3狼3神3平民）"
            )
            game_config = GameConfig.default()

        return game_config

    def _log_startup(self) -> None:
        """打印启动日志"""
        config = self.game_config
        ai_status = "已关闭" if not config.enable_ai_review else (
            f"{config.ai_review_model if config.ai_review_model else '默认模型'}"
            f"{' (自定义提示词)' if config.ai_review_prompt else ''}"
        )
        logger.info(
            f"[狼人杀] 插件已加载 | "
            f"游戏配置：{config.total_players}人局"
            f"({config.werewolf_count}狼{config.god_count}神{config.villager_count}民) | "
            f"AI复盘：{ai_status}"
        )

    # ==================== 房间管理命令 ====================

    @filter.command("创建房间")
    async def create_room(self, event: AstrMessageEvent):
        """创建游戏房间"""
        async for result in self.room_handler.create_room(event):
            yield result

    @filter.command("加入房间")
    async def join_room(self, event: AstrMessageEvent):
        """加入游戏"""
        async for result in self.room_handler.join_room(event):
            yield result

    @filter.command("加人房间")
    async def join_room_alias1(self, event: AstrMessageEvent):
        """加入游戏（别名）"""
        async for result in self.room_handler.join_room(event):
            yield result

    @filter.command("加入")
    async def join_room_alias2(self, event: AstrMessageEvent):
        """加入游戏（别名）"""
        async for result in self.room_handler.join_room(event):
            yield result

    @filter.command("加人")
    async def join_room_alias3(self, event: AstrMessageEvent):
        """加入游戏（别名）"""
        async for result in self.room_handler.join_room(event):
            yield result

    @filter.permission_type(PermissionType.ADMIN)
    @filter.regex(r"^[/／]?(.+?)加入$")
    async def ai_join_room(self, event: AstrMessageEvent):
        """AI玩家加入游戏（管理员专用），支持格式：/小咪加入 或 小咪加入"""
        async for result in self.room_handler.ai_join_room(event):
            yield result

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("踢出AI")
    async def kick_ai_player(self, event: AstrMessageEvent):
        """踢出AI玩家（管理员专用）"""
        async for result in self.room_handler.kick_ai_player(event):
            yield result

    @filter.command("开始游戏")
    async def start_game(self, event: AstrMessageEvent):
        """开始游戏（房主专用）"""
        async for result in self.room_handler.start_game(event):
            yield result

    @filter.command("结束游戏")
    async def end_game(self, event: AstrMessageEvent):
        """强制结束游戏（房主专用）"""
        async for result in self.room_handler.end_game(event):
            yield result

    # ==================== 夜晚命令 ====================

    @filter.command("办掉")
    async def werewolf_kill(self, event: AstrMessageEvent):
        """狼人夜晚办掉目标"""
        async for result in self.night_handler.werewolf_kill(event):
            yield result

    @filter.command("密谋")
    async def werewolf_chat(self, event: AstrMessageEvent):
        """狼人队友之间交流（私聊）"""
        async for result in self.night_handler.werewolf_chat(event):
            yield result

    @filter.command("验人")
    async def seer_check(self, event: AstrMessageEvent):
        """预言家夜晚验人"""
        async for result in self.night_handler.seer_check(event):
            yield result

    @filter.command("救人")
    async def witch_save(self, event: AstrMessageEvent):
        """女巫使用解药救人"""
        async for result in self.night_handler.witch_save(event):
            yield result

    @filter.command("毒人")
    async def witch_poison(self, event: AstrMessageEvent):
        """女巫使用毒药毒人"""
        async for result in self.night_handler.witch_poison(event):
            yield result

    @filter.command("不操作")
    async def witch_pass(self, event: AstrMessageEvent):
        """女巫选择不操作"""
        async for result in self.night_handler.witch_pass(event):
            yield result

    @filter.command("开枪")
    async def hunter_shoot(self, event: AstrMessageEvent):
        """猎人开枪（私聊）"""
        async for result in self.night_handler.hunter_shoot(event):
            yield result

    # ==================== 白天命令 ====================

    @filter.command("遗言完毕")
    async def finish_last_words(self, event: AstrMessageEvent):
        """被杀玩家遗言完毕"""
        async for result in self.day_handler.finish_last_words(event):
            yield result

    @filter.command("发言完毕")
    async def finish_speaking(self, event: AstrMessageEvent):
        """当前发言者发言完毕"""
        async for result in self.day_handler.finish_speaking(event):
            yield result

    @filter.command("开始投票")
    async def start_vote(self, event: AstrMessageEvent):
        """跳过发言直接进入投票阶段（房主专用）"""
        async for result in self.day_handler.start_vote(event):
            yield result

    @filter.command("投票")
    async def day_vote(self, event: AstrMessageEvent):
        """白天投票放逐"""
        async for result in self.day_handler.day_vote(event):
            yield result

    # ==================== 查询命令 ====================

    @filter.command("查角色")
    async def check_role(self, event: AstrMessageEvent):
        """查看自己的角色（私聊）"""
        async for result in self.query_handler.check_role(event):
            yield result

    @filter.command("游戏状态")
    async def show_status(self, event: AstrMessageEvent):
        """查看游戏状态"""
        async for result in self.query_handler.show_status(event):
            yield result

    @filter.command("狼人杀帮助")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        async for result in self.query_handler.show_help(event):
            yield result

    # ==================== 事件监听 ====================

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def capture_speech(self, event: AstrMessageEvent):
        """捕获发言阶段和遗言阶段的玩家发言"""
        await self.day_handler.capture_speech(event)

    async def terminate(self):
        """插件终止时"""
        # 清理所有房间
        for group_id in list(self.game_manager.rooms.keys()):
            await self.game_manager.cleanup_room(group_id)
        logger.info("[狼人杀] 插件已终止")
