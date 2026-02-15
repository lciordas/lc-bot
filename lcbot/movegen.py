"""Move generation: pseudo-legal moves, then a check/pin filter for legality.

Castling is fully checked at generation time. _generate_legal_moves_reference is
the slow make/unmake version, used by tests as an oracle.
"""

from lcbot.constants import (
    A1, A8, BISHOP, BLACK, FULL_BB, H1, H8, KING, KNIGHT, PAWN, QUEEN, ROOK,
    RANKS, WHITE, BLACK_KING_SIDE, BLACK_QUEEN_SIDE,
    WHITE_KING_SIDE, WHITE_QUEEN_SIDE,
)
from lcbot.bitboard import iter_bits, lsb, popcount
from lcbot.move import (
    FLAG_CAPTURE, FLAG_DOUBLE_PUSH, FLAG_EN_PASSANT, FLAG_KING_CASTLE,
    FLAG_PROMO_B, FLAG_PROMO_B_CAPTURE, FLAG_PROMO_N, FLAG_PROMO_N_CAPTURE,
    FLAG_PROMO_Q, FLAG_PROMO_Q_CAPTURE, FLAG_PROMO_R, FLAG_PROMO_R_CAPTURE,
    FLAG_QUEEN_CASTLE, FLAG_QUIET, encode_move, move_flag, move_from, move_to,
)
from lcbot.attacks import (
    KING_ATTACKS, KNIGHT_ATTACKS, PAWN_ATTACKS, SQUARES_BETWEEN,
    bishop_attacks, queen_attacks, rook_attacks,
)


_PROMO_QUIET = (FLAG_PROMO_Q, FLAG_PROMO_R, FLAG_PROMO_B, FLAG_PROMO_N)
_PROMO_CAPTURE = (FLAG_PROMO_Q_CAPTURE, FLAG_PROMO_R_CAPTURE, FLAG_PROMO_B_CAPTURE, FLAG_PROMO_N_CAPTURE)


def generate_pseudo_legal_moves(board):
    moves = []
    us = board.side
    them = us ^ 1
    our_pieces = board.occupied[us]
    their_pieces = board.occupied[them]
    all_pieces = board.all_occupied
    empty = ~all_pieces & FULL_BB

    pawns = board.pieces[us][PAWN]
    if us == WHITE:
        single = (pawns << 8) & empty
        double = ((single & RANKS[2]) << 8) & empty
        promo_rank = RANKS[7]
        push = 8
    else:
        single = (pawns >> 8) & empty
        double = ((single & RANKS[5]) >> 8) & empty
        promo_rank = RANKS[0]
        push = -8

    for to_sq in iter_bits(single & ~promo_rank):
        moves.append(encode_move(to_sq - push, to_sq, FLAG_QUIET))
    for to_sq in iter_bits(single & promo_rank):
        from_sq = to_sq - push
        for f in _PROMO_QUIET:
            moves.append(encode_move(from_sq, to_sq, f))
    for to_sq in iter_bits(double):
        moves.append(encode_move(to_sq - 2 * push, to_sq, FLAG_DOUBLE_PUSH))

    for from_sq in iter_bits(pawns):
        attacks = PAWN_ATTACKS[us][from_sq] & their_pieces
        for to_sq in iter_bits(attacks):
            if (1 << to_sq) & promo_rank:
                for f in _PROMO_CAPTURE:
                    moves.append(encode_move(from_sq, to_sq, f))
            else:
                moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))

    if board.ep_square >= 0:
        attackers = PAWN_ATTACKS[them][board.ep_square] & pawns
        for from_sq in iter_bits(attackers):
            moves.append(encode_move(from_sq, board.ep_square, FLAG_EN_PASSANT))

    # Knights.
    for from_sq in iter_bits(board.pieces[us][KNIGHT]):
        attacks = KNIGHT_ATTACKS[from_sq] & ~our_pieces
        for to_sq in iter_bits(attacks):
            flag = FLAG_CAPTURE if (1 << to_sq) & their_pieces else FLAG_QUIET
            moves.append(encode_move(from_sq, to_sq, flag))

    # Bishops.
    for from_sq in iter_bits(board.pieces[us][BISHOP]):
        attacks = bishop_attacks(from_sq, all_pieces) & ~our_pieces
        for to_sq in iter_bits(attacks):
            flag = FLAG_CAPTURE if (1 << to_sq) & their_pieces else FLAG_QUIET
            moves.append(encode_move(from_sq, to_sq, flag))

    # Rooks.
    for from_sq in iter_bits(board.pieces[us][ROOK]):
        attacks = rook_attacks(from_sq, all_pieces) & ~our_pieces
        for to_sq in iter_bits(attacks):
            flag = FLAG_CAPTURE if (1 << to_sq) & their_pieces else FLAG_QUIET
            moves.append(encode_move(from_sq, to_sq, flag))

    # Queens.
    for from_sq in iter_bits(board.pieces[us][QUEEN]):
        attacks = queen_attacks(from_sq, all_pieces) & ~our_pieces
        for to_sq in iter_bits(attacks):
            flag = FLAG_CAPTURE if (1 << to_sq) & their_pieces else FLAG_QUIET
            moves.append(encode_move(from_sq, to_sq, flag))

    # King (non-castle).
    for from_sq in iter_bits(board.pieces[us][KING]):
        attacks = KING_ATTACKS[from_sq] & ~our_pieces
        for to_sq in iter_bits(attacks):
            flag = FLAG_CAPTURE if (1 << to_sq) & their_pieces else FLAG_QUIET
            moves.append(encode_move(from_sq, to_sq, flag))

    # Castling: path empty and king's three squares not attacked.
    if us == WHITE:
        if (board.castling & WHITE_KING_SIDE
                and not (all_pieces & ((1 << 5) | (1 << 6)))
                and not board.is_square_attacked(4, BLACK)
                and not board.is_square_attacked(5, BLACK)
                and not board.is_square_attacked(6, BLACK)):
            moves.append(encode_move(4, 6, FLAG_KING_CASTLE))
        if (board.castling & WHITE_QUEEN_SIDE
                and not (all_pieces & ((1 << 1) | (1 << 2) | (1 << 3)))
                and not board.is_square_attacked(4, BLACK)
                and not board.is_square_attacked(3, BLACK)
                and not board.is_square_attacked(2, BLACK)):
            moves.append(encode_move(4, 2, FLAG_QUEEN_CASTLE))
    else:
        if (board.castling & BLACK_KING_SIDE
                and not (all_pieces & ((1 << 61) | (1 << 62)))
                and not board.is_square_attacked(60, WHITE)
                and not board.is_square_attacked(61, WHITE)
                and not board.is_square_attacked(62, WHITE)):
            moves.append(encode_move(60, 62, FLAG_KING_CASTLE))
        if (board.castling & BLACK_QUEEN_SIDE
                and not (all_pieces & ((1 << 57) | (1 << 58) | (1 << 59)))
                and not board.is_square_attacked(60, WHITE)
                and not board.is_square_attacked(59, WHITE)
                and not board.is_square_attacked(58, WHITE)):
            moves.append(encode_move(60, 58, FLAG_QUEEN_CASTLE))

    return moves


