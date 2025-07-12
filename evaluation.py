"""Handcrafted evaluation: material, tapered PSTs, pawn structure, mobility,
king safety, center control, king tropism, and endgame mop-up.

Every term is antisymmetric under a colour flip. Tables are written in reading
order (index 0 = a8); white reads table[sq ^ 56], black reads table[sq].
"""

from constants import WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, FILES
from bitboard import popcount, iter_bits, lsb
from attacks import KNIGHT_ATTACKS, bishop_attacks, rook_attacks, queen_attacks


# --- Material, by piece type. A list so tuning.py can mutate it. ---
PIECE_VALUE = [100, 320, 330, 500, 900, 0]

# --- Tapered-eval phase weights, indexed by piece type ---
_PHASE_WEIGHT = (0, 1, 1, 2, 4, 0)
PHASE_MAX = 24  # 2*(N+B) + 2*2*R + 2*4*Q over both sides at the start


# --- Piece-square tables (reading order, index 0 = a8) ---
# Each entry is (midgame, endgame). Midgame tables are the Simplified Evaluation
# Function's.

_PST_READING = {
    PAWN: (
        # midgame
        (  0,   0,   0,   0,   0,   0,   0,   0,
          50,  50,  50,  50,  50,  50,  50,  50,
          10,  10,  20,  30,  30,  20,  10,  10,
           5,   5,  10,  25,  25,  10,   5,   5,
           0,   0,   0,  20,  20,   0,   0,   0,
           5,  -5, -10,   0,   0, -10,  -5,   5,
           5,  10,  10, -20, -20,  10,  10,   5,
           0,   0,   0,   0,   0,   0,   0,   0),
        # endgame
        (  0,   0,   0,   0,   0,   0,   0,   0,
         150, 150, 150, 150, 150, 150, 150, 150,
          75,  75,  75,  75,  75,  75,  75,  75,
          50,  50,  50,  50,  50,  50,  50,  50,
          25,  25,  25,  25,  25,  25,  25,  25,
          10,  10,  10,  10,  10,  10,  10,  10,
           0,   0,   0,   0,   0,   0,   0,   0,
           0,   0,   0,   0,   0,   0,   0,   0),
    ),
    KNIGHT: (
        (-50, -40, -30, -30, -30, -30, -40, -50,
         -40, -20,   0,   0,   0,   0, -20, -40,
         -30,   0,  10,  15,  15,  10,   0, -30,
         -30,   5,  15,  20,  20,  15,   5, -30,
         -30,   0,  15,  20,  20,  15,   0, -30,
         -30,   5,  10,  15,  15,  10,   5, -30,
         -40, -20,   0,   5,   5,   0, -20, -40,
         -50, -40, -30, -30, -30, -30, -40, -50),
        (-50, -40, -30, -30, -30, -30, -40, -50,
         -40, -20,   0,   0,   0,   0, -20, -40,
         -30,   0,  10,  15,  15,  10,   0, -30,
         -30,   5,  15,  20,  20,  15,   5, -30,
         -30,   0,  15,  20,  20,  15,   0, -30,
         -30,   5,  10,  15,  15,  10,   5, -30,
         -40, -20,   0,   5,   5,   0, -20, -40,
         -50, -40, -30, -30, -30, -30, -40, -50),
    ),
    BISHOP: (
        (-20, -10, -10, -10, -10, -10, -10, -20,
         -10,   0,   0,   0,   0,   0,   0, -10,
         -10,   0,   5,  10,  10,   5,   0, -10,
         -10,   5,   5,  10,  10,   5,   5, -10,
         -10,   0,  10,  10,  10,  10,   0, -10,
         -10,  10,  10,  10,  10,  10,  10, -10,
         -10,   5,   0,   0,   0,   0,   5, -10,
         -20, -10, -10, -10, -10, -10, -10, -20),
        (-20, -10, -10, -10, -10, -10, -10, -20,
         -10,   0,   0,   0,   0,   0,   0, -10,
         -10,   0,   5,  10,  10,   5,   0, -10,
         -10,   0,  10,  10,  10,  10,   0, -10,
         -10,   0,  10,  10,  10,  10,   0, -10,
         -10,   0,   5,  10,  10,   5,   0, -10,
         -10,   0,   0,   0,   0,   0,   0, -10,
         -20, -10, -10, -10, -10, -10, -10, -20),
    ),
    ROOK: (
        (  0,   0,   0,   0,   0,   0,   0,   0,
           5,  10,  10,  10,  10,  10,  10,   5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
           0,   0,   0,   5,   5,   0,   0,   0),
        ( -5,  -5,  -5,  -5,  -5,  -5,  -5,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,   0,   0,   0,   0,   0,   0,  -5,
          -5,  -5,  -5,  -5,  -5,  -5,  -5,  -5),
    ),
    QUEEN: (
        (-20, -10, -10,  -5,  -5, -10, -10, -20,
         -10,   0,   0,   0,   0,   0,   0, -10,
         -10,   0,   5,   5,   5,   5,   0, -10,
          -5,   0,   5,   5,   5,   5,   0,  -5,
           0,   0,   5,   5,   5,   5,   0,  -5,
         -10,   5,   5,   5,   5,   5,   0, -10,
         -10,   0,   5,   0,   0,   0,   0, -10,
         -20, -10, -10,  -5,  -5, -10, -10, -20),
        (-20, -10, -10,  -5,  -5, -10, -10, -20,
         -10,   0,   0,   0,   0,   0,   0, -10,
         -10,   0,   5,   5,   5,   5,   0, -10,
          -5,   0,   5,   5,   5,   5,   0,  -5,
           0,   0,   5,   5,   5,   5,   0,  -5,
         -10,   5,   5,   5,   5,   5,   0, -10,
         -10,   0,   5,   0,   0,   0,   0, -10,
         -20, -10, -10,  -5,  -5, -10, -10, -20),
    ),
    KING: (
        (-30, -40, -40, -50, -50, -40, -40, -30,
         -30, -40, -40, -50, -50, -40, -40, -30,
         -30, -40, -40, -50, -50, -40, -40, -30,
         -30, -40, -40, -50, -50, -40, -40, -30,
         -20, -30, -30, -40, -40, -30, -30, -20,
         -10, -20, -20, -20, -20, -20, -20, -10,
          20,  20,   0,   0,   0,   0,  20,  20,
          20,  30,  10,   0,   0,  10,  30,  20),
        (  0,  10,  20,  30,  30,  20,  10,   0,
          10,  20,  30,  40,  40,  30,  20,  10,
          20,  30,  40,  50,  50,  40,  30,  20,
          30,  40,  50,  60,  60,  50,  40,  30,
          30,  40,  50,  60,  60,  50,  40,  30,
          20,  30,  40,  50,  50,  40,  30,  20,
          10,  20,  30,  40,  40,  30,  20,  10,
           0,  10,  20,  30,  30,  20,  10,   0),
    ),
}

