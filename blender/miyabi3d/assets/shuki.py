"""酒器 — 白磁の徳利と猪口。口縁に呉須の一本線を回す."""

from __future__ import annotations

from mathutils import Vector

from .. import materials as MAT
from .. import modeling as M

TOKKURI = [(0.0225, 0.0070), (0.0300, 0.0215), (0.0358, 0.0400), (0.0372, 0.0560),
           (0.0338, 0.0710), (0.0248, 0.0855), (0.0176, 0.0975), (0.0168, 0.1090),
           (0.0203, 0.1215)]
CHOKO = [(0.0148, 0.0042), (0.0192, 0.0140), (0.0222, 0.0268), (0.0238, 0.0392)]


def _porcelain():
    return MAT.ceramic(color=(0.735, 0.735, 0.715), roughness=0.075, speckle=0.12,
                       name="白磁")


def _gosu():
    return MAT.ceramic(color=(0.038, 0.062, 0.185), roughness=0.10, name="呉須")


def tokkuri(collection=None):
    profile, zones = M.vessel_profile(TOKKURI, thickness=0.0024, foot_width=0.0050,
                                      base_thickness=0.0032, rim_steps=3)
    top = max(z for _, z in profile)

    def rule(i, label):
        if label in ('outer', 'rim') and profile[i][1] >= top - 0.0062:
            return 2
        return None

    slots = M.zone_slots(zones, {'under': 0, 'outer': 0, 'rim': 2, 'inner': 1}, rule)
    obj = M.revolve(profile, 128, "徳利", smooth_angle=30, collection=collection,
                    slots=slots)
    M.set_material(obj, _porcelain(), _porcelain(), _gosu())
    return obj


def choko(x=0.0, y=0.0, spin=0.0, filled=True, collection=None):
    out = []
    profile, zones = M.vessel_profile(CHOKO, thickness=0.0020, foot_width=0.0038,
                                      base_thickness=0.0028, rim_steps=3)
    top = max(z for _, z in profile)

    def rule(i, label):
        if label in ('outer', 'rim') and profile[i][1] >= top - 0.0034:
            return 2
        return None

    slots = M.zone_slots(zones, {'under': 0, 'outer': 0, 'rim': 2, 'inner': 1}, rule)
    cup = M.revolve(profile, 96, "猪口", smooth_angle=30, collection=collection,
                    slots=slots)
    M.set_material(cup, _porcelain(), _porcelain(), _gosu())
    M.place(cup, (x, y, 0.0), (0, 0, spin))
    out.append(cup)

    if filled:
        level = top - 0.0075
        inner = sorted([(r - 0.0004, z) for (r, z), label
                        in zip(profile, zones + zones[-1:])
                        if label == 'inner' and z <= level], key=lambda p: p[1])
        surface_r = inner[-1][0]
        sake = M.revolve(M.chain([(0.0, inner[0][1] + 0.0002)], inner,
                                 [(surface_r, level), (0.0, level)]),
                         96, "酒", 18, collection)
        M.set_material(sake, MAT.dashi(color=(0.90, 0.86, 0.66), density=4.0,
                                       cloud=0.02, tint=(0.92, 0.90, 0.80),
                                       name="酒"))
        M.place(sake, (x, y, 0.0))
        out.append(sake)
    return out


def build(collection=None, cups=2):
    objs = [tokkuri(collection)]
    spots = ((0.0585, -0.0215, 14), (0.0480, 0.0395, -32))
    for i in range(min(cups, len(spots))):
        x, y, spin = spots[i]
        objs += choko(x, y, spin, collection=collection)
    return {
        "name": "酒器",
        "objects": objs,
        "focus": Vector((0.022, 0.0, 0.048)),
        "radius": 0.072,
        "height": 0.1215,
    }
