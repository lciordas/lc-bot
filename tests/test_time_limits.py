"""Search time limits: small hard limits must not be overshot, and a generous
hard limit must let iterative deepening use most of the soft target.
"""

import time

from lcbot.board import Board
from lcbot.search import LIMIT_CHECK_INTERVAL, Searcher

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"


def test_check_interval():
    """Panic-mode budgets can be ~10ms, so the check must run often."""
    assert LIMIT_CHECK_INTERVAL <= 256


def test_small_hard_limit():
    for hard_ms in (5, 10, 20, 45):
        b = Board(KIWIPETE)
        s = Searcher()
        budget_s = hard_ms / 1000.0
        t0 = time.perf_counter()
        s.search(b, max_depth=64, movetime=budget_s, hard_limit=budget_s)
        actual_ms = (time.perf_counter() - t0) * 1000
        # Headroom for loaded machines; a coarse check interval overshoots 2-9x.
        assert actual_ms <= hard_ms * 1.5 + 15, (
            f"hard_limit={hard_ms}ms grossly overshot: actual={actual_ms:.1f}ms"
        )


def test_uses_soft_limit():
    b = Board(KIWIPETE)
    s = Searcher()
    soft = 0.3
    t0 = time.perf_counter()
    s.search(b, max_depth=64, movetime=soft, hard_limit=soft * 3)
    elapsed = time.perf_counter() - t0
    assert elapsed >= soft * 0.7


def test_hard_limit_bounds():
    b = Board(KIWIPETE)
    s = Searcher()
    soft = 0.1
    hard = 0.3
    t0 = time.perf_counter()
    s.search(b, max_depth=64, movetime=soft, hard_limit=hard)
    elapsed = time.perf_counter() - t0
    assert elapsed <= hard + 0.1  # allowance for the depth in progress


# --- apply_time_budget ---

def test_budget_resets_clock():
    s = Searcher()
    s.start = 0.0  # stale
    before = time.perf_counter()
    s.apply_time_budget(movetime=1.0, hard_limit=None)
    assert s.start >= before


def test_budget_hard_over_movetime():
    s = Searcher()
    s.apply_time_budget(movetime=5.0, hard_limit=1.5)
    assert s.time_limit == 1.5


def test_budget_movetime_fallback():
    s = Searcher()
    s.apply_time_budget(movetime=2.0, hard_limit=None)
    assert s.time_limit == 2.0


def test_budget_unbounded():
    s = Searcher()
    s.apply_time_budget(movetime=None, hard_limit=None)
    assert s.time_limit is None
