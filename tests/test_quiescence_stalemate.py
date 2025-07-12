"""_quiescence's
not-in-check branch checked "are there any captures?" but never "are there
any legal moves at all?" -- so a genuine stalemate (zero legal moves, not in
check) fell through to `return alpha` (or the stand-pat eval) instead of the
correct draw score, 0. Reachable via razoring (which hands quiescence a
position it never itself verified has a legal move) and via any real
quiescence leaf that happens to be a stalemate.
"""

from board import Board
from search import Searcher


def test_stalemate_is_draw():
    b = Board("k7/8/1Q6/2K5/8/8/8/8 b - - 0 1")  # verified stalemate: 0 legal moves, not in check
    s = Searcher()
    s.start = __import__("time").perf_counter()
    for alpha, beta in ((-50, -49), (-10, -9), (5, 6), (20, 21)):
        assert s._quiescence(b, alpha, beta, ply=1) == 0


def test_razoring_stalemate():
    """Reproduces the exact path the bug was found through: a razoring-
    eligible _negamax call (non-PV, not in check, ply>0, depth in [1,2])
    on a real stalemate position must return 0, not echo back alpha."""
    b = Board("k7/8/1Q6/2K5/8/8/8/8 b - - 0 1")
    s = Searcher()
    s.start = __import__("time").perf_counter()
    for alpha in (-50, -10, 5, 20):
        result = s._negamax(b, depth=1, alpha=alpha, beta=alpha + 1, ply=1)
        assert result == 0, f"alpha={alpha}: got {result}, expected 0 (stalemate)"


def test_quiet_position_stand_pat():
    """Guards against an overzealous fix: a position with no captures
    available but plenty of legal quiet moves must still use the normal
    stand-pat evaluation, not be treated as a stalemate."""
    from evaluation import evaluate

    b = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")  # bare kings, no captures, definitely not stalemate
    s = Searcher()
    s.start = __import__("time").perf_counter()
    result = s._quiescence(b, -1_000_000, 1_000_000, ply=1)
    assert result == evaluate(b)