# Mutable copies for tuning.py.
_PST_READING = {pt: (list(mg), list(eg)) for pt, (mg, eg) in _PST_READING.items()}


def _build_pst():
    """Build (MG, EG), each [color][piece] -> 64-tuple indexed by LERF square."""
    mg = [[None] * 6, [None] * 6]
    eg = [[None] * 6, [None] * 6]
    for pt in range(6):
        mg_tbl, eg_tbl = _PST_READING[pt]
        mg[WHITE][pt] = tuple(mg_tbl[sq ^ 56] for sq in range(64))
        eg[WHITE][pt] = tuple(eg_tbl[sq ^ 56] for sq in range(64))
        mg[BLACK][pt] = tuple(mg_tbl)
        eg[BLACK][pt] = tuple(eg_tbl)
    return mg, eg


def _update_pst_pt_phase(pt: int, phase_idx: int) -> None:
    """Rebuild MG (phase_idx 0) or EG (1) for one piece type; used by the tuner."""
    tbl = _PST_READING[pt][phase_idx]
    target = MG if phase_idx == 0 else EG
    target[WHITE][pt] = tuple(tbl[sq ^ 56] for sq in range(64))
    target[BLACK][pt] = tuple(tbl)


MG, EG = _build_pst()


# --- Pawn-structure tables ---

# Passed-pawn bonus: white pawn on rank r (0 = rank 1) gets PASSED_BONUS[7 - r],
# black gets PASSED_BONUS[r].
PASSED_BONUS = (0, 90, 60, 40, 25, 15, 15, 0)

