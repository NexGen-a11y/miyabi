"""シーンづくり — レンダ設定・ライティング・カメラ・書き出し."""

from __future__ import annotations

import math
import os
from typing import Iterable, Sequence

import bpy
from mathutils import Euler, Vector

from . import modeling as M


# --------------------------------------------------------------------------
# シーン初期化
# --------------------------------------------------------------------------
def reset():
    """既定のシーンを空にする (bpy モジュールは起動時の Cube などを持つ)."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.curves, bpy.data.textures,
                 bpy.data.images, bpy.data.node_groups):
        for item in list(coll):
            if getattr(item, "users", 0) == 0 or True:
                try:
                    coll.remove(item, do_unlink=True)
                except (ReferenceError, RuntimeError):
                    pass
    from . import materials
    materials.reset_cache()
    return bpy.context.scene


# --------------------------------------------------------------------------
# レンダ設定
# --------------------------------------------------------------------------
def _apply(target, **kwargs):
    """バージョン差のあるプロパティを黙って読み飛ばしながら設定する."""
    for key, value in kwargs.items():
        try:
            setattr(target, key, value)
        except (AttributeError, TypeError):
            pass
    return target


def configure(width=1600, height=1200, samples=96, transparent=False,
              exposure=0.0, look="Punchy", max_bounces=12, clamp_indirect=8.0,
              scene=None):
    sc = scene or bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    _apply(cy, device='CPU', samples=samples, use_adaptive_sampling=True,
           adaptive_threshold=0.012, use_denoising=True,
           max_bounces=max_bounces, diffuse_bounces=4, glossy_bounces=6,
           transmission_bounces=10, transparent_max_bounces=12, volume_bounces=2,
           sample_clamp_indirect=clamp_indirect, blur_glossy=1.0,
           caustics_refractive=True, use_auto_tile=True)
    for denoiser in ('OPENIMAGEDENOISE', 'OPTIX'):
        try:
            cy.denoiser = denoiser
            break
        except (TypeError, AttributeError):
            continue

    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.use_persistent_data = True

    view = sc.view_settings
    view.exposure = exposure
    for name in ("AgX", "Filmic", "Standard"):
        try:
            view.view_transform = name
            break
        except TypeError:
            continue
    for candidate in (look, f"AgX - {look}", "AgX - Punchy", "Punchy",
                      "Medium High Contrast", "None"):
        try:
            view.look = candidate
            break
        except TypeError:
            continue
    return sc


def color_management(look=None, exposure=None, gamma=None, scene=None):
    view = (scene or bpy.context.scene).view_settings
    if exposure is not None:
        view.exposure = exposure
    if gamma is not None:
        view.gamma = gamma
    if look is not None:
        for candidate in (look, f"AgX - {look}", "None"):
            try:
                view.look = candidate
                break
            except TypeError:
                continue


# --------------------------------------------------------------------------
# ワールド
# --------------------------------------------------------------------------
def world(strength=0.18, zenith=(0.19, 0.20, 0.25), horizon=(0.055, 0.048, 0.046),
          ground=(0.008, 0.007, 0.007), scene=None):
    sc = scene or bpy.context.scene
    wd = bpy.data.worlds.get("雅") or bpy.data.worlds.new("雅")
    sc.world = wd
    wd.use_nodes = True
    nt = wd.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    out.location = (300, 0)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.location = (100, 0)
    bg.inputs["Strength"].default_value = strength
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (-700, 0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-500, 0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-300, 0)
    elements = ramp.color_ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    elements[0].position = 0.0
    elements[0].color = (*ground, 1)
    for pos, col in ((0.48, horizon), (0.54, horizon), (1.0, zenith)):
        el = elements.new(pos)
        el.color = (*col, 1)
    # 方向ベクトル Z(-1..1) を 0..1 に写す
    mapr = nt.nodes.new("ShaderNodeMapRange")
    mapr.location = (-420, -200)
    mapr.inputs["From Min"].default_value = -1.0
    mapr.inputs["From Max"].default_value = 1.0
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mapr.inputs["Value"])
    nt.links.new(mapr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    return wd


# --------------------------------------------------------------------------
# ライト
# --------------------------------------------------------------------------
def _aim(obj, target):
    direction = Vector(target) - obj.location
    if direction.length < 1e-9:
        return obj
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return obj


def area_light(name="key", location=(0.5, -0.5, 0.7), target=(0, 0, 0.05),
               size=0.9, energy=120.0, color=(1.0, 0.96, 0.92), shape='SQUARE',
               size_y=None, spread=math.pi / 2):
    data = bpy.data.lights.new(name, type='AREA')
    data.shape = shape
    data.size = size
    if size_y is not None:
        data.size_y = size_y
    data.energy = energy
    data.color = color
    data.spread = spread
    obj = M.link(bpy.data.objects.new(name, data))
    obj.location = location
    return _aim(obj, target)


def point_light(name="accent", location=(0, 0, 0.3), energy=8.0,
                color=(1.0, 0.72, 0.42), radius=0.02):
    data = bpy.data.lights.new(name, type='POINT')
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = M.link(bpy.data.objects.new(name, data))
    obj.location = location
    return obj


def _watts(irradiance: float, distance: float) -> float:
    """狙った照度 (W/m^2) と距離からエリアライトのワット数を逆算する.

    被写体が 6cm でも 60cm でも同じ絵になるよう、明るさは距離の二乗で効かせる。
    """
    return irradiance * 4.0 * math.pi * max(distance, 1e-3) ** 2


def studio(target=(0, 0, 0.04), radius=0.065, key=1.25, fill=0.18, rim=1.7,
           overhead=0.32, softness=2.4, warm=(1.0, 0.92, 0.82), cool=(0.74, 0.82, 1.0),
           key_dir=(2.3, 1.7, 2.9), fill_dir=(-2.9, -2.3, 0.9),
           rim_dir=(-0.9, 3.2, 1.3), overhead_dir=(0.35, -1.15, 3.3)):
    """料理撮影の定番 — 斜め後ろからの大きなキー、弱いフィル、輪郭のリム.

    位置も光源サイズも被写体半径の倍数で決めるので、
    椀でも土鍋でも同じ光の回り方になる。照度の既定値は、
    反射率 0.18 の面が中間調に落ちるところを実測して決めた。
    """
    t = Vector(target)
    out = []
    rig = [("key", key_dir, key, softness, warm),
           ("fill", fill_dir, fill, softness * 1.5, cool),
           ("rim", rim_dir, rim, softness * 0.42, (1.0, 0.86, 0.68))]
    if overhead > 0:
        # 汁物の水面や釉薬に映り込む天トレ。これがないと液体が death black になる
        rig.append(("overhead", overhead_dir, overhead, softness * 1.9,
                    (1.0, 0.95, 0.88)))
    for name, direction, irradiance, size, color in rig:
        offset = Vector(direction) * radius
        distance = offset.length
        out.append(area_light(name, tuple(t + offset), target,
                              size=size * radius,
                              energy=_watts(irradiance, distance), color=color))
    return out


# --------------------------------------------------------------------------
# 影だけを拾う床
# --------------------------------------------------------------------------
def shadow_floor(size=3.0, z=0.0, name="影床"):
    """接地影だけを残す床。二次光線からは隠して映り込みを断つ.

    これをやらないと黒漆の器が白い床を鏡のように映してしまう。
    """
    from . import materials
    obj = M.grid((size, size), (2, 2), name)
    obj.location.z = z
    _apply(obj, is_shadow_catcher=True, visible_diffuse=False,
           visible_glossy=False, visible_transmission=False,
           visible_volume_scatter=False)
    M.set_material(obj, materials.ceramic(color=(0.5, 0.5, 0.5), roughness=0.9,
                                          name="影床"))
    return obj


# --------------------------------------------------------------------------
# カメラ
# --------------------------------------------------------------------------
def camera(target=(0, 0, 0.04), distance=0.55, azimuth=-58.0, elevation=24.0,
           focal=90.0, fstop=None, focus=None, shift=(0.0, 0.0), name="camera",
           sensor=36.0):
    data = bpy.data.cameras.new(name)
    data.lens = focal
    data.sensor_width = sensor
    data.shift_x, data.shift_y = shift
    data.clip_start = 0.005
    data.clip_end = 100.0
    obj = M.link(bpy.data.objects.new(name, data))
    t = Vector(target)
    az, el = math.radians(azimuth), math.radians(elevation)
    obj.location = t + Vector((distance * math.cos(el) * math.cos(az),
                               distance * math.cos(el) * math.sin(az),
                               distance * math.sin(el)))
    _aim(obj, t)
    if fstop:
        data.dof.use_dof = True
        data.dof.aperture_fstop = fstop
        data.dof.focus_distance = focus if focus else (obj.location - t).length
        data.dof.aperture_blades = 7
    bpy.context.scene.camera = obj
    return obj


def frame(cam, objs: Iterable[bpy.types.Object], margin=1.12, keep_direction=True):
    """対象のバウンディングボックスが収まるところまでカメラを引く."""
    sc = bpy.context.scene
    lo, hi = M.bounds(list(objs))
    center = (lo + hi) * 0.5
    radius = max((hi - lo).length * 0.5, 1e-4)
    aspect = sc.render.resolution_x / max(sc.render.resolution_y, 1)
    fov = 2.0 * math.atan(cam.data.sensor_width / (2.0 * cam.data.lens))
    if aspect < 1.0:
        fov = 2.0 * math.atan(math.tan(fov / 2.0) * aspect)
    dist = radius * margin / math.sin(min(fov / 2.0, 1.2))
    direction = (cam.location - center)
    if keep_direction and direction.length > 1e-9:
        direction.normalize()
    else:
        direction = Vector((0, -1, 0.4)).normalized()
    cam.location = center + direction * dist
    _aim(cam, center)
    if cam.data.dof.use_dof:
        cam.data.dof.focus_distance = (cam.location - center).length
    return cam


# --------------------------------------------------------------------------
# 書き出し
# --------------------------------------------------------------------------
EXT_FORMAT = {".webp": 'WEBP', ".png": 'PNG', ".jpg": 'JPEG', ".jpeg": 'JPEG'}


def render(path: str, fmt=None, quality=90, scene=None):
    sc = scene or bpy.context.scene
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fmt = fmt or EXT_FORMAT.get(os.path.splitext(path)[1].lower(), 'WEBP')
    img = sc.render.image_settings
    img.file_format = fmt
    img.color_mode = 'RGBA' if sc.render.film_transparent else 'RGB'
    if fmt in {'WEBP', 'JPEG'}:
        img.quality = quality
    if fmt == 'PNG':
        img.compression = 20
        img.color_depth = '8'
    stem, ext = os.path.splitext(path)
    sc.render.filepath = stem
    bpy.ops.render.render(write_still=True)
    produced = stem + {'WEBP': '.webp', 'PNG': '.png', 'JPEG': '.jpg'}[fmt]
    if produced != path and os.path.exists(produced):
        os.replace(produced, path)
    return path


def turntable(objs: Sequence[bpy.types.Object], out_dir: str, frames=36,
              prefix="frame", fmt="WEBP", quality=88, axis='Z'):
    """対象を回してコマ撮りする。ライトは固定なので回転体のショールームになる."""
    pivot = M.empty("turntable")
    M.parent_to(objs, pivot)
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i in range(frames):
        angle = 2.0 * math.pi * i / frames
        pivot.rotation_euler = Euler((0, 0, angle) if axis == 'Z' else (angle, 0, 0), 'XYZ')
        bpy.context.view_layer.update()
        paths.append(render(os.path.join(out_dir, f"{prefix}-{i:02d}.{fmt.lower()}"),
                            fmt=fmt, quality=quality))
    pivot.rotation_euler = Euler((0, 0, 0), 'XYZ')
    return paths


def export_glb(objs: Sequence[bpy.types.Object], path: str, apply_modifiers=True):
    """Web ビューア用に glTF-Binary を書き出す."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    for obj in bpy.data.objects:
        obj.select_set(False)
    meshes = [o for o in objs if o.type in {'MESH', 'CURVE', 'FONT', 'EMPTY'}]
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0] if meshes else None
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=apply_modifiers,
        export_materials='EXPORT',
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_draco_mesh_compression_enable=False,
    )
    return path
