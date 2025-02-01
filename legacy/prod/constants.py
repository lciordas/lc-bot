"""Bitboard constants, piece / color enums, file & rank masks."""

# --- Piece types (indices into pieces[color][type]) ---
PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING = range(6)
PIECE_TYPES = (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING)
PIECE_CHARS = ("P", "N", "B", "R", "Q", "K")

# --- Colors ---
WHITE, BLACK = 0, 1
COLORS = (WHITE, BLACK)

# --- Square names <-> indices ---
SQUARE_NAMES = tuple(f + r for r in "12345678" for f in "abcdefgh")
SQUARE_INDEX = {name: i for i, name in enumerate(SQUARE_NAMES)}

# --- Files (bitboards) ---
FILE_A = 0x0101010101010101
FILES = tuple(FILE_A << i for i in range(8))
FILE_A_BB, FILE_B_BB, FILE_C_BB, FILE_D_BB, \
    FILE_E_BB, FILE_F_BB, FILE_G_BB, FILE_H_BB = FILES

# --- Ranks (bitboards) ---
RANK_1 = 0xFF
RANKS = tuple(RANK_1 << (8 * i) for i in range(8))
RANK_1_BB, RANK_2_BB, RANK_3_BB, RANK_4_BB, \
    RANK_5_BB, RANK_6_BB, RANK_7_BB, RANK_8_BB = RANKS

# --- Boundary masks (for shift-based attack generation) ---
FULL_BB = 0xFFFFFFFFFFFFFFFF
EMPTY_BB = 0

NOT_FILE_A = FULL_BB ^ FILE_A_BB
NOT_FILE_H = FULL_BB ^ FILE_H_BB
NOT_FILE_AB = FULL_BB ^ (FILE_A_BB | FILE_B_BB)
NOT_FILE_GH = FULL_BB ^ (FILE_G_BB | FILE_H_BB)

# --- Castling rights (bit flags) ---
WHITE_KING_SIDE = 1
WHITE_QUEEN_SIDE = 2
BLACK_KING_SIDE = 4
BLACK_QUEEN_SIDE = 8
ANY_CASTLING = WHITE_KING_SIDE | WHITE_QUEEN_SIDE | BLACK_KING_SIDE | BLACK_QUEEN_SIDE

# --- Common square indices used by the engine ---
A1, B1, C1, D1, E1, F1, G1, H1 = range(8)
A8, B8, C8, D8, E8, F8, G8, H8 = range(56, 64)
