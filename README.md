# lc-bot

A pure-Python hobby chess engine, with bitboard move generation, alpha-beta
search, and a toggleable NNUE eval. Comes with a Pygame GUI and a
[UCI integration for playing online](#lichess-bot).

Rated **2000+** playing against other bots on Lichess.
[Watch it play live!](https://lichess.org/@/lc-bot)

Started in January 2024 as my first major coding project. It began with a
mailbox approach, moved to bitboards, and went all the way to NNUE.

## Features

Search
- negamax alpha-beta, PVS, iterative deepening
- transposition table, depth-preferred replacement
- quiescence search with SEE pruning
- null move, LMR, futility pruning, razoring
- aspiration windows, check extensions, singular extensions
- killer/history move ordering
- clock-based time management, pondering
- multiprocessing root-split search (fixed depth only, not wired into UCI yet)

Evaluation (`UseNNUE` switches between them)
- hand-written (default): tapered PSTs, pawn structure, mobility, king safety,
  king tropism, center control, mop-up
- NNUE: the hand-written eval plus a 768-256-1 residual net trained on
  Stockfish-labelled positions. Weights are quantized to 16-bit lanes packed
  into one int, so making a move is a few big-int adds rather than a forward pass.

Other
- magic bitboards, verified with perft
- Polyglot books, Syzygy tablebases
- Pygame GUI (`--nnue` flag, `E` toggles the eval during a game)
- NNUE training scripts (data generation, Stockfish relabelling, PyTorch)
- A/B match scripts that report Elo with 95% confidence intervals
- Lichess bot scripts (`bot.sh`, `watchdog.sh`)

## Running it

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run python uci.py              # UCI engine on stdin/stdout
uv run python gui.py              # play against it
uv run python gui.py --nnue       # same, with the NNUE eval
```

Any UCI GUI works with `uv run python uci.py` as the engine command. Or by hand:

```
$ uv run python uci.py
uci
setoption name UseNNUE value true
position startpos
go movetime 1000
```

### UCI options

| option | type | notes |
|---|---|---|
| `UseNNUE` | check, default false | |
| `NNUEPath` | path | empty = `nets/sf_hybrid_adv_damped.json`; falls back to the hand-written eval if the file can't be loaded |
| `NNUEMode` | `hybrid` / `pure` | `pure` drops the hand-written eval and tested about 56 Elo weaker |
| `Hash` | 1-4096 | TT size in MB |
| `OwnBook` / `BookPath` | check / path | Polyglot book |
| `UseTablebase` / `TablebasePath` | check / path | local Syzygy files |
| `Ponder` | check | advertises pondering; `go ponder` works regardless |

## Results

All matches are against the previous version of the bot, using 100+ openings
with both colours (the engines are deterministic, so with only a few openings
most games end up being repeats). Ranges are 95% CIs.

| config | time control | games | Elo |
|---|---|---|---|
| NNUE | 300 ms/move | 200 | +85 [+43, +130] |
| NNUE | 1 s/move | 200 | +74 [+35, +116] |
| NNUE + ponder | 60+0.6 | 120 | +151 [+103, +204] |
| hand-written only | 300 ms/move | 200 | -28 [-72, +15] |

Self-play gaps tend to be larger than what shows up against other opponents.

## NNUE details

The net predicts a correction on top of the hand-written eval:
`score = evaluate(board) + clip(net(board), -600, 600)`.

- Inputs: 768 features (6 piece types x 2 colours x 64 squares), encoded as
  own/opponent from each side's point of view, board mirrored for Black.
- Hidden: 256 clipped-ReLU units. Both perspectives share the output weights
  with opposite signs, so a position and its colour-flipped mirror get exactly
  opposite scores.
- Quantization: 16-bit weights packed into one big int (SWAR). Make/unmake add
  or subtract feature columns from the accumulator.
- Damping: the output layer is scaled by 0.3 (the `damped` in the net names).
  Undamped, the net had lower validation loss but played worse, since its
  corrections were too large for a shallow search.
- Training: `tools/gen_data.py` generates positions, `tools/relabel_sf.py`
  scores them with Stockfish at depth 14, and `tools/train.py` fits the net
  (`uv sync --group train` installs PyTorch). Nets are stored as JSON in `nets/`.

## Tests

```
uv run pytest -q                  # test suite
uv run python -m lcbot.perft      # perft
uv run python -m lcbot.search     # module self-tests (evaluation, nnue_ref, etc. have them too)
```

With NNUE turned off, the engine's output (move, score, node count, PV) is
identical to the pre-NNUE version on a 60-position set.
`tests/test_merge_nnue.py` checks that the accumulator stays in sync through
all the pruning paths.

Example matches:

```
# NNUE on vs off, 300 ms per move
uv run python tools/ab_test.py --games 200 --movetime 300 \
    --a-dir . --a-opt UseNNUE=true --b-dir . --b-opt UseNNUE=false

# pondering on vs off, 30+0.3
uv run python tools/ab_clock.py --games 100 --base 30 --inc 0.3 \
    --a-dir . --a-opt UseNNUE=true --a-ponder --b-dir . --b-opt UseNNUE=true
```

## Lichess bot

Runs through [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot).
Clone it into `lichess-bot/` (git-ignored because `config.yml` contains the
account token) and create `lichess-bot/engines/lc-bot`:

```sh
#!/bin/sh
ENGINE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
exec uv run --project "$ENGINE_DIR" python3 "$ENGINE_DIR/uci.py"
```

In `config.yml`, set `engine.name: "lc-bot"` and the UCI options
(`UseNNUE: true`, `Hash: 128`, `ponder: true`). Then:

```
./bot.sh start | stop | restart | status | log
nohup ./watchdog.sh >> lichess-bot/watchdog.log 2>&1 &    # restarts the bot if it dies, keeps the Mac awake
```

## Layout

```
lcbot/            engine: board, movegen, search, eval, NNUE, UCI, book, tablebases
uci.py            UCI entry point
gui.py            Pygame GUI (images in piece_textures/)
tools/            benchmarks, match harnesses, NNUE data/training
matches/          scripts used for the results above
nets/             trained nets
tests/            pytest suite
```

## License

MIT, see [LICENSE](LICENSE).
