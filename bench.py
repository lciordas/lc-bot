import sys
import time

from board import Board, STARTING_FEN
from evaluation import evaluate
from perft import perft
from search import Searcher

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
ENDGAME = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"


def bench_perft(depth):
    print(f"perft  (depth {depth})")
    total_nodes = total_dt = 0.0
    for name, fen in (("initial", STARTING_FEN), ("kiwipete", KIWIPETE)):
        b = Board(fen)
        t0 = time.perf_counter()
        nodes = perft(b, depth)
        dt = time.perf_counter() - t0
        total_nodes += nodes
        total_dt += dt
        print(f"    {name:10} {nodes:>10} nodes  {dt:7.2f}s  {nodes / dt:>9,.0f} nps")
    print(f"    {'overall':10} {'':>10}        {total_dt:7.2f}s  {total_nodes / total_dt:>9,.0f} nps\n")
    return total_nodes / total_dt


def bench_search(depth):
    print(f"search (fixed depth {depth})")
    total_nodes = 0
    total_dt = 0.0
    for name, fen in (("initial", STARTING_FEN), ("kiwipete", KIWIPETE), ("endgame", ENDGAME)):
        s = Searcher()
        t0 = time.perf_counter()
        s.search(Board(fen), max_depth=depth)
        dt = time.perf_counter() - t0
        total_nodes += s.nodes
        total_dt += dt
        print(f"    {name:10} {s.nodes:>10} nodes  {dt:7.2f}s  {s.nodes / dt:>9,.0f} nps")
    print(f"    {'overall':10} {total_nodes:>10} nodes  {total_dt:7.2f}s  {total_nodes / total_dt:>9,.0f} nps\n")
    return total_nodes / total_dt


def bench_eval(n):
    b = Board(KIWIPETE)
    t0 = time.perf_counter()
    for _ in range(n):
        evaluate(b)
    dt = time.perf_counter() - t0
    print(f"eval   {n:>10} calls   {dt:7.2f}s  {n / dt:>9,.0f} evals/sec\n")
    return n / dt


def bench_depth_in_time(seconds):
    s = Searcher()
    t0 = time.perf_counter()
    s.search(Board(KIWIPETE), movetime=seconds)
    dt = time.perf_counter() - t0
    print(f"depth  kiwipete in {seconds:.0f}s budget -> reached depth "
          f"{s.completed_depth}  ({s.nodes:,} nodes, {dt:.2f}s)\n")
    return s.completed_depth


if __name__ == "__main__":
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    perft_depth = 3 if quick else 4
    search_depth = 4 if quick else 5
    eval_n = 50_000 if quick else 200_000
    budget = 3.0 if quick else 5.0

    print(f"=== lc-bot bench {'(quick)' if quick else ''} ===\n")
    bench_perft(perft_depth)
    bench_search(search_depth)
    bench_eval(eval_n)
    bench_depth_in_time(budget)
