# 雅 — 和食処のランディングページ

架空の和食処「雅（みやび）」のランディングページ。
**載っている写真はすべて Blender で組んだ 3D モデルを Cycles でレンダリングしたもの**で、
素材サイトの写真も、既成の 3D モデルも使っていない。
器も料理も提灯も、Python から手続き的に生成している。

```
index.html          ページ本体
styles/miyabi.css   見た目
scripts/miyabi.js   ヘッダー・ナビ・器ビューア
scripts/vendor/     three.js (リアルタイム3D表示のみに使用, MIT)
assets/renders/     Cycles で焼いた静止画 (WebP / JPEG)
assets/turntable/   汁椀を 32 コマで一周させた連番
assets/models/      glTF-Binary。ブラウザでそのまま回せる
blender/            3D をつくっているコード一式 → blender/README.md
```

## 見る

ES モジュールと importmap を使っているので、`file://` ではなく HTTP で開く。

```sh
python3 -m http.server 8000
# http://localhost:8000/
```

## 3D をつくり直す

```sh
python3 -m venv .venv                       # Python 3.11 が必要 (bpy の制約)
.venv/bin/pip install -r blender/requirements.txt
blender/fonts/fetch.sh                      # 「雅」の一文字に使う和文フォント
.venv/bin/python blender/build.py --quality draft    # 下見。数分
.venv/bin/python blender/build.py --quality final    # 本番。1時間ほど (CPU 4コア)
```

Blender 本体のインストールは要らない。`pip install bpy` で入る Blender 5.0 を
Python モジュールとして叩いている。詳しくは [blender/README.md](blender/README.md)。

## ページの中身

| 節 | 内容 | 使っている 3D |
| --- | --- | --- |
| ヒーロー | 店の第一印象 | 欅のカウンター・汁椀・塗り箸・徳利・金屏風 |
| こころ | 料理の考え方 | 提灯（火袋に「雅」の一文字、中から発光） |
| お品書き | 四品 | 椀物 / 握り三貫 / 土鍋ご飯 / 酒器 |
| 器 | ドラッグで回せる汁椀 | 連番 32 コマ + glTF のリアルタイム表示 |
| 席 | 店内の様子 | ヒーローと同じ席を広角で |
| ご案内 | 営業時間・アクセス | 紋（黒漆に金の「雅」）・箸 |

## つくりで気をつけたところ

- **器のビューアは写真が既定**。32 コマの連番をドラッグで送るので、WebGL が
  使えない環境でも回せる。使える環境では「リアルタイム3Dで見る」で
  glTF に切り替わる（three.js はそのときだけ動的 import する）。
- **キーボードで回せる**。「回す」ボタンにフォーカスして左右キー。
- `prefers-reduced-motion` を見て、自動回転と出現アニメーションを止める。
- 画像はすべて WebP（アルファ付き）、ヒーローだけ `fetchpriority="high"` で先読み。
- ページの JavaScript が落ちても、献立も連絡先も読めるように素の HTML で書いてある。

## 注意

**このサイトは制作サンプル**。店名・住所・電話番号・料金・店主の言葉はすべて架空で、
実在の店舗や人物とは関係ない。

three.js (`scripts/vendor/`) は MIT License、同梱の `three-LICENSE.txt` を参照。
和文フォント Noto Serif JP は SIL Open Font License 1.1（リポジトリには含めず、
`blender/fonts/fetch.sh` で取得する）。
