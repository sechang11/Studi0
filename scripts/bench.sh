#!/usr/bin/env bash
# Benchmark the 5090 across resolutions / frame counts.
# Run:  bash scripts/bench.sh 2>&1 | tee bench-results.txt
set -u
cd "$(dirname "$0")/.."
R() { echo "### $1"; python3 scripts/comfy.py run "$2" "${@:3}" 2>/dev/null; }

echo "=== IMAGE: Qwen-Image 2512 + Lightning 4-step (cfg 1.0) ==="
R "1024x1024   4step" workflows/01_qwen_t2i_turbo.json -s 12.inputs.width=1024 -s 12.inputs.height=1024 -s 13.inputs.seed=1
R "1328x1328   4step" workflows/01_qwen_t2i_turbo.json -s 12.inputs.width=1328 -s 12.inputs.height=1328 -s 13.inputs.seed=2
R "1664x928    4step" workflows/01_qwen_t2i_turbo.json -s 12.inputs.width=1664 -s 12.inputs.height=928  -s 13.inputs.seed=3
R "2048x1152   4step" workflows/01_qwen_t2i_turbo.json -s 12.inputs.width=2048 -s 12.inputs.height=1152 -s 13.inputs.seed=4
R "1328 batch4 4step" workflows/01_qwen_t2i_turbo.json -s 12.inputs.width=1328 -s 12.inputs.height=1328 -s 12.inputs.batch_size=4 -s 13.inputs.seed=5

echo "=== IMAGE: Qwen-Image 2512 full quality (20 step, cfg 2.5) ==="
R "1328x1328  20step" workflows/02_qwen_t2i_quality.json -s 13.inputs.seed=11
R "1664x928   20step" workflows/02_qwen_t2i_quality.json -s 12.inputs.width=1664 -s 12.inputs.height=928 -s 13.inputs.seed=12

echo "=== VIDEO: Wan 2.2 I2V 14B + lightx2v 4-step ==="
R "832x480   81f (5.1s)"  workflows/04_wan22_i2v_turbo.json -s 13.inputs.width=832  -s 13.inputs.height=480 -s 13.inputs.length=81
R "1280x720  81f (5.1s)"  workflows/04_wan22_i2v_turbo.json -s 13.inputs.width=1280 -s 13.inputs.height=720 -s 13.inputs.length=81
R "1280x720 121f (7.6s)"  workflows/04_wan22_i2v_turbo.json -s 13.inputs.width=1280 -s 13.inputs.height=720 -s 13.inputs.length=121
R "1920x1080 81f (5.1s)"  workflows/04_wan22_i2v_turbo.json -s 13.inputs.width=1920 -s 13.inputs.height=1088 -s 13.inputs.length=81

echo "=== done ==="
