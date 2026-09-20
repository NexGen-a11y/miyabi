"""PIL で文字を焼いてテクスチャにする (提灯と暖簾の「雅」)."""

from __future__ import annotations

import os
import tempfile

import bpy

FONT_ENV = "MIYABI_FONT"
_DEFAULT_FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "fonts", "NotoSerifJP.ttf")


def font_path() -> str:
    path = os.environ.get(FONT_ENV) or _DEFAULT_FONT
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"和文フォントが見つからない: {path}\n"
            f"blender/fonts/fetch.sh を実行するか {FONT_ENV} で指定してください。")
    return path


def kanji_image(text="雅", size=(2048, 1024), ratio=0.62, center=(0.5, 0.45),
                rotate=0.0, name=None) -> bpy.types.Image:
    """透過 PNG に文字を焼き、Blender の Image として返す."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = size
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    px = int(min(width, height) * ratio)
    font = ImageFont.truetype(font_path(), px)
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    x = int(width * center[0] - tw / 2 - box[0])
    y = int(height * center[1] - th / 2 - box[1])
    draw.text((x, y), text, font=font, fill=(0, 0, 0, 255))
    if rotate:
        img = img.rotate(rotate, resample=Image.BICUBIC, expand=False)

    path = os.path.join(tempfile.gettempdir(), f"miyabi-{name or text}-{width}.png")
    img.save(path)
    image = bpy.data.images.load(path, check_existing=True)
    image.name = name or f"文字-{text}"
    image.colorspace_settings.name = 'Non-Color'
    return image
