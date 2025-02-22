"""Bitboard board: FEN I/O, make/unmake, draw detection.

history holds (move, captured_pt, captured_sq, castling, ep_square, halfmove,
zobrist) per ply, with the state from before the move.
"""

from constants import (
    A1, A8, BISHOP, BLACK, E1, E8, H1, H8, KING, KNIGHT, PAWN, QUEEN, ROOK, WHITE,
    BLACK_KING_SIDE, BLACK_QUEEN_SIDE, WHITE_KING_SIDE, WHITE_QUEEN_SIDE,
    SQUARE_INDEX, SQUARE_NAMES, FULL_BB,
)
from bitboard import lsb, popcount
from move import (
    FLAG_DOUBLE_PUSH, FLAG_EN_PASSANT, FLAG_KING_CASTLE, FLAG_QUEEN_CASTLE,
    FLAG_PROMO_N, FLAG_PROMO_Q_CAPTURE, PROMO_FLAG_TO_PIECE,
    move_flag, move_from, move_to,
)
from attacks import KING_ATTACKS, KNIGHT_ATTACKS, PAWN_ATTACKS, bishop_attacks, rook_attacks
from zobrist import PIECE_KEYS, CASTLE_KEYS, EP_KEYS, SIDE_KEY, compute_hash


STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

CHAR_TO_PIECE = {
    "P": (WHITE, 0), "N": (WHITE, 1), "B": (WHITE, 2),
    "R": (WHITE, 3), "Q": (WHITE, 4), "K": (WHITE, 5),
    "p": (BLACK, 0), "n": (BLACK, 1), "b": (BLACK, 2),
    "r": (BLACK, 3), "q": (BLACK, 4), "k": (BLACK, 5),
}
PIECE_TO_CHAR = {v: k for k, v in CHAR_TO_PIECE.items()}

_FEN_TO_CASTLE = {
    "K": WHITE_KING_SIDE, "Q": WHITE_QUEEN_SIDE,
    "k": BLACK_KING_SIDE, "q": BLACK_QUEEN_SIDE,
}

_UNICODE_PIECES = {
    (WHITE, 0): "♙", (WHITE, 1): "♘", (WHITE, 2): "♗",
    (WHITE, 3): "♖", (WHITE, 4): "♕", (WHITE, 5): "♔",
    (BLACK, 0): "♟", (BLACK, 1): "♞", (BLACK, 2): "♝",
    (BLACK, 3): "♜", (BLACK, 4): "♛", (BLACK, 5): "♚",
}

# AND into castling rights for any move from or to the square.
_CASTLING_MASK = [FULL_BB] * 64
_CASTLING_MASK[A1] = ~WHITE_QUEEN_SIDE & FULL_BB
_CASTLING_MASK[H1] = ~WHITE_KING_SIDE & FULL_BB
_CASTLING_MASK[E1] = ~(WHITE_KING_SIDE | WHITE_QUEEN_SIDE) & FULL_BB
_CASTLING_MASK[A8] = ~BLACK_QUEEN_SIDE & FULL_BB
_CASTLING_MASK[H8] = ~BLACK_KING_SIDE & FULL_BB
_CASTLING_MASK[E8] = ~(BLACK_KING_SIDE | BLACK_QUEEN_SIDE) & FULL_BB


