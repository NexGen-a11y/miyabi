#!/usr/bin/env python3
"""和食処「雅」LP のための 3D アセットを焼く.

    # 下見 (小さく速く)
    blender/build.py --quality draft
    # 本番
    blender/build.py --quality final

bpy をモジュールとして使うので、Blender 本体のインストールは要らない。
    python -m venv .venv && .venv/bin/pip install -r blender/requirements.txt
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from miyabi3d import assets, materials as MAT, modeling as M, staging as S  # noqa: E402

DEFAULT_OUT = os.path.normpath(os.path.join(HERE, "..", "assets"))

QUALITY = {
    "draft": dict(scale=0.34, samples=0.22, frames=8),
    "preview": dict(scale=0.6, samples=0.5, frames=16),
    "final": dict(scale=1.0, samples=1.0, frames=32),
}

SHOTS: dict[str, callable] = {}


def shot(name):
    def register(fn):
        SHOTS[name] = fn
        return fn
    return register


class Ctx:
    """出力先と品質を持ち回るだけの入れ物."""

    def __init__(self, out_dir, quality):
        self.out = out_dir
        self.q = QUALITY[quality]
        self.quality = quality

    def size(self, width, height):
        s = self.q["scale"]
        return max(int(width * s) // 2 * 2, 32), max(int(height * s) // 2 * 2, 32)

    def samples(self, base):
        return max(int(base * self.q["samples"]), 12)

    def path(self, *parts):
        return os.path.join(self.out, *parts)


# --------------------------------------------------------------------------
# 器単体のカット — 透過背景に接地影だけ残す
# --------------------------------------------------------------------------
def _dish(ctx, module, filename, width, height, samples, azimuth, elevation,
          focal=105.0, margin=1.10, exposure=0.0, key=1.25, build_kwargs=None):
    S.reset()
    w, h = ctx.size(width, height)
    S.configure(w, h, ctx.samples(samples), transparent=True, exposure=exposure)
    S.world(0.20)
    res = assets.build(module, **(build_kwargs or {}))
    S.studio(target=res["focus"], radius=res["radius"], key=key)
    S.shadow_floor(size=max(res["radius"] * 26, 1.0))
    cam = S.camera(target=res["focus"], distance=res["radius"] * 6,
                   azimuth=azimuth, elevation=elevation, focal=focal)
    S.frame(cam, res["objects"], margin)
    return S.render(ctx.path("renders", filename), quality=92)


@shot("wanmono")
def shot_wanmono(ctx):
    return _dish(ctx, "wanmono", "dish-wanmono.webp", 1100, 1100, 104,
                 azimuth=-62, elevation=40, focal=110, margin=1.12)


@shot("sushi")
def shot_sushi(ctx):
    return _dish(ctx, "sushi", "dish-sushi.webp", 1400, 1000, 96,
                 azimuth=-70, elevation=31, focal=100, margin=1.06)


@shot("donabe")
def shot_donabe(ctx):
    return _dish(ctx, "donabe", "dish-donabe.webp", 1400, 1000, 96,
                 azimuth=-64, elevation=34, focal=100, margin=1.06)


@shot("shuki")
def shot_shuki(ctx):
    return _dish(ctx, "shuki", "dish-shuki.webp", 1100, 1100, 100,
                 azimuth=-56, elevation=26, focal=110, margin=1.14)


@shot("hashi")
def shot_hashi(ctx):
    return _dish(ctx, "hashi", "hashi.webp", 1400, 620, 88,
                 azimuth=-72, elevation=27, focal=95, margin=1.05)


@shot("emblem")
def shot_emblem(ctx):
    """紋は正対で。床影は切って、金だけが浮くようにする."""
    S.reset()
    w, h = ctx.size(900, 900)
    S.configure(w, h, ctx.samples(112), transparent=True, exposure=0.10)
    S.world(0.12)
    res = assets.build("emblem", stand=False)
    S.studio(target=res["focus"], radius=res["radius"], key=1.1, rim=2.6,
             overhead=0.5, key_dir=(1.9, -1.2, 2.6), rim_dir=(-2.0, 2.4, 1.2),
             fill_dir=(-2.6, -2.2, -0.6))
    cam = S.camera(target=res["focus"], distance=0.6, azimuth=-90, elevation=0,
                   focal=125)
    S.frame(cam, res["objects"], 1.16)
    return S.render(ctx.path("renders", "emblem.webp"), quality=94)


@shot("chochin")
def shot_chochin(ctx):
    """提灯は暗がりで撮ってこそ灯りに見える."""
    S.reset()
    w, h = ctx.size(820, 1320)
    S.configure(w, h, ctx.samples(104), transparent=True, exposure=-0.05)
    S.world(0.04, zenith=(0.10, 0.11, 0.16), horizon=(0.03, 0.028, 0.030))
    res = assets.build("chochin", facing=-62.0, glow=7.0)
    S.studio(target=res["focus"], radius=res["radius"], key=0.22, fill=0.04,
             rim=0.6, overhead=0.05)
    cam = S.camera(target=res["focus"], distance=1.2, azimuth=-62, elevation=6,
                   focal=105)
    S.frame(cam, res["objects"], 1.10)
    return S.render(ctx.path("renders", "chochin.webp"), quality=93)


# --------------------------------------------------------------------------
# 席の場面 — 暗い店内、奥に金屏風と提灯
# --------------------------------------------------------------------------
def _zashiki(ctx, filename, width, height, samples, azimuth, elevation,
             focal, distance, fstop, exposure=-0.15, quality=92,
             lantern=True, lantern_at=(-0.455, 0.335, 0.315), pendant=0.85,
             shift=(0.0, 0.0), byobu=0.32, rim=1.15, bounce=0.07):
    S.reset()
    w, h = ctx.size(width, height)
    S.configure(w, h, ctx.samples(samples), transparent=False, exposure=exposure,
                clamp_indirect=6.0)
    S.world(0.045, zenith=(0.10, 0.11, 0.15), horizon=(0.030, 0.026, 0.026),
            ground=(0.004, 0.004, 0.004))
    res = assets.build("zen", facing=azimuth, with_lantern=lantern,
                       lantern_at=lantern_at)
    focus = res["focus"]

    # 頭上の小さな吊り灯り
    S.area_light("pendant", (focus.x - 0.22, focus.y + 0.14, focus.z + 0.46),
                 focus, size=0.16, energy=S._watts(pendant, 0.52),
                 color=(1.0, 0.86, 0.68))
    # 客席側からのごく弱い返し
    S.area_light("bounce", (focus.x - 0.55, focus.y - 0.62, focus.z + 0.18),
                 focus, size=0.75, energy=S._watts(bounce, 0.85),
                 color=(0.80, 0.85, 1.0))
    # 器の輪郭を拾うリム
    S.area_light("rim", (focus.x + 0.34, focus.y + 0.46, focus.z + 0.22),
                 focus, size=0.12, energy=S._watts(rim, 0.60),
                 color=(1.0, 0.84, 0.62))
    # 金屏風をぼんやり起こす
    S.area_light("byobu", (0.25, 0.30, 0.62), (0.15, 0.62, 0.26),
                 size=1.1, energy=S._watts(byobu, 0.55), color=(1.0, 0.90, 0.74))

    S.camera(target=focus, distance=distance, azimuth=azimuth, elevation=elevation,
             focal=focal, fstop=fstop, focus=distance, shift=shift)
    return S.render(ctx.path("renders", filename), quality=quality)


@shot("hero")
def shot_hero(ctx):
    return _zashiki(ctx, "hero.webp", 2000, 1200, 150, azimuth=-70, elevation=26,
                    focal=52, distance=0.76, fstop=2.8, exposure=0.0,
                    lantern=False, byobu=0.55)


@shot("seat")
def shot_seat(ctx):
    return _zashiki(ctx, "scene-seat.webp", 1600, 1100, 132, azimuth=-64,
                    elevation=11, focal=38, distance=0.78, fstop=3.5,
                    exposure=0.0, lantern_at=(-0.300, 0.440, 0.055),
                    pendant=0.62, shift=(0.0, 0.05), byobu=0.52)


@shot("og")
def shot_og(ctx):
    return _zashiki(ctx, "og.jpg", 1200, 630, 120, azimuth=-70, elevation=23,
                    focal=52, distance=0.72, fstop=2.8, exposure=0.0,
                    lantern=False, quality=88, byobu=0.55)


# --------------------------------------------------------------------------
# 回転台 — ドラッグで回せるようコマ撮りする
# --------------------------------------------------------------------------
@shot("turntable")
def shot_turntable(ctx):
    S.reset()
    side, _ = ctx.size(620, 620)
    S.configure(side, side, ctx.samples(66), transparent=True, exposure=0.0)
    S.world(0.20)
    res = assets.build("wanmono")
    S.studio(target=res["focus"], radius=res["radius"])
    S.shadow_floor(size=1.4)
    cam = S.camera(target=res["focus"], distance=0.42, azimuth=-62, elevation=27,
                   focal=105)
    S.frame(cam, res["objects"], 1.18)
    frames = ctx.q["frames"]
    paths = S.turntable(res["objects"], ctx.path("turntable"), frames=frames,
                        prefix="wanmono", quality=88)
    return f"{len(paths)} frames"


# --------------------------------------------------------------------------
# glTF 書き出し — ブラウザで回せるようにする
# --------------------------------------------------------------------------
@shot("models")
def shot_models(ctx):
    done = []
    for name, kwargs in (("wanmono", {}), ("sushi", {}), ("donabe", {}),
                         ("shuki", {}), ("emblem", {"stand": False}),
                         ("chochin", {"with_light": False})):
        S.reset()
        S.configure(64, 64, 12)
        res = assets.build(name, **kwargs)
        meshes = [o for o in res["objects"] if o.type == 'MESH']
        for obj in meshes:
            M.apply_modifiers(obj)
        path = S.export_glb(meshes, ctx.path("models", f"{name}.glb"))
        done.append(f"{name} ({os.path.getsize(path) // 1024}KB)")
    return ", ".join(done)


# --------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description="雅 LP の 3D アセットを焼く")
    parser.add_argument("--quality", choices=sorted(QUALITY), default="final")
    parser.add_argument("--out", default=DEFAULT_OUT, help="書き出し先ディレクトリ")
    parser.add_argument("--only", default="", help="カンマ区切りのカット名")
    parser.add_argument("--list", action="store_true", help="カット名を並べる")
    args = parser.parse_args(argv)

    if args.list:
        print("\n".join(sorted(SHOTS)))
        return 0

    names = [n.strip() for n in args.only.split(",") if n.strip()] or list(SHOTS)
    unknown = [n for n in names if n not in SHOTS]
    if unknown:
        parser.error(f"知らないカット: {', '.join(unknown)} "
                     f"(--list で一覧)")

    ctx = Ctx(os.path.abspath(args.out), args.quality)
    os.makedirs(ctx.out, exist_ok=True)
    print(f"雅 3D — quality={args.quality} out={ctx.out}")
    started = time.time()
    for name in names:
        t = time.time()
        result = SHOTS[name](ctx)
        print(f"  {name:10s} {time.time() - t:7.1f}s  {result}", flush=True)
    print(f"合計 {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
