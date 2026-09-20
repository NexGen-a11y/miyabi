"""マテリアル一式 — 漆・金・檜・陶・出汁・和紙 など.

すべて手続き的ノードで組んでおり、外部テクスチャ画像に依存しない
(暖簾や提灯の「雅」だけは PIL で焼いた文字テクスチャを使う)。
"""

from __future__ import annotations

import bpy

from . import KIN, SHU, URUSHI

_CACHE: dict[str, bpy.types.Material] = {}


# --------------------------------------------------------------------------
# ノード用ユーティリティ
# --------------------------------------------------------------------------
def _material(name: str):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:  # Blender 6.0 以降はデフォルトでノード
        pass
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(bsdf.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return mat, nt, bsdf


def _set(bsdf, **kwargs):
    alias = {
        "base_color": "Base Color", "metallic": "Metallic", "roughness": "Roughness",
        "ior": "IOR", "alpha": "Alpha", "transmission": "Transmission Weight",
        "coat": "Coat Weight", "coat_roughness": "Coat Roughness", "coat_ior": "Coat IOR",
        "coat_tint": "Coat Tint", "sheen": "Sheen Weight", "sheen_roughness": "Sheen Roughness",
        "sheen_tint": "Sheen Tint", "subsurface": "Subsurface Weight",
        "subsurface_radius": "Subsurface Radius", "subsurface_scale": "Subsurface Scale",
        "specular": "Specular IOR Level", "specular_tint": "Specular Tint",
        "anisotropic": "Anisotropic", "emission": "Emission Color",
        "emission_strength": "Emission Strength",
    }
    for key, value in kwargs.items():
        socket = bsdf.inputs.get(alias.get(key, key))
        if socket is None:
            continue
        if socket.type == 'RGBA' and not hasattr(value, "__len__"):
            value = (value, value, value, 1.0)
        elif socket.type == 'RGBA' and len(value) == 3:
            value = (*value, 1.0)
        socket.default_value = value


def _coords(nt, kind="Object", scale=(1, 1, 1), location=(-1400, 0)):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = location
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (location[0] + 200, location[1])
    mp.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs[kind], mp.inputs["Vector"])
    return tc, mp


def _ramp(nt, stops, location=(-700, 0), interpolation='LINEAR'):
    node = nt.nodes.new("ShaderNodeValToRGB")
    node.location = location
    node.color_ramp.interpolation = interpolation
    elements = node.color_ramp.elements
    while len(elements) > 1:
        elements.remove(elements[-1])
    for i, (pos, col) in enumerate(stops):
        el = elements[0] if i == 0 else elements.new(pos)
        el.position = pos
        el.color = (*col, 1.0) if len(col) == 3 else col
    return node


def _bump(nt, bsdf, height_socket, strength=0.2, distance=0.001, location=(-350, -420)):
    bump = nt.nodes.new("ShaderNodeBump")
    bump.location = location
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return bump


def _noise(nt, vector, scale=12.0, detail=6.0, roughness=0.5, location=(-950, -400),
           distortion=0.0):
    node = nt.nodes.new("ShaderNodeTexNoise")
    node.location = location
    node.inputs["Scale"].default_value = scale
    node.inputs["Detail"].default_value = detail
    node.inputs["Roughness"].default_value = roughness
    if "Distortion" in node.inputs:
        node.inputs["Distortion"].default_value = distortion
    if vector is not None:
        nt.links.new(vector, node.inputs["Vector"])
    return node


def cached(fn):
    def wrapper(*args, **kwargs):
        key = f"{fn.__name__}:{args}:{sorted(kwargs.items())}"
        mat = _CACHE.get(key)
        if mat is not None and mat.name in bpy.data.materials:
            return mat
        mat = fn(*args, **kwargs)
        _CACHE[key] = mat
        return mat
    return wrapper


def reset_cache():
    _CACHE.clear()


# --------------------------------------------------------------------------
# 漆 — 黒漆 / 朱漆 / 蒔絵
# --------------------------------------------------------------------------
@cached
def urushi(color=URUSHI, gloss=0.055, name="漆"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=color, roughness=gloss, metallic=0.0, specular=0.6,
         coat=1.0, coat_roughness=0.02, coat_ior=1.55)
    _, mp = _coords(nt, "Object", (6, 6, 6))
    noise = _noise(nt, mp.outputs["Vector"], scale=9.0, detail=8.0, roughness=0.6)
    ramp = _ramp(nt, [(0.35, (0.35, 0.35, 0.35)), (0.65, (0.62, 0.62, 0.62))], (-700, -400))
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    _bump(nt, bsdf, ramp.outputs["Color"], strength=0.06, distance=0.0004)
    return mat


