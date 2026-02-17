"""Compares hand-written eval vs the NNUE net on 1-ply move choice and error tails.

Search depends on ranking siblings correctly and on large errors, not mean
error, so this reports top-1 agreement with Stockfish and error percentiles.

    uv run python tools/check_ranking.py
"""
import random

import chess
import chess.engine

from lcbot.board import Board
from lcbot.evaluation import evaluate
from lcbot.movegen import generate_legal_moves
from lcbot.nnue import load_evaluator
from lcbot.uci import move_to_uci

SF = "/opt/homebrew/bin/stockfish"


def positions(n=260, seed=11):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        b = Board()
        for _ in range(rng.randint(8, 50)):
            mvs = generate_legal_moves(b)
            if not mvs:
                break
            b.make_move(rng.choice(mvs))
        if generate_legal_moves(b) and not chess.Board(b.get_fen()).is_game_over():
            out.append(b.get_fen())
    return out


def best_by_eval(fen, evaluator):
    """1-ply best move under an evaluator: maximise the negated child score."""
    b = Board(fen)
    if evaluator is not None:
        evaluator.attach(b)
    best, best_sc = None, None
    for mv in generate_legal_moves(b):
        b.make_move(mv)
        sc = -(evaluator(b) if evaluator is not None else evaluate(b))
        b.unmake_move()
        if best_sc is None or sc > best_sc:
            best, best_sc = mv, sc
    return move_to_uci(best) if best is not None else None


def main():
    ev = load_evaluator("nets/sf_hybrid.json")
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": 2, "Hash": 128})
    fens = positions()

    agree_h = agree_n = 0
    err_h, err_n = [], []
    for fen in fens:
        cb = chess.Board(fen)
        info = eng.analyse(cb, chess.engine.Limit(depth=14))
        sf_best = info["pv"][0].uci() if info.get("pv") else None
        sc = info["score"].relative.score(mate_score=30000)
        if sf_best is None or sc is None:
            continue
        sc = max(-2000, min(2000, sc))
        if best_by_eval(fen, None) == sf_best:
            agree_h += 1
        if best_by_eval(fen, ev) == sf_best:
            agree_n += 1
        b = Board(fen)
        ev.attach(b)
        err_h.append(abs(evaluate(b) - sc))
        err_n.append(abs(ev(b) - sc))
    eng.quit()

    n = len(err_h)
    def pct(v, p):
        v = sorted(v)
        return v[min(len(v) - 1, int(len(v) * p))]

    print(f"{n} positions, Stockfish depth 14 as truth\n")
    print(f"{'metric':<34} {'hand-written':>13} {'hybrid+net':>12}")
    print("-" * 62)
    print(f"{'top-1 move agrees with SF':<34} {agree_h/n*100:>12.1f}% {agree_n/n*100:>11.1f}%")
    print(f"{'mean abs error':<34} {sum(err_h)/n:>12.1f} {sum(err_n)/n:>12.1f}")
    print(f"{'median abs error':<34} {pct(err_h,0.50):>12.1f} {pct(err_n,0.50):>12.1f}")
    print(f"{'90th pct abs error':<34} {pct(err_h,0.90):>12.1f} {pct(err_n,0.90):>12.1f}")
    print(f"{'99th pct abs error (the tail)':<34} {pct(err_h,0.99):>12.1f} {pct(err_n,0.99):>12.1f}")
    print(f"{'max abs error':<34} {max(err_h):>12.1f} {max(err_n):>12.1f}")


if __name__ == "__main__":
    main()