# Total isolated-pawn penalty by number of isolated pawns.
ISO_PEN = (0, -25, -50, -75, -100, -100, -100, -100, -100)
DOUBLED_PEN = -12  # per extra pawn on a file


def _build_passed_masks():
    """PASSED_MASK[color][sq]: same and adjacent files, all ranks ahead of sq."""
    masks = [[0] * 64, [0] * 64]
    for sq in range(64):
        f, r = sq & 7, sq >> 3
        files = [ff for ff in (f - 1, f, f + 1) if 0 <= ff < 8]
        white = 0
        for rr in range(r + 1, 8):
            for ff in files:
                white |= 1 << (rr * 8 + ff)
        black = 0
        for rr in range(0, r):
            for ff in files:
                black |= 1 << (rr * 8 + ff)
        masks[WHITE][sq] = white
        masks[BLACK][sq] = black
    return masks


PASSED_MASK = _build_passed_masks()

ADJACENT_FILES = tuple(
    (FILES[f - 1] if f > 0 else 0) | (FILES[f + 1] if f < 7 else 0) for f in range(8)
)


# --- King-safety table ---

SHIELD_BONUS = 10  # per friendly pawn shielding the king


def _build_king_shield():
    """KING_SHIELD[color][sq]: the king's file +/- 1, next two ranks forward."""
    shield = [[0] * 64, [0] * 64]
    for sq in range(64):
        f, r = sq & 7, sq >> 3
        files = [ff for ff in (f - 1, f, f + 1) if 0 <= ff < 8]
        white = 0
        for rr in (r + 1, r + 2):
            if rr < 8:
                for ff in files:
                    white |= 1 << (rr * 8 + ff)
        black = 0
        for rr in (r - 1, r - 2):
            if rr >= 0:
                for ff in files:
                    black |= 1 << (rr * 8 + ff)
        shield[WHITE][sq] = white
        shield[BLACK][sq] = black
    return shield


KING_SHIELD = _build_king_shield()


# --- Mobility and mop-up ---

MOBILITY_WEIGHT = 2  # centipawns per attacked square

# Manhattan distance from the centre (symmetric, so orientation doesn't matter).
CMD = (
    6, 5, 4, 3, 3, 4, 5, 6,
    5, 4, 3, 2, 2, 3, 4, 5,
    4, 3, 2, 1, 1, 2, 3, 4,
    3, 2, 1, 0, 0, 1, 2, 3,
    3, 2, 1, 0, 0, 1, 2, 3,
    4, 3, 2, 1, 1, 2, 3, 4,
    5, 4, 3, 2, 2, 3, 4, 5,
    6, 5, 4, 3, 3, 4, 5, 6,
)
CHEB_BONUS = (0, 0, 50, 30, 20, 15, 10, 5)  # by king-to-king Chebyshev distance


# --- Center-control table ---
CENTER_SQUARES = (1 << 27) | (1 << 28) | (1 << 35) | (1 << 36)  # d4, e4, d5, e5
CENTER_OCCUPY_BONUS = 10  # per non-king piece on a center square
CENTER_ATTACK_BONUS = 4   # per N/B/R/Q attack on a center square


# --- King-tropism table ---
# Per-piece-type weight for proximity to the enemy king; pawns and king excluded.
TROPISM_WEIGHT = (0, 4, 3, 2, 5, 0)


# --- Components (all from White's perspective) ---

def game_phase(board) -> int:
    """0 (bare-king endgame) .. PHASE_MAX (full board), from non-pawn material."""
    phase = 0
    for color in (WHITE, BLACK):
        p = board.pieces[color]
        phase += _PHASE_WEIGHT[KNIGHT] * popcount(p[KNIGHT])
        phase += _PHASE_WEIGHT[BISHOP] * popcount(p[BISHOP])
        phase += _PHASE_WEIGHT[ROOK] * popcount(p[ROOK])
        phase += _PHASE_WEIGHT[QUEEN] * popcount(p[QUEEN])
    return phase if phase < PHASE_MAX else PHASE_MAX  # cap: promotions can exceed