class Board:
    __slots__ = (
        "pieces", "occupied", "all_occupied", "side", "castling",
        "ep_square", "halfmove", "fullmove", "history",
        "zobrist", "_null_history",
    )

    def __init__(self, fen: str = STARTING_FEN):
        self.set_fen(fen)

    # --- FEN ---

    def set_fen(self, fen: str) -> None:
        self.pieces = [[0] * 6, [0] * 6]
        self.occupied = [0, 0]
        parts = fen.split()
        rank, file = 7, 0
        for c in parts[0]:
            if c == "/":
                rank -= 1
                file = 0
            elif c.isdigit():
                file += int(c)
            else:
                color, ptype = CHAR_TO_PIECE[c]
                sq = rank * 8 + file
                self.pieces[color][ptype] |= 1 << sq
                self.occupied[color] |= 1 << sq
                file += 1
        self.all_occupied = self.occupied[WHITE] | self.occupied[BLACK]
        self.side = WHITE if parts[1] == "w" else BLACK
        self.castling = 0
        if parts[2] != "-":
            for c in parts[2]:
                self.castling |= _FEN_TO_CASTLE[c]
        self.ep_square = -1 if parts[3] == "-" else SQUARE_INDEX[parts[3]]
        self.halfmove = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove = int(parts[5]) if len(parts) > 5 else 1
        self.history = []
        self._null_history = []
        self.zobrist = compute_hash(self)

    def get_fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for file in range(8):
                p = self.piece_at(rank * 8 + file)
                if p is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += PIECE_TO_CHAR[p]
            if empty:
                row += str(empty)
            rows.append(row)
        placement = "/".join(rows)
        side = "w" if self.side == WHITE else "b"
        castling = ""
        if self.castling & WHITE_KING_SIDE: castling += "K"
        if self.castling & WHITE_QUEEN_SIDE: castling += "Q"
        if self.castling & BLACK_KING_SIDE: castling += "k"
        if self.castling & BLACK_QUEEN_SIDE: castling += "q"
        castling = castling or "-"
        ep = "-" if self.ep_square < 0 else SQUARE_NAMES[self.ep_square]
        return f"{placement} {side} {castling} {ep} {self.halfmove} {self.fullmove}"

    # --- Inspection ---

    def piece_at(self, sq: int):
        bb = 1 << sq
        for color in (WHITE, BLACK):
            if self.occupied[color] & bb:
                for pt in range(6):
                    if self.pieces[color][pt] & bb:
                        return (color, pt)
        return None

    def render(self) -> str:
        lines = []
        for rank in range(7, -1, -1):
            row = f"{rank + 1} "
            for file in range(8):
                p = self.piece_at(rank * 8 + file)
                row += (_UNICODE_PIECES[p] if p else "·") + " "
            lines.append(row)
        lines.append("  a b c d e f g h")
        return "\n".join(lines)

    def is_square_attacked(self, sq: int, by_color: int) -> bool:
        """Return True if any piece of `by_color` attacks `sq`."""
        # Pawn: a pawn of (1-by_color) on sq would attack the same squares that
        # by_color's pawns must be on to attack sq.
        if PAWN_ATTACKS[by_color ^ 1][sq] & self.pieces[by_color][PAWN]:
            return True
        if KNIGHT_ATTACKS[sq] & self.pieces[by_color][KNIGHT]:
            return True
        if KING_ATTACKS[sq] & self.pieces[by_color][KING]:
            return True
        diag = self.pieces[by_color][2] | self.pieces[by_color][4]  # bishop | queen
        if diag and bishop_attacks(sq, self.all_occupied) & diag:
            return True
        ortho = self.pieces[by_color][ROOK] | self.pieces[by_color][4]  # rook | queen
        if ortho and rook_attacks(sq, self.all_occupied) & ortho:
            return True
        return False

    def in_check(self, color: int = None) -> bool:
        color = self.side if color is None else color
        king_bb = self.pieces[color][KING]
        if not king_bb:
            return False
        return self.is_square_attacked(lsb(king_bb), color ^ 1)

    # --- make / unmake ---

    def make_move(self, move: int) -> None:
        from_sq = move_from(move)
        to_sq = move_to(move)
        flag = move_flag(move)
        us = self.side
        them = us ^ 1
        from_bb = 1 << from_sq
        to_bb = 1 << to_sq

        moving_piece = -1
        for pt in range(6):
            if self.pieces[us][pt] & from_bb:
                moving_piece = pt
                break

        captured_piece = -1
        captured_sq = to_sq
        if flag == FLAG_EN_PASSANT:
            captured_piece = PAWN
            captured_sq = to_sq + (-8 if us == WHITE else 8)
        else:
            for pt in range(6):
                if self.pieces[them][pt] & to_bb:
                    captured_piece = pt
                    break

        old_castling = self.castling
        old_ep = self.ep_square

        # unmake restores the key from here instead of reversing the XORs.
        self.history.append((
            move, captured_piece, captured_sq,
            old_castling, old_ep, self.halfmove, self.zobrist,
        ))

        key = self.zobrist

        self.pieces[us][moving_piece] ^= from_bb
        self.occupied[us] ^= from_bb
        key ^= PIECE_KEYS[us][moving_piece][from_sq]

        if captured_piece >= 0:
            cap_bb = 1 << captured_sq
            self.pieces[them][captured_piece] ^= cap_bb
            self.occupied[them] ^= cap_bb
            key ^= PIECE_KEYS[them][captured_piece][captured_sq]

        if flag >= FLAG_PROMO_N:
            promo_pt = PROMO_FLAG_TO_PIECE[flag]
            self.pieces[us][promo_pt] ^= to_bb
            key ^= PIECE_KEYS[us][promo_pt][to_sq]
        else:
            self.pieces[us][moving_piece] ^= to_bb
            key ^= PIECE_KEYS[us][moving_piece][to_sq]
        self.occupied[us] ^= to_bb

        if flag == FLAG_KING_CASTLE:
            if us == WHITE:
                self.pieces[us][ROOK] ^= (1 << H1) | (1 << 5)
                self.occupied[us] ^= (1 << H1) | (1 << 5)
                key ^= PIECE_KEYS[us][ROOK][H1] ^ PIECE_KEYS[us][ROOK][5]
            else:
                self.pieces[us][ROOK] ^= (1 << H8) | (1 << 61)
                self.occupied[us] ^= (1 << H8) | (1 << 61)
                key ^= PIECE_KEYS[us][ROOK][H8] ^ PIECE_KEYS[us][ROOK][61]
        elif flag == FLAG_QUEEN_CASTLE:
            if us == WHITE:
                self.pieces[us][ROOK] ^= (1 << A1) | (1 << 3)
                self.occupied[us] ^= (1 << A1) | (1 << 3)
                key ^= PIECE_KEYS[us][ROOK][A1] ^ PIECE_KEYS[us][ROOK][3]
            else:
                self.pieces[us][ROOK] ^= (1 << A8) | (1 << 59)
                self.occupied[us] ^= (1 << A8) | (1 << 59)
                key ^= PIECE_KEYS[us][ROOK][A8] ^ PIECE_KEYS[us][ROOK][59]

        self.castling &= _CASTLING_MASK[from_sq]
        self.castling &= _CASTLING_MASK[to_sq]
        if self.castling != old_castling:
            key ^= CASTLE_KEYS[old_castling] ^ CASTLE_KEYS[self.castling]

        if old_ep >= 0:
            key ^= EP_KEYS[old_ep & 7]
        if flag == FLAG_DOUBLE_PUSH:
            self.ep_square = (from_sq + to_sq) >> 1
            key ^= EP_KEYS[self.ep_square & 7]
        else:
            self.ep_square = -1

        if moving_piece == PAWN or captured_piece >= 0:
            self.halfmove = 0
        else:
            self.halfmove += 1

        if us == BLACK:
            self.fullmove += 1

        key ^= SIDE_KEY
        self.zobrist = key

        self.all_occupied = self.occupied[WHITE] | self.occupied[BLACK]
        self.side = them

    def unmake_move(self) -> None:
        move, captured_piece, captured_sq, castling, ep_square, halfmove, zob = self.history.pop()
        from_sq = move_from(move)
        to_sq = move_to(move)
        flag = move_flag(move)
        them = self.side  # current side; the mover is the other
        us = them ^ 1
        from_bb = 1 << from_sq
        to_bb = 1 << to_sq

        if flag >= FLAG_PROMO_N:
            promo_pt = PROMO_FLAG_TO_PIECE[flag]
            self.pieces[us][promo_pt] ^= to_bb
            self.pieces[us][PAWN] ^= from_bb
        else:
            moving_piece = -1
            for pt in range(6):
                if self.pieces[us][pt] & to_bb:
                    moving_piece = pt
                    break
            self.pieces[us][moving_piece] ^= to_bb
            self.pieces[us][moving_piece] ^= from_bb
        self.occupied[us] ^= to_bb
        self.occupied[us] ^= from_bb

        if captured_piece >= 0:
            cap_bb = 1 << captured_sq
            self.pieces[them][captured_piece] ^= cap_bb
            self.occupied[them] ^= cap_bb

        if flag == FLAG_KING_CASTLE:
            if us == WHITE:
                self.pieces[us][ROOK] ^= (1 << H1) | (1 << 5)
                self.occupied[us] ^= (1 << H1) | (1 << 5)
            else:
                self.pieces[us][ROOK] ^= (1 << H8) | (1 << 61)
                self.occupied[us] ^= (1 << H8) | (1 << 61)
        elif flag == FLAG_QUEEN_CASTLE:
            if us == WHITE:
                self.pieces[us][ROOK] ^= (1 << A1) | (1 << 3)
                self.occupied[us] ^= (1 << A1) | (1 << 3)
            else:
                self.pieces[us][ROOK] ^= (1 << A8) | (1 << 59)
                self.occupied[us] ^= (1 << A8) | (1 << 59)

        self.castling = castling
        self.ep_square = ep_square
        self.halfmove = halfmove
        self.zobrist = zob
        if us == BLACK:
            self.fullmove -= 1

        self.all_occupied = self.occupied[WHITE] | self.occupied[BLACK]
        self.side = us

    # --- null move (for null-move pruning in search) ---

    def make_null_move(self) -> None:
        """Pass the turn: flip side, clear the ep square. No piece moves."""
        self._null_history.append((self.ep_square, self.zobrist, self.halfmove))
        if self.ep_square >= 0:
            self.zobrist ^= EP_KEYS[self.ep_square & 7]
            self.ep_square = -1
        self.zobrist ^= SIDE_KEY
        self.halfmove += 1
        self.side ^= 1

    def unmake_null_move(self) -> None:
        self.ep_square, self.zobrist, self.halfmove = self._null_history.pop()
        self.side ^= 1

    # --- draw detection ---

    def is_repetition(self) -> bool:
        """True if the position occurred before since the last irreversible move.

        One earlier occurrence counts as a draw for search purposes.
        """
        key = self.zobrist
        hist = self.history
        # Same side to move only: step two plies at a time from history[-2].
        i = len(hist) - 2
        stop = len(hist) - self.halfmove
        while i >= 0 and i >= stop:
            if hist[i][6] == key:
                return True
            i -= 2
        return False

    def is_insufficient_material(self) -> bool:
        """K vs K, K+N vs K, or K+B vs K."""
        for c in (WHITE, BLACK):
            if self.pieces[c][PAWN] or self.pieces[c][ROOK] or self.pieces[c][QUEEN]:
                return False
        minors = (popcount(self.pieces[WHITE][KNIGHT]) + popcount(self.pieces[WHITE][BISHOP])
                  + popcount(self.pieces[BLACK][KNIGHT]) + popcount(self.pieces[BLACK][BISHOP]))
        return minors <= 1

    def is_draw(self) -> bool:
        """50-move rule, repetition, or insufficient material."""
        if self.halfmove >= 100:
            return True
        if self.is_repetition():
            return True
        if self.is_insufficient_material():
            return True
        return False
