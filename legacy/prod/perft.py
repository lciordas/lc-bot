"""Perft (performance test) — counts legal-move tree nodes at a given depth.

Perft is the standard correctness check for a move generator: published node
counts exist for many positions, so any disagreement pinpoints a bug.
"""

import sys
import time

from board import STARTING_FEN, Board
from movegen import generate_legal_moves


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    moves = generate_legal_moves(board)
    if depth == 1:
        return len(moves)
    nodes = 0
    for m in moves:
        board.make_move(m)
        nodes += perft(board, depth - 1)
        board.unmake_move()
    return nodes


# Standard perft positions and expected node counts (chessprogramming.org).
PERFT_SUITE = [
    (
        "initial",
        STARTING_FEN,
        {1: 20, 2: 400, 3: 8902, 4: 197281, 5: 4865609},
    ),
    (
        "kiwipete",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        {1: 48, 2: 2039, 3: 97862, 4: 4085603},
    ),
    (
        "endgame",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        {1: 14, 2: 191, 3: 2812, 4: 43238, 5: 674624},
    ),
    (
        "position-4",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        {1: 6, 2: 264, 3: 9467, 4: 422333},
    ),
    (
        "position-5",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        {1: 44, 2: 1486, 3: 62379, 4: 2103487},
    ),
]


def run_suite(max_depth: int = 3) -> bool:
    """Run every perft case up to `max_depth`. Returns True iff all matched."""
    all_ok = True
    for name, fen, expected in PERFT_SUITE:
        print(f"[{name}]  {fen}")
        board = Board(fen)
        for depth in sorted(expected):
            if depth > max_depth:
                continue
            t0 = time.perf_counter()
            actual = perft(board, depth)
            dt = time.perf_counter() - t0
            ok = actual == expected[depth]
            all_ok &= ok
            marker = "ok  " if ok else "FAIL"
            print(f"  d={depth}  nodes={actual:>10}  expected={expected[depth]:>10}  {dt:6.2f}s  {marker}")
        print()
    return all_ok


if __name__ == "__main__":
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    ok = run_suite(max_depth=depth)
    sys.exit(0 if ok else 1)