def _material_white(board) -> int:
    wp = board.pieces[WHITE]
    bp = board.pieces[BLACK]
    score = 0
    for pt in range(5):  # PAWN..QUEEN; king value is 0
        score += PIECE_VALUE[pt] * (popcount(wp[pt]) - popcount(bp[pt]))
    return score


def _pst_white(board, phase: int) -> int:
    mg = 0
    eg = 0
    for color in (WHITE, BLACK):
        sign = 1 if color == WHITE else -1
        mg_c = MG[color]
        eg_c = EG[color]
        pieces = board.pieces[color]
        for pt in range(6):
            for sq in iter_bits(pieces[pt]):
                mg += sign * mg_c[pt][sq]
                eg += sign * eg_c[pt][sq]
    # round() is symmetric about 0, which keeps the eval antisymmetric.
    return round((mg * phase + eg * (PHASE_MAX - phase)) / PHASE_MAX)


def _isolated_count(pawns: int) -> int:
    count = 0
    for f in range(8):
        on_file = pawns & FILES[f]
        if on_file and not (pawns & ADJACENT_FILES[f]):
            count += popcount(on_file)
    return count


def _doubled_count(pawns: int) -> int:
    extra = 0
    for f in range(8):
        c = popcount(pawns & FILES[f])
        if c > 1:
            extra += c - 1
    return extra


def _pawn_structure_white(board) -> int:
    wp = board.pieces[WHITE][PAWN]
    bp = board.pieces[BLACK][PAWN]
    score = 0
    for sq in iter_bits(wp):
        if not (PASSED_MASK[WHITE][sq] & bp):
            score += PASSED_BONUS[7 - (sq >> 3)]
    for sq in iter_bits(bp):
        if not (PASSED_MASK[BLACK][sq] & wp):
            score -= PASSED_BONUS[sq >> 3]
    score += ISO_PEN[min(_isolated_count(wp), 8)]
    score -= ISO_PEN[min(_isolated_count(bp), 8)]
    score += DOUBLED_PEN * (_doubled_count(wp) - _doubled_count(bp))
    return score


def _piece_activity_white(board):
    """(mobility_score, center_attack_score) from one pass over the attack sets."""
    occ = board.all_occupied
    mobility = 0
    center_attacks = 0
    for color, sign in ((WHITE, 1), (BLACK, -1)):
        own = board.occupied[color]
        p = board.pieces[color]
        m = 0
        c = 0
        for sq in iter_bits(p[KNIGHT]):
            atk = KNIGHT_ATTACKS[sq]
            m += popcount(atk & ~own)
            c += popcount(atk & CENTER_SQUARES)
        for sq in iter_bits(p[BISHOP]):
            atk = bishop_attacks(sq, occ)
            m += popcount(atk & ~own)
            c += popcount(atk & CENTER_SQUARES)
        for sq in iter_bits(p[ROOK]):
            atk = rook_attacks(sq, occ)
            m += popcount(atk & ~own)
            c += popcount(atk & CENTER_SQUARES)
        for sq in iter_bits(p[QUEEN]):
            atk = queen_attacks(sq, occ)
            m += popcount(atk & ~own)
            c += popcount(atk & CENTER_SQUARES)
        mobility += sign * m
        center_attacks += sign * c
    return mobility * MOBILITY_WEIGHT, center_attacks * CENTER_ATTACK_BONUS


def _mobility_white(board) -> int:
    return _piece_activity_white(board)[0]


def _king_safety_white(board, phase: int) -> int:
    if phase == 0:
        return 0
    total = 0
    for color, sign in ((WHITE, 1), (BLACK, -1)):
        ksq = lsb(board.pieces[color][KING])
        shield = KING_SHIELD[color][ksq] & board.pieces[color][PAWN]
        total += sign * popcount(shield) * SHIELD_BONUS
    return round(total * phase / PHASE_MAX)


def _center_occupation_white(board) -> int:
    score = 0
    for color, sign in ((WHITE, 1), (BLACK, -1)):
        p = board.pieces[color]
        non_king = board.occupied[color] & ~p[KING]
        score += sign * CENTER_OCCUPY_BONUS * popcount(non_king & CENTER_SQUARES)
    return score


