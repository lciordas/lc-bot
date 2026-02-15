from lcbot.board import Board, STARTING_FEN
from lcbot.config import EngineConfig
from lcbot.search import Searcher


def test_default_config():
    s = Searcher()
    assert s.config.tt_size_mb == 64
    assert s._tt_max_entries == Searcher._compute_tt_cap(64)


def test_custom_size():
    small = Searcher(config=EngineConfig(tt_size_mb=1))
    big = Searcher(config=EngineConfig(tt_size_mb=64))
    assert small._tt_max_entries < big._tt_max_entries


def _populated(tt):
    return sum(1 for entry in tt if entry is not None)


def test_resize():
    s = Searcher()
    b = Board(STARTING_FEN)
    s.search(b, max_depth=3)
    assert _populated(s.tt) > 0

    s.resize_tt(1)
    assert s.config.tt_size_mb == 1
    assert s._tt_max_entries == Searcher._compute_tt_cap(1)
    assert len(s.tt) == s._tt_max_entries
    assert _populated(s.tt) == 0


def test_fixed_size():
    s = Searcher(config=EngineConfig(tt_size_mb=1))
    cap = s._tt_max_entries
    assert len(s.tt) == cap
    for key in range(cap + 500):
        s._tt_store(key, depth=1, score=0, flag=0, move=0, ply=0)
    assert len(s.tt) == cap


def test_depth_preferred():
    """A shallower store never evicts a deeper entry, even for the same key.

    Same-key shallow revisits are routine (e.g. singular-extension verification
    searches) and must not destroy the deeper entry."""
    s = Searcher(config=EngineConfig(tt_size_mb=1))
    cap = s._tt_max_entries
    key_a, key_b = 5, 5 + cap
    assert s._tt_index(key_a) == s._tt_index(key_b)

    s._tt_store(key_a, depth=5, score=100, flag=0, move=42, ply=0)
    s._tt_store(key_b, depth=2, score=-50, flag=0, move=7, ply=0)  # shallower, different key: rejected
    assert s._tt_lookup(key_a) == (5, 0, 100, 42)
    assert s._tt_lookup(key_b) is None

    s._tt_store(key_b, depth=9, score=-50, flag=0, move=7, ply=0)  # deeper, different key: evicts
    assert s._tt_lookup(key_b) == (9, 0, -50, 7)
    assert s._tt_lookup(key_a) is None

    s._tt_store(key_b, depth=1, score=0, flag=0, move=3, ply=0)  # same key, but shallower: rejected
    assert s._tt_lookup(key_b) == (9, 0, -50, 7)

    s._tt_store(key_b, depth=9, score=0, flag=0, move=3, ply=0)  # same key, equal depth: refreshes
    assert s._tt_lookup(key_b) == (9, 0, 0, 3)


def test_resize_mid_use():
    s = Searcher()
    b = Board(STARTING_FEN)
    s.search(b, max_depth=3)
    s.resize_tt(32)
    move, score = s.search(b, max_depth=3)
    assert move != 0
    assert abs(score) < 150  # start position is roughly balanced
