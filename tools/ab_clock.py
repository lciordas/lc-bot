"""A/B match on real clocks (base + increment, optional pondering), as on Lichess.

Same openings and Elo maths as ab_test.py; a flag counts as a loss.

    uv run python tools/ab_clock.py --games 100 --base 30 --inc 0.3 \\
        --a-dir . --a-opt UseNNUE=true --a-ponder \\
        --b-dir . --b-opt UseNNUE=true
"""
import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor

import chess
import chess.engine

from ab_test import elo_ci, load_openings

MAX_PLIES = 300


def _engine(spec):
    d = spec["dir"]
    e = chess.engine.SimpleEngine.popen_uci(
        ["uv", "run", "--project", d, "python", os.path.join(d, "uci.py")],
        cwd=d, stderr=open(os.devnull, "w"))
    e.configure({k: v for k, v in spec["options"].items()})
    return e


def _play_one(job):
    a, b, a_is_white, fen, base, inc = job
    ea = eb = None
    try:
        ea, eb = _engine(a), _engine(b)
        white, black = (ea, eb) if a_is_white else (eb, ea)
        ponder = {chess.WHITE: a["ponder"] if a_is_white else b["ponder"],
                  chess.BLACK: b["ponder"] if a_is_white else a["ponder"]}
        board = chess.Board(fen)
        clock = {chess.WHITE: base, chess.BLACK: base}
        game = object()                   # one game id -> engines see one game
        while not board.is_game_over(claim_draw=True):
            if board.ply() >= MAX_PLIES:
                return 0.5, "adjudicated draw", board.ply()
            side = board.turn
            eng = white if side == chess.WHITE else black
            t0 = time.perf_counter()
            r = eng.play(board, chess.engine.Limit(
                white_clock=clock[chess.WHITE], black_clock=clock[chess.BLACK],
                white_inc=inc, black_inc=inc), ponder=ponder[side], game=game)
            clock[side] -= time.perf_counter() - t0
            if clock[side] < 0:
                a_lost = (side == chess.WHITE) == a_is_white
                return (0.0 if a_lost else 1.0), "flag", board.ply()
            clock[side] += inc
            if r.move is None or r.move not in board.legal_moves:
                a_lost = (side == chess.WHITE) == a_is_white
                return (0.0 if a_lost else 1.0), f"illegal move {r.move}", board.ply()
            board.push(r.move)
        res = board.result(claim_draw=True)
        reason = board.outcome(claim_draw=True).termination.name.lower()
        if res == "1/2-1/2":
            return 0.5, reason, board.ply()
        a_won = (res == "1-0") == a_is_white
        return (1.0 if a_won else 0.0), reason, board.ply()
    except Exception as e:                       # noqa: BLE001
        return 0.5, f"error: {type(e).__name__}: {e}", 0
    finally:
        for e in (ea, eb):
            if e is not None:
                try:
                    e.quit()
                except Exception:                # noqa: BLE001
                    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--base", type=float, default=30.0, help="seconds per side")
    ap.add_argument("--inc", type=float, default=0.3, help="increment, seconds")
    ap.add_argument("--concurrency", type=int, default=4,
                    help="games at once. With pondering both engines think at "
                         "once, so keep 2x this under the core count.")
    ap.add_argument("--label", default="")
    for side in ("a", "b"):
        ap.add_argument(f"--{side}-dir", required=True)
        ap.add_argument(f"--{side}-opt", action="append", default=[], metavar="NAME=VALUE")
        ap.add_argument(f"--{side}-ponder", action="store_true")
        ap.add_argument(f"--{side}-name", default=None)
    args = ap.parse_args()

    def spec(side):
        d = os.path.abspath(getattr(args, f"{side}_dir"))
        return {"dir": d,
                "options": dict(p.split("=", 1) for p in getattr(args, f"{side}_opt")),
                "ponder": getattr(args, f"{side}_ponder"),
                "name": getattr(args, f"{side}_name") or os.path.basename(d)}
    a, b = spec("a"), spec("b")
    for tag, s in (("A", a), ("B", b)):
        print(f"{tag} = {s['name']}  {s['options'] or '(defaults)'}  ponder={'on' if s['ponder'] else 'off'}")
    print(f"{args.games} games @ {args.base:g}+{args.inc:g}s, concurrency {args.concurrency}")
    openings = load_openings(args.games)
    print(f"{len(openings)} distinct openings, each played once per colour\n")

    jobs = [(a, b, i % 2 == 0, openings[i // 2], args.base, args.inc) for i in range(args.games)]
    w = d = l = 0
    reasons = {}
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.concurrency) as ex:
        for i, (sa, reason, _plies) in enumerate(ex.map(_play_one, jobs), 1):
            w += sa == 1.0
            d += sa == 0.5
            l += sa == 0.0
            reasons[reason[:44]] = reasons.get(reason[:44], 0) + 1
            if i % 4 == 0 or i == len(jobs):
                e, lo, hi = elo_ci(w, d, l)
                print(f"  {i:>3}/{len(jobs)}  +{w}={d}-{l}  score {(w + 0.5 * d) / i * 100:5.1f}%  "
                      f"Elo {e:+7.1f} [{lo:+.0f}, {hi:+.0f}]", flush=True)
    n = w + d + l
    e, lo, hi = elo_ci(w, d, l)
    print(f"\n{'=' * 60}")
    print(f"RESULT {args.label}: A +{w} ={d} -{l} of {n}  ({(w + 0.5 * d) / n * 100:.1f}%)")
    print(f"Elo(A - B) = {e:+.1f}  95% CI [{lo:+.0f}, {hi:+.0f}]")
    print("-" * 60)
    if lo > 0:
        print("VERDICT: A is stronger (interval excludes zero).")
    elif hi < 0:
        print("VERDICT: A is WEAKER (interval excludes zero).")
    else:
        print("VERDICT: inconclusive -- the interval contains zero. More games needed.")
    print("\ngame endings:")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>4}x  {k}")
    print(f"({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
