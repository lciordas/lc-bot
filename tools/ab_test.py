"""A/B match between two engine configurations, with Elo and a 95% CI.

Fixed movetime per move, or fixed --depth to compare evaluation only.

Each side is an engine directory (runs its uci.py) plus UCI options. Every game
starts from a distinct opening, played once per colour, since the engines are
deterministic and repeated openings would just replay the same game.

    uv run python tools/ab_test.py --games 200 --movetime 300 \\
        --a-dir . --a-opt UseNNUE=true \\
        --b-dir . --b-opt UseNNUE=false
"""
import argparse
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor

import chess
import chess.engine

MAX_PLIES = 300          # longer games are adjudicated as draws


def load_openings(n, seed=12345, path=None):
    """`n // 2` distinct opening FENs (each is played once per colour)."""
    need = max(1, n // 2)
    if path:
        with open(path) as fh:
            fens = [l.strip() for l in fh if l.strip()]
        random.Random(seed).shuffle(fens)
        if need > len(fens):
            fens = fens * (need // len(fens) + 1)
        return fens[:need]
    rng = random.Random(seed)
    seen, fens = set(), []
    while len(fens) < need:
        b = chess.Board()
        for _ in range(8):
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(rng.choice(moves))
        key = b.board_fen()
        if b.is_game_over() or key in seen:
            continue
        seen.add(key)
        fens.append(b.fen())
    return fens


def _engine(spec):
    d = spec["dir"]
    e = chess.engine.SimpleEngine.popen_uci(
        ["uv", "run", "--project", d, "python", os.path.join(d, "uci.py")],
        cwd=d, stderr=open(os.devnull, "w"))
    e.configure(dict(spec.get("options", {})))
    return e


def _play_one(job):
    a_spec, b_spec, a_is_white, fen, movetime, depth = job
    ea = eb = None
    try:
        ea, eb = _engine(a_spec), _engine(b_spec)
        white, black = (ea, eb) if a_is_white else (eb, ea)
        limit = (chess.engine.Limit(depth=depth) if depth
                 else chess.engine.Limit(time=movetime / 1000.0))
        board = chess.Board(fen)
        game = object()                        # one game id -> engines see one game
        while not board.is_game_over(claim_draw=True):
            if board.ply() >= MAX_PLIES:
                return 0.5, "adjudicated draw", board.ply()
            mover_is_white = board.turn == chess.WHITE
            r = (white if mover_is_white else black).play(board, limit, game=game)
            if r.move is None or r.move not in board.legal_moves:
                a_lost = mover_is_white == a_is_white
                return (0.0 if a_lost else 1.0), f"illegal move {r.move}", board.ply()
            board.push(r.move)
        res = board.result(claim_draw=True)
        reason = board.outcome(claim_draw=True).termination.name.lower()
        if res == "1/2-1/2":
            return 0.5, reason, board.ply()
        a_won = (res == "1-0") == a_is_white
        return (1.0 if a_won else 0.0), reason, board.ply()
    except Exception as e:                     # noqa: BLE001
        return 0.5, f"error: {type(e).__name__}: {e}", 0
    finally:
        for e in (ea, eb):
            if e is not None:
                try:
                    e.quit()
                except Exception:              # noqa: BLE001
                    pass


def elo(score_rate):
    if score_rate <= 0:
        return float("-inf")
    if score_rate >= 1:
        return float("inf")
    return -400.0 * math.log10(1.0 / score_rate - 1.0)


def elo_ci(wins, draws, losses):
    """Elo with a 95% interval, from the per-game score variance."""
    n = wins + draws + losses
    if n == 0:
        return 0.0, 0.0, 0.0
    mu = (wins + 0.5 * draws) / n
    var = (wins * (1 - mu) ** 2 + draws * (0.5 - mu) ** 2
           + losses * (0 - mu) ** 2) / max(1, n - 1)
    se = math.sqrt(var / n)
    lo, hi = max(1e-9, mu - 1.96 * se), min(1 - 1e-9, mu + 1.96 * se)
    return elo(mu), elo(lo), elo(hi)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--movetime", type=int, default=300, help="ms per move")
    ap.add_argument("--depth", type=int, default=None,
                    help="fixed depth instead of fixed time")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--openings", default=None, metavar="FILE",
                    help="file of opening FENs, one per line (default: generated)")
    ap.add_argument("--label", default="")
    for side in ("a", "b"):
        ap.add_argument(f"--{side}-dir", default=".",
                        help=f"engine {side.upper()}'s directory (runs its uci.py)")
        ap.add_argument(f"--{side}-opt", action="append", default=[], metavar="NAME=VALUE",
                        help=f"UCI option for engine {side.upper()}; repeatable")
        ap.add_argument(f"--{side}-name", default=None)
    args = ap.parse_args()

    def spec(side):
        d = os.path.abspath(getattr(args, f"{side}_dir"))
        return {"dir": d, "options": dict(p.split("=", 1) for p in getattr(args, f"{side}_opt")),
                "name": getattr(args, f"{side}_name") or os.path.basename(d)}
    a_spec, b_spec = spec("a"), spec("b")
    for tag, s in (("A", a_spec), ("B", b_spec)):
        print(f"{tag} = {s['name']}  {s['options'] or '(defaults)'}")
    return run_match(args, a_spec, b_spec)


def run_match(args, a_spec, b_spec):
    limit = f"depth {args.depth}" if args.depth else f"{args.movetime}ms/move"
    print(f"{args.games} games @ {limit}, concurrency {args.concurrency}\n")

    openings = load_openings(args.games, path=args.openings)
    print(f"{len(openings)} distinct openings, each played once per colour\n")
    jobs = [(a_spec, b_spec, i % 2 == 0, openings[i // 2], args.movetime, args.depth)
            for i in range(args.games)]

    w = d = l = 0
    reasons = {}
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.concurrency) as ex:
        for i, (sa, reason, plies) in enumerate(ex.map(_play_one, jobs), 1):
            if sa == 1.0:
                w += 1
            elif sa == 0.5:
                d += 1
            else:
                l += 1
            key = reason.split("(")[0].strip()[:44]
            reasons[key] = reasons.get(key, 0) + 1
            if i % 4 == 0 or i == len(jobs):
                e, lo, hi = elo_ci(w, d, l)
                print(f"  {i:>3}/{len(jobs)}  +{w}={d}-{l}  "
                      f"score {(w+0.5*d)/i*100:5.1f}%  "
                      f"Elo {e:+7.1f} [{lo:+.0f}, {hi:+.0f}]", flush=True)

    n = w + d + l
    e, lo, hi = elo_ci(w, d, l)
    print(f"\n{'='*60}")
    print(f"RESULT {args.label}: A +{w} ={d} -{l} of {n}  "
          f"({(w+0.5*d)/n*100:.1f}%)")
    print(f"Elo(A - B) = {e:+.1f}  95% CI [{lo:+.0f}, {hi:+.0f}]")
    print(f"{'-'*60}")
    if lo > 0:
        print("VERDICT: A is stronger (interval excludes zero).")
    elif hi < 0:
        print("VERDICT: A is WEAKER (interval excludes zero).")
    else:
        print("VERDICT: inconclusive — the interval contains zero. More games needed.")
    print("\ngame endings:")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>4}x  {k}")
    print(f"({time.perf_counter()-t0:.0f}s)")


if __name__ == "__main__":
    main()
