"""角色卡片图片生成"""
from PIL import Image, ImageDraw
from .styles import (
    load_font,
    COLOR_BACKGROUND_TOP,
    COLOR_BACKGROUND_BOT,
    COLOR_TITLE,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_DIM,
    COLOR_CARD_BG,
    COLOR_WEREWOLF,
    COLOR_SEER,
    COLOR_WITCH,
    COLOR_HUNTER,
    COLOR_VILLAGER,
    COLOR_GOOD_CAMP,
    COLOR_EVIL_CAMP,
)
from .gradient_utils import create_vertical_gradient

# 角色配置
ROLE_CONFIG = {
    "狼人": {
        "emoji": "🐺",
        "color": COLOR_WEREWOLF,
        "camp": "狼人阵营",
        "camp_color": COLOR_EVIL_CAMP,
        "desc": "每晚可以与同伴一起选择一名玩家袭击",
        "tips": [
            "• 与队友统一目标后私聊 /办掉 编号",
            "• 使用 /密谋 消息 与队友交流",
            "• 白天隐藏身份，引导投票",
        ],
    },
    "预言家": {
        "emoji": "🔮",
        "color": COLOR_SEER,
        "camp": "好人阵营",
        "camp_color": COLOR_GOOD_CAMP,
        "desc": "每晚可以查验一名玩家的身份",
        "tips": [
            "• 私聊 /验人 编号 查验目标",
            "• 验出狼人要适时公开信息",
            "• 注意保护自己，避免被狼人针对",
        ],
    },
    "女巫": {
        "emoji": "🧪",
        "color": COLOR_WITCH,
        "camp": "好人阵营",
        "camp_color": COLOR_GOOD_CAMP,
        "desc": "拥有一瓶解药和一瓶毒药，各限用一次",
        "tips": [
            "• /救人 使用解药救活被杀玩家",
            "• /毒人 编号 使用毒药毒杀目标",
            "• /不操作 选择不使用任何药剂",
            "• 注意：不能同时救人和毒人",
        ],
    },
    "猎人": {
        "emoji": "🔫",
        "color": COLOR_HUNTER,
        "camp": "好人阵营",
        "camp_color": COLOR_GOOD_CAMP,
        "desc": "死亡时可以开枪带走一名玩家",
        "tips": [
            "• 被狼杀或投票出局时可开枪",
            "• 被女巫毒死时不能开枪",
            "• 私聊 /开枪 编号 带走目标",
        ],
    },
    "平民": {
        "emoji": "👤",
        "color": COLOR_VILLAGER,
        "camp": "好人阵营",
        "camp_color": COLOR_GOOD_CAMP,
        "desc": "没有特殊技能，依靠分析和投票帮助好人阵营",
        "tips": [
            "• 仔细观察每个人的发言",
            "• 分析场上形势，找出狼人",
            "• 投票时要谨慎，避免误杀好人",
        ],
    },
}


def draw_role_card(role_name: str, player_number: int = None, teammates: list = None) -> Image.Image:
    """
    生成角色卡片图片

    Args:
        role_name: 角色名称（狼人/预言家/女巫/猎人/平民）
        player_number: 玩家编号
        teammates: 队友列表（狼人专用）

    Returns:
        PIL Image 对象
    """
    config = ROLE_CONFIG.get(role_name)
    if not config:
        config = ROLE_CONFIG["平民"]

    width = 500
    height = 400 if role_name != "狼人" or not teammates else 450

    # 加载字体
    title_font = load_font(32)
    subtitle_font = load_font(20)
    text_font = load_font(16)
    tip_font = load_font(14)

    # 创建画布
    image = create_vertical_gradient(width, height, COLOR_BACKGROUND_TOP, COLOR_BACKGROUND_BOT)
    draw = ImageDraw.Draw(image, "RGBA")

    # 角色图标和名称
    y = 40
    role_text = f"{config['emoji']} {role_name}"
    draw.text((width // 2, y), role_text, fill=config["color"], font=title_font, anchor="mm")

    # 阵营
    y += 45
    draw.text((width // 2, y), config["camp"], fill=config["camp_color"], font=subtitle_font, anchor="mm")

    # 玩家编号
    if player_number:
        y += 30
        draw.text((width // 2, y), f"你是 {player_number} 号玩家", fill=COLOR_TEXT_LIGHT, font=text_font, anchor="mm")

    # 分割线
    y += 30
    line_margin = 60
    draw.line([(line_margin, y), (width - line_margin, y)], fill=config["color"], width=2)

    # 角色描述
    y += 25
    draw.text((width // 2, y), config["desc"], fill=COLOR_TEXT_LIGHT, font=text_font, anchor="mm")

    # 技能提示卡片
    y += 35
    card_margin = 40
    card_x0, card_y0 = card_margin, y
    card_x1 = width - card_margin

    # 计算卡片高度
    tips = config["tips"]
    card_height = 30 + len(tips) * 24 + 15
    card_y1 = card_y0 + card_height

    # 绘制卡片背景
    draw.rounded_rectangle(
        [card_x0, card_y0, card_x1, card_y1],
        radius=10,
        fill=COLOR_CARD_BG,
        outline=config["color"],
        width=1,
    )

    # 卡片标题
    draw.text((card_x0 + 15, card_y0 + 12), "💡 技能提示", fill=config["color"], font=text_font)

    # 技能列表
    tip_y = card_y0 + 38
    for tip in tips:
        draw.text((card_x0 + 15, tip_y), tip, fill=COLOR_TEXT_DIM, font=tip_font)
        tip_y += 24

    y = card_y1 + 15

    # 狼人队友信息
    if role_name == "狼人" and teammates:
        teammate_text = "🐺 你的狼队友：" + "、".join(teammates)
        draw.text((width // 2, y), teammate_text, fill=COLOR_WEREWOLF, font=text_font, anchor="mm")
        y += 30

    # 底部提示
    y = max(y, height - 35)
    draw.text(
        (width // 2, y),
        "🤫 请勿将角色信息泄露给他人",
        fill=COLOR_TEXT_DIM,
        font=tip_font,
        anchor="mm",
    )

    # 裁剪到实际高度
    final_height = y + 20
    if final_height < height:
        image = image.crop((0, 0, width, final_height))

    return image