@cached
def urushi_makie(base=URUSHI, dust=KIN, name="蒔絵漆"):
    """黒漆の腰に金粉を蒔いたもの。下から上へ金が散って消える。"""
    mat, nt, bsdf = _material(name)
    _set(bsdf, roughness=0.06, coat=1.0, coat_roughness=0.02, specular=0.6)

    tc, mp = _coords(nt, "Generated", (1, 1, 1), (-1600, 200))
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-1200, 260)
    nt.links.new(mp.outputs["Vector"], sep.inputs["Vector"])
    height = _ramp(nt, [(0.02, (1, 1, 1)), (0.42, (0, 0, 0))], (-1000, 320))
    nt.links.new(sep.outputs["Z"], height.inputs["Fac"])

    speck = _noise(nt, mp.outputs["Vector"], scale=190.0, detail=2.0, roughness=0.9,
                   location=(-1200, -60))
    speck_ramp = _ramp(nt, [(0.56, (0, 0, 0)), (0.63, (1, 1, 1))], (-1000, -60))
    nt.links.new(speck.outputs["Fac"], speck_ramp.inputs["Fac"])

    mask = nt.nodes.new("ShaderNodeMath")
    mask.operation = 'MULTIPLY'
    mask.location = (-760, 120)
    nt.links.new(height.outputs["Color"], mask.inputs[0])
    nt.links.new(speck_ramp.outputs["Color"], mask.inputs[1])

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = 'RGBA'
    mix_col.location = (-480, 220)
    mix_col.inputs[6].default_value = (*base, 1.0)
    mix_col.inputs[7].default_value = (*dust, 1.0)
    nt.links.new(mask.outputs[0], mix_col.inputs[0])
    nt.links.new(mix_col.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(mask.outputs[0], bsdf.inputs["Metallic"])
    return mat


@cached
def shu_urushi(name="朱漆"):
    return urushi(color=SHU, gloss=0.08, name=name)


# --------------------------------------------------------------------------
# 金
# --------------------------------------------------------------------------
@cached
def gold(color=KIN, roughness=0.20, hammered=0.0, name="金"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=color, metallic=1.0, roughness=roughness)
    _, mp = _coords(nt, "Object", (4, 4, 4))
    noise = _noise(nt, mp.outputs["Vector"], scale=26.0, detail=5.0, roughness=0.55)
    ramp = _ramp(nt, [(0.30, (roughness * 0.55,) * 3), (0.72, (min(roughness * 1.9, 1.0),) * 3)],
                 (-700, -320))
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    if hammered > 0:
        big = _noise(nt, mp.outputs["Vector"], scale=7.0, detail=2.0, roughness=0.4,
                     location=(-950, -700))
        _bump(nt, bsdf, big.outputs["Fac"], strength=hammered, distance=0.002)
    return mat


@cached
def kinpaku_screen(name="金屏風"):
    """金屏風 — 箔の継ぎ目が見える背景用の面."""
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.72, 0.50, 0.19), metallic=1.0, roughness=0.34)
    _, mp = _coords(nt, "Object", (11, 11, 11))
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.location = (-950, 0)
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.004
    brick.inputs["Color1"].default_value = (0.78, 0.56, 0.22, 1)
    brick.inputs["Color2"].default_value = (0.68, 0.46, 0.16, 1)
    brick.inputs["Mortar"].default_value = (0.52, 0.34, 0.11, 1)
    nt.links.new(mp.outputs["Vector"], brick.inputs["Vector"])
    nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    grain = _noise(nt, mp.outputs["Vector"], scale=60.0, detail=8.0, roughness=0.7,
                   location=(-950, -420))
    ramp = _ramp(nt, [(0.35, (0.26, 0.26, 0.26)), (0.70, (0.46, 0.46, 0.46))], (-700, -420))
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    _bump(nt, bsdf, brick.outputs["Fac"], strength=0.25, distance=0.0012)
    return mat


