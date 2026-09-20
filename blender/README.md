# blender/ — 雅の 3D

LP に載っている画像と glTF を生成する一式。
`pip install bpy` で入る **Blender 5.0 を Python モジュールとして** 使うので、
Blender アプリのインストールも `.blend` ファイルも要らない。
形はすべてコードから起こしている。

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
fonts/fetch.sh
.venv/bin/python build.py --list                  # 撮れるカット一覧
.venv/bin/python build.py --quality draft         # 下見 (34% サイズ / 少サンプル)
.venv/bin/python build.py --only wanmono,hero     # 一部だけ焼き直す
.venv/bin/python build.py --quality final         # 本番 → ../assets/
```

## 構成

```
build.py                 カットの定義と CLI。どこをどう撮るかはここ
miyabi3d/
  modeling.py            形をつくる道具 — 回転体・器の断面・葉・立体文字
  materials.py           漆・金・檜・陶・出汁・和紙。すべて手続き的ノード
  staging.py             レンダ設定・ライティング・カメラ・書き出し
  textures.py            PIL で「雅」を焼いて画像テクスチャにする
  assets/                一品ずつの組み立て
    wanmono.py           汁椀と出汁と浮き実
    sushi.py             寿司下駄と握り三貫
    donabe.py            土鍋と炊き込みご飯と蓋
    shuki.py             徳利と猪口
    chochin.py           提灯（火袋・骨・輪）
    emblem.py            紋（黒漆の地に金の輪と「雅」）
    hashi.py             塗り箸と箸置き
    zen.py               上のものを並べたヒーロー用の場面
```

各 `assets/*.py` は `build(collection=None, **kwargs) -> dict` を持ち、
`{"name", "objects", "focus", "radius", "height"}` を返す。
`focus` と `radius` を見て `staging` がライトとカメラを置く。

## 考え方

**寸法は実寸（メートル）**。汁椀は口径 120mm、寿司下駄は 245mm。
実寸で組んでおくと、被写界深度もライトの回り込みも写真どおりの挙動になる。

**器は断面を回して挽く**。`modeling.vessel_profile()` に外側の曲線を渡すと、
一定の肉厚で内壁をオフセットし、高台と口縁を足して閉じた断面を返す。
区間ごとにラベル（`under` / `outer` / `rim` / `inner`）が付くので、
「外は黒漆、口縁は金、内は朱」といった塗り分けがそのまま書ける。

**明るさは照度で指定する**。`staging.studio()` はワット数ではなく
W/m² で受け取り、被写体半径に応じた距離からワット数を逆算する。
反射率 0.18 の面が中間調に落ちるところを測って既定値を決めてあるので、
6cm の椀でも 25cm の土鍋でも同じ露出で撮れる。

**接地影は専用の床で拾う**。`staging.shadow_floor()` は影だけを残し、
二次光線からは隠す。これをやらないと、黒漆の器が白い床を鏡のように映して
真っ白になる（最初これで一度ハマった）。

影はフレームの端まで届くことがあるので、焼いたあとに
`postprocess.feather_edges()` で外周のアルファを落としている。
暗い背景に置いたときに、画像の縁が直線で見えてしまうのを防ぐため。

## 撮っているカット

| 名前 | 出力 | 中身 |
| --- | --- | --- |
| `wanmono` `sushi` `donabe` `shuki` | `renders/dish-*.webp` | お品書きの四品。透過 + 接地影 |
| `hashi` | `renders/hashi.webp` | 箸と箸置き |
| `emblem` | `renders/emblem.webp` | 紋。正対、ロゴとファビコンに使う |
| `chochin` | `renders/chochin.webp` | 提灯。暗い設定で灯りを見せる |
| `hero` `seat` `og` | `renders/*.webp` `og.jpg` | 席の場面。被写界深度あり |
| `turntable` | `turntable/wanmono-NN.webp` | 汁椀を 32 コマで一周 |
| `models` | `models/*.glb` | モディファイアを焼いてから glTF 書き出し |
| `polish` | （既存の出力を上書き） | 透過画像の縁だけ整える。焼き直しは不要 |

## 一品足すには

1. `miyabi3d/assets/新しい品.py` に `build()` を書く
2. `miyabi3d/assets/__init__.py` の `MODULES` に名前を足す
3. `build.py` に `@shot("新しい品")` でカットを足す
4. `--only 新しい品 --quality draft` で見ながら詰める

## 環境

CPU レンダリング（Cycles + OpenImageDenoise）。GPU は要らない。
4 コアで本番一式およそ 1 時間、下見は数分。
