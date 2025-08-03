"""NNUE feature extraction — position to active input indices."""

from bitboard import iter_bits
from constants import WHITE, BLACK, COLORS, PIECE_TYPES

NUM_FEATURES = 768
_PER_COLOUR = 384          # 6 piece types * 64 squares


def feature_index(perspective: int, colour: int, piece_type: int, sq: int) -> int:
    """Index of one (colour, piece_type, square) as seen from `perspective`."""
    if perspective == WHITE:
        return (0 if colour == WHITE else 1) * _PER_COLOUR + piece_type * 64 + sq
    return (0 if colour == BLACK else 1) * _PER_COLOUR + piece_type * 64 + (sq ^ 56)


def active_features(board, perspective: int):
    """Every active input index for `board`, from `perspective`.

    Order is unspecified — callers sum over these, and addition commutes.
    """
    out = []
    for colour in COLORS:
        rel = (0 if colour == perspective else 1) * _PER_COLOUR
        flip = 0 if perspective == WHITE else 56
        for pt in PIECE_TYPES:
            base = rel + pt * 64
            for sq in iter_bits(board.pieces[colour][pt]):
                out.append(base + (sq ^ flip))
    return out


def both_perspectives(board):
    """(white-perspective features, black-perspective features)."""
    return active_features(board, WHITE), active_features(board, BLACK)


def _run_self_test() -> bool:
    from board import Board
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        ok = ok and cond

    b = Board()
    w, bl = both_perspectives(b)
    check("startpos: 32 active features per perspective",
          len(w) == 32 and len(bl) == 32)
    check("startpos: all indices in range",
          all(0 <= i < NUM_FEATURES for i in w + bl))
    check("startpos: no duplicate indices",
          len(set(w)) == 32 and len(set(bl)) == 32)
    # The start position is colour-symmetric, so both perspectives see the
    # identical feature multiset.
    check("startpos is symmetric: both perspectives agree",
          sorted(w) == sorted(bl))

    # A white pawn on e2, seen from White, must be the same index as a black
    # pawn on e7 seen from Black (e2=12, e7=52, and 12 ^ 56 == 52).
    from constants import PAWN
    check("perspective relativisation: We2 == Be7 mirrored",
          feature_index(WHITE, WHITE, PAWN, 12)
          == feature_index(BLACK, BLACK, PAWN, 52))

    # An asymmetric position: the two perspectives must now disagree.
    b2 = Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN1 w Qkq - 0 1")
    w2, b2f = both_perspectives(b2)
    check("asymmetric position: perspectives differ",
          sorted(w2) != sorted(b2f) and len(w2) == 31 and len(b2f) == 31)

    # Mirroring a position must swap the two perspectives' feature sets.
    from evaluation import _mirror_fen
    for fen in ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
                "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
                "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"):
        orig, mirr = Board(fen), Board(_mirror_fen(fen))
        ow, ob = both_perspectives(orig)
        mw, mb = both_perspectives(mirr)
        if sorted(ow) != sorted(mb) or sorted(ob) != sorted(mw):
            check(f"mirror swaps perspectives: {fen[:24]}...", False)
            break
    else:
        check("mirror swaps perspectives (3 positions)", True)

    print("\n" + ("ALL PASS" if ok else "FAILURES"))
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_self_test() else 1)
