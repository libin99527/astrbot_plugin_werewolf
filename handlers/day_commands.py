"""白天命令处理"""
from typing import TYPE_CHECKING, AsyncGenerator
from astrbot.api.event import AstrMessageEvent

from .base import BaseCommandHandler
from ..models import GamePhase
from ..utils import cmd

if TYPE_CHECKING:
    from ..services import GameManager


class DayCommandHandler(BaseCommandHandler):
    """白天命令处理器"""

    async def finish_last_words(self, event: AstrMessageEvent) -> AsyncGenerator:
        """遗言完毕"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有进行中的游戏！")
            return

        player_id = event.get_sender_id()

        if room.phase != GamePhase.LAST_WORDS:
            yield event.plain_result("⚠️ 现在不是遗言阶段！")
            return

        if room.last_killed_id != player_id:
            yield event.plain_result("⚠️ 只有被杀的玩家才能使用此命令！")
            return

        yield event.plain_result("✅ 遗言完毕！")

        from ..phases import LastWordsPhase
        last_words_phase = LastWordsPhase(self.game_manager)
        await last_words_phase.on_finish(room)

    async def finish_speaking(self, event: AstrMessageEvent) -> AsyncGenerator:
        """发言完毕"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有进行中的游戏！")
            return

        player_id = event.get_sender_id()

        if room.phase not in (GamePhase.DAY_SPEAKING, GamePhase.DAY_PK):
            yield event.plain_result("⚠️ 现在不是发言阶段！")
            return

        if room.speaking_state.current_speaker_id != player_id:
            yield event.plain_result("⚠️ 现在不是你的发言时间！")
            return

        yield event.plain_result("✅ 发言完毕！")

        from ..phases import DaySpeakingPhase
        speaking_phase = DaySpeakingPhase(self.game_manager)
        await speaking_phase.on_finish_speaking(room)

    async def start_vote(self, event: AstrMessageEvent) -> AsyncGenerator:
        """跳过发言进入投票"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有进行中的游戏！")
            return

        if event.get_sender_id() != room.creator_id:
            yield event.plain_result("⚠️ 只有房主才能跳过发言环节！")
            return

        if room.phase not in (GamePhase.DAY_SPEAKING, GamePhase.DAY_PK):
            yield event.plain_result("⚠️ 现在不是发言阶段！")
            return

        # 取消定时器
        room.cancel_timer()

        # 取消当前发言者管理员
        from ..services import BanService
        if room.speaking_state.current_speaker_id:
            await BanService.remove_temp_admin(room, room.speaking_state.current_speaker_id)

        yield event.plain_result("✅ 房主跳过发言环节，直接进入投票！")

        from ..phases import PhaseManager
        phase_manager = PhaseManager(self.game_manager)

        if room.phase == GamePhase.DAY_PK:
            await phase_manager.enter_pk_vote_phase(room)
        else:
            await phase_manager.enter_vote_phase(room)

    async def day_vote(self, event: AstrMessageEvent) -> AsyncGenerator:
        """投票放逐"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 请在群聊中使用此命令！")
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            yield event.plain_result("❌ 当前群没有进行中的游戏！")
            return

        player_id = event.get_sender_id()

        if room.phase != GamePhase.DAY_VOTE:
            yield event.plain_result(f"⚠️ 现在不是投票阶段！使用 {cmd('开始投票')} 进入投票")
            return

        if not room.is_player_in_room(player_id):
            yield event.plain_result("❌ 你不在游戏中！")
            return

        if not room.is_player_alive(player_id):
            yield event.plain_result("❌ 你已经出局了！")
            return

        # 获取目标
        target_str = self.get_target_user(event)
        if not target_str:
            yield event.plain_result(f"❌ 请指定投票目标！\n使用：{cmd('投票')} 编号\n示例：{cmd('投票')} 2")
            return

        target_id = room.parse_target(target_str)
        if not target_id:
            yield event.plain_result(f"❌ 无效的目标：{target_str}\n请使用玩家编号（1-9）")
            return

        if not room.is_player_alive(target_id):
            yield event.plain_result("❌ 目标玩家已经出局！")
            return

        # PK投票限制
        if room.vote_state.is_pk_vote:
            if target_id not in room.vote_state.pk_players:
                pk_names = []
                for pid in room.vote_state.pk_players:
                    p = room.get_player(pid)
                    if p:
                        pk_names.append(p.display_name)
                yield event.plain_result(
                    f"❌ PK投票只能投给平票玩家！\n\n"
                    f"可投票对象：\n" + "\n".join([f"  • {name}" for name in pk_names])
                )
                return

        # 记录投票
        room.vote_state.day_votes[player_id] = target_id

        # 记录日志
        voter = room.get_player(player_id)
        target = room.get_player(target_id)
        is_pk = room.vote_state.is_pk_vote
        if is_pk:
            room.log(f"🗳️ PK投票：{voter.display_name} 投给 {target.display_name}")
        else:
            room.log(f"🗳️ {voter.display_name} 投票给 {target.display_name}")

        # 同步投票到所有AI玩家上下文
        for p in room.players.values():
            if p.is_ai and p.ai_context:
                p.ai_context.add_vote(voter.display_name, target.display_name, is_pk)

        yield event.plain_result(
            f"✅ 投票成功！当前已投票 {len(room.vote_state.day_votes)}/{room.alive_count} 人"
        )

        # 检查是否所有人都投票了
        if len(room.vote_state.day_votes) >= room.alive_count:
            from ..phases import DayVotePhase
            vote_phase = DayVotePhase(self.game_manager)
            await vote_phase.on_all_voted(room)

    async def capture_speech(self, event: AstrMessageEvent) -> None:
        """捕获发言内容（非命令消息）"""
        group_id = event.get_group_id()
        if not group_id:
            return

        room = self.game_manager.get_room(group_id)
        if not room:
            return

        player_id = event.get_sender_id()
        message_text = event.get_message_outline()

        # 排除命令
        from ..utils import get_command_prefix
        if message_text.startswith(get_command_prefix()):
            return

        if not message_text.strip():
            return

        # 投票阶段：监听所有人的讨论
        if room.phase == GamePhase.DAY_VOTE:
            player = room.get_player(player_id)
            if player and player.is_alive:
                # 记录到投票讨论
                if not hasattr(room, 'vote_discussion'):
                    room.vote_discussion = []
                room.vote_discussion.append({
                    "player": player.display_name,
                    "content": message_text[:100]  # 限制长度
                })
                # 同步投票讨论到所有AI上下文（实时，使用专门的投票讨论字段）
                for p in room.players.values():
                    if p.is_ai and p.ai_context:
                        p.ai_context.add_vote_discussion(player.display_name, message_text[:120])
            return

        # 发言阶段和遗言阶段：只记录当前发言者
        if room.phase not in (GamePhase.DAY_SPEAKING, GamePhase.DAY_PK, GamePhase.LAST_WORDS):
            return

        # 检查是否是当前发言者/遗言者
        if room.phase == GamePhase.LAST_WORDS:
            if room.last_killed_id != player_id:
                return
        else:
            if room.speaking_state.current_speaker_id != player_id:
                return

        # 记录发言
        room.speaking_state.current_speech.append(message_text)
