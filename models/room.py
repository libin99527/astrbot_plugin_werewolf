"""游戏房间数据模型"""
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Any, TYPE_CHECKING
import asyncio
from .enums import GamePhase, Role
from .player import Player
from .config import GameConfig

if TYPE_CHECKING:
    from ..roles import WitchState, HunterState


@dataclass
class VoteState:
    """投票状态"""
    night_votes: Dict[str, str] = field(default_factory=dict)  # 夜晚投票 {狼人ID: 目标ID}
    day_votes: Dict[str, str] = field(default_factory=dict)    # 白天投票 {玩家ID: 目标ID}
    pk_players: List[str] = field(default_factory=list)        # 平票PK玩家列表
    is_pk_vote: bool = False                                    # 是否是PK投票

    def clear_night_votes(self) -> None:
        """清空夜晚投票"""
        self.night_votes.clear()

    def clear_day_votes(self) -> None:
        """清空白天投票"""
        self.day_votes.clear()
        self.pk_players.clear()
        self.is_pk_vote = False


@dataclass
class SpeakingState:
    """发言状态"""
    order: List[str] = field(default_factory=list)       # 发言顺序
    current_index: int = 0                                # 当前发言者索引
    current_speaker_id: Optional[str] = None              # 当前发言者ID
    current_speech: List[str] = field(default_factory=list)  # 当前发言内容缓存

    def reset(self) -> None:
        """重置发言状态"""
        self.order.clear()
        self.current_index = 0
        self.current_speaker_id = None
        self.current_speech.clear()