# --------------------------------------------------------------------------
# 木
# --------------------------------------------------------------------------
def _wood(name, light, dark, scale, band_scale, roughness, coat=0.0, bump=0.3,
          direction='Y', contrast=0.5, distortion=2.4):
    """木理。板は長手に木目が走るので、縞は短手方向 (既定は Y) に変化させる.

    縞がくっきり出すぎると木というより木目調の紙に見えるので、
    明暗の差は contrast で抑えめに混ぜる。
    """
    mat, nt, bsdf = _material(name)
    _set(bsdf, roughness=roughness, coat=coat, coat_roughness=0.14, specular=0.38)
    _, mp = _coords(nt, "Object", scale)
    warp = _noise(nt, mp.outputs["Vector"], scale=1.9, detail=5.0, roughness=0.55,
                  location=(-1150, -260))
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.location = (-900, 40)
    wave.wave_type = 'BANDS'
    wave.bands_direction = direction
    wave.wave_profile = 'SIN'
    wave.inputs["Scale"].default_value = band_scale
    wave.inputs["Distortion"].default_value = distortion
    wave.inputs["Detail"].default_value = 1.6
    wave.inputs["Detail Scale"].default_value = 0.8
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    nt.links.new(warp.outputs["Fac"], wave.inputs["Phase Offset"])
    blend = tuple(light[i] + (dark[i] - light[i]) * contrast for i in range(3))
    ramp = _ramp(nt, [(0.22, blend), (0.50, light), (0.78, light),
                      (0.96, blend)], (-620, 40))
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    fine = _noise(nt, mp.outputs["Vector"], scale=190.0, detail=3.0, roughness=0.5,
                  location=(-900, -640))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'FLOAT'
    mix.location = (-620, -560)
    mix.inputs[0].default_value = 0.45
    nt.links.new(wave.outputs["Fac"], mix.inputs[2])
    nt.links.new(fine.outputs["Fac"], mix.inputs[3])
    _bump(nt, bsdf, mix.outputs[0], strength=bump, distance=0.0005)
    return mat


@cached
def hinoki(name="檜"):
    return _wood(name, (0.400, 0.294, 0.176), (0.250, 0.166, 0.090),
                 scale=(1.4, 7.0, 7.0), band_scale=3.0, roughness=0.48,
                 bump=0.22, contrast=0.42, distortion=1.8)


@cached
def keyaki(name="欅"):
    # 艶を落とさないと、浅い角度でフレネルが効いて天板が白く光ってしまう
    return _wood(name, (0.0480, 0.0248, 0.0132), (0.0185, 0.0086, 0.0046),
                 scale=(0.9, 1.7, 1.7), band_scale=0.95, roughness=0.42, coat=0.12,
                 bump=0.06, contrast=0.62, distortion=5.2)


@cached
def kuroki(name="黒木"):
    return _wood(name, (0.030, 0.021, 0.017), (0.012, 0.008, 0.007),
                 scale=(1.2, 6.0, 6.0), band_scale=2.8, roughness=0.34, bump=0.18,
                 contrast=0.5)


@cached
def bamboo(name="竹"):
    return _wood(name, (0.430, 0.352, 0.196), (0.320, 0.246, 0.122),
                 scale=(6.0, 6.0, 1.0), band_scale=5.0, roughness=0.38, coat=0.22,
                 bump=0.10, direction='Z', contrast=0.35)


