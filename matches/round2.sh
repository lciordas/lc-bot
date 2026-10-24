#!/bin/bash
# Retrained net (damping 0.3): confirm vs a reference engine at 1s/move, sweep damping, test pondering.
# Usage: LIVE_DIR=/path/to/engine matches/round2.sh
cd "$(dirname "$0")/.."
ROOT=$PWD
LIVE_DIR=$(cd "${LIVE_DIR:?set LIVE_DIR to the engine to play against}" && pwd)
LIVE="--b-dir $LIVE_DIR --b-name LIVE --b-opt UseNNUE=true --b-opt NNUEPath=$LIVE_DIR/nets/sf_hybrid_damped.json"
NET30=$ROOT/nets/sf_hybrid_adv_damped.json
A30="--a-dir . --a-opt UseNNUE=true --a-opt NNUEPath=$NET30"
B30="--b-dir . --b-name advnet-d30 --b-opt UseNNUE=true --b-opt NNUEPath=$NET30"
# vs LIVE at 1s/move
uv run python tools/ab_test.py --games 200 --movetime 1000 --concurrency 8 $A30 --a-name advnet-d30 $LIVE --label "advnet-d30 vs LIVE @1s" > matches/r2_advnet_vs_live_1s.log 2>&1
# damping 0.2 and 0.4 vs 0.3
for d in 20 40; do
  uv run python tools/ab_test.py --games 200 --movetime 300 --concurrency 8 --a-dir . --a-name advnet-d$d --a-opt UseNNUE=true --a-opt NNUEPath=$ROOT/nets/sf_hybrid_adv_d$d.json $B30 --label "d$d vs d30" > matches/r2_d${d}_vs_d30.log 2>&1
done
# ponder on vs off on real clocks (pondering doubles busy cores: keep 2x concurrency under the core count)
uv run python tools/ab_clock.py --games 100 --base 30 --inc 0.3 --concurrency 6 $A30 --a-name advnet-ponder --a-ponder --b-dir . --b-name advnet-noponder --b-opt UseNNUE=true --b-opt NNUEPath=$NET30 --label "ponder on vs off" > matches/r2_ponder.log 2>&1
