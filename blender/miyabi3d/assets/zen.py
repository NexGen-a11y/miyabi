"""席 — カウンターに椀と箸を据え、奥に金屏風と提灯を置いたヒーロー用の場面."""

from __future__ import annotations

from mathutils import Vector

from . import chochin, hashi, shuki, wanmono
from .. import materials as MAT
from .. import modeling as M


def counter(collection=None, width=1.9, depth=0.72, thickness=0.048):
    top = M.plank((width, depth, thickness), bevel=0.0035, name="欅のカウンター",
                  collection=collection)
    M.place(top, (0, 0, -thickness / 2))
    M.set_material(top, MAT.keyaki())
    return top


def byobu(collection=None, width=2.6, height=1.15, distance=0.52):
    panel = M.plank((width, 0.028, height), bevel=0.004, name="金屏風",
                    collection=collection)
    M.place(panel, (0.12, distance, height / 2 - 0.34))
    M.set_material(panel, MAT.kinpaku_screen())
    return panel


def build(collection=None, with_lantern=True, facing=-74.0,
          lantern_at=(-0.455, 0.335, 0.315), with_shuki=True,
          shuki_at=(0.248, 0.238)):
    """カウンター・金屏風・椀・箸(・提灯)を一式並べる."""
    objs = [counter(collection), byobu(collection)]

    wan = wanmono.build(collection)
    for obj in wan["objects"]:
        obj.location.x += 0.018
        obj.location.y += 0.012
    objs += wan["objects"]

    sticks = hashi.build(collection)
    for obj in sticks["objects"]:
        obj.location.x -= 0.055
        obj.location.y -= 0.155
    objs += sticks["objects"]

    if with_shuki:
        sake = shuki.build(collection, cups=1)
        for obj in sake["objects"]:
            obj.location.x += shuki_at[0]
            obj.location.y += shuki_at[1]
        objs += sake["objects"]

    extra = []
    if with_lantern:
        lamp = chochin.build(collection, facing=facing, glow=9.0)
        for obj in lamp["all"]:
            obj.location.x += lantern_at[0]
            obj.location.y += lantern_at[1]
            obj.location.z += lantern_at[2]
        objs += lamp["objects"]
        extra += [o for o in lamp["all"] if o.type != 'MESH']

    return {
        "name": "席",
        "objects": objs,
        "all": objs + extra,
        "focus": Vector((0.018, 0.012, 0.040)),
        "radius": 0.075,          # ピントと明るさは椀に合わせる
        "height": 0.072,
    }