# --------------------------------------------------------------------------
# 陶
# --------------------------------------------------------------------------
@cached
def ceramic(color=(0.86, 0.85, 0.80), roughness=0.11, speckle=0.0, name="磁器"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=color, roughness=roughness, specular=0.55,
         coat=0.8, coat_roughness=0.04)
    _, mp = _coords(nt, "Object", (8, 8, 8))
    if speckle > 0:
        spots = _noise(nt, mp.outputs["Vector"], scale=120.0, detail=3.0, roughness=0.8,
                       location=(-1000, 120))
        ramp = _ramp(nt, [(0.60, (*color,)), (0.68, (color[0] * 0.35, color[1] * 0.33, color[2] * 0.30))],
                     (-720, 120))
        nt.links.new(spots.outputs["Fac"], ramp.inputs["Fac"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.location = (-460, 160)
        mix.inputs[0].default_value = speckle
        mix.inputs[6].default_value = (*color, 1)
        nt.links.new(ramp.outputs["Color"], mix.inputs[7])
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    wobble = _noise(nt, mp.outputs["Vector"], scale=18.0, detail=4.0, roughness=0.5,
                    location=(-1000, -420))
    _bump(nt, bsdf, wobble.outputs["Fac"], strength=0.08, distance=0.0006)
    return mat


@cached
def clay(color=(0.055, 0.048, 0.044), roughness=0.62, name="土鍋土肌"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=color, roughness=roughness, specular=0.3)
    _, mp = _coords(nt, "Object", (7, 7, 7))
    grit = _noise(nt, mp.outputs["Vector"], scale=95.0, detail=8.0, roughness=0.75)
    _bump(nt, bsdf, grit.outputs["Fac"], strength=0.5, distance=0.0016)
    coarse = _noise(nt, mp.outputs["Vector"], scale=13.0, detail=3.0, roughness=0.5,
                    location=(-950, 40))
    ramp = _ramp(nt, [(0.35, (roughness - 0.12,) * 3), (0.7, (min(roughness + 0.22, 1),) * 3)],
                 (-700, 40))
    nt.links.new(coarse.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


@cached
def ameyu(name="飴釉"):
    """土鍋の内側などの艶のある飴釉."""
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.085, 0.052, 0.030), roughness=0.10, specular=0.6,
         coat=0.9, coat_roughness=0.05)
    _, mp = _coords(nt, "Object", (9, 9, 9))
    flow = _noise(nt, mp.outputs["Vector"], scale=16.0, detail=6.0, roughness=0.6)
    ramp = _ramp(nt, [(0.3, (0.06, 0.06, 0.06)), (0.75, (0.22, 0.22, 0.22))], (-700, -320))
    nt.links.new(flow.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    _bump(nt, bsdf, flow.outputs["Fac"], strength=0.12, distance=0.0008)
    return mat


@cached
def stone_dark(name="鉄平石"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.020, 0.020, 0.022), roughness=0.55, specular=0.35)
    _, mp = _coords(nt, "Object", (3, 3, 3))
    n1 = _noise(nt, mp.outputs["Vector"], scale=4.0, detail=9.0, roughness=0.75, distortion=1.4)
    _bump(nt, bsdf, n1.outputs["Fac"], strength=0.35, distance=0.004)
    ramp = _ramp(nt, [(0.30, (0.34, 0.34, 0.34)), (0.72, (0.66, 0.66, 0.66))], (-700, 40))
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    return mat


# --------------------------------------------------------------------------
# 料理
# --------------------------------------------------------------------------
@cached
def dashi(color=(0.20, 0.115, 0.045), density=26.0, cloud=0.0,
          tint=(0.84, 0.56, 0.20), name="出汁"):
    """澄んだ出汁。深さで色が乗るようボリューム吸収を併用.

    cloud を上げると濁りが出て、黒い器の中でも液体として見える。
    """
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=tint, roughness=0.025, ior=1.34,
         transmission=1.0 - cloud)
    absorb = nt.nodes.new("ShaderNodeVolumeAbsorption")
    absorb.location = (-300, -260)
    absorb.inputs["Color"].default_value = (*color, 1)
    absorb.inputs["Density"].default_value = density
    nt.links.new(absorb.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    return mat


@cached
def shoyu(name="醤油"):
    return dashi(color=(0.085, 0.030, 0.012), density=140.0, name=name)


@cached
def rice(name="米"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.830, 0.808, 0.758), roughness=0.33, specular=0.45,
         subsurface=0.30, subsurface_radius=(0.9, 0.80, 0.72), subsurface_scale=0.0014,
         coat=0.30, coat_roughness=0.20)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    grains = nt.nodes.new("ShaderNodeTexVoronoi")
    grains.location = (-950, -300)
    grains.inputs["Scale"].default_value = 210.0
    nt.links.new(mp.outputs["Vector"], grains.inputs["Vector"])
    _bump(nt, bsdf, grains.outputs["Distance"], strength=0.55, distance=0.0012)
    return mat


