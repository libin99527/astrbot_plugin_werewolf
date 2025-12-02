"""渐变工具函数"""
from PIL import Image


def create_vertical_gradient(
    width: int, height: int, color_top: tuple, color_bot: tuple
) -> Image.Image:
    """
    创建垂直渐变背景

    Args:
        width: 图片宽度
        height: 图片高度
        color_top: 顶部颜色 RGB元组
        color_bot: 底部颜色 RGB元组

    Returns:
        PIL Image 对象
    """
    image = Image.new("RGB", (width, height), color_top)
    pixels = image.load()

    r1, g1, b1 = color_top
    r2, g2, b2 = color_bot

    for y in range(height):
        ratio = y / height
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)

        for x in range(width):
            pixels[x, y] = (r, g, b)

    return image


def create_radial_gradient(
    width: int, height: int, color_center: tuple, color_edge: tuple
) -> Image.Image:
    """
    创建径向渐变背景（从中心向外）

    Args:
        width: 图片宽度
        height: 图片高度
        color_center: 中心颜色 RGB元组
        color_edge: 边缘颜色 RGB元组

    Returns:
        PIL Image 对象
    """
    image = Image.new("RGB", (width, height), color_edge)
    pixels = image.load()

    cx, cy = width // 2, height // 2
    max_dist = ((cx**2) + (cy**2)) ** 0.5

    r1, g1, b1 = color_center
    r2, g2, b2 = color_edge

    for y in range(height):
        for x in range(width):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            ratio = min(dist / max_dist, 1.0)

            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)

            pixels[x, y] = (r, g, b)

    return image
