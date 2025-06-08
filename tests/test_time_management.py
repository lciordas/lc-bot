import pytest

from time_management import MAX_FRACTION_OF_REMAINING, TimeBudget, compute_budget


def test_hard_at_least_soft():
    b = compute_budget(my_time_ms=300_000, my_inc_ms=0)
    assert isinstance(b, TimeBudget)
    assert b.hard_limit >= b.soft_limit > 0


def test_plenty_of_time():
    b = compute_budget(my_time_ms=300_000, my_inc_ms=0)
    assert 0 < b.soft_limit < 15


def test_low_time():
    b = compute_budget(my_time_ms=500, my_inc_ms=0)
    assert b.soft_limit > 0
    assert b.hard_limit > 0
    assert b.hard_limit < 1.0  # panic mode


def test_zero_time():
    b = compute_budget(my_time_ms=0, my_inc_ms=0)
    assert b.soft_limit > 0
    assert b.hard_limit > 0


def test_negative_time():
    """A GUI may send a negative wtime right at the flag."""
    b = compute_budget(my_time_ms=-500, my_inc_ms=0)
    assert b.soft_limit > 0
    assert b.hard_limit > 0


def test_increment():
    fast = compute_budget(my_time_ms=60_000, my_inc_ms=0)
    slow = compute_budget(my_time_ms=60_000, my_inc_ms=5_000)
    assert slow.soft_limit > fast.soft_limit


def test_movestogo():
    default_n = compute_budget(my_time_ms=60_000, my_inc_ms=0)
    fewer = compute_budget(my_time_ms=60_000, my_inc_ms=0, moves_to_go=5)
    more = compute_budget(my_time_ms=60_000, my_inc_ms=0, moves_to_go=60)
    assert fewer.soft_limit > default_n.soft_limit > more.soft_limit


def test_bad_movestogo():
    default_n = compute_budget(my_time_ms=60_000, my_inc_ms=0)
    zero = compute_budget(my_time_ms=60_000, my_inc_ms=0, moves_to_go=0)
    negative = compute_budget(my_time_ms=60_000, my_inc_ms=0, moves_to_go=-3)
    assert zero.soft_limit == pytest.approx(default_n.soft_limit)
    assert negative.soft_limit == pytest.approx(default_n.soft_limit)


def test_budget_cap():
    huge_inc = compute_budget(my_time_ms=10_000, my_inc_ms=1_000_000)
    assert huge_inc.soft_limit <= 10.0 * MAX_FRACTION_OF_REMAINING + 1e-9


def test_budget_monotonic():
    less = compute_budget(my_time_ms=30_000, my_inc_ms=0)
    more = compute_budget(my_time_ms=300_000, my_inc_ms=0)
    assert more.soft_limit >= less.soft_limit