@cached
def maguro(name="鮪"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.168, 0.0135, 0.0125), roughness=0.26, specular=0.55,
         subsurface=0.22, subsurface_radius=(0.9, 0.22, 0.18), subsurface_scale=0.0022,
         coat=0.35, coat_roughness=0.13)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    sinew = nt.nodes.new("ShaderNodeTexWave")
    sinew.location = (-950, 60)
    sinew.wave_type = 'BANDS'
    sinew.bands_direction = 'Y'
    sinew.wave_profile = 'SIN'
    sinew.inputs["Scale"].default_value = 26.0
    sinew.inputs["Distortion"].default_value = 5.5
    sinew.inputs["Detail"].default_value = 3.0
    nt.links.new(mp.outputs["Vector"], sinew.inputs["Vector"])
    ramp = _ramp(nt, [(0.74, (0.168, 0.0135, 0.0125)), (0.93, (0.345, 0.088, 0.076))], (-700, 60))
    nt.links.new(sinew.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _bump(nt, bsdf, sinew.outputs["Fac"], strength=0.10, distance=0.0004)
    return mat


@cached
def salmon(name="鮭"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, roughness=0.24, specular=0.55, subsurface=0.26,
         subsurface_radius=(0.9, 0.45, 0.26), subsurface_scale=0.0024,
         coat=0.35, coat_roughness=0.12)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    stripes = nt.nodes.new("ShaderNodeTexWave")
    stripes.location = (-950, 60)
    stripes.wave_type = 'BANDS'
    stripes.bands_direction = 'Y'
    stripes.wave_profile = 'SIN'
    stripes.inputs["Scale"].default_value = 15.0
    stripes.inputs["Distortion"].default_value = 3.0
    stripes.inputs["Detail"].default_value = 2.0
    nt.links.new(mp.outputs["Vector"], stripes.inputs["Vector"])
    ramp = _ramp(nt, [(0.40, (0.560, 0.148, 0.038)), (0.585, (0.760, 0.520, 0.395)),
                      (0.72, (0.560, 0.148, 0.038))], (-700, 60))
    nt.links.new(stripes.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _bump(nt, bsdf, stripes.outputs["Fac"], strength=0.14, distance=0.0005)
    return mat


@cached
def tamago(name="玉子"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.680, 0.408, 0.062), roughness=0.38, specular=0.40,
         subsurface=0.24, subsurface_radius=(0.9, 0.55, 0.20), subsurface_scale=0.0025)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    pores = _noise(nt, mp.outputs["Vector"], scale=120.0, detail=5.0, roughness=0.7)
    _bump(nt, bsdf, pores.outputs["Fac"], strength=0.25, distance=0.0006)
    return mat


@cached
def ebi(name="海老"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, roughness=0.22, specular=0.6, subsurface=0.3,
         subsurface_radius=(0.9, 0.42, 0.34), subsurface_scale=0.0026,
         coat=0.45, coat_roughness=0.10)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    band = nt.nodes.new("ShaderNodeTexWave")
    band.location = (-950, 60)
    band.wave_type = 'BANDS'
    band.bands_direction = 'Y'
    band.inputs["Scale"].default_value = 9.0
    band.inputs["Distortion"].default_value = 1.2
    nt.links.new(mp.outputs["Vector"], band.inputs["Vector"])
    ramp = _ramp(nt, [(0.30, (0.80, 0.76, 0.70)), (0.62, (0.62, 0.075, 0.042))], (-700, 60))
    nt.links.new(band.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


@cached
def nori(name="海苔"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.012, 0.018, 0.014), roughness=0.44, specular=0.35,
         anisotropic=0.4)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    fibre = _noise(nt, mp.outputs["Vector"], scale=180.0, detail=6.0, roughness=0.8)
    _bump(nt, bsdf, fibre.outputs["Fac"], strength=0.4, distance=0.0004)
    return mat


@cached
def greens(color=(0.040, 0.125, 0.028), roughness=0.38, name="青味"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=color, roughness=roughness, specular=0.45,
         subsurface=0.22, subsurface_radius=(0.003, 0.006, 0.002), subsurface_scale=0.004,
         coat=0.25, coat_roughness=0.22)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    vein = _noise(nt, mp.outputs["Vector"], scale=70.0, detail=5.0, roughness=0.6)
    _bump(nt, bsdf, vein.outputs["Fac"], strength=0.25, distance=0.0004)
    return mat


@cached
def wasabi(name="山葵"):
    return greens(color=(0.115, 0.215, 0.055), roughness=0.45, name=name)


@cached
def yuzu(name="柚子"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.72, 0.55, 0.055), roughness=0.42, specular=0.45,
         subsurface=0.4, subsurface_radius=(0.006, 0.005, 0.002), subsurface_scale=0.005)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    pores = nt.nodes.new("ShaderNodeTexVoronoi")
    pores.location = (-950, -300)
    pores.inputs["Scale"].default_value = 260.0
    nt.links.new(mp.outputs["Vector"], pores.inputs["Vector"])
    _bump(nt, bsdf, pores.outputs["Distance"], strength=0.6, distance=0.0006)
    return mat


