"""Pseudo-legal and legal move generation."""

from constants import (
    A1, A8, BISHOP, BLACK, FULL_BB, H1, H8, KING, KNIGHT, PAWN, QUEEN, ROOK,
    RANKS, WHITE, BLACK_KING_SIDE, BLACK_QUEEN_SIDE,
    WHITE_KING_SIDE, WHITE_QUEEN_SIDE,
)
from bitboard import iter_bits, lsb
from move import (
    FLAG_CAPTURE, FLAG_DOUBLE_PUSH, FLAG_EN_PASSANT, FLAG_KING_CASTLE,
    FLAG_PROMO_B, FLAG_PROMO_B_CAPTURE, FLAG_PROMO_N, FLAG_PROMO_N_CAPTURE,
    FLAG_PROMO_Q, FLAG_PROMO_Q_CAPTURE, FLAG_PROMO_R, FLAG_PROMO_R_CAPTURE,
    FLAG_QUEEN_CASTLE, FLAG_QUIET, encode_move,
)
from attacks import KING_ATTACKS, KNIGHT_ATTACKS, PAWN_ATTACKS, bishop_attacks, queen_attacks, rook_attacks


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

    # Pawn pushes (non-promo).
    for to_sq in iter_bits(single & ~promo_rank):
        moves.append(encode_move(to_sq - push, to_sq, FLAG_QUIET))
    # Pawn pushes (promo).
    for to_sq in iter_bits(single & promo_rank):
        from_sq = to_sq - push
        for f in _PROMO_QUIET:
            moves.append(encode_move(from_sq, to_sq, f))
    # Double pushes.
    for to_sq in iter_bits(double):
        moves.append(encode_move(to_sq - 2 * push, to_sq, FLAG_DOUBLE_PUSH))

    # Pawn captures (per-pawn so we get from-square cheaply).
    for from_sq in iter_bits(pawns):
        attacks = PAWN_ATTACKS[us][from_sq] & their_pieces
        for to_sq in iter_bits(attacks):
            if (1 << to_sq) & promo_rank:
                for f in _PROMO_CAPTURE:
                    moves.append(encode_move(from_sq, to_sq, f))
            else:
                moves.append(encode_move(from_sq, to_sq, FLAG_CAPTURE))

    # En passant.
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

    # Castling (pre-filtered for legality: squares between rook/king empty,
    # king's three squares not attacked).
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


def generate_legal_moves(board):
    pseudo = generate_pseudo_legal_moves(board)
    legal = []
    for m in pseudo:
        board.make_move(m)
        # The side that just moved is the one *not* currently to move.
        mover = board.side ^ 1
        king_bb = board.pieces[mover][KING]
        if king_bb and not board.is_square_attacked(lsb(king_bb), board.side):
            legal.append(m)
        board.unmake_move()
    return legal