def _center_control_white(board) -> int:
    return _center_occupation_white(board) + _piece_activity_white(board)[1]


def _manhattan(a: int, b: int) -> int:
    return abs((a & 7) - (b & 7)) + abs((a >> 3) - (b >> 3))


def _chebyshev(a: int, b: int) -> int:
    return max(abs((a & 7) - (b & 7)), abs((a >> 3) - (b >> 3)))


def _king_tropism_white(board, phase: int) -> int:
    """Pieces near the enemy king, scaled by phase like king safety."""
    if phase == 0:
        return 0
    total = 0
    for color, sign in ((WHITE, 1), (BLACK, -1)):
        enemy_ksq = lsb(board.pieces[color ^ 1][KING])
        p = board.pieces[color]
        for pt in (KNIGHT, BISHOP, ROOK, QUEEN):
            weight = TROPISM_WEIGHT[pt]
            for sq in iter_bits(p[pt]):
                total += sign * weight * (7 - _chebyshev(sq, enemy_ksq))
    return round(total * phase / PHASE_MAX)


def _mopup_white(board) -> int:
    """Drive the losing king to the edge in won, pawnless endgames of <= 5 pieces."""
    if board.pieces[WHITE][PAWN] or board.pieces[BLACK][PAWN]:
        return 0
    if popcount(board.all_occupied) > 5:
        return 0
    mat = _material_white(board)
    if abs(mat) < 500:
        return 0
    wk = lsb(board.pieces[WHITE][KING])
    bk = lsb(board.pieces[BLACK][KING])
    md = _manhattan(wk, bk)
    cd = _chebyshev(wk, bk)
    if mat > 0:
        val = CMD[bk] * 5 + (14 - md) * 3 + CHEB_BONUS[cd]
        return val
    else:
        val = CMD[wk] * 5 + (14 - md) * 3 + CHEB_BONUS[cd]
        return -val


# --- Public API ---

def evaluate_white(board) -> int:
    """Static score from White's perspective (positive = better for White)."""
    phase = game_phase(board)
    score = _material_white(board)
    score += _pst_white(board, phase)
    score += _pawn_structure_white(board)
    mobility_score, center_attack_score = _piece_activity_white(board)
    score += mobility_score
    score += _king_safety_white(board, phase)
    score += _center_occupation_white(board) + center_attack_score
    score += _king_tropism_white(board, phase)
    score += _mopup_white(board)
    return score


def evaluate(board) -> int:
    """Static score relative to the side to move (negamax convention)."""
    score = evaluate_white(board)
    return score if board.side == WHITE else -score


# --- Self-test ------------------------------------------------------------

def _mirror_fen(fen: str) -> str:
    """Flip ranks and swap colours and side to move."""
    parts = fen.split()
    ranks = parts[0].split("/")[::-1]
    placement = "/".join("".join(c.swapcase() for c in r) for r in ranks)
    side = "b" if parts[1] == "w" else "w"
    castling = parts[2].swapcase() if parts[2] != "-" else "-"
    if len(parts) > 3 and parts[3] != "-":
        ep = parts[3][0] + str(9 - int(parts[3][1]))
    else:
        ep = "-"
    rest = parts[4:] if len(parts) > 4 else []
    return " ".join([placement, side, castling, ep] + rest)


