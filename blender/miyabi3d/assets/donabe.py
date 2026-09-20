"""土鍋 — 炊き込みご飯を炊いた黒土鍋と、そのそばに置いた蓋."""

from __future__ import annotations

import math

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M

OUTER = [(0.0560, 0.0110), (0.0760, 0.0250), (0.0940, 0.0430), (0.1055, 0.0625),
         (0.1100, 0.0800), (0.1080, 0.0942), (0.1008, 0.1042)]
WALL = 0.0070
LID_R, LID_H, LID_T = 0.1050, 0.0325, 0.0062
FILL = 0.0655      # 飯の高さ
CAP = 0.0165       # 山盛りの盛り上がり


def _shape():
    return M.vessel_profile(OUTER, thickness=WALL, foot_width=0.012,
                            base_thickness=0.0088, rim_steps=4)


def _inner_wall(limit=FILL, inset=0.0014):
    profile, zones = _shape()
    pts = [(r - inset, z) for (r, z), label in zip(profile, zones + zones[-1:])
           if label == 'inner' and z <= limit]
    pts.sort(key=lambda p: p[1])
    return pts


def surface_z(distance: float) -> float:
    """盛り上がった飯の、中心から distance 離れた位置の高さ."""
    top_r = _inner_wall()[-1][0]
    t = min(max(distance / max(top_r, 1e-6), 0.0), 1.0)
    return FILL + CAP * max(1.0 - t ** 2, 0.0) ** 0.62


def pot(collection=None):
    profile, zones = _shape()
    slots = M.zone_slots(zones, {'under': 0, 'outer': 0, 'rim': 0, 'inner': 1})
    obj = M.revolve(profile, 128, "土鍋", smooth_angle=32,
                    collection=collection, slots=slots)
    M.set_material(obj, MAT.clay(), MAT.ameyu())
    return obj


def ears(collection=None):
    """両耳。持つところなので少し下ぶくれに."""
    out = []
    for sign in (-1, 1):
        ear = M.rounded_box((0.034, 0.019, 0.016), bevel=0.0055, segments=4,
                            subsurf=2, name="耳", collection=collection)
        M.place(ear, (sign * 0.1135, 0.0, 0.0790), (0, sign * -7, 0))
        M.set_material(ear, MAT.clay())
        out.append(ear)
    return out


def lid(collection=None, location=(0.206, 0.072, 0.0), spin=18.0):
    steps = 24
    top, under = [], []
    for i in range(steps + 1):
        t = i / steps
        top.append((LID_R * t, LID_H * (1.0 - t ** 2) ** 0.78))
        under.append(((LID_R - 0.0055) * t,
                      (LID_H - LID_T) * (1.0 - t ** 2) ** 0.78 - 0.0058 * t ** 2))
    profile = M.chain([(0.0, LID_H)], top[1:], [(LID_R, -0.0058)],
                      list(reversed(under))[:-1], [(0.0, LID_H - LID_T)])
    body = M.revolve(profile, 128, "蓋", smooth_angle=32, collection=collection)
    M.set_material(body, MAT.clay())

    knob = M.revolve(M.chain([(0.0, 0.0)], [(0.0165, 0.0), (0.0175, 0.0042)],
                             M.arc((0.0090, 0.0118), 0.0092, -18, 96, 10),
                             [(0.0, 0.0212)]),
                     72, "つまみ", 34, collection)
    M.set_material(knob, MAT.clay())

    for obj in (body, knob):
        obj.location = Vector(location) + Vector(
            (0.0, 0.0, LID_H if obj is knob else 0.0))
        obj.rotation_euler = (0.0, 0.0, math.radians(spin))
    knob.location.z = location[2] + LID_H - 0.0016
    return [body, knob]


def rice(collection=None):
    """炊き上がりの飯。鍋の内壁なりに詰めて、中央を山にする."""
    wall = _inner_wall()
    top_r = wall[-1][0]
    cap = []
    for i in range(1, 15):
        t = i / 14
        cap.append((top_r * max(math.cos(t * math.pi / 2), 0.0) ** 0.62,
                    FILL + CAP * max(math.sin(t * math.pi / 2), 0.0) ** 0.9))
    profile = M.chain([(0.0, wall[0][1] + 0.0004)], wall, cap)
    mound = M.revolve(profile, 120, "炊き込みご飯", smooth_angle=44,
                      collection=collection)
    tex = M.noise_texture("飯粒", size=0.0058, ttype='VORONOI', contrast=1.5)
    M.add_displace(mound, tex, strength=0.0024, mid_level=0.42)
    M.set_material(mound, MAT.rice())
    return mound


def toppings(collection=None):
    out = []
    ginnan_mat = MAT.greens(color=(0.52, 0.50, 0.11), roughness=0.30, name="銀杏")
    for x, y, spin in ((-0.030, 0.026, 24), (0.020, 0.036, -40), (0.042, -0.016, 62)):
        nut = M.dome(radius=0.0072, height=0.0115, steps=12, segments=40,
                     flatten=-0.35, name="銀杏", collection=collection)
        M.place(nut, (x, y, surface_z(math.hypot(x, y)) - 0.0035),
                (72, 0, spin), scale=(1.0, 0.78, 1.0))
        M.set_material(nut, ginnan_mat)
        out.append(nut)

    carrot_mat = MAT.greens(color=(0.62, 0.20, 0.035), roughness=0.34, name="人参")
    for i, (x, y, spin, tilt) in enumerate((
            (-0.012, -0.038, 18, 6), (0.048, 0.020, -52, -9), (-0.052, -0.006, 74, 4))):
        stick = M.rounded_box((0.026, 0.0055, 0.0038), bevel=0.0012, segments=3,
                              subsurf=1, name=f"人参{i}", collection=collection)
        M.place(stick, (x, y, surface_z(math.hypot(x, y)) - 0.0022), (tilt, 0, spin))
        M.set_material(stick, carrot_mat)
        out.append(stick)

    for i, (x, y, rot) in enumerate(((0.006, -0.006, -14), (-0.018, 0.006, 52))):
        lf = M.leaf(length=0.030, width=0.016, curl=0.14, thickness=0.00022,
                    name=f"三つ葉{i}", collection=collection)
        M.place(lf, (x, y, surface_z(math.hypot(x, y)) + 0.0014), (5, -3, rot))
        M.set_material(lf, MAT.greens())
        out.append(lf)
    return out


def build(collection=None, with_lid=True, with_rice=True):
    objs = [pot(collection)]
    objs += ears(collection)
    if with_rice:
        objs.append(rice(collection))
        objs += toppings(collection)
    if with_lid:
        objs += lid(collection)
    return {
        "name": "土鍋",
        "objects": objs,
        "focus": Vector((0.035 if with_lid else 0.0, 0.01, 0.055)),
        "radius": 0.175 if with_lid else 0.115,
        "height": 0.1042,
    }
