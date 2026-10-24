#!/bin/bash
# Bot configuration (retrained net d30, ponder on) vs a reference engine (ponder off), 60+0.6.
# Usage: LIVE_DIR=/path/to/engine matches/round3.sh
cd "$(dirname "$0")/.."
LIVE_DIR=$(cd "${LIVE_DIR:?set LIVE_DIR to the engine to play against}" && pwd)
uv run python tools/ab_clock.py --games 120 --base 60 --inc 0.6 --concurrency 6 \
  --a-dir . --a-name FINAL --a-ponder --a-opt UseNNUE=true --a-opt NNUEPath=$PWD/nets/sf_hybrid_adv_damped.json \
  --b-dir $LIVE_DIR --b-name LIVE --b-opt UseNNUE=true --b-opt NNUEPath=$LIVE_DIR/nets/sf_hybrid_damped.json \
  --label "FINAL vs LIVE @60+0.6" > matches/r3_final_vs_live_clock.log 2>&1
