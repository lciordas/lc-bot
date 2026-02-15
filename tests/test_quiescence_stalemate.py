"""Quiescence must score a stalemate as 0, not stand pat or alpha.

Reachable via razoring, which passes positions to quiescence without checking for legal moves.
"""

from lcbot.board import Board
from lcbot.search import Searcher


def test_stalemate_is_draw():
    b = Board("k7/8/1Q6/2K5/8/8/8/8 b - - 0 1")  # stalemate
    s = Searcher()
    s.start = __import__("time").perf_counter()
    for alpha, beta in ((-50, -49), (-10, -9), (5, 6), (20, 21)):
        assert s._quiescence(b, alpha, beta, ply=1) == 0


def test_razoring_stalemate():
    """A razoring-eligible _negamax call (non-PV, ply > 0, depth 1-2) on a stalemate returns 0."""
    b = Board("k7/8/1Q6/2K5/8/8/8/8 b - - 0 1")
    s = Searcher()
    s.start = __import__("time").perf_counter()
    for alpha in (-50, -10, 5, 20):
        result = s._negamax(b, depth=1, alpha=alpha, beta=alpha + 1, ply=1)
        assert result == 0, f"alpha={alpha}: got {result}, expected 0 (stalemate)"


def test_quiet_position_stand_pat():
    from lcbot.evaluation import evaluate

    b = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    s = Searcher()
    s.start = __import__("time").perf_counter()
    result = s._quiescence(b, -1_000_000, 1_000_000, ply=1)
    assert result == evaluate(b)
