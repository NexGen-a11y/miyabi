"""提灯 — 骨を巻いた火袋に「雅」の一文字、中から灯りを入れる."""

from __future__ import annotations

import math

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M
from .. import textures as T

HEIGHT = 0.340
R_MAX = 0.1075
R_OPEN = 0.0405
RIBS = 26


def radius_at(t: float) -> float:
    return R_OPEN + (R_MAX - R_OPEN) * max(math.sin(math.pi * t), 0.0) ** 0.38


def paper(text="雅", collection=None, facing=-62.0, glow=6.0):
    profile = [(radius_at(i / 48), HEIGHT * i / 48) for i in range(49)]
    obj = M.revolve(profile, 128, "火袋", smooth_angle=40, collection=collection,
                    uv=True)
    M.add_solidify(obj, 0.00045, offset=0.0)
    image = T.kanji_image(text, (2048, 1024), ratio=0.44, center=(0.5, 0.47))
    M.set_material(obj, MAT.image_decal(image, base=(0.90, 0.84, 0.70),
                                        ink=(0.012, 0.011, 0.012),
                                        name="火袋の紙", emission=glow))
    # UV の u=0.5 は角度 180 度。そこが facing の方角を向くように回す
    obj.rotation_euler = (0.0, 0.0, math.radians(facing - 180.0))
    return obj


def ribs(collection=None):
    mat = MAT.kuroki()
    out = []
    for i in range(RIBS):
        t = (i + 0.5) / RIBS
        rib = M.torus(major=radius_at(t) + 0.0009, minor=0.0017,
                      major_seg=56, minor_seg=8, name=f"骨{i}", collection=collection)
        rib.location.z = t * HEIGHT
        M.set_material(rib, mat)
        out.append(rib)
    return out


def caps(collection=None):
    mat = MAT.kuroki()
    out = []
    for z0, z1 in ((HEIGHT - 0.002, HEIGHT + 0.0125), (-0.0125, 0.002)):
        ring = M.revolve([(0.0295, z0), (R_OPEN + 0.004, z0),
                          (R_OPEN + 0.004, z1), (0.0295, z1), (0.0295, z0)],
                         96, "輪", 44, collection)
        M.set_material(ring, mat)
        out.append(ring)
    hook = M.torus(major=0.0105, minor=0.0021, major_seg=48, minor_seg=10,
                   name="吊り手", collection=collection)
    M.place(hook, (0, 0, HEIGHT + 0.0215), (90, 0, 0))
    M.set_material(hook, mat)
    out.append(hook)
    return out


def build(collection=None, text="雅", with_light=True, facing=-62.0, glow=6.0):
    objs = [paper(text, collection, facing=facing, glow=glow)]
    objs += ribs(collection)
    objs += caps(collection)
    if with_light:
        from .. import staging
        lamp = staging.point_light("灯芯", (0, 0, HEIGHT * 0.42), energy=0.9,
                                   color=(1.0, 0.66, 0.34), radius=0.035)
        objs.append(lamp)
    return {
        "name": "提灯",
        "objects": [o for o in objs if o.type == 'MESH'],
        "all": objs,
        "focus": Vector((0.0, 0.0, HEIGHT * 0.5)),
        "radius": 0.19,
        "height": HEIGHT,
    }
