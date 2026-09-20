"""miyabi3d — 和食処「雅」LP のための 3D アセット生成パッケージ.

Blender を Python モジュール (`pip install bpy`) として使い、
器・料理・提灯などをすべて手続き的に組み立てて Cycles で焼く。
外部の 3D モデルは一切使わず、寸法はすべて実寸 (メートル) で扱う。
"""

__version__ = "1.0.0"

# 店の色 (リニア sRGB)。ウェブ側 styles/miyabi.css の --sumi / --kin と揃えてある
URUSHI = (0.010, 0.009, 0.010)     # 黒漆
KIN = (0.760, 0.520, 0.180)        # 金
