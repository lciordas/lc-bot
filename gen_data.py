"""Generate NNUE training data from self-play, labelled by this engine's search."""
import argparse
import json
import os
import random
import sys
import time
from multiprocessing import Process, Queue

from board import Board
from evaluation import evaluate
from movegen import generate_legal_moves
from move import move_flag, FLAG_CAPTURE, FLAG_EN_PASSANT
from search import Searcher

MAX_PLIES = 160
RANDOM_OPENING_PLIES = 8      # random legal moves, for opening diversity
TEACHER_DEPTH = 6
TEACHER_NODES = 8000          # caps teacher cost so throughput is predictable


def is_quiet(board, best_move) -> bool:
    """Not in check, and the best move is not a capture or promotion.

    Rejecting every position with any capture available leaves too little data.
    """
    if board.in_check():
        return False
    f = move_flag(best_move)
    return not ((f & FLAG_CAPTURE) or f == FLAG_EN_PASSANT or f >= 8)


def play_game(rng, searcher):
    """One self-play game. Returns (records, result_for_white)."""
    board = Board()
    positions = []          # (fen, side, score, static)

    for _ in range(RANDOM_OPENING_PLIES):
        moves = generate_legal_moves(board)
        if not moves:
            break
        board.make_move(rng.choice(moves))

    result_white = 0.0
    for ply in range(MAX_PLIES):
        moves = generate_legal_moves(board)
        if not moves:
            if board.in_check():
                result_white = -1.0 if board.side == 0 else 1.0
            break
        if board.is_draw():
            break

        mv, score = searcher.search(board, max_depth=TEACHER_DEPTH,
                                    max_nodes=TEACHER_NODES)
        if mv == 0:
            break
        if is_quiet(board, mv) and abs(score) < 2000:
            positions.append((board.get_fen(), board.side, score,
                              evaluate(board)))
        # Occasional random move so games don't all follow the same line.
        if rng.random() < 0.06:
            mv = rng.choice(moves)
        board.make_move(mv)
    else:
        result_white = 0.0

    return positions, result_white


def worker(wid, seed, target, out_q):
    rng = random.Random(seed)
    searcher = Searcher()
    made = 0
    while made < target:
        searcher.tt.clear()
        positions, result_white = play_game(rng, searcher)
        recs = []
        for fen, side, score, static in positions:
            r = result_white if side == 0 else -result_white
            recs.append({"fen": fen, "score": score, "static": static,
                         "result": r})
        made += len(recs)
        out_q.put(recs)
    out_q.put(None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/train.jsonl")
    ap.add_argument("--positions", type=int, default=200_000)
    ap.add_argument("--workers", type=int, default=max(1, os.cpu_count() - 2))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    per = args.positions // args.workers + 1
    q = Queue(maxsize=256)
    procs = [Process(target=worker, args=(i, 1000 + i, per, q), daemon=True)
             for i in range(args.workers)]
    for p in procs:
        p.start()

    written = 0
    done = 0
    t0 = time.perf_counter()
    with open(args.out, "w") as fh:
        while done < args.workers:
            item = q.get()
            if item is None:
                done += 1
                continue
            for rec in item:
                fh.write(json.dumps(rec) + "\n")
            written += len(item)
            if written % 2000 < len(item):
                el = time.perf_counter() - t0
                print(f"  {written:>8,} positions  {el:7.0f}s  "
                      f"{written / max(el, 1e-9):6.1f} pos/s", flush=True)
    for p in procs:
        p.terminate()
    el = time.perf_counter() - t0
    print(f"done: {written:,} positions in {el:.0f}s "
          f"({written / max(el, 1e-9):.1f}/s) -> {args.out}")


if __name__ == "__main__":
    main()
