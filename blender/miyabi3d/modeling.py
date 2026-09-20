"""ジオメトリ生成のプリミティブ.

bpy.ops はコンテキストに依存して bpy モジュール単体だと不安定なので、
メッシュ操作は原則 bmesh で完結させている。
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import bpy  # noqa: F401  (bmesh は bpy 読み込み後でないと import できない)
import bmesh
from mathutils import Vector

Profile = Sequence[tuple[float, float]]


# --------------------------------------------------------------------------
# 基本
# --------------------------------------------------------------------------
def link(obj: bpy.types.Object, collection: bpy.types.Collection | None = None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_object(name: str, verts, faces, collection=None) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata(list(verts), [], [list(f) for f in faces])
    me.validate()
    me.update()
    return link(bpy.data.objects.new(name, me), collection)


def recalc_normals(obj: bpy.types.Object, merge: float = 0.0):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if merge > 0:
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def auto_smooth(obj: bpy.types.Object, angle_deg: float = 35.0):
    """角度でシャープ辺を立てる。4.1 以降の Shade Auto Smooth 相当を bmesh で。"""
    me = obj.data
    limit = math.radians(angle_deg)
    bm = bmesh.new()
    bm.from_mesh(me)
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        sharp = True
        if len(edge.link_faces) == 2:
            try:
                sharp = edge.calc_face_angle() > limit
            except ValueError:
                sharp = False
        edge.smooth = not sharp
    bm.to_mesh(me)
    bm.free()
    me.update()


# --------------------------------------------------------------------------
# 回転体 (轆轤) — 椀・皿・湯呑・土鍋・提灯はすべてこれで挽く
# --------------------------------------------------------------------------
def revolve(profile: Profile, segments: int = 96, name: str = "revolved",
            smooth_angle: float = 35.0, collection=None,
            slots: Sequence[int] | None = None, uv: bool = False) -> bpy.types.Object:
    """(r, z) の断面を Z 軸まわりに回して閉じた立体をつくる。

    r == 0 の点は極 (1 頂点) に潰れるので、断面の始端と終端を軸上に
    置けばそのまま閉じたソリッドになる。

    slots に断面の区間ごと (len(profile)-1 個) のマテリアル番号を渡すと、
    外側は黒漆・内側は朱漆といった塗り分けができる。
    """
    verts: list[tuple[float, float, float]] = []
    rings: list[tuple[int, int]] = []
    for r, z in profile:
        if abs(r) < 1e-7:
            rings.append((len(verts), 1))
            verts.append((0.0, 0.0, z))
        else:
            rings.append((len(verts), segments))
            for s in range(segments):
                a = 2.0 * math.pi * s / segments
                verts.append((r * math.cos(a), r * math.sin(a), z))

    faces: list[tuple[int, ...]] = []
    face_slot: list[int] = []
    for i in range(len(profile) - 1):
        s0, c0 = rings[i]
        s1, c1 = rings[i + 1]
        if c0 == 1 and c1 == 1:
            continue
        slot = slots[i] if slots and i < len(slots) else 0
        if c0 == 1:
            new = [(s0, s1 + s, s1 + (s + 1) % segments) for s in range(segments)]
        elif c1 == 1:
            new = [(s0 + s, s0 + (s + 1) % segments, s1) for s in range(segments)]
        else:
            new = [(s0 + s, s0 + (s + 1) % segments,
                    s1 + (s + 1) % segments, s1 + s) for s in range(segments)]
        faces.extend(new)
        face_slot.extend([slot] * len(new))

    obj = mesh_object(name, verts, faces, collection)
    if uv:
        _cylindrical_uv(obj, verts, faces, segments, profile)
    recalc_normals(obj, merge=0.0 if uv else 1e-6)
    if slots:
        for poly, slot in zip(obj.data.polygons, face_slot):
            poly.material_index = slot
    auto_smooth(obj, smooth_angle)
    return obj


def _cylindrical_uv(obj, verts, faces, segments, profile):
    """円筒展開の UV。u が周方向、v が断面に沿った距離."""
    lengths = [0.0]
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        lengths.append(lengths[-1] + math.hypot(r1 - r0, z1 - z0))
    total = max(lengths[-1], 1e-9)
    v_of_vert: dict[int, float] = {}
    index = 0
    for i, (r, _z) in enumerate(profile):
        count = 1 if abs(r) < 1e-7 else segments
        for _ in range(count):
            v_of_vert[index] = lengths[i] / total
            index += 1
    layer = obj.data.uv_layers.new(name="UVMap")
    loop_index = 0
    for face in faces:
        base = None
        for vert in face:
            angle = math.atan2(verts[vert][1], verts[vert][0])
            u = (angle / (2.0 * math.pi)) % 1.0
            if base is None:
                base = u
            elif u - base > 0.5:
                u -= 1.0
            elif base - u > 0.5:
                u += 1.0
            layer.data[loop_index].uv = (u, v_of_vert.get(vert, 0.0))
            loop_index += 1
    return layer


# --------------------------------------------------------------------------
# 箱・板
# --------------------------------------------------------------------------
def rounded_box(size=(1.0, 1.0, 1.0), bevel=0.05, segments=4, subsurf=1,
                name="box", collection=None) -> bpy.types.Object:
    sx, sy, sz = (v / 2.0 for v in size)
    verts = [(x * sx, y * sy, z * sz)
             for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    obj = mesh_object(name, verts, faces, collection)
    recalc_normals(obj)
    if bevel > 0:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges),
                        offset=bevel, segments=segments, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
        bm.to_mesh(obj.data)
        bm.free()
        recalc_normals(obj, merge=1e-6)
    if subsurf:
        add_subsurf(obj, subsurf, subsurf)
    auto_smooth(obj, 40)
    return obj


def plank(size=(1.0, 1.0, 1.0), bevel=0.002, name="plank", collection=None):
    return rounded_box(size, bevel=bevel, segments=3, subsurf=0,
                       name=name, collection=collection)


def cylinder(radius=0.05, height=0.1, segments=64, cap_bevel=0.0,
             name="cylinder", collection=None) -> bpy.types.Object:
    r, h = radius, height / 2.0
    b = min(cap_bevel, radius * 0.9, height * 0.45)
    if b > 0:
        prof = [(0, -h), (r - b, -h), (r, -h + b), (r, h - b), (r - b, h), (0, h)]
    else:
        prof = [(0, -h), (r, -h), (r, h), (0, h)]
    return revolve(prof, segments, name, 40, collection)


def torus(major=0.05, minor=0.005, major_seg=72, minor_seg=16,
          name="torus", collection=None) -> bpy.types.Object:
    verts, faces = [], []
    for i in range(major_seg):
        a = 2 * math.pi * i / major_seg
        ca, sa = math.cos(a), math.sin(a)
        for j in range(minor_seg):
            b = 2 * math.pi * j / minor_seg
            rr = major + minor * math.cos(b)
            verts.append((rr * ca, rr * sa, minor * math.sin(b)))
    for i in range(major_seg):
        ii = (i + 1) % major_seg
        for j in range(minor_seg):
            jj = (j + 1) % minor_seg
            faces.append((i * minor_seg + j, ii * minor_seg + j,
                          ii * minor_seg + jj, i * minor_seg + jj))
    obj = mesh_object(name, verts, faces, collection)
    recalc_normals(obj)
    auto_smooth(obj, 60)
    return obj


def grid(size=(1.0, 1.0), res=(24, 24), name="grid", collection=None):
    nx, ny = res
    sx, sy = size
    verts = [(-sx / 2 + sx * i / (nx - 1), -sy / 2 + sy * j / (ny - 1), 0.0)
             for j in range(ny) for i in range(nx)]
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i)
             for j in range(ny - 1) for i in range(nx - 1)]
    obj = mesh_object(name, verts, faces, collection)
    recalc_normals(obj)
    return obj


# --------------------------------------------------------------------------
# モディファイア
# --------------------------------------------------------------------------
def add_subsurf(obj, levels=2, render_levels=2, simple=False):
    m = obj.modifiers.new("Subdivision", 'SUBSURF')
    m.levels = levels
    m.render_levels = render_levels
    m.subdivision_type = 'SIMPLE' if simple else 'CATMULL_CLARK'
    return m


def add_solidify(obj, thickness=0.001, offset=-1.0):
    m = obj.modifiers.new("Solidify", 'SOLIDIFY')
    m.thickness = thickness
    m.offset = offset
    return m


def noise_texture(name, size=0.2, contrast=1.0, intensity=1.0, ttype='CLOUDS',
                  noise_depth=2, noise_basis='VORONOI_F1'):
    tex = bpy.data.textures.new(name, type=ttype)
    tex.noise_scale = size
    tex.contrast = contrast
    tex.intensity = intensity
    if ttype == 'CLOUDS':
        tex.noise_depth = noise_depth
        try:
            tex.noise_basis = noise_basis
        except TypeError:
            pass
    return tex


def add_displace(obj, tex, strength=0.001, mid_level=0.5, coords='LOCAL'):
    m = obj.modifiers.new("Displace", 'DISPLACE')
    m.texture = tex
    m.strength = strength
    m.mid_level = mid_level
    m.texture_coords = coords
    return m


def apply_modifiers(obj):
    """モディファイアを評価済みメッシュとして焼き込む (glTF 書き出し前などに)。"""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.clear()
    old = obj.data
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------
def place(obj, location=(0, 0, 0), rotation=(0, 0, 0), scale=None):
    obj.location = location
    obj.rotation_euler = tuple(math.radians(a) for a in rotation)
    if scale is not None:
        obj.scale = scale if isinstance(scale, (tuple, list)) else (scale,) * 3
    return obj


def set_material(obj, *mats, slot_clear=True):
    """マテリアルを割り当てる。複数渡すとスロット 0,1,2… の順に入る.

    materials.clear() は面のスロット番号まで 0 に戻してしまうので、
    revolve(slots=...) で塗り分けた面が潰れないよう退避して戻す。
    """
    me = obj.data
    saved = [poly.material_index for poly in me.polygons]
    if slot_clear:
        me.materials.clear()
    for mat in mats:
        me.materials.append(mat)
    if saved and len(me.materials) > 1:
        limit = len(me.materials) - 1
        for poly, index in zip(me.polygons, saved):
            poly.material_index = min(index, limit)
    return obj


def parent_to(children: Iterable[bpy.types.Object], parent: bpy.types.Object):
    for c in children:
        if c is parent:
            continue
        c.parent = parent
        c.matrix_parent_inverse = parent.matrix_world.inverted()
    return parent


def empty(name="root", location=(0, 0, 0), collection=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.05
    obj.location = location
    return link(obj, collection)


def bounds(objs) -> tuple[Vector, Vector]:
    # place() 直後は matrix_world が古いままなので、測る前に評価し直す
    bpy.context.view_layer.update()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != 'MESH':
            continue
        for corner in o.bound_box:
            w = o.matrix_world @ Vector(corner)
            lo = Vector((min(lo[i], w[i]) for i in range(3)))
            hi = Vector((max(hi[i], w[i]) for i in range(3)))
    return lo, hi


# --------------------------------------------------------------------------
# 断面づくり (轆轤用のプロファイル)
# --------------------------------------------------------------------------
def arc(center=(0.0, 0.0), radius=0.05, a0=0.0, a1=90.0, steps=12,
        radius_z=None) -> list[tuple[float, float]]:
    """(r, z) 平面上の円弧/楕円弧。角度は度、0 度が +r 方向."""
    cr, cz = center
    rz = radius_z if radius_z is not None else radius
    out = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        out.append((cr + radius * math.cos(a), cz + rz * math.sin(a)))
    return out


def offset_profile(points: Profile, distance: float) -> list[tuple[float, float]]:
    """(r, z) の折れ線を法線方向にずらす。器の内壁を一定の肉厚で掘るのに使う.

    正の distance で外向き (r が増える向き)、負で内向き。
    """
    pts = [Vector(p) for p in points]
    out: list[tuple[float, float]] = []
    for i, p in enumerate(pts):
        prev = pts[max(i - 1, 0)]
        nxt = pts[min(i + 1, len(pts) - 1)]
        tangent = (nxt - prev)
        if tangent.length < 1e-9:
            tangent = Vector((0.0, 1.0))
        tangent.normalize()
        normal = Vector((tangent.y, -tangent.x))
        q = p + normal * distance
        out.append((max(q.x, 0.0), q.y))
    return out


def chain(*parts) -> list[tuple[float, float]]:
    """断面の断片をつなぐ。重複した端点は落とす."""
    out: list[tuple[float, float]] = []
    for part in parts:
        seq = [part] if isinstance(part, tuple) and len(part) == 2 and \
            isinstance(part[0], (int, float)) else list(part)
        for p in seq:
            if out and abs(out[-1][0] - p[0]) < 1e-9 and abs(out[-1][1] - p[1]) < 1e-9:
                continue
            out.append((float(p[0]), float(p[1])))
    return out


# --------------------------------------------------------------------------
# 葉・花 — 添えものの形
# --------------------------------------------------------------------------
def leaf(length=0.035, width=0.016, steps=18, rings=7, curl=0.28, tip=1.7,
         thickness=0.0004, name="leaf", collection=None) -> bpy.types.Object:
    """先の尖った葉。長手方向にゆるく反らせる."""
    verts, faces = [], []
    for i in range(steps + 1):
        t = i / steps
        half = width * 0.5 * max(math.sin(math.pi * t ** 0.78), 0.0) ** (1.0 / tip)
        z = curl * length * (t - 0.42) ** 2 - curl * length * 0.18
        for j in range(rings):
            u = -1.0 + 2.0 * j / (rings - 1)
            verts.append((t * length - length * 0.5, u * half,
                          z + abs(u) ** 2 * width * 0.10))
    for i in range(steps):
        for j in range(rings - 1):
            a = i * rings + j
            faces.append((a, a + rings, a + rings + 1, a + 1))
    obj = mesh_object(name, verts, faces, collection)
    recalc_normals(obj, merge=1e-6)
    add_solidify(obj, thickness, offset=0.0)
    auto_smooth(obj, 55)
    return obj


def blossom(radius=0.010, petals=5, lobe=0.26, thickness=0.004, rings=5,
            segments=96, name="花", collection=None) -> bpy.types.Object:
    """梅花麩のような花形の板。r(θ) を花弁の数で揺らす."""
    verts, faces = [], []
    half = thickness * 0.5
    for k in range(rings):
        t = k / (rings - 1)
        z = math.cos(math.pi * t) * half
        shrink = max(math.sin(math.pi * t), 0.0) ** 0.35
        for s in range(segments):
            a = 2 * math.pi * s / segments
            r = radius * (1.0 - lobe + lobe * math.cos(petals * a)) * shrink
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for k in range(rings - 1):
        for s in range(segments):
            n = (s + 1) % segments
            faces.append((k * segments + s, k * segments + n,
                          (k + 1) * segments + n, (k + 1) * segments + s))
    obj = mesh_object(name, verts, faces, collection)
    recalc_normals(obj, merge=1e-5)
    auto_smooth(obj, 50)
    return obj


def text_mesh(body: str, font_path: str, size=0.05, extrude=0.004, bevel=0.0008,
              name="text", align='CENTER', collection=None) -> bpy.types.Object:
    """日本語フォントを立体にする (金の「雅」用)."""
    data = bpy.data.curves.new(name, type='FONT')
    data.body = body
    data.size = size
    data.extrude = extrude
    data.bevel_depth = bevel
    data.bevel_resolution = 3
    data.align_x = align
    data.align_y = 'CENTER'
    font = bpy.data.fonts.load(font_path, check_existing=True)
    data.font = font
    obj = link(bpy.data.objects.new(name, data), collection)
    return obj


# --------------------------------------------------------------------------
# 器 — 外形の曲線から肉厚のある器の断面を起こす
# --------------------------------------------------------------------------
def bell_curve(foot_radius, rim_radius, foot_z, rim_z, steps=26, ease=1.85):
    """高台から口縁へ向かう椀形の外側曲線。ease が大きいほど腰が張る."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        r = foot_radius + (rim_radius - foot_radius) * (1.0 - (1.0 - t) ** ease)
        out.append((r, foot_z + (rim_z - foot_z) * t))
    return out