def _generate_legal_moves_reference(board):
    """Slow make/unmake legality filter; test oracle for generate_legal_moves."""
    pseudo = generate_pseudo_legal_moves(board)
    legal = []
    for m in pseudo:
        board.make_move(m)
        mover = board.side ^ 1
        king_bb = board.pieces[mover][KING]
        if king_bb and not board.is_square_attacked(lsb(king_bb), board.side):
            legal.append(m)
        board.unmake_move()
    return legal


def _check_and_pin_info(board):
    """Return (checkers_count, capture_or_block_mask, pinned_bb, pin_ray_full).

    capture_or_block_mask is only meaningful with exactly one checker.
    pin_ray_full[sq] is the king-to-pinner line, pinner included.
    """
    us = board.side
    them = us ^ 1
    king_sq = lsb(board.pieces[us][KING])
    occ = board.all_occupied

    checkers_bb = PAWN_ATTACKS[us][king_sq] & board.pieces[them][PAWN]
    checkers_bb |= KNIGHT_ATTACKS[king_sq] & board.pieces[them][KNIGHT]
    checkers_bb |= bishop_attacks(king_sq, occ) & (board.pieces[them][BISHOP] | board.pieces[them][QUEEN])
    checkers_bb |= rook_attacks(king_sq, occ) & (board.pieces[them][ROOK] | board.pieces[them][QUEEN])
    checkers_count = popcount(checkers_bb)

    capture_or_block_mask = FULL_BB
    if checkers_count == 1:
        checker_sq = lsb(checkers_bb)
        capture_or_block_mask = 1 << checker_sq
        sliders = board.pieces[them][BISHOP] | board.pieces[them][ROOK] | board.pieces[them][QUEEN]
        if (1 << checker_sq) & sliders:
            capture_or_block_mask |= SQUARES_BETWEEN[king_sq][checker_sq]

    # X-ray from the king through our pieces; a slider with exactly one of ours
    # in between pins it.
    own_occ = board.occupied[us]
    occ_without_own = occ & ~own_occ
    xray = bishop_attacks(king_sq, occ_without_own) & (board.pieces[them][BISHOP] | board.pieces[them][QUEEN])
    xray |= rook_attacks(king_sq, occ_without_own) & (board.pieces[them][ROOK] | board.pieces[them][QUEEN])

    pinned_bb = 0
    pin_ray_full = {}
    for pinner_sq in iter_bits(xray):
        between = SQUARES_BETWEEN[king_sq][pinner_sq] & own_occ
        if popcount(between) == 1:
            pinned_sq = lsb(between)
            pinned_bb |= 1 << pinned_sq
            pin_ray_full[pinned_sq] = SQUARES_BETWEEN[king_sq][pinner_sq] | (1 << pinner_sq)

    return checkers_count, capture_or_block_mask, pinned_bb, pin_ray_full


