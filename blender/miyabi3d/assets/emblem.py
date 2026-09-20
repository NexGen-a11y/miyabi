"""紋 — 黒漆の円盤に金の輪と「雅」。LP のロゴに使う.

正面が -Y を向くように立てて組んでいるので、真横から撮ると正対する。
"""

from __future__ import annotations

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M
from .. import textures as T

RADIUS = 0.075


def build(collection=None, text="雅", plate=True, stand=True):
    objs = []
    lift = RADIUS * 1.02 if stand else 0.0
    gold = MAT.gold(roughness=0.17, hammered=0.06)

    if plate:
        disc = M.cylinder(radius=RADIUS, height=0.0105, segments=160,
                          cap_bevel=0.0026, name="紋の地", collection=collection)
        M.place(disc, (0, 0, lift), (90, 0, 0))
        M.set_material(disc, MAT.urushi(gloss=0.05, name="紋の黒漆"))
        objs.append(disc)

        ring = M.torus(major=RADIUS - 0.0072, minor=0.0028, major_seg=180,
                       minor_seg=16, name="紋の輪", collection=collection)
        M.place(ring, (0, -0.0050, lift), (90, 0, 0))
        M.set_material(ring, gold)
        objs.append(ring)

    # Blender の文字サイズは em 基準で、和文書体だと字面がかなり小さく出る。
    # 実測して、輪の内側いっぱいに字面が来るところまで上げている。
    glyph = M.text_mesh(text, T.font_path(), size=0.248, extrude=0.0062,
                        bevel=0.0016, name="雅", collection=collection)
    M.place(glyph, (0, -0.0062, lift), (90, 0, 0))
    glyph = M.to_mesh(glyph, "雅")
    M.set_material(glyph, gold)
    objs.append(glyph)

    return {
        "name": "紋",
        "objects": objs,
        "focus": Vector((0.0, 0.0, lift)),
        "radius": RADIUS * 1.02,
        "height": RADIUS * 2,
    }
