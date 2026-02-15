"""Static Exchange Evaluation (swap algorithm), used for capture ordering
and quiescence pruning.

The king may recapture like any other piece, even into check; fine for a
heuristic.
"""

from lcbot.attacks import KING_ATTACKS, KNIGHT_ATTACKS, PAWN_ATTACKS, bishop_attacks, rook_attacks
from lcbot.bitboard import lsb
from lcbot.constants import BISHOP, BLACK, KING, KNIGHT, PAWN, QUEEN, ROOK, WHITE
from lcbot.evaluation import PIECE_VALUE
from lcbot.move import FLAG_EN_PASSANT, PROMO_FLAG_TO_PIECE, is_capture, move_flag, move_from, move_to


def _attackers_to(board, sq: int, occ: int) -> int:
    """Attackers of both colors on `sq` under occupancy `occ`, which shrinks
    during the exchange so x-ray attackers show up."""
    attackers = 0
    attackers |= PAWN_ATTACKS[BLACK][sq] & board.pieces[WHITE][PAWN]
    attackers |= PAWN_ATTACKS[WHITE][sq] & board.pieces[BLACK][PAWN]
    attackers |= KNIGHT_ATTACKS[sq] & (board.pieces[WHITE][KNIGHT] | board.pieces[BLACK][KNIGHT])
    attackers |= KING_ATTACKS[sq] & (board.pieces[WHITE][KING] | board.pieces[BLACK][KING])
    diag_sliders = board.pieces[WHITE][BISHOP] | board.pieces[BLACK][BISHOP] | board.pieces[WHITE][QUEEN] | board.pieces[BLACK][QUEEN]
    attackers |= bishop_attacks(sq, occ) & diag_sliders
    orth_sliders = board.pieces[WHITE][ROOK] | board.pieces[BLACK][ROOK] | board.pieces[WHITE][QUEEN] | board.pieces[BLACK][QUEEN]
    attackers |= rook_attacks(sq, occ) & orth_sliders
    return attackers & occ


def _least_valuable_attacker(board, attackers: int, color: int):
    """(square, piece_type) of `color`'s cheapest attacker, or (None, None)."""
    for pt in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING):
        bb = attackers & board.pieces[color][pt]
        if bb:
            return lsb(bb), pt
    return None, None


def _piece_type_on(board, color: int, sq: int):
    """Piece type of `color` on `sq`, or None."""
    bit = 1 << sq
    for pt in range(6):
        if board.pieces[color][pt] & bit:
            return pt
    return None


_PROMO_BONUS_VALUE = PIECE_VALUE[QUEEN] - PIECE_VALUE[PAWN]


def _is_promotion_square(sq: int, color: int) -> bool:
    rank = sq // 8
    return rank == 7 if color == WHITE else rank == 0


def see(board, move: int) -> int:
    """Net material gain of the exchange `move` starts, for the side making
    it; 0 for a non-capture. Pawn recaptures on the last rank count as queen
    promotions."""
    if not is_capture(move):
        return 0

    to_sq = move_to(move)
    from_sq = move_from(move)
    flag = move_flag(move)
    us = board.side
    them = us ^ 1

    moving_pt = _piece_type_on(board, us, from_sq)

    if flag == FLAG_EN_PASSANT:
        captured_value = PIECE_VALUE[PAWN]
        cap_sq = to_sq + (-8 if us == WHITE else 8)
    else:
        cap_sq = to_sq
        captured_pt = _piece_type_on(board, them, to_sq)
        captured_value = PIECE_VALUE[captured_pt] if captured_pt is not None else 0

    promo_pt = PROMO_FLAG_TO_PIECE.get(flag)
    initial_promo_bonus = (PIECE_VALUE[promo_pt] - PIECE_VALUE[PAWN]) if promo_pt is not None else 0
    on_square_value = PIECE_VALUE[promo_pt] if promo_pt is not None else PIECE_VALUE[moving_pt]

    occ = board.all_occupied & ~(1 << from_sq)
    if flag == FLAG_EN_PASSANT:
        occ &= ~(1 << cap_sq)

    gain = [captured_value + initial_promo_bonus]
    current_value = on_square_value  # value of the piece presently sitting on to_sq
    side = them
    attackers = _attackers_to(board, to_sq, occ)

    d = 0
    while True:
        lva_sq, lva_pt = _least_valuable_attacker(board, attackers, side)
        if lva_sq is None:
            break
        d += 1
        gain.append(current_value - gain[d - 1])
        if max(-gain[d - 1], gain[d]) < 0:
            break  # this recapture can never be worth playing; stop early
        occ &= ~(1 << lva_sq)
        attackers = _attackers_to(board, to_sq, occ)
        if lva_pt == PAWN and _is_promotion_square(to_sq, side):
            current_value = PIECE_VALUE[QUEEN]
            gain[d] += _PROMO_BONUS_VALUE
        else:
            current_value = PIECE_VALUE[lva_pt]
        side ^= 1

    while d > 0:
        gain[d - 1] = -max(-gain[d - 1], gain[d])
        d -= 1
    return gain[0]
