"""箸と箸置き — 黒漆の塗り箸を、白磁の箸置きに架ける."""

from __future__ import annotations

import math

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M

LENGTH = 0.228
REST_L, REST_W, REST_H = 0.058, 0.019, 0.0135


def hashioki(collection=None):
    """真ん中がくぼんだ箸置き。両端が高く、断面は半楕円."""
    steps, rings = 30, 14
    verts, faces = [], []
    for i in range(steps + 1):
        u = -1.0 + 2.0 * i / steps
        taper = max(1.0 - u ** 6, 1e-3) ** 0.34
        height = REST_H * (0.62 + 0.38 * math.cos(math.pi * u)) * taper
        width = REST_W * 0.5 * taper
        for j in range(rings):
            a = math.pi * j / (rings - 1)
            # sin(pi) が -1e-16 に転ぶことがあり、負数の累乗で複素数になるので潰す
            arch = max(math.sin(a), 0.0) ** 0.85
            verts.append((u * REST_L * 0.5, width * math.cos(a), height * arch))
    for i in range(steps):
        for j in range(rings - 1):
            a = i * rings + j
            faces.append((a, a + rings, a + rings + 1, a + 1))
    obj = M.mesh_object("箸置き", verts, faces, collection)
    M.recalc_normals(obj, merge=1e-5)
    M.add_solidify(obj, 0.0016, offset=0.0)
    M.auto_smooth(obj, 45)
    M.set_material(obj, MAT.ceramic(color=(0.78, 0.76, 0.71), roughness=0.09,
                                    speckle=0.25, name="白磁"))
    return obj


def sticks(collection=None, rest_z=REST_H, spread=0.0105):
    mat = MAT.urushi(gloss=0.07, name="塗り箸")
    out = []
    for i, offset in enumerate((-spread * 0.5, spread * 0.5)):
        bar = M.taper_bar(length=LENGTH, base=0.0064, tip=0.0021, sections=16,
                          name=f"箸{i}", collection=collection)
        M.place(bar, (-LENGTH * 0.46, offset, rest_z + 0.0028),
                (0, 88.6, 0 if i == 0 else -1.6))
        M.set_material(bar, mat)
        out.append(bar)
    return out


def build(collection=None, with_rest=True):
    objs = []
    if with_rest:
        objs.append(hashioki(collection))
    objs += sticks(collection)
    return {
        "name": "箸",
        "objects": objs,
        "focus": Vector((0.0, 0.0, 0.010)),
        "radius": 0.118,
        "height": 0.020,
    }
