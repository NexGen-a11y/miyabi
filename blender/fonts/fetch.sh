#!/bin/sh
# 3D の「雅」に使う和文フォントを取ってくる。
# Noto Serif JP (SIL Open Font License 1.1) — Google Fonts より。
set -eu
dir=$(cd "$(dirname "$0")" && pwd)
url="https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifjp/NotoSerifJP%5Bwght%5D.ttf"

if [ -f "$dir/NotoSerifJP.ttf" ]; then
  echo "すでにあります: $dir/NotoSerifJP.ttf"
  exit 0
fi

echo "取得中: $url"
curl -fsSL -o "$dir/NotoSerifJP.ttf" "$url"
echo "保存しました: $dir/NotoSerifJP.ttf"
echo "別のフォントを使う場合は MIYABI_FONT に .ttf のパスを入れてください。"