def _run_self_test() -> bool:
    from board import STARTING_FEN, Board

    ok = True

    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")

    # 1. Starting position is perfectly balanced.
    start = Board(STARTING_FEN)
    check("start: evaluate_white == 0", evaluate_white(start) == 0)
    check("start: evaluate == 0", evaluate(start) == 0)

    # 2. Colour-mirror antisymmetry (last FEN exercises mop-up).
    fens = [
        STARTING_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "k7/8/2K5/8/8/8/8/4Q3 w - - 0 1",
    ]
    for fen in fens:
        b = Board(fen)
        m = Board(_mirror_fen(fen))
        check(f"mirror antisymmetric: {fen[:24]}…",
              evaluate_white(b) == -evaluate_white(m))
        check(f"mirror same-to-move:  {fen[:24]}…",
              evaluate(b) == evaluate(m))

    # 3. Material dominates: White up a queen is clearly winning for White.
    upq = Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    check("white up a queen: evaluate_white > 800", evaluate_white(upq) > 800)

    # 4. After 1.e4 White is slightly better.
    e4 = Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
    check("after 1.e4: evaluate_white > 0", evaluate_white(e4) > 0)

    # 5. PST: a centralised knight beats a cornered one.
    center = Board("4k3/8/8/3N4/8/8/8/4K3 w - - 0 1")
    corner = Board("N3k3/8/8/8/8/8/8/4K3 w - - 0 1")
    check("knight d5 > knight a8", evaluate_white(center) > evaluate_white(corner))

    # 6. Passed pawns: lone e5 pawn is +40 passed, -25 isolated = +15.
    passed = Board("4k3/8/8/4P3/8/8/8/4K3 w - - 0 1")
    blocked = Board("4k3/4p3/8/4P3/8/8/8/4K3 w - - 0 1")
    check("passed pawn: structure term == +15", _pawn_structure_white(passed) == 15)
    check("passed pawn: blocked scores lower",
          _pawn_structure_white(passed) > _pawn_structure_white(blocked))

    # 7. Isolated / doubled pawn counters.
    connected = Board("4k3/8/8/8/3PP3/8/8/4K3 w - - 0 1")
    isolated = Board("4k3/8/8/8/P7/8/8/4K3 w - - 0 1")
    check("isolated count: d4+e4 == 0", _isolated_count(connected.pieces[WHITE][PAWN]) == 0)
    check("isolated count: lone a4 == 1", _isolated_count(isolated.pieces[WHITE][PAWN]) == 1)
    doubled = Board("4k3/8/8/8/4P3/4P3/8/4K3 w - - 0 1")
    check("doubled count: e4+e3 == 1", _doubled_count(doubled.pieces[WHITE][PAWN]) == 1)
    check("doubled count: d4+e3 == 0", _doubled_count(connected.pieces[WHITE][PAWN]) == 0)

    # 8. Mobility: a centralised knight attacks more squares than a cornered one.
    check("mobility: knight d5 > knight a8",
          _mobility_white(center) > _mobility_white(corner))

    # 9. King safety: pawn shield beats a bare king (queens on).
    shielded = Board("3q2k1/8/8/8/8/8/5PPP/3Q2K1 w - - 0 1")
    bare = Board("3q2k1/8/8/8/8/8/8/3Q2K1 w - - 0 1")
    check("king safety: shield > exposed",
          _king_safety_white(shielded, game_phase(shielded))
          > _king_safety_white(bare, game_phase(bare)))

    # 10. Mop-up: KQ v K prefers the losing king in the corner; off when level.
    edge = Board("k7/8/2K5/8/8/8/8/4Q3 w - - 0 1")
    centre_k = Board("8/8/8/8/4k3/8/2K5/4Q3 w - - 0 1")
    check("mop-up: drives losing king to edge", _mopup_white(edge) > _mopup_white(centre_k))
    check("mop-up: active (non-zero) when winning", _mopup_white(edge) > 0)
    check("mop-up: off when material is level", _mopup_white(Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")) == 0)

    # 11. Center control: central knight beats a corner knight.
    center_knight = Board("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1")
    corner_knight = Board("4k3/8/8/8/8/8/8/N3K3 w - - 0 1")
    check("center control: knight d4 > knight a1",
          _center_control_white(center_knight) > _center_control_white(corner_knight))

    # 11b. A second attacker on an already-attacked square still counts.
    one_attacker = Board("4k3/8/8/8/8/1N6/8/4K3 w - - 0 1")       # Nb3 attacks d4
    two_attackers = Board("4k3/8/8/8/8/1N6/2N5/4K3 w - - 0 1")    # Nb3 + Nc2, both attack d4
    check("center control: a second attacker on the same square adds credit",
          _center_control_white(two_attackers) > _center_control_white(one_attacker))

    # 12. King tropism: queen near the enemy king beats a distant one.
    close_queen = Board("4k3/3Q4/8/8/8/8/8/4K3 w - - 0 1")
    far_queen = Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
    check("king tropism: queen near enemy king > queen far away",
          _king_tropism_white(close_queen, game_phase(close_queen))
          > _king_tropism_white(far_queen, game_phase(far_queen)))

    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_self_test() else 1)
