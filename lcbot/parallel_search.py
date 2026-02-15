"""Fixed-depth root-splitting search across processes (the GIL rules out threads).

PVS at the root: the first move gets a full window to set alpha, the rest get
null-window searches in workers, fail-highs are re-searched. Workers share no TT.
"""

import os
import multiprocessing as mp

from lcbot.movegen import generate_legal_moves
from lcbot.nnue import load_evaluator
from lcbot.search import INF, Searcher
from lcbot.tablebase import Tablebase

MIN_PARALLEL_DEPTH = 3

# One NNUE evaluator per (path, mode), per process: quantising a net is ~0.3s.
_EVALUATORS = {}


def _evaluator_for(nnue_path, nnue_mode):
    """Cached NNUEEvaluator for this net, or None for the hand-written eval.
    Load errors propagate; validate the net first if you want a fallback."""
    if not nnue_path:
        return None
    key = (nnue_path, nnue_mode)
    ev = _EVALUATORS.get(key)
    if ev is None:
        ev = _EVALUATORS[key] = load_evaluator(nnue_path, nnue_mode)
    return ev


def _split_round_robin(moves, num_workers):
    buckets = [[] for _ in range(num_workers)]
    for i, m in enumerate(moves):
        buckets[i % num_workers].append(m)
    return [b for b in buckets if b]


def _score_after(searcher, board, move, depth, alpha, beta):
    """-negamax(child) after `move`, as _negamax's root move loop does. The
    root's check extension is applied before subtracting the ply."""
    child_depth = (depth + 1 if board.in_check() else depth) - 1
    board.make_move(move)
    try:
        score = -searcher._negamax(board, child_depth, -beta, -alpha, 1)
    finally:
        board.unmake_move()
    return score


def _open_tablebase(tablebase_path):
    """A Tablebase for `tablebase_path`, or None if unset or it fails to open."""
    if not tablebase_path:
        return None
    try:
        return Tablebase(tablebase_path)
    except OSError:
        return None


def _search_bucket_null_window(args):
    """Worker: null-window test each move against `alpha`. Module-level so
    'spawn' can pickle it. Returns ([(move, score, failed_high)], nodes)."""
    board, moves, depth, alpha, killers, history, tablebase_path, nnue_path, nnue_mode = args
    # A Tablebase holds open file handles and can't be pickled; open one per worker.
    tablebase = _open_tablebase(tablebase_path)
    try:
        evaluator = _evaluator_for(nnue_path, nnue_mode)
        searcher = Searcher(tablebase=tablebase, evaluator=evaluator)
        if evaluator is not None:
            # The accumulator was stripped before pickling; rebuild it.
            evaluator.refresh(board)
        searcher.killers = killers
        searcher.history = history
        results = []
        for m in moves:
            score = _score_after(searcher, board, m, depth, alpha, alpha + 1)
            results.append((m, score, score > alpha))
        return results, searcher.nodes
    finally:
        if tablebase is not None:
            tablebase.close()


def parallel_find_best_move(board, depth: int, num_workers: int = None, pool: mp.Pool = None,
                             tablebase_path: str = None, nnue_path: str = None,
                             nnue_mode: str = "hybrid"):
    """Root-split search to a fixed `depth` on `num_workers` processes
    (default os.cpu_count()). Returns (best_move, best_score) like
    search.find_best_move. `tablebase_path` and `nnue_path` apply to every
    Searcher, sequential and worker."""
    num_workers = num_workers or os.cpu_count() or 1
    moves = generate_legal_moves(board)
    if not moves:
        return 0, 0

    evaluator = _evaluator_for(nnue_path, nnue_mode)
    tablebase = _open_tablebase(tablebase_path)
    try:
        if len(moves) == 1 or num_workers <= 1 or depth < MIN_PARALLEL_DEPTH:
            searcher = Searcher(tablebase=tablebase, evaluator=evaluator)
            return searcher.search(board, max_depth=depth)

        # Step 1: sequential warm-up.
        probe = Searcher(tablebase=tablebase, evaluator=evaluator)
        probe.search(board, max_depth=depth - 1)
        ordered = probe._order_moves(board, moves, probe.best_move_root, 0)

        # Step 2: first move, full window, sequential; sets alpha.
        best_move = ordered[0]
        best_score = _score_after(probe, board, best_move, depth, -INF, INF)
        rest = ordered[1:]
        if not rest:
            return best_move, best_score

        # Step 3: every remaining move, null window, in parallel.
        buckets = _split_round_robin(rest, num_workers)
        tasks = [(board, bucket, depth, best_score, probe.killers, probe.history, tablebase_path,
                  nnue_path, nnue_mode)
                 for bucket in buckets]

        # Strip the accumulator so the quantised net isn't pickled with every
        # task. pool.map pickles before returning, so restoring after is safe.
        acc, board.nnue = board.nnue, None
        try:
            if pool is not None:
                raw_results = pool.map(_search_bucket_null_window, tasks)
            else:
                with mp.Pool(processes=len(buckets)) as owned_pool:
                    raw_results = owned_pool.map(_search_bucket_null_window, tasks)
        finally:
            board.nnue = acc

        fail_highs = [m for move_results, _nodes in raw_results for m, _s, failed in move_results if failed]

        # Step 4: re-search any fail-high move at full window, sequentially.
        for m in fail_highs:
            score = _score_after(probe, board, m, depth, -INF, INF)
            if score > best_score:
                best_move, best_score = m, score

        return best_move, best_score
    finally:
        if tablebase is not None:
            tablebase.close()


# --- self-test ------------------------------------------------------------

def _run_self_test() -> bool:
    from lcbot.board import Board
    from lcbot.move import move_to_uci
    from lcbot.search import MATE_THRESHOLD

    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")

    # 1. A single legal move falls back to sequential search.
    b = Board("k7/8/1K6/8/8/8/8/7Q b - - 0 1")
    move, score = parallel_find_best_move(b, depth=4, num_workers=4)
    check("single legal move: falls back and returns a legal move", move != 0)

    # 2. Depth below MIN_PARALLEL_DEPTH falls back to sequential search.
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=2, num_workers=4)
    check("depth below MIN_PARALLEL_DEPTH: still returns a legal move", move != 0)

    # 3. Mate-in-1 is still found with real multi-worker parallel search.
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    check("mate-in-1 rook: parallel search finds it", move_to_uci(move) == "e1e8")
    check("mate-in-1 rook: score reflects forced mate", score >= MATE_THRESHOLD)

    # 4. Hanging queen is still captured with real multi-worker parallel search.
    b = Board("3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    check("hanging queen: parallel search captures it", move_to_uci(move) == "d3d5")
    check("hanging queen: score reflects material win", score > 500)

    # 5. A different worker count gives a different round-robin split.
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=2)
    check("num_workers=2: still finds the mate", move_to_uci(move) == "e1e8")

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_self_test() else 1)
