from board import Board, STARTING_FEN
from config import EngineConfig
from search import Searcher


def test_default_config():
    s = Searcher()
    assert s.config.tt_size_mb == 64
    assert s._tt_max_entries == Searcher._compute_tt_cap(64)


def test_custom_size():
    small = Searcher(config=EngineConfig(tt_size_mb=1))
    big = Searcher(config=EngineConfig(tt_size_mb=64))
    assert small._tt_max_entries < big._tt_max_entries


def test_resize():
    s = Searcher()
    b = Board(STARTING_FEN)
    s.search(b, max_depth=3)
    assert len(s.tt) > 0

    s.resize_tt(1)
    assert s.config.tt_size_mb == 1
    assert s._tt_max_entries == Searcher._compute_tt_cap(1)
    assert len(s.tt) == 0


def test_store_respects_cap():
    """Directly drives _tt_store past its cap with synthetic keys — a real
    search on the starting position doesn't generate enough distinct nodes to
    exercise the cap, so this isolates the bounding logic itself."""
    s = Searcher(config=EngineConfig(tt_size_mb=1))
    cap = s._tt_max_entries
    for key in range(cap + 500):
        s._tt_store(key, depth=1, score=0, flag=0, move=0, ply=0)
    assert len(s.tt) <= cap


def test_resize_mid_use():
    s = Searcher()
    b = Board(STARTING_FEN)
    s.search(b, max_depth=3)
    s.resize_tt(32)
    move, score = s.search(b, max_depth=3)
    assert move != 0
    assert abs(score) < 150  # start position is roughly balanced
