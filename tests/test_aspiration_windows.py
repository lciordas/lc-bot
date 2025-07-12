"""Aspiration windows must not change the result vs an effectively full-width window.

Both sides run the same iterative deepening so killers/history/TT state match;
comparing against a single isolated depth gives spurious differences.
"""

import search
from board import Board, STARTING_FEN

POSITIONS = [
    STARTING_FEN,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",  # kiwipete
    "3k4/8/8/3q4/8/3R4/3K4/8 w - - 0 1",  # tactical
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",  # endgame
]


def test_matches_full_window():
    original_window = search.ASPIRATION_WINDOW
    try:
        for fen in POSITIONS:
            for depth in (3, 4, 5):
                search.ASPIRATION_WINDOW = original_window
                narrow_move, narrow_score = search.Searcher().search(Board(fen), max_depth=depth)

                search.ASPIRATION_WINDOW = 10_000_000  # effectively full-width every iteration
                wide_move, wide_score = search.Searcher().search(Board(fen), max_depth=depth)

                assert narrow_score == wide_score, (
                    f"depth {depth}, {fen}: narrow={narrow_score} wide={wide_score}"
                )
                assert narrow_move == wide_move
    finally:
        search.ASPIRATION_WINDOW = original_window


def test_constant_restored():
    """Catches a leak from the monkeypatch in the previous test."""
    assert search.ASPIRATION_WINDOW == 50
