"""握り — 檜の寿司下駄に鮪・鮭・玉子の三貫、笹と山葵と生姜を添えて."""

from __future__ import annotations

import math

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M

BOARD_X, BOARD_Y, BOARD_T = 0.245, 0.126, 0.0135
FOOT_H = 0.0125
TOP = FOOT_H + BOARD_T        # 下駄の甲板の高さ


def geta(collection=None):
    """寿司下駄 — 甲板と、両端で渡した足."""
    out = []
    top = M.plank((BOARD_X, BOARD_Y, BOARD_T), bevel=0.0018, name="寿司下駄",
                  collection=collection)
    M.place(top, (0, 0, FOOT_H + BOARD_T / 2))
    M.set_material(top, MAT.hinoki())
    out.append(top)
    for sign in (-1, 1):
        foot = M.plank((0.024, BOARD_Y, FOOT_H), bevel=0.0012,
                       name="下駄の足", collection=collection)
        M.place(foot, (sign * (BOARD_X / 2 - 0.020), 0, FOOT_H / 2))
        M.set_material(foot, MAT.hinoki())
        out.append(foot)
    return out


def shari(length=0.049, width=0.0245, height=0.0195, name="舎利", collection=None):
    """握った飯。ボロノイで米粒の凹凸を出す."""
    obj = M.rounded_box((length, width, height), bevel=width * 0.40, segments=6,
                        subsurf=2, name=name, collection=collection)
    tex = M.noise_texture(f"{name}-粒", size=0.0055, ttype='VORONOI', contrast=1.6)
    M.add_displace(obj, tex, strength=0.0016, mid_level=0.40)
    M.set_material(obj, MAT.rice())
    return obj


def neta(material, length=0.058, width=0.029, thickness=0.0052, droop=0.0062,
         name="種", collection=None):
    """舎利に被せる種。中央を山にして両端を垂らし、切り身の反りを出す."""
    obj = M.grid((length, width), (30, 14), name, collection)
    half_x, half_y = length / 2, width / 2
    for vert in obj.data.vertices:
        tx = vert.co.x / half_x
        ty = vert.co.y / half_y
        vert.co.y *= 1.0 - 0.14 * tx ** 2          # 端に向けて少し細く
        vert.co.z = -droop * tx ** 2 - droop * 0.38 * ty ** 2 \
            + math.sin(tx * 2.4) * 0.00035          # 包丁目のうねり
    M.recalc_normals(obj)
    M.add_solidify(obj, thickness, offset=0.0)
    M.add_subsurf(obj, 1, 2)
    M.auto_smooth(obj, 45)
    M.set_material(obj, material)
    return obj


def nigiri(material, x=0.0, y=0.0, spin=0.0, neta_length=0.058, neta_thickness=0.0052,
           droop=0.0062, name="握り", collection=None):
    out = []
    rice = shari(name=f"{name}の舎利", collection=collection)
    M.place(rice, (x, y, TOP + 0.0092), (0, 0, spin))
    out.append(rice)
    top = neta(material, length=neta_length, thickness=neta_thickness, droop=droop,
               name=f"{name}の種", collection=collection)
    M.place(top, (x, y, TOP + 0.0196), (0, 0, spin))
    out.append(top)
    return out


def _band(width=0.0115, name="海苔", collection=None):
    """玉子に巻く海苔 — 天面から両脇へ回り込む帯."""
    steps, rings = 26, 5
    verts, faces = [], []
    half_w, half_h, rise = 0.0138, 0.0152, 0.0
    for i in range(steps + 1):
        t = i / steps
        a = math.pi * (1.0 - t)
        y = half_w * math.cos(a) * 1.02
        z = half_h * math.sin(a) ** 0.72
        for j in range(rings):
            u = -0.5 + j / (rings - 1)
            verts.append((u * width, y, z + rise))
    for i in range(steps):
        for j in range(rings - 1):
            a = i * rings + j
            faces.append((a, a + rings, a + rings + 1, a + 1))
    obj = M.mesh_object(name, verts, faces, collection)
    M.recalc_normals(obj)
    M.add_solidify(obj, 0.00025, offset=0.0)
    M.auto_smooth(obj, 50)
    M.set_material(obj, MAT.nori())
    return obj


def tamago_nigiri(x=0.0, y=0.0, spin=0.0, collection=None):
    out = []
    rice = shari(length=0.046, width=0.023, height=0.017, name="玉子の舎利",
                 collection=collection)
    M.place(rice, (x, y, TOP + 0.0082), (0, 0, spin))
    out.append(rice)
    block = M.rounded_box((0.052, 0.026, 0.0135), bevel=0.0016, segments=3,
                          subsurf=1, name="玉子焼", collection=collection)
    M.place(block, (x, y, TOP + 0.0228), (0, 0, spin))
    M.set_material(block, MAT.tamago())
    out.append(block)
    band = _band(collection=collection)
    M.place(band, (x, y, TOP + 0.0161), (0, 0, spin))
    out.append(band)
    return out


def garnish(collection=None):
    out = []
    sasa = M.leaf(length=0.098, width=0.040, curl=0.10, thickness=0.00028,
                  name="笹", collection=collection)
    M.place(sasa, (0.082, 0.028, TOP + 0.0009), (0, 0, 16))
    M.set_material(sasa, MAT.greens(color=(0.022, 0.085, 0.020), roughness=0.34,
                                    name="笹の葉"))
    out.append(sasa)

    mound = M.dome(radius=0.0105, height=0.0125, steps=14, segments=48,
                   flatten=0.25, name="山葵", collection=collection)
    tex = M.noise_texture("山葵の目", size=0.003, ttype='VORONOI', contrast=1.3)
    M.add_displace(mound, tex, strength=0.0009, mid_level=0.45)
    M.place(mound, (0.0955, -0.0295, TOP), scale=(1.0, 0.92, 1.0))
    M.set_material(mound, MAT.wasabi())
    out.append(mound)

    gari_mat = MAT.greens(color=(0.78, 0.60, 0.61), roughness=0.30, name="甘酢生姜")
    for i, (dx, dy, rot, tilt) in enumerate((
            (0.0, 0.0, 12, 26), (0.006, 0.004, -34, 14),
            (-0.005, 0.005, 58, 34), (0.002, 0.009, 96, 8))):
        slice_ = M.grid((0.026, 0.017), (12, 8), f"生姜{i}", collection)
        for vert in slice_.data.vertices:
            vert.co.z = math.sin(vert.co.x / 0.013 * 1.1) * 0.0032
        M.recalc_normals(slice_)
        M.add_solidify(slice_, 0.00045, offset=0.0)
        M.auto_smooth(slice_, 50)
        M.place(slice_, (0.0775 + dx, 0.0015 + dy, TOP + 0.0016 + i * 0.0011),
                (tilt, 0, rot))
        M.set_material(slice_, gari_mat)
        out.append(slice_)
    return out


def build(collection=None, with_garnish=True):
    objs = list(geta(collection))
    objs += nigiri(MAT.maguro(), x=-0.0595, y=-0.004, spin=-7, name="鮪",
                   collection=collection)
    objs += nigiri(MAT.salmon(), x=-0.0015, y=0.002, spin=5, neta_thickness=0.0058,
                   droop=0.0070, name="鮭", collection=collection)
    objs += tamago_nigiri(x=0.0565, y=-0.003, spin=-4, collection=collection)
    if with_garnish:
        objs += garnish(collection)
    return {
        "name": "握り",
        "objects": objs,
        "focus": Vector((0.0, 0.0, TOP + 0.012)),
        "radius": 0.115,
        "height": TOP + 0.035,
    }
