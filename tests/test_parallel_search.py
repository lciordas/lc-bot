"""Root-split parallel search, checked on known-answer positions.

Workers have their own TT/killers/history, so scores can differ from a
sequential search at the same depth; only objectively correct answers are asserted.
"""

from lcbot.board import Board
from lcbot.move import move_to_uci
from lcbot.movegen import generate_legal_moves
from lcbot.search import MATE_THRESHOLD, Searcher
from lcbot.parallel_search import MIN_PARALLEL_DEPTH, _score_after, _split_round_robin, parallel_find_best_move


def test_round_robin():
    moves = list(range(7))
    buckets = _split_round_robin(moves, num_workers=3)
    assert buckets == [[0, 3, 6], [1, 4], [2, 5]]


def test_round_robin_more_workers():
    buckets = _split_round_robin([1, 2], num_workers=5)
    assert buckets == [[1], [2]]


def test_single_move_sequential():
    b = Board("k7/8/1K6/8/8/8/8/7Q b - - 0 1")  # in check, one legal move
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
    """A root move that mates must score as mate, not 0.

    Searcher.search() returns (0, 0) on a position with no legal moves, which
    is wrong when a worker reaches it right after a mating move."""
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
    """num_workers=2 gives a different root split than the 4-worker tests."""
    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(b, depth=MIN_PARALLEL_DEPTH + 2, num_workers=2)
    assert move_to_uci(move) == "e1e8"


def test_node_count():
    """Parallel wall time must stay within a small multiple of sequential.

    Searching every root move with a full window costs ~15x the nodes; the
    null-window design is ~1.76x. Wall time is used since worker node counts
    aren't exposed."""
    import time
    from lcbot.search import Searcher

    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"  # kiwipete
    depth = 5

    t0 = time.perf_counter()
    Searcher().search(Board(fen), max_depth=depth)
    sequential_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    parallel_find_best_move(Board(fen), depth=depth, num_workers=4)
    parallel_time = time.perf_counter() - t0

    # Loose bound to absorb process-spawn overhead and machine noise.
    assert parallel_time < sequential_time * 5 + 2.0


def test_score_after_check_extension(monkeypatch):
    """When the root is in check, children get the extended depth, as in _negamax.

    Checked by spying on the depth _negamax receives rather than comparing scores."""
    captured_depths = []
    real_negamax = Searcher._negamax

    def spy(self, board, depth, alpha, beta, ply, ext_count=0):
        captured_depths.append(depth)
        return real_negamax(self, board, depth, alpha, beta, ply, ext_count)

    monkeypatch.setattr(Searcher, "_negamax", spy)

    in_check = Board("4r2k/8/8/8/8/8/8/4K3 w - - 0 1")
    assert in_check.in_check()
    move = generate_legal_moves(in_check)[0]
    s = Searcher()
    _score_after(s, in_check, move, depth=5, alpha=-10**6, beta=10**6)
    assert captured_depths[0] == 5  # check extension applied

    captured_depths.clear()
    not_in_check = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert not not_in_check.in_check()
    move2 = generate_legal_moves(not_in_check)[0]
    _score_after(s, not_in_check, move2, depth=5, alpha=-10**6, beta=10**6)
    assert captured_depths[0] == 4  # no extension


def test_score_after_mate_score():
    """A mating move scores MATE - ply, not a flat MATE (uci.py's mate distance relies on it)."""
    from lcbot.search import MATE

    b = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    mate_move = next(m for m in generate_legal_moves(b) if move_to_uci(m) == "e1e8")
    s = Searcher()
    score = _score_after(s, b, mate_move, depth=3, alpha=-10**6, beta=10**6)
    assert score == MATE - 1  # mated at ply 1


def test_tablebase_path():
    """A bad tablebase_path must not crash the sequential or parallel paths.

    Tablebase raises OSError on a bad path; _open_tablebase turns that into no
    tablebase. Actual probing needs Syzygy files, which aren't shipped."""
    single_move = Board("k7/8/1K6/8/8/8/8/7Q b - - 0 1")
    move, score = parallel_find_best_move(
        single_move, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4,
        tablebase_path="/tmp/not-a-real-tablebase-dir-lc-bot",
    )
    assert move != 0

    real_parallel = Board("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1")
    move, score = parallel_find_best_move(
        real_parallel, depth=MIN_PARALLEL_DEPTH + 2, num_workers=4,
        tablebase_path="/tmp/not-a-real-tablebase-dir-lc-bot",
    )
    assert move_to_uci(move) == "e1e8"
