"""Bitboard utilities. All ops assume Python int treated as unsigned 64-bit."""


def popcount(bb: int) -> int:
    return bb.bit_count()  # native C popcount (Python 3.10+); ~5x bin().count("1")


def lsb(bb: int) -> int:
    """Index of the least-significant set bit. Caller must ensure bb != 0."""
    return (bb & -bb).bit_length() - 1


def msb(bb: int) -> int:
    """Index of the most-significant set bit. Caller must ensure bb != 0."""
    return bb.bit_length() - 1


def pop_lsb(bb: int):
    """Return (square_index, bb_with_that_bit_cleared)."""
    sq = (bb & -bb).bit_length() - 1
    return sq, bb & (bb - 1)


def iter_bits(bb: int):
    """Yield the index of each set bit, low to high."""
    while bb:
        yield (bb & -bb).bit_length() - 1
        bb &= bb - 1


def set_bit(bb: int, sq: int) -> int:
    return bb | (1 << sq)


def clear_bit(bb: int, sq: int) -> int:
    return bb & ~(1 << sq)


def test_bit(bb: int, sq: int) -> int:
    return (bb >> sq) & 1


def print_bb(bb: int) -> str:
    """Render a bitboard as an 8x8 grid (rank 8 at top) for debugging."""
    lines = []
    for rank in range(7, -1, -1):
        row = f"{rank + 1} "
        for file in range(8):
            row += "1 " if (bb >> (rank * 8 + file)) & 1 else ". "
        lines.append(row)
    lines.append("  a b c d e f g h")
    return "\n".join(lines)
