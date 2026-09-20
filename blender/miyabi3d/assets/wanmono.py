"""椀物 — 黒内朱の汁椀に張った出汁と、浮かべた梅花麩・三つ葉・柚子.

寸法は実寸。口径 約120mm、高さ 約72mm の汁椀。
総黒の漆に金粉を蒔き、口縁だけ金。澄んだ出汁の色がそのまま映える。
"""

from __future__ import annotations

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M

RIM_R = 0.0601       # 口径の半径
RIM_Z = 0.0718       # 器の高さ
FOOT_R = 0.0302      # 高台の半径
FOOT_Z = 0.0068      # 高台の高さ
THICK = 0.0019       # 肉厚
FILL = 0.0512        # 出汁の水位
GOLD_FROM = 0.0645   # この高さから上の外側は金の口縁


def _shape():
    outer = M.bell_curve(FOOT_R, RIM_R, FOOT_Z, RIM_Z, steps=30, ease=1.9)
    return M.vessel_profile(outer, thickness=THICK, foot_width=0.0042,
                            base_thickness=0.0024, rim_steps=4)


def _inner_radius_at(z: float) -> float:
    """内壁のどの高さで何ミリ開いているか (出汁の水面半径に使う)."""
    profile, zones = _shape()
    inner = sorted(((r, zz) for (r, zz), label in zip(profile, zones + zones[-1:])
                    if label == 'inner'), key=lambda p: p[1])
    for (r0, z0), (r1, z1) in zip(inner, inner[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / max(z1 - z0, 1e-9)
            return r0 + (r1 - r0) * t
    return inner[-1][0]


def bowl(collection=None):
    profile, zones = _shape()

    def rule(i, label):
        # 外側の口もと寄りと口縁そのものは金に塗り分ける
        if label in ('outer', 'rim') and profile[i][1] >= GOLD_FROM:
            return 2
        return None

    slots = M.zone_slots(zones, {'under': 0, 'outer': 0, 'rim': 2, 'inner': 1}, rule)
    obj = M.revolve(profile, 144, "汁椀", smooth_angle=30,
                    collection=collection, slots=slots)
    M.set_material(obj, MAT.urushi_makie(), MAT.urushi(gloss=0.045, name="内黒漆"),
                   MAT.gold(roughness=0.15))
    return obj


def soup(collection=None):
    """出汁。内壁から 0.4mm 内側に落として面が刺さらないようにする."""
    gap = 0.0004
    profile, zones = _shape()
    inner = [(r - gap, z) for (r, z), label in zip(profile, zones + zones[-1:])
             if label == 'inner' and z <= FILL]
    inner.sort(key=lambda p: p[1])
    surface_r = _inner_radius_at(FILL) - gap
    shape = M.chain([(0.0, inner[0][1] + 0.0002)], inner,
                    [(surface_r, FILL), (0.0, FILL)])
    obj = M.revolve(shape, 144, "出汁", smooth_angle=18, collection=collection)
    M.set_material(obj, MAT.dashi(color=(0.80, 0.50, 0.16), density=16.0, cloud=0.10))
    return obj


def garnish(collection=None):
    out = []

    fu = M.blossom(radius=0.0128, petals=5, lobe=0.30, thickness=0.0072,
                   rings=9, segments=96, name="梅花麩", collection=collection)
    M.place(fu, (-0.0142, 0.0108, FILL - 0.0014), (0, 0, 22))
    M.set_material(fu, MAT.fu())
    out.append(fu)

    beni = M.blossom(radius=0.0046, petals=5, lobe=0.24, thickness=0.0079,
                     rings=6, segments=64, name="麩の紅", collection=collection)
    M.place(beni, (-0.0142, 0.0108, FILL - 0.0010), (0, 0, 22))
    M.set_material(beni, MAT.greens(color=(0.58, 0.085, 0.11), roughness=0.5, name="紅"))
    out.append(beni)

    for i, (x, y, rot, length) in enumerate((
            (0.0176, -0.0072, (8, 3, -26), 0.0325),
            (0.0232, 0.0042, (-6, 5, 40), 0.0280),
            (0.0116, 0.0040, (4, -4, 6), 0.0235))):
        lf = M.leaf(length=length, width=length * 0.50, curl=0.13,
                    thickness=0.00022, name=f"三つ葉{i}", collection=collection)
        M.place(lf, (x, y, FILL + 0.0014), rot)
        M.set_material(lf, MAT.greens())
        out.append(lf)

    stem = M.cylinder(radius=0.00075, height=0.0225, segments=16,
                      name="三つ葉の軸", collection=collection)
    M.place(stem, (0.0082, -0.0042, FILL + 0.0006), (0, 84, -32))
    M.set_material(stem, MAT.greens(color=(0.15, 0.29, 0.065), roughness=0.4, name="軸"))
    out.append(stem)

    peel = M.grid((0.0118, 0.0052), (12, 7), "柚子皮", collection)
    for vert in peel.data.vertices:
        vert.co.z = (vert.co.x / 0.0118) ** 2 * 0.0026 - 0.0004
    M.recalc_normals(peel)
    M.add_solidify(peel, 0.0009, offset=0.0)
    M.auto_smooth(peel, 50)
    M.place(peel, (-0.0046, -0.0196, FILL + 0.0012), (0, 0, 58))
    M.set_material(peel, MAT.yuzu())
    out.append(peel)
    return out


def build(collection=None, with_soup=True):
    objs = [bowl(collection)]
    if with_soup:
        objs.append(soup(collection))
        objs.extend(garnish(collection))
    return {
        "name": "椀物",
        "objects": objs,
        "focus": Vector((0.0, 0.0, 0.038)),
        "radius": 0.062,
        "height": RIM_Z,
    }
