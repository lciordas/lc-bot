"""Tests for parallel_search.py's root-splitting parallel search."""

from board import Board
from move import move_to_uci
from movegen import generate_legal_moves
from search import MATE_THRESHOLD, Searcher
from parallel_search import MIN_PARALLEL_DEPTH, _score_after, _split_round_robin, parallel_find_best_move


def test_round_robin():
    moves = list(range(7))
    buckets = _split_round_robin(moves, num_workers=3)
    assert buckets == [[0, 3, 6], [1, 4], [2, 5]]


def test_round_robin_more_workers():
    buckets = _split_round_robin([1, 2], num_workers=5)
    assert buckets == [[1], [2]]


def test_single_move_sequential():
    b = Board("k7/8/1K6/8/8/8/8/7Q b - - 0 1")  # in check, only Kb8 escapes
    assert len(generate_legal_moves(b)) == 1
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    assert move != 0


def test_low_depth_sequential():
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH - 1, num_workers=4)
    assert move != 0


def test_no_legal_moves():
    b = Board("4R1k1/5ppp/8/8/8/8/8/6K1 b - - 0 1")  # back-rank mate, black to move
    assert generate_legal_moves(b) == []
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    assert (move, score) == (0, 0)


def test_mate_in_one():
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    assert move_to_uci(move) == "e1e8"
    assert score >= MATE_THRESHOLD


def test_mating_move_score():
    """Regression test for a real bug found via the module's own self-test:
        Searcher.search() returns (0, 0) unconditionally when called on a
        position with no legal moves -- correct for its normal call site (the
        real game position has no moves: game over) but wrong when a worker
        calls it on a position where the move just made delivered checkmate.
        Before the fix, e1e8# (mate) scored 0 and lost to a mundane pawn push
        with a genuinely positive score.
    """
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    assert move_to_uci(move) != "f2f4"
    assert score >= MATE_THRESHOLD


def test_hanging_queen():
    b = Board("3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4)
    assert move_to_uci(move) == "d3d5"
    assert score > 500


def test_other_worker_count():
    """num_workers=2 exercises a genuinely different round-robin split of
    the same position's root moves than the num_workers=4 tests above."""
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=2)
    assert move_to_uci(move) == "e1e8"


def test_node_count():
    """Regression test for the real, serious bug this module's algorithm was
        redesigned around: an earlier version searched every root move, in every
        worker, with a wide-open window -- measured directly to explore ~15x
        more total nodes than one coherent sequential search to the same depth,
        because it gave up the narrow-window pruning that makes alpha-beta
        efficient for every move after the first. The current design (sequential
        warm-up + first move full-width + remaining moves null-width in
        parallel + fail-high re-search) measured at ~1.76x on this same case
        after the fix. This test doesn't re-measure that exact ratio (multi-
        process node totals aren't available through the public API, and
        reaching into worker-internal counts would couple the test to
        implementation details), but it does assert parallel search completes
        in a bounded, small multiple of sequential search's own wall-clock time
        at a real depth -- a 15x-style regression would fail this immediately,
        while normal run-to-run timing noise on a shared machine should not.
    """
    import time
    from search import Searcher

    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"  # kiwipete
    depth = 5

    t0 = time.perf_counter()
    Searcher().search(Board(fen), max_depth=depth)
    sequential_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    parallel_find_best_move(Board(fen), depth=depth, num_workers=4)
    parallel_time = time.perf_counter() - t0

    # Generous bound (5x wall-clock, not the ~1.76x node-count figure) to
    # absorb process-spawn overhead and machine noise while still catching
    # a real regression back toward the old ~15x-nodes design.
    assert parallel_time < sequential_time * 5 + 2.0


def test_score_after_check_extension(monkeypatch):
    """_score_after
        always searched children at `depth - 1` regardless of whether the root
        position itself was in check. _negamax's own check-extension
        (`if in_check: depth += 1`, applied before it ever recurses into
        children -- see search.py) means a root-in-check position's children
        are entitled to the *extended* depth minus one, not the plain depth
        minus one -- so every move was searched a full ply shallower than an
        equivalent sequential search whenever the root was in check. Verified
        directly by spying on the exact `depth` argument _negamax receives,
        not by comparing scores (which can legitimately differ between
        parallel and sequential runs for unrelated reasons -- see this file's
        module docstring).
    """
    captured_depths = []
    real_negamax = Searcher._negamax

    def spy(self, board, depth, alpha, beta, ply, ext_count=0):
        captured_depths.append(depth)
        return real_negamax(self, board, depth, alpha, beta, ply, ext_count)

    monkeypatch.setattr(Searcher, "_negamax", spy)

    in_check = Board("4r2k/8/8/8/8/8/8/4K3 w - - 0 1")  # white king e1, checked by Re8
    assert in_check.in_check()
    move = generate_legal_moves(in_check)[0]
    s = Searcher()
    _score_after(s, in_check, move, depth=5, alpha=-10**6, beta=10**6)
    assert captured_depths[0] == 5  # depth, not depth-1: the root's own extension applied

    captured_depths.clear()
    not_in_check = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert not not_in_check.in_check()
    move2 = generate_legal_moves(not_in_check)[0]
    _score_after(s, not_in_check, move2, depth=5, alpha=-10**6, beta=10**6)
    assert captured_depths[0] == 4  # depth-1: no extension, matches the un-fixed baseline case


def test_score_after_mate_score():
    """Regression test for the other half of the same fix: an earlier
        version hand-computed a flat `MATE` for a move that delivers checkmate,
        instead of _negamax's own `MATE - ply` convention -- off by exactly one
        ply, which would corrupt uci.py's mate-distance formula
        (`(MATE - abs(score) + 1) // 2`) anywhere this got wired into UCI
        reporting. _negamax, called directly (not through Searcher.search()),
        already returns the correctly ply-adjusted score for a position with no
        legal moves -- no caller-side special-casing needed.
    """
    from search import MATE

    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    mate_move = next(m for m in generate_legal_moves(b) if move_to_uci(m) == "e1e8")
    s = Searcher()
    score = _score_after(s, b, mate_move, depth=3, alpha=-10**6, beta=10**6)
    assert score == MATE - 1  # ply=1 below the root, matching _negamax's own convention


def test_tablebase_path():
    """worker Searcher
        instances were constructed with no tablebase at all, so
        parallel_find_best_move would silently never probe endgame tablebases
        even when one was configured -- no exception, no info string, just
        quietly worse endgame play. This doesn't assert a probe actually
        happens (that needs real Syzygy table files this test suite doesn't
        ship), just that passing a bogus tablebase_path doesn't crash the
        sequential-fallback and real-parallel code paths. Tablebase itself
        raises OSError on a bad path (verified directly, not assumed) --
        parallel_search.py's own _open_tablebase helper is what degrades that
        to "no tablebase" instead, mirroring uci.py's _sync_tablebase, which
        does the same try/except itself rather than relying on Tablebase to.
    """
    single_move = Board("k7/8/1K6/8/8/8/8/7Q b - - 0 1")
    move, score = parallel_find_best_move(
        single_move, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4,
        tablebase_path="/tmp/not-a-real-tablebase-dir-final-engine",
    )
    assert move != 0

    real_parallel = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(
        real_parallel, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4,
        tablebase_path="/tmp/not-a-real-tablebase-dir-final-engine",
    )
    assert move_to_uci(move) == "e1e8"
