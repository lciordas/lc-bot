"""generate_legal_captures must equal the capture/promotion subset of generate_legal_moves."""

import random

from board import Board
from move import is_capture, is_promotion
from movegen import generate_legal_captures, generate_legal_moves
from perft import PERFT_SUITE


def _noisy(moves):
    return sorted(m for m in moves if is_capture(m) or is_promotion(m))


def test_captures_subset_of_legal():
    rng = random.Random(42)
    checked = 0
    for name, fen, _expected in PERFT_SUITE:
        for walk in range(8):
            board = Board(fen)
            for ply in range(30):
                legal = generate_legal_moves(board)
                if not legal:
                    break
                assert sorted(generate_legal_captures(board)) == _noisy(legal), (
                    f"mismatch at {board.get_fen()} ({name} walk={walk} ply={ply})"
                )
                checked += 1
                board.make_move(rng.choice(legal))
    assert checked > 1000
