#!/bin/bash
# Each eval configuration vs a reference engine, fixed 300ms/move.
# Usage: LIVE_DIR=/path/to/engine matches/round1.sh   (the engine dir must have uci.py and nets/sf_hybrid_damped.json)
cd "$(dirname "$0")/.."
LIVE_DIR=$(cd "${LIVE_DIR:?set LIVE_DIR to the engine to play against}" && pwd)
LIVE="--b-dir $LIVE_DIR --b-name LIVE --b-opt UseNNUE=true --b-opt NNUEPath=$LIVE_DIR/nets/sf_hybrid_damped.json"
COMMON="--games 200 --movetime 300 --concurrency 8"
uv run python tools/ab_test.py $COMMON --a-dir . --a-name handwritten --a-opt UseNNUE=false $LIVE --label handwritten > matches/r1_handwritten.log 2>&1
uv run python tools/ab_test.py $COMMON --a-dir . --a-name oldnet --a-opt UseNNUE=true --a-opt NNUEPath=$PWD/nets/sf_hybrid_damped.json $LIVE --label oldnet > matches/r1_oldnet.log 2>&1
uv run python tools/ab_test.py $COMMON --a-dir . --a-name advnet --a-opt UseNNUE=true --a-opt NNUEPath=$PWD/nets/sf_hybrid_adv_damped.json $LIVE --label advnet > matches/r1_advnet.log 2>&1
