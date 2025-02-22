"""16-bit move encoding: bits 0-5 from square, 6-11 to square, 12-15 flag.

Promotion flags are >= 8; promotion captures are >= 12.
"""

from constants import SQUARE_NAMES

# Move flags (4 bits)
FLAG_QUIET = 0
FLAG_DOUBLE_PUSH = 1
FLAG_KING_CASTLE = 2
FLAG_QUEEN_CASTLE = 3
FLAG_CAPTURE = 4
FLAG_EN_PASSANT = 5
FLAG_PROMO_N = 8
FLAG_PROMO_B = 9
FLAG_PROMO_R = 10
FLAG_PROMO_Q = 11
FLAG_PROMO_N_CAPTURE = 12
FLAG_PROMO_B_CAPTURE = 13
FLAG_PROMO_R_CAPTURE = 14
FLAG_PROMO_Q_CAPTURE = 15

PROMO_FLAGS_QUIET = (FLAG_PROMO_Q, FLAG_PROMO_R, FLAG_PROMO_B, FLAG_PROMO_N)
PROMO_FLAGS_CAPTURE = (
    FLAG_PROMO_Q_CAPTURE,
    FLAG_PROMO_R_CAPTURE,
    FLAG_PROMO_B_CAPTURE,
    FLAG_PROMO_N_CAPTURE,
)

# Promotion flag -> piece type. (flag - FLAG_PROMO_N) & 3 gives 0..3 for N/B/R/Q.
PROMO_FLAG_TO_PIECE = {
    FLAG_PROMO_N: 1, FLAG_PROMO_B: 2, FLAG_PROMO_R: 3, FLAG_PROMO_Q: 4,
    FLAG_PROMO_N_CAPTURE: 1, FLAG_PROMO_B_CAPTURE: 2,
    FLAG_PROMO_R_CAPTURE: 3, FLAG_PROMO_Q_CAPTURE: 4,
}


def encode_move(from_sq: int, to_sq: int, flag: int = FLAG_QUIET) -> int:
    return from_sq | (to_sq << 6) | (flag << 12)


def move_from(m: int) -> int:
    return m & 0x3F


def move_to(m: int) -> int:
    return (m >> 6) & 0x3F


def move_flag(m: int) -> int:
    return (m >> 12) & 0xF


def is_capture(m: int) -> bool:
    f = move_flag(m)
    return f == FLAG_CAPTURE or f == FLAG_EN_PASSANT or f >= FLAG_PROMO_N_CAPTURE


def is_promotion(m: int) -> bool:
    return move_flag(m) >= FLAG_PROMO_N


def is_castle(m: int) -> bool:
    f = move_flag(m)
    return f == FLAG_KING_CASTLE or f == FLAG_QUEEN_CASTLE


def move_to_uci(m: int) -> str:
    uci = SQUARE_NAMES[move_from(m)] + SQUARE_NAMES[move_to(m)]
    if is_promotion(m):
        uci += "nbrq"[(move_flag(m) - FLAG_PROMO_N) & 3]
    return uci