def _filter_legal(board, pseudo):
    """Keep the legal moves of `pseudo` using check/pin info.

    King moves and en passant are checked directly against attacks.
    """
    us = board.side
    them = us ^ 1
    king_sq = lsb(board.pieces[us][KING])
    checkers_count, capture_or_block_mask, pinned_bb, pin_ray_full = _check_and_pin_info(board)

    if checkers_count >= 2:
        pseudo = [m for m in pseudo if move_from(m) == king_sq]

    occ_without_king = board.all_occupied & ~(1 << king_sq)
    legal = []
    for m in pseudo:
        flag = move_flag(m)
        from_sq = move_from(m)
        to_sq = move_to(m)

        if flag in (FLAG_KING_CASTLE, FLAG_QUEEN_CASTLE):
            legal.append(m)  # checked at generation
            continue

        if flag == FLAG_EN_PASSANT:
            # Removing two pawns from one rank can expose the king without
            # either being pinned; rare, so just make/unmake.
            board.make_move(m)
            ok = not board.is_square_attacked(lsb(board.pieces[us][KING]), them)
            board.unmake_move()
            if ok:
                legal.append(m)
            continue

        if from_sq == king_sq:
            if not board.is_square_attacked(to_sq, them, occupied=occ_without_king):
                legal.append(m)
            continue

        if checkers_count == 1 and not ((1 << to_sq) & capture_or_block_mask):
            continue

        if (pinned_bb & (1 << from_sq)) and not ((1 << to_sq) & pin_ray_full[from_sq]):
            continue

        legal.append(m)

    return legal


def generate_legal_moves(board):
    return _filter_legal(board, generate_pseudo_legal_moves(board))


def generate_pseudo_legal_captures(board):
    """Captures, en passant, and all promotions (including quiet ones), for quiescence."""
    moves = []
    us = board.side
    them = us ^ 1
    their_pieces = board.occupied[them]
    all_pieces = board.all_occupied

    pawns = board.pieces[us][PAWN]
    if us == WHITE:
        single_empty = (pawns << 8) & ~all_pieces & FULL_BB
        promo_rank = RANKS[7]
        push = 8
    else:
        single_empty = (pawns >> 8) & ~all_pieces & FULL_BB
        promo_rank = RANKS[0]
        push = -8

    # Quiet promotions.
    for to_sq in iter_bits(single_empty & promo_rank):
        from_sq = to_sq - push
        for f in _PROMO_QUIET:
            moves.append(encode_move(from_sq, to_sq, f))

    for from_sq in iter_bits(pawns):
        attacks = PAWN_ATTACKS[us][from_sq] & their_pieces
        for to_sq in iter_bits(attacks):
            if (1 << to_sq) & promo_rank:
                for f in _PROMO_CAPTURE:
                    moves.append(encode_move(from_sq, to_sq, f))
            else:
                moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))

    if board.ep_square >= 0:
        attackers = PAWN_ATTACKS[them][board.ep_square] & pawns
        for from_sq in iter_bits(attackers):
            moves.append(encode_move(from_sq, board.ep_square, FLAG_EN_PASSANT))

    for from_sq in iter_bits(board.pieces[us][KNIGHT]):
        for to_sq in iter_bits(KNIGHT_ATTACKS[from_sq] & their_pieces):
            moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))
    for from_sq in iter_bits(board.pieces[us][BISHOP]):
        for to_sq in iter_bits(bishop_attacks(from_sq, all_pieces) & their_pieces):
            moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))
    for from_sq in iter_bits(board.pieces[us][ROOK]):
        for to_sq in iter_bits(rook_attacks(from_sq, all_pieces) & their_pieces):
            moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))
    for from_sq in iter_bits(board.pieces[us][QUEEN]):
        for to_sq in iter_bits(queen_attacks(from_sq, all_pieces) & their_pieces):
            moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))
    for from_sq in iter_bits(board.pieces[us][KING]):
        for to_sq in iter_bits(KING_ATTACKS[from_sq] & their_pieces):
            moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))

    return moves


def generate_legal_captures(board):
    return _filter_legal(board, generate_pseudo_legal_captures(board))
