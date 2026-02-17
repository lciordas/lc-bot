"""Compares hand-written eval vs the NNUE net against Stockfish on quiet and tactical positions.

The net is trained on quiet positions, but search also evaluates quiescence
leaves where captures are pending, so error is reported for both sets.

    uv run python tools/check_distribution.py
"""
import random

import chess
import chess.engine

from lcbot.board import Board
from lcbot.evaluation import evaluate
from lcbot.movegen import generate_legal_moves
from lcbot.nnue import load_evaluator

SF = "/opt/homebrew/bin/stockfish"


def collect(n=900, seed=5):
    """Random legal positions, split by whether they are quiet."""
    rng = random.Random(seed)
    quiet, noisy = [], []
    while len(quiet) < n or len(noisy) < n:
        b = Board()
        for _ in range(rng.randint(6, 60)):
            mvs = generate_legal_moves(b)
            if not mvs:
                break
            b.make_move(rng.choice(mvs))
            cb = chess.Board(b.get_fen())
            if cb.is_game_over():
                break
            tactical = cb.is_check() or any(cb.is_capture(m) for m in cb.legal_moves)
            if tactical and len(noisy) < n:
                noisy.append(b.get_fen())
            elif not tactical and len(quiet) < n:
                quiet.append(b.get_fen())
    return quiet[:n], noisy[:n]


def main():
    ev = load_evaluator("nets/sf_hybrid.json")
    eng = chess.engine.SimpleEngine.popen_uci(SF)
    eng.configure({"Threads": 2, "Hash": 64})
    quiet, noisy = collect()
    print(f"{len(quiet)} quiet / {len(noisy)} tactical positions, "
          f"labelled by Stockfish depth 12\n")
    print(f"{'set':<10} {'hand-written':>13} {'hybrid+net':>12} {'change':>9}")
    print("-" * 48)
    for label, fens in (("quiet", quiet), ("tactical", noisy)):
        eh = en = 0.0
        for fen in fens:
            info = eng.analyse(chess.Board(fen), chess.engine.Limit(depth=12))
            sc = info["score"].relative.score(mate_score=30000)
            if sc is None:
                continue
            sc = max(-2000, min(2000, sc))
            b = Board(fen)
            ev.attach(b)
            eh += abs(evaluate(b) - sc)
            en += abs(ev(b) - sc)
        n = len(fens)
        delta = (en - eh) / n
        arrow = "better" if delta < 0 else "WORSE"
        print(f"{label:<10} {eh/n:>12.1f} {en/n:>12.1f} {delta:>+8.1f}  {arrow}")
    eng.quit()


if __name__ == "__main__":
    main()
