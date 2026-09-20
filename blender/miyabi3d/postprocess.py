"""焼いたあとの仕上げ.

接地影はフレームの端まで届くことがあり、そのまま切ると
透過画像の縁に直線が出る。外周だけアルファを落として逃がす。
"""

from __future__ import annotations

import os


def feather_edges(path: str, fade: float = 0.045, floor: float = 0.0) -> str:
    """透過画像の外周 fade 割ぶんで、アルファをなめらかに 0 へ落とす."""
    from PIL import Image
    import numpy as np

    img = Image.open(path)
    if img.mode != 'RGBA':
        return path
    arr = np.array(img)
    h, w = arr.shape[:2]

    def ramp(n):
        band = max(int(n * fade), 1)
        edge = np.linspace(floor, 1.0, band, endpoint=False)
        line = np.ones(n, dtype=np.float32)
        line[:band] = edge
        line[-band:] = edge[::-1]
        return line

    mask = np.minimum(ramp(h)[:, None], ramp(w)[None, :])
    arr[:, :, 3] = np.clip(arr[:, :, 3] * mask, 0, 255).astype(arr.dtype)

    out = Image.fromarray(arr, 'RGBA')
    ext = os.path.splitext(path)[1].lower()
    if ext == '.webp':
        out.save(path, 'WEBP', quality=92, method=5)
    else:
        out.save(path)
    return path


def soften_shadow(path: str, amount: float = 0.5, luma_max: float = 0.07,
                  alpha_max: float = 0.985) -> str:
    """接地影だけを薄くする.

    影の画素は「ほぼ黒」かつ「半透明」なので、そこだけアルファを落とす。
    器そのものは不透明なので触らずに済む。暗い背景のカードに置くと、
    等倍の影は四角い染みのように見えてしまうため。
    """
    from PIL import Image
    import numpy as np

    img = Image.open(path)
    if img.mode != 'RGBA':
        return path
    arr = np.array(img)
    alpha = arr[:, :, 3].astype(np.float32) / 255.0
    luma = arr[:, :, :3].astype(np.float32).mean(axis=2) / 255.0

    shadow = (alpha > 0.0) & (alpha < alpha_max) & (luma < luma_max)
    alpha[shadow] *= amount
    arr[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(arr.dtype)

    out = Image.fromarray(arr, 'RGBA')
    if os.path.splitext(path)[1].lower() == '.webp':
        out.save(path, 'WEBP', quality=92, method=5)
    else:
        out.save(path)
    return path
