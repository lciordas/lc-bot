"""Zobrist hashing — a 64-bit key identifying a position."""

import random

from constants import WHITE, BLACK

_rng = random.Random(0xC0FFEE)


def _rand64() -> int:
    return _rng.getrandbits(64)


# PIECE_KEYS[color][piece_type][square]
PIECE_KEYS = [[[_rand64() for _ in range(64)] for _ in range(6)] for _ in range(2)]
# One key per castling-rights value (the 4-bit mask, 0..15).
CASTLE_KEYS = [_rand64() for _ in range(16)]
# One key per en-passant file (only the file is hash-relevant).
EP_KEYS = [_rand64() for _ in range(8)]
# XORed in whenever it is Black to move.
SIDE_KEY = _rand64()


def compute_hash(board) -> int:
    """Rebuild the full Zobrist key from board state (slow; not on the hot path)."""
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