@cached
def fu(name="手毬麩"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.93, 0.91, 0.86), roughness=0.55, specular=0.35,
         subsurface=0.55, subsurface_radius=(0.006, 0.005, 0.005), subsurface_scale=0.006)
    return mat


# --------------------------------------------------------------------------
# 和紙・布
# --------------------------------------------------------------------------
@cached
def washi(emission=6.0, tint=(1.0, 0.72, 0.40), name="和紙"):
    """提灯の火袋。内側からの灯りを透かす."""
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=(0.94, 0.88, 0.76), roughness=0.75, specular=0.2,
         emission=tint, emission_strength=emission, sheen=0.3)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    fibre = _noise(nt, mp.outputs["Vector"], scale=150.0, detail=8.0, roughness=0.75,
                   distortion=1.2)
    ramp = _ramp(nt, [(0.32, (0.65, 0.65, 0.65)), (0.70, (1.0, 1.0, 1.0))], (-700, 120))
    nt.links.new(fibre.outputs["Fac"], ramp.inputs["Fac"])
    strength = nt.nodes.new("ShaderNodeMath")
    strength.operation = 'MULTIPLY'
    strength.location = (-460, 120)
    strength.inputs[1].default_value = emission
    nt.links.new(ramp.outputs["Color"], strength.inputs[0])
    nt.links.new(strength.outputs[0], bsdf.inputs["Emission Strength"])
    _bump(nt, bsdf, fibre.outputs["Fac"], strength=0.2, distance=0.0004)
    return mat


@cached
def noren_cloth(color=(0.030, 0.028, 0.032), name="暖簾"):
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=color, roughness=0.85, specular=0.2,
         sheen=0.6, sheen_roughness=0.4)
    _, mp = _coords(nt, "Object", (1, 1, 1))
    weave = nt.nodes.new("ShaderNodeTexWave")
    weave.location = (-950, -300)
    weave.wave_type = 'BANDS'
    weave.bands_direction = 'X'
    weave.inputs["Scale"].default_value = 300.0
    nt.links.new(mp.outputs["Vector"], weave.inputs["Vector"])
    _bump(nt, bsdf, weave.outputs["Fac"], strength=0.15, distance=0.0003)
    return mat


@cached
def emissive(color=(1.0, 0.68, 0.34), strength=30.0, name="灯"):
    mat, nt, bsdf = _material(name)
    nt.nodes.remove(bsdf)
    node = nt.nodes.new("ShaderNodeEmission")
    node.location = (-200, 0)
    node.inputs["Color"].default_value = (*color, 1)
    node.inputs["Strength"].default_value = strength
    nt.links.new(node.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    return mat


def image_decal(image: bpy.types.Image, base, ink=(0.02, 0.02, 0.02),
                name="文字", emission=0.0):
    """PIL で焼いた文字画像を UV で貼る (暖簾・提灯の「雅」用)."""
    mat, nt, bsdf = _material(name)
    _set(bsdf, base_color=base, roughness=0.8, specular=0.2, sheen=0.5)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-900, 0)
    tex.image = image
    tex.extension = 'EXTEND'
    tex.interpolation = 'Cubic'
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.location = (-1120, 0)
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.location = (-520, 60)
    mix.inputs[6].default_value = (*base, 1)
    mix.inputs[7].default_value = (*ink, 1)
    nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    if emission > 0:
        _set(bsdf, emission=base, emission_strength=emission)
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = 'SUBTRACT'
        inv.location = (-520, -260)
        inv.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs["Alpha"], inv.inputs[1])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = 'MULTIPLY'
        mul.location = (-320, -260)
        mul.inputs[1].default_value = emission
        nt.links.new(inv.outputs[0], mul.inputs[0])
        nt.links.new(mul.outputs[0], bsdf.inputs["Emission Strength"])
    return mat