def vessel_profile(outer: Profile, thickness=0.0020, foot_width=0.0040,
                   foot_height=None, base_thickness=0.0022, rim_steps=3):
    """外側の曲線から、高台・口縁・内壁まで閉じた回転断面をつくる.

    返り値は (断面, 区間ラベル) で、ラベルは 'under' / 'outer' / 'rim' /
    'inner' のいずれか。呼び出し側でラベルごとにマテリアルを割り当てる。
    """
    outer = [(float(r), float(z)) for r, z in outer]
    inner = offset_profile(outer, -thickness)
    foot_r = outer[0][0]
    foot_h = outer[0][1] if foot_height is None else foot_height
    ceiling = max(foot_h * 0.45, foot_h - base_thickness * 0.5)
    under = [(0.0, ceiling),
             (max(foot_r - foot_width - 0.0025, 0.0), ceiling),
             (max(foot_r - foot_width, 0.0), ceiling * 0.5),
             (max(foot_r - foot_width, 0.0), 0.0),
             (foot_r, 0.0)]

    tip_o, tip_i = outer[-1], inner[-1]
    rim = []
    for i in range(1, rim_steps + 1):
        t = i / (rim_steps + 1)
        rim.append((tip_o[0] + (tip_i[0] - tip_o[0]) * t,
                    tip_o[1] + (tip_i[1] - tip_o[1]) * t
                    + math.sin(math.pi * t) * thickness * 0.5))

    inner_rev = list(reversed(inner))
    floor_z = max(ceiling + base_thickness, inner_rev[-1][1])
    parts = [(under, 'under'), (outer, 'outer'), (rim, 'rim'),
             (inner_rev, 'inner'), ([(0.0, floor_z)], 'inner')]

    profile: list[tuple[float, float]] = []
    zones: list[str] = []
    for points, label in parts:
        for p in points:
            if profile and abs(profile[-1][0] - p[0]) < 1e-9 \
                    and abs(profile[-1][1] - p[1]) < 1e-9:
                continue
            if profile:
                zones.append(label)
            profile.append((float(p[0]), float(p[1])))
    return profile, zones


