"""Zobrist keys for position hashing (TT lookups and repetition detection).

Board.make_move/unmake_move update the key incrementally. The PRNG has a fixed
seed so keys, and therefore searches, are reproducible.
"""

import random

from constants import WHITE, BLACK

_rng = random.Random(0xC0FFEE)


def _rand64() -> int:
    return _rng.getrandbits(64)


# PIECE_KEYS[color][piece_type][square]
PIECE_KEYS = [[[_rand64() for _ in range(64)] for _ in range(6)] for _ in range(2)]
# Indexed by the 4-bit castling mask.
CASTLE_KEYS = [_rand64() for _ in range(16)]
# Indexed by en-passant file.
EP_KEYS = [_rand64() for _ in range(8)]
# XORed in when Black is to move.
SIDE_KEY = _rand64()


def compute_hash(board) -> int:
    """Compute the key from scratch. Slow; used for setup and tests."""
    h = 0
    for color in (WHITE, BLACK):
        for pt in range(6):
            bb = board.pieces[color][pt]
            while bb:
                sq = (bb & -bb).bit_length() - 1
                h ^= PIECE_KEYS[color][pt][sq]
                bb &= bb - 1
    h ^= CASTLE_KEYS[board.castling]
    if board.ep_square >= 0:
        h ^= EP_KEYS[board.ep_square & 7]
    if board.side == BLACK:
        h ^= SIDE_KEY
    return h
