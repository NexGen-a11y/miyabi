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
