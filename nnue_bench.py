"""Search nps and depth-in-3s for hand-written, hybrid NNUE and pure NNUE eval.

Uses random weights, so only the timings mean anything.

    uv run python nnue_bench.py
"""
import time

from board import Board
from search import Searcher
from nnue_net import random_net
from nnue import evaluator_from_net

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
ENDGAME = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"


def fixed_depth(evaluator, depth=4):
    total_nodes, total_time = 0, 0.0
    for fen in (START, KIWIPETE, ENDGAME):
        b = Board(fen)
        s = Searcher(evaluator=evaluator)
        t = time.perf_counter()
        s.search(b, max_depth=depth)
        total_time += time.perf_counter() - t
        total_nodes += s.nodes
    return total_nodes, total_time


def depth_in_budget(evaluator, budget=3.0):
    b = Board(KIWIPETE)
    s = Searcher(evaluator=evaluator)
    s.search(b, max_depth=64, movetime=budget)
    return s.completed_depth, s.nodes


def main():
    print("Building nets (N=256)...")
    hyb = evaluator_from_net(random_net(N=256, seed=11, mode="hybrid"))
    pure_net = random_net(N=256, seed=11, mode="pure")
    pure_net.scale = 300.0
    pure = evaluator_from_net(pure_net)

    modes = (("hand-written", None), ("nnue hybrid", hyb), ("nnue pure", pure))

    print(f"\n{'mode':<16} {'nodes':>9} {'time':>8} {'nps':>10}"
          f" {'depth@3s':>9} {'nodes@3s':>10}")
    print("-" * 68)
    base_nps = None
    for label, ev in modes:
        n, t = fixed_depth(ev)
        nps = n / t
        d, dn = depth_in_budget(ev)
        if base_nps is None:
            base_nps = nps
        print(f"{label:<16} {n:>9} {t:>7.2f}s {nps:>10,.0f}"
              f" {d:>9} {dn:>10,}   ({nps / base_nps:.2f}x)")


if __name__ == "__main__":
    main()
