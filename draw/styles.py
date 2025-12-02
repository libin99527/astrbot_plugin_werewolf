"""狼人杀插件样式配置 - 暗夜狼嚎主题"""
import os
from PIL import ImageFont

# --- 基础配置 ---
IMG_WIDTH = 800
PADDING = 30
CORNER_RADIUS = 15

# --- 颜色定义 ---
# 主题色 - 暗夜血月色系
COLOR_BACKGROUND_TOP = (15, 15, 25)       # 深夜黑
COLOR_BACKGROUND_BOT = (35, 25, 35)       # 暗紫黑

# 角色主题色
COLOR_WEREWOLF = (180, 50, 50)            # 狼人红
COLOR_SEER = (100, 150, 220)              # 预言家蓝
COLOR_WITCH = (150, 80, 180)              # 女巫紫
COLOR_HUNTER = (200, 150, 50)             # 猎人金
COLOR_VILLAGER = (120, 180, 120)          # 平民绿
COLOR_DEAD = (80, 80, 80)                 # 死亡灰

# 阵营颜色
COLOR_GOOD_CAMP = (80, 160, 200)          # 好人阵营蓝
COLOR_EVIL_CAMP = (200, 60, 60)           # 狼人阵营红

# 文本颜色
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_TEXT_LIGHT = (220, 220, 235)
COLOR_TEXT_GRAY = (180, 180, 200)
COLOR_TEXT_DIM = (130, 130, 150)

# 标题颜色
COLOR_TITLE = (255, 220, 180)             # 月光金
COLOR_SUBTITLE = (180, 180, 200)          # 副标题灰

# 卡片颜色
COLOR_CARD_BG = (40, 35, 50, 230)         # 半透明暗卡片
COLOR_CARD_BORDER = (100, 80, 120)        # 紫灰边框
COLOR_CARD_SHADOW = (0, 0, 0, 100)        # 阴影

# 命令颜色
COLOR_CMD = (220, 200, 180)               # 命令文本（暖白）
COLOR_CMD_NIGHT = (150, 180, 220)         # 夜晚命令（冷蓝）
COLOR_CMD_DAY = (220, 180, 100)           # 白天命令（暖金）

# 特殊颜色
COLOR_BLOOD_MOON = (200, 80, 80)          # 血月红
COLOR_MOONLIGHT = (200, 220, 255)         # 月光白
COLOR_MYSTERY = (180, 150, 220)           # 神秘紫
COLOR_SUCCESS = (100, 200, 120)           # 成功绿
COLOR_WARNING = (220, 180, 80)            # 警告橙
COLOR_DANGER = (220, 80, 80)              # 危险红

# 分割线
COLOR_LINE = (80, 60, 100)                # 暗紫线

# 状态颜色
COLOR_ALIVE = (100, 200, 120)             # 存活绿
COLOR_NIGHT = (80, 100, 150)              # 夜晚蓝
COLOR_DAY = (200, 180, 100)               # 白天金

# --- 字体路径 ---
# 尝试使用钓鱼插件的字体
FONT_PATH_BOLD = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "astrbot_plugin_fishing", "draw", "resource", "DouyinSansBold.otf"
)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """加载字体，失败则使用默认字体"""
    try:
        if os.path.exists(FONT_PATH_BOLD):
            return ImageFont.truetype(FONT_PATH_BOLD, size)
    except IOError:
        pass

    # 尝试系统字体
    system_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]
    for font_path in system_fonts:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except IOError:
            continue

    # 最后使用默认字体
    return ImageFont.load_default()


def get_role_color(role_name: str) -> tuple:
    """根据角色名返回对应颜色"""
    role_colors = {
        "狼人": COLOR_WEREWOLF,
        "预言家": COLOR_SEER,
        "女巫": COLOR_WITCH,
        "猎人": COLOR_HUNTER,
        "平民": COLOR_VILLAGER,
    }
    return role_colors.get(role_name, COLOR_TEXT_GRAY)


def get_camp_color(is_werewolf: bool) -> tuple:
    """根据阵营返回对应颜色"""
    return COLOR_EVIL_CAMP if is_werewolf else COLOR_GOOD_CAMP
