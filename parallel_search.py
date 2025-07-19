"""Multiprocessing root-splitting search parallelism."""

import os
import multiprocessing as mp

from movegen import generate_legal_moves
from search import INF, Searcher
from tablebase import Tablebase

MIN_PARALLEL_DEPTH = 3


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
    """Worker entry point (must be a module-level function: multiprocessing
        on this platform uses 'spawn', which pickles the callable by reference).
        Null-window-tests every move in `moves` against `alpha` (the score of
        the best move found so far, established sequentially before this call
        -- see parallel_find_best_move). Returns (results, nodes), where
        `results` is a list of (move, score, failed_high) -- failed_high moves
        need a full-window re-search back in the caller to get their true score,
        matching normal PVS's own re-search-on-fail-high pattern.
    """
    board, moves, depth, alpha, killers, history, tablebase_path = args
    # A live Tablebase wraps an open file handle and isn't picklable across
    # processes -- each worker opens its own from the path instead (mirrors
    # uci.py's own per-session Tablebase lifecycle, just one per worker
    # rather than one per UCI session).
    tablebase = _open_tablebase(tablebase_path)
    try:
        searcher = Searcher(tablebase=tablebase)
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
                             tablebase_path: str = None):
    """Root-split search to a fixed `depth` across `num_workers` processes
        (defaults to os.cpu_count()). Returns (best_move, best_score) -- the same
        2-tuple contract as search.find_best_move, so it's a drop-in alternative
        at call sites that don't need the sequential engine's movetime support.
        See the module docstring for the algorithm and why it isn't simpler.
    """
    num_workers = num_workers or os.cpu_count() or 1
    moves = generate_legal_moves(board)
    if not moves:
        return 0, 0

    tablebase = _open_tablebase(tablebase_path)
    try:
        if len(moves) == 1 or num_workers <= 1 or depth < MIN_PARALLEL_DEPTH:
            searcher = Searcher(tablebase=tablebase)
            return searcher.search(board, max_depth=depth)

        # Step 1: sequential warm-up.
        probe = Searcher(tablebase=tablebase)
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
        tasks = [(board, bucket, depth, best_score, probe.killers, probe.history, tablebase_path)
                 for bucket in buckets]

        if pool is not None:
            raw_results = pool.map(_search_bucket_null_window, tasks)
        else:
            with mp.Pool(processes=len(buckets)) as owned_pool:
                raw_results = owned_pool.map(_search_bucket_null_window, tasks)

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
    from board import Board
    from move import move_to_uci
    from search import MATE_THRESHOLD

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
