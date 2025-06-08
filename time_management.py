"""Move-time budgeting for UCI `go wtime/btime/winc/binc`.

Returns a soft limit (don't start a new depth past it) and a hard limit
(absolute ceiling, enforced mid-search).
"""

from dataclasses import dataclass

# Safety margin for network/GUI lag.
MOVE_OVERHEAD_MS = 50

# Assumed moves remaining when the GUI doesn't send `movestogo`.
DEFAULT_MOVES_TO_GO = 30

# Cap on the share of remaining time one move may use, even with a big increment.
MAX_FRACTION_OF_REMAINING = 0.5

# Fraction of the increment added to this move's budget.
INCREMENT_USAGE = 0.75


@dataclass
class TimeBudget:
    soft_limit: float  # seconds -- stop starting new depths once elapsed reaches this
    hard_limit: float  # seconds -- absolute ceiling, checked mid-search


def compute_budget(my_time_ms, my_inc_ms=0, moves_to_go=None) -> TimeBudget:
    """Budget from the side to move's clock and increment (ms). `moves_to_go`
    overrides DEFAULT_MOVES_TO_GO when given."""
    my_time_ms = max(0, my_time_ms - MOVE_OVERHEAD_MS)
    my_inc_ms = max(0, my_inc_ms)
    n = moves_to_go if moves_to_go and moves_to_go > 0 else DEFAULT_MOVES_TO_GO

    target_ms = my_time_ms / n + my_inc_ms * INCREMENT_USAGE
    target_ms = min(target_ms, my_time_ms * MAX_FRACTION_OF_REMAINING)
    target_ms = max(target_ms, 10.0)  # always attempt at least a token search

    soft_limit = target_ms / 1000.0
    hard_limit = min(soft_limit * 3.0, my_time_ms / 1000.0 * MAX_FRACTION_OF_REMAINING)
    hard_limit = max(hard_limit, soft_limit)  # hard limit is never tighter than soft

    return TimeBudget(soft_limit=soft_limit, hard_limit=hard_limit)


if __name__ == "__main__":
    import sys

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
        return cond

    ok = True

    b = compute_budget(my_time_ms=300_000, my_inc_ms=0)
    ok &= check("plenty of time: soft limit is a small slice of it", 0 < b.soft_limit < 15)
    ok &= check("hard limit is never tighter than soft", b.hard_limit >= b.soft_limit)

    b = compute_budget(my_time_ms=500, my_inc_ms=0)
    ok &= check("very low time: budget still positive", b.soft_limit > 0 and b.hard_limit > 0)
    ok &= check("very low time: hard limit stays small (panic mode)", b.hard_limit < 1.0)

    b = compute_budget(my_time_ms=0, my_inc_ms=0)
    ok &= check("zero time left: still returns a positive token budget", b.soft_limit > 0)

    fast = compute_budget(my_time_ms=60_000, my_inc_ms=0)
    slow = compute_budget(my_time_ms=60_000, my_inc_ms=5_000)
    ok &= check("increment increases the budget", slow.soft_limit > fast.soft_limit)

    default_n = compute_budget(my_time_ms=60_000, my_inc_ms=0)
    fewer_moves = compute_budget(my_time_ms=60_000, my_inc_ms=0, moves_to_go=5)
    ok &= check("fewer moves-to-go gives a bigger budget per move",
                fewer_moves.soft_limit > default_n.soft_limit)

    huge_inc = compute_budget(my_time_ms=10_000, my_inc_ms=100_000)
    ok &= check("budget never exceeds the fraction-of-remaining cap",
                huge_inc.soft_limit <= 10.0 * MAX_FRACTION_OF_REMAINING + 1e-9)

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)
