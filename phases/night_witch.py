"""夜晚-女巫行动阶段"""
import random
from typing import TYPE_CHECKING
from astrbot.api import logger

from .base import BasePhase
from ..models import GamePhase, Role
from ..roles import HunterDeathType
from ..services import BanService
from ..roles import WitchRole

if TYPE_CHECKING:
    from ..models import GameRoom


class NightWitchPhase(BasePhase):
    """女巫行动阶段"""

    @property
    def name(self) -> str:
        return "女巫行动阶段"

    @property
    def timeout_seconds(self) -> int:
        return self.game_manager.config.timeout_witch

    def _is_current_phase(self, room: "GameRoom") -> bool:
        return room.phase == GamePhase.NIGHT_WITCH

    async def on_enter(self, room: "GameRoom") -> None:
        """进入女巫行动阶段"""
        room.phase = GamePhase.NIGHT_WITCH
        room.witch_state.reset_night()

        witch = room.get_witch()

        # 如果游戏中没有女巫角色，直接跳过
        if not witch:
            logger.info(f"[狼人杀] 群 {room.group_id} 没有女巫角色，跳过女巫阶段")
            await self._finish_night(room)
            return

        # 发送群提示
        await self.message_service.announce_witch_phase(room)

        # 给女巫发私聊
        await self._notify_witch(room)

        # 计算等待时间
        wait_time = self._calculate_wait_time(room)

        # 启动定时器
        await self.start_timer(room, wait_time)

    def _calculate_wait_time(self, room: "GameRoom") -> float:
        """计算等待时间"""
        witch = room.get_witch()
        if not witch:
            return random.uniform(
                self.game_manager.config.timeout_dead_min,
                self.game_manager.config.timeout_dead_max
            )

        # 女巫存活，或今晚被杀（可以救自己）
        witch_alive = witch.is_alive
        witch_killed_tonight = (room.last_killed_id == witch.id)

        if witch_alive or witch_killed_tonight:
            return self.timeout_seconds
        else:
            return random.uniform(
                self.game_manager.config.timeout_dead_min,
                self.game_manager.config.timeout_dead_max
            )

    async def _notify_witch(self, room: "GameRoom") -> None:
        """通知女巫"""
        witch = room.get_witch()
        if not witch:
            return

        # 女巫存活 或 今晚被杀（可以救自己）时才通知
        witch_killed_tonight = (room.last_killed_id == witch.id)
        if not witch.is_alive and not witch_killed_tonight:
            return

        # 使用角色类生成提示
        witch_role = WitchRole()
        prompt = witch_role.get_action_prompt(room)

        await self.message_service.send_private_message(room, witch.id, prompt)
        logger.info(f"[狼人杀] 已告知女巫 {witch.id} 夜晚信息")

    async def on_timeout(self, room: "GameRoom") -> None:
        """女巫行动超时"""
        room.witch_state.has_acted = True

        # 只有女巫存活时才发送超时提示
        if room.is_witch_alive():
            await self.message_service.announce_timeout(room, "女巫行动")

        await self._finish_night(room)

    async def on_acted(self, room: "GameRoom") -> None:
        """女巫行动完成"""
        room.cancel_timer()
        await self._finish_night(room)

    async def _finish_night(self, room: "GameRoom") -> None:
        """结束夜晚，进入白天"""
        logger.info(f"[狼人杀] 群 {room.group_id} 开始结束夜晚流程")

        # 处理女巫行动结果
        await self.game_manager.process_witch_action(room)
        logger.info(f"[狼人杀] 群 {room.group_id} 女巫行动处理完成")

        # 处理猎人死亡
        await self._handle_hunter_death(room)
        logger.info(f"[狼人杀] 群 {room.group_id} 猎人死亡处理完成，pending_shot={room.hunter_state.pending_shot_player_id}")

        # 发送天亮消息
        await self._announce_dawn(room)
        logger.info(f"[狼人杀] 群 {room.group_id} 天亮消息发送完成")

        # 检查猎人是否需要开枪（猎人开枪优先于胜负判定）
        if room.hunter_state.pending_shot_player_id:
            logger.info(f"[狼人杀] 群 {room.group_id} 等待猎人开枪")
            await self._wait_for_hunter_shot(room)
            return

        # 猎人不需要开枪时，检查游戏是否结束
        logger.info(f"[狼人杀] 群 {room.group_id} 检查胜负")
        if await self.game_manager.check_and_handle_victory(room):
            logger.info(f"[狼人杀] 群 {room.group_id} 游戏结束")
            return

        # 进入白天流程
        logger.info(f"[狼人杀] 群 {room.group_id} 进入白天阶段")
        await self._enter_day_phase(room)

    async def _handle_hunter_death(self, room: "GameRoom") -> None:
        """处理猎人死亡"""
        witch_state = room.witch_state

        # 被毒的猎人不能开枪
        if witch_state.poisoned_player_id:
            poisoned_player = room.get_player(witch_state.poisoned_player_id)
            if poisoned_player and poisoned_player.role == Role.HUNTER:
                room.hunter_state.death_type = HunterDeathType.POISON

        # 被狼杀的猎人可以开枪（未被救的情况）
        if room.last_killed_id and not witch_state.saved_player_id:
            killed_player = room.get_player(room.last_killed_id)
            if killed_player and killed_player.role == Role.HUNTER:
                room.hunter_state.pending_shot_player_id = room.last_killed_id
                room.hunter_state.death_type = HunterDeathType.WOLF

    async def _announce_dawn(self, room: "GameRoom") -> None:
        """公告天亮"""
        killed_name = None
        poisoned_name = None
        saved = bool(room.witch_state.saved_player_id)

        if room.last_killed_id and not saved:
            killed_player = room.get_player(room.last_killed_id)
            if killed_player:
                killed_name = killed_player.display_name

        if room.witch_state.poisoned_player_id:
            poisoned_player = room.get_player(room.witch_state.poisoned_player_id)
            if poisoned_player:
                poisoned_name = poisoned_player.display_name

        await self.message_service.announce_dawn(room, killed_name, saved, poisoned_name)

    async def _wait_for_hunter_shot(self, room: "GameRoom") -> None:
        """等待猎人开枪"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)
        await phase_manager.wait_for_hunter_shot(room, "wolf")

    async def _enter_day_phase(self, room: "GameRoom") -> None:
        """进入白天阶段"""
        from .phase_manager import PhaseManager
        phase_manager = PhaseManager(self.game_manager)

        # 第一晚被杀有遗言
        if room.is_first_night and room.last_killed_id:
            await phase_manager.enter_last_words_phase(room)
        else:
            # 禁言死亡玩家
            if room.last_killed_id:
                await BanService.ban_player(room, room.last_killed_id)
            if room.witch_state.poisoned_player_id:
                await BanService.ban_player(room, room.witch_state.poisoned_player_id)

            room.end_first_night()
            await phase_manager.enter_speaking_phase(room)