def zone_slots(zones, mapping, rule=None):
    """区間ラベルをマテリアルスロット番号に変換する.

    rule(index, label) が None 以外を返せばそれを優先する (金の口縁など)。
    """
    slots = []
    for i, label in enumerate(zones):
        slot = rule(i, label) if rule else None
        slots.append(mapping.get(label, 0) if slot is None else slot)
    return slots


def to_mesh(obj: bpy.types.Object, name=None) -> bpy.types.Object:
    """カーブ/テキストをメッシュに変換する (glTF 書き出しと bmesh 処理のため)."""
    if obj.type == 'MESH':
        return obj
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    me.name = name or obj.name
    new = link(bpy.data.objects.new(name or obj.name, me))
    new.matrix_world = obj.matrix_world.copy()
    bpy.data.objects.remove(obj, do_unlink=True)
    return new


def taper_bar(length=0.23, base=0.0062, tip=0.0022, sections=14, corners=4,
              round_amount=0.35, name="bar", collection=None) -> bpy.types.Object:
    """元が四角、先が細い棒 — 箸のための単純なロフト."""
    verts, faces = [], []
    ring = max(corners * 4, 8)
    for i in range(sections + 1):
        t = i / sections
        half = (base + (tip - base) * t ** 1.25) * 0.5
        for j in range(ring):
            a = 2 * math.pi * j / ring
            ca, sa = math.cos(a), math.sin(a)
            # 角の丸い正方形 (superellipse)
            p = 2.0 + round_amount * 8.0
            x = math.copysign(abs(ca) ** (2.0 / p), ca)
            y = math.copysign(abs(sa) ** (2.0 / p), sa)
            verts.append((x * half, y * half, t * length))
    for i in range(sections):
        for j in range(ring):
            n = (j + 1) % ring
            faces.append((i * ring + j, i * ring + n,
                          (i + 1) * ring + n, (i + 1) * ring + j))
    base_centre = len(verts)
    verts.append((0.0, 0.0, 0.0))
    tip_centre = len(verts)
    verts.append((0.0, 0.0, length))
    for j in range(ring):
        n = (j + 1) % ring
        faces.append((base_centre, n, j))
        faces.append((tip_centre, sections * ring + j, sections * ring + n))
    obj = mesh_object(name, verts, faces, collection)
    recalc_normals(obj, merge=1e-6)
    auto_smooth(obj, 40)
    return obj


def dome(radius=0.08, height=0.05, steps=18, segments=96, flatten=0.0,
         name="dome", collection=None) -> bpy.types.Object:
    """伏せた椀形のかたまり (ご飯の盛りや蓋に)."""
    profile = [(0.0, height)]
    for i in range(1, steps + 1):
        t = i / steps
        r = radius * max(math.sin(t * math.pi / 2), 0.0) ** (1.0 - flatten * 0.5)
        z = height * max(math.cos(t * math.pi / 2), 0.0) ** (1.0 + flatten)
        profile.append((r, z))
    profile.append((radius, 0.0))
    profile.append((0.0, 0.0))
    return revolve(profile, segments, name, 40, collection)
