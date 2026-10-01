#!/bin/bash
# 平行渲染一個目錄下所有樂譜:batch.sh <樂譜目錄> <輸出目錄> [render.mjs 其他參數...]
IN=$1; OUT=$2; shift 2
mkdir -p "$OUT"
ls "$IN"/*.musicxml | xargs -P 3 -I{} sh -c 'b=$(basename {} .musicxml); node "$(dirname "$0")/render.mjs" {} "'"$OUT"'/$b.wav" --taps '"$*"' > "'"$OUT"'/$b.log" 2>&1' "$0"
python3 "$(dirname "$0")/analyze.py" "$OUT"/*.wav