@dataclass
class GameRoom:
    """游戏房间"""
    group_id: str                                        # 群ID
    creator_id: str                                      # 房主ID
    config: GameConfig                                   # 游戏配置
    msg_origin: Any = None                               # 消息源（用于主动发送）
    bot: Any = None                                      # Bot实例

    # 玩家管理
    players: Dict[str, Player] = field(default_factory=dict)  # {玩家ID: Player}
    number_to_player: Dict[int, str] = field(default_factory=dict)  # {编号: 玩家ID}

    # 游戏状态
    phase: GamePhase = GamePhase.WAITING
    current_round: int = 0                               # 当前回合数
    is_first_night: bool = True                          # 是否第一晚

    # 夜晚状态
    last_killed_id: Optional[str] = None                 # 上一晚被杀的玩家ID
    seer_checked: bool = False                           # 预言家是否已验人

    # 遗言状态
    last_words_from_vote: bool = False                   # 遗言是否来自投票放逐

    # 子状态
    witch_state: Any = None  # WitchState, 延迟初始化避免循环导入
    hunter_state: Any = None  # HunterState, 延迟初始化避免循环导入
    vote_state: VoteState = field(default_factory=VoteState)
    speaking_state: SpeakingState = field(default_factory=SpeakingState)

    def __post_init__(self):
        """初始化角色状态（避免循环导入）"""
        from ..roles import WitchState, HunterState
        if self.witch_state is None:
            self.witch_state = WitchState()
        if self.hunter_state is None:
            self.hunter_state = HunterState()

    # 管理状态
    banned_player_ids: Set[str] = field(default_factory=set)   # 被禁言的玩家
    temp_admin_ids: Set[str] = field(default_factory=set)      # 临时管理员

    # 定时器
    timer_task: Optional[asyncio.Task] = None

    # 游戏日志
    game_log: List[str] = field(default_factory=list)

    # ========== 玩家管理方法 ==========

    def add_player(self, player: Player) -> None:
        """添加玩家"""
        self.players[player.id] = player

    def get_player(self, player_id: str) -> Optional[Player]:
        """获取玩家"""
        return self.players.get(player_id)

    def get_player_by_number(self, number: int) -> Optional[Player]:
        """通过编号获取玩家"""
        player_id = self.number_to_player.get(number)
        return self.players.get(player_id) if player_id else None

    def get_alive_players(self) -> List[Player]:
        """获取所有存活玩家"""
        return [p for p in self.players.values() if p.is_alive]

    def get_alive_player_ids(self) -> Set[str]:
        """获取所有存活玩家ID"""
        return {p.id for p in self.players.values() if p.is_alive}

    def get_players_by_role(self, role: Role) -> List[Player]:
        """获取指定角色的所有玩家"""
        return [p for p in self.players.values() if p.role == role]

    def get_alive_players_by_role(self, role: Role) -> List[Player]:
        """获取指定角色的存活玩家"""
        return [p for p in self.players.values() if p.role == role and p.is_alive]

    def get_werewolves(self) -> List[Player]:
        """获取所有狼人"""
        return self.get_players_by_role(Role.WEREWOLF)

    def get_alive_werewolves(self) -> List[Player]:
        """获取存活狼人"""
        return self.get_alive_players_by_role(Role.WEREWOLF)

    def is_player_in_room(self, player_id: str) -> bool:
        """玩家是否在房间中"""
        return player_id in self.players

    def is_player_alive(self, player_id: str) -> bool:
        """玩家是否存活"""
        player = self.get_player(player_id)
        return player.is_alive if player else False

    def kill_player(self, player_id: str) -> Optional[Player]:
        """杀死玩家"""
        player = self.get_player(player_id)
        if player:
            player.kill()
        return player

    @property
    def player_count(self) -> int:
        """当前玩家数量"""
        return len(self.players)

    @property
    def alive_count(self) -> int:
        """存活玩家数量"""
        return len(self.get_alive_players())

    @property
    def is_full(self) -> bool:
        """房间是否已满"""
        return self.player_count >= self.config.total_players

    # ========== 角色查询方法 ==========

    def get_seer(self) -> Optional[Player]:
        """获取预言家"""
        seers = self.get_players_by_role(Role.SEER)
        return seers[0] if seers else None

    def get_witch(self) -> Optional[Player]:
        """获取女巫"""
        witches = self.get_players_by_role(Role.WITCH)
        return witches[0] if witches else None

    def get_hunter(self) -> Optional[Player]:
        """获取猎人"""
        hunters = self.get_players_by_role(Role.HUNTER)
        return hunters[0] if hunters else None

    def is_seer_alive(self) -> bool:
        """预言家是否存活"""
        seer = self.get_seer()
        return seer.is_alive if seer else False

    def is_witch_alive(self) -> bool:
        """女巫是否存活"""
        witch = self.get_witch()
        return witch.is_alive if witch else False

    def is_hunter_alive(self) -> bool:
        """猎人是否存活"""
        hunter = self.get_hunter()
        return hunter.is_alive if hunter else False

    # ========== 阶段管理方法 ==========

    def set_phase(self, phase: GamePhase) -> None:
        """设置游戏阶段"""
        self.phase = phase

    def is_phase(self, phase: GamePhase) -> bool:
        """判断当前阶段"""
        return self.phase == phase

    def is_night_phase(self) -> bool:
        """是否是夜晚阶段"""
        return self.phase in (
            GamePhase.NIGHT_WOLF,
            GamePhase.NIGHT_SEER,
            GamePhase.NIGHT_WITCH
        )

    def is_day_phase(self) -> bool:
        """是否是白天阶段"""
        return self.phase in (
            GamePhase.DAY_SPEAKING,
            GamePhase.DAY_VOTE,
            GamePhase.DAY_PK,
            GamePhase.LAST_WORDS
        )

    # ========== 回合管理方法 ==========

    def start_new_night(self) -> None:
        """开始新的夜晚"""
        self.current_round += 1
        self.phase = GamePhase.NIGHT_WOLF
        self.seer_checked = False
        self.last_killed_id = None
        self.witch_state.reset_night()
        self.vote_state.clear_night_votes()

    def end_first_night(self) -> None:
        """结束第一晚"""
        self.is_first_night = False

    # ========== 定时器管理方法 ==========

    def cancel_timer(self) -> None:
        """取消当前定时器"""
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            self.timer_task = None

    def set_timer(self, task: asyncio.Task) -> None:
        """设置定时器"""
        self.cancel_timer()
        self.timer_task = task

    # ========== 日志方法 ==========

    def log(self, message: str) -> None:
        """添加游戏日志"""
        self.game_log.append(message)

    def log_separator(self) -> None:
        """添加分隔线"""
        self.game_log.append("=" * 30)

    def log_round_start(self) -> None:
        """记录回合开始"""
        self.log_separator()
        self.log(f"第{self.current_round}晚")
        self.log_separator()

    # ========== 目标解析方法 ==========

    def parse_target(self, target_str: str) -> Optional[str]:
        """解析目标玩家（支持编号或QQ号）"""
        # 尝试作为编号解析
        try:
            number = int(target_str)
            if number in self.number_to_player:
                return self.number_to_player[number]
        except ValueError:
            pass

        # 尝试作为QQ号解析
        if target_str in self.players:
            return target_str

        return None
