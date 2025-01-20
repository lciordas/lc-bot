r"""
8  63 62 61 60 59 58 57 56         
7  55 54 53 52 51 50 49 48    +9  +8  +7
6  47 46 45 44 43 42 41 40       \ | /
5  39 38 37 36 35 34 33 32   +1 -- X -- -1
4  31 30 29 28 27 26 25 24       / | \
3  23 23 21 20 19 18 17 16     -7 -8  -9
2  15 14 13 12 11 10  9  8          
1   7  6  5  4  3  2  1  0
    A  B  C  D  E  F  G  H
"""


#    +17      +15
# +10 +9  +8  +7 +6
#        \ | /
#    +1 -- X -- -1
#        / | \
#  -6  -7 -8  -9 -10
#    -15      -17


#all_pieces = ''
#white_pieces = ''
#black_pieces = ''
#pawns = ''
#knights = ''
#bishops = ''
#rooks = ''
#queens = ''
#kings = ''


import numpy as np
from numba import njit
import random
import time


def square_to_num(square):
    """
        Convert algebraic notation to numerical notation.

        Args:
            square (str): Square in algebraic notation (eg. 'e5').

        Return:
            num (int): Square represented by a number (eg. 35).
    """
    file, rank = list(square)

    if (file not in 'abcdefgh') or (rank not in '12345678'):
        print(f"[square_to_num] Error: No such square as '{square}'.")
        return

    file_num = 7 - (ord(file) - ord('a'))
    rank_num = 8 * (int(rank) - 1)
    num = rank_num + file_num
    return num

@njit
def square_num_to_coords(square_num):
    "square_num --> 0-63"
    "coords --> (rank, file), both 0-7"
    rank = square_num // 8
    file = 7 - (square_num % 8)
    return rank, file


@njit
def generate_king_moves(king_num):
    """
        Make a bitboard of the pseudolegal moves available to the king.
        (FOR NOW DOESN'T FACTOR IN OTHER PIECES ON END SQUARES)

        Args:
            king_num (int): The starting square of the king in number form (0-63).
        
        Returns:
            king_moves (int): A 64 bit bitboard where all the squares available to move to
                              are 1s while the rest are 0s.
    """
    NOT_FILE_A = np.uint64(0x7F7F7F7F7F7F7F7F)
    NOT_FILE_H = np.uint64(0xFEFEFEFEFEFEFEFE)
    NOT_RANK_8 = np.uint64(0x00FFFFFFFFFFFFFF)
    NOT_RANK_1 = np.uint64(0xFFFFFFFFFFFFFF00)
    
    king_pos   = np.uint64(1) << np.uint64(king_num)
    king_moves = np.uint64(0)

    king_moves |= (king_pos & NOT_FILE_A) << 1 # left
    king_moves |= (king_pos & NOT_FILE_H) >> 1 # right
    king_moves |= (king_pos & NOT_RANK_8) << 8 # up
    king_moves |= (king_pos & NOT_RANK_1) >> 8 # down
    king_moves |= (king_pos & (NOT_RANK_8 & NOT_FILE_H)) << 7 # up-right
    king_moves |= (king_pos & (NOT_RANK_1 & NOT_FILE_H)) >> 9 # down-right
    king_moves |= (king_pos & (NOT_RANK_1 & NOT_FILE_A)) >> 7 # down-left
    king_moves |= (king_pos & (NOT_RANK_8 & NOT_FILE_A)) << 9 # up-left

    return king_moves


@njit
def generate_knight_moves(knight_num):
    NOT_FILE_A = np.uint64(0x7F7F7F7F7F7F7F7F)
    NOT_FILE_B = np.uint64(0xBFBFBFBFBFBFBFBF)
    NOT_FILE_G = np.uint64(0xFDFDFDFDFDFDFDFD)
    NOT_FILE_H = np.uint64(0xFEFEFEFEFEFEFEFE)
    NOT_RANK_8 = np.uint64(0x00FFFFFFFFFFFFFF)
    NOT_RANK_7 = np.uint64(0xFF00FFFFFFFFFFFF)
    NOT_RANK_2 = np.uint64(0xFFFFFFFFFFFF00FF)
    NOT_RANK_1 = np.uint64(0xFFFFFFFFFFFFFF00)

    knight_pos   = np.uint64(1) << np.uint64(knight_num)
    knight_moves = np.uint64(0)

    knight_moves |= (knight_pos & ((NOT_RANK_7 & NOT_RANK_8) & NOT_FILE_H)) << 15 # up-right
    knight_moves |= (knight_pos & ((NOT_FILE_G & NOT_FILE_H) & NOT_RANK_8)) << 6  # right-up
    knight_moves |= (knight_pos & ((NOT_FILE_G & NOT_FILE_H) & NOT_RANK_1)) >> 10 # right-down
    knight_moves |= (knight_pos & ((NOT_RANK_2 & NOT_RANK_1) & NOT_FILE_H)) >> 17 # down-right
    knight_moves |= (knight_pos & ((NOT_RANK_2 & NOT_RANK_1) & NOT_FILE_A)) >> 15 # down-left
    knight_moves |= (knight_pos & ((NOT_FILE_A & NOT_FILE_B) & NOT_RANK_1)) >> 6  # left-down
    knight_moves |= (knight_pos & ((NOT_FILE_A & NOT_FILE_B) & NOT_RANK_8)) << 10 # left-up
    knight_moves |= (knight_pos & ((NOT_RANK_7 & NOT_RANK_8) & NOT_FILE_A)) << 17 # up-left

    return knight_moves

#          +16
#       +9  +8  +7
#            X
#        -7 -8  -9
#          -16
# flip direction based on color

@njit
def generate_pawn_moves(pawn_num, is_white):
    NOT_FILE_A = np.uint64(0x7F7F7F7F7F7F7F7F)
    NOT_FILE_H = np.uint64(0xFEFEFEFEFEFEFEFE)
    NOT_RANK_8 = np.uint64(0x00FFFFFFFFFFFFFF)
    NOT_RANK_7 = np.uint64(0xFF00FFFFFFFFFFFF)
    NOT_RANK_2 = np.uint64(0xFFFFFFFFFFFF00FF)
    NOT_RANK_1 = np.uint64(0xFFFFFFFFFFFFFF00)
    RANK_7     = np.uint64(0x00FF000000000000)
    RANK_2     = np.uint64(0x000000000000FF00)

    pawn_pos   = np.uint64(1) << np.uint64(pawn_num)
    pawn_moves = np.uint64(0)

    if is_white:
        pawn_moves |= pawn_pos << 8             # forward     -->  no need to mask since no pawns can be on rank 8
        pawn_moves |= (pawn_pos & RANK_2) << 16 # double forward
        pawn_moves |= (pawn_pos & (NOT_FILE_A & NOT_RANK_8)) << 9  # left diag
        pawn_moves |= (pawn_pos & (NOT_FILE_H & NOT_RANK_8)) << 7  # right diag
    else:
        pawn_moves |= (pawn_pos) >> 8           # forward     -->  no need to mask since no pawns can be on rank 1
        pawn_moves |= (pawn_pos & RANK_7) >> 16 # double forward
        pawn_moves |= (pawn_pos & (NOT_FILE_A & NOT_RANK_1)) >> 7  # left diag
        pawn_moves |= (pawn_pos & (NOT_FILE_H & NOT_RANK_1)) >> 9  # right diag

    return pawn_moves


# 7 x x x x x x x
# 6 x x x x x x x
# 5 x x x x x x x
# 4 x x x x x x x
# 3 x x x x x x x
# 2 x x x x x x x
# 1 x x x x x x x
# 0 1 2 3 4 5 6 7

@njit # ROOK
def square_to_rook_mask(rook_num):
    NOT_EDGES = np.uint64(0x007E7E7E7E7E7E00)
    rook_mask = np.uint64(0)
    # given a number --> file, row          rank: 1-0 2-1 3-2 4-3...   file: a-0 b-1 c-2 d-3...
    rank, file = square_num_to_coords(rook_num)
    rook_mask |= np.uint64(0b1111110) << (8 * rank)
    for i in range(1,7):
        rook_mask ^= np.uint64(1) << (7 - file) + (8*i)
    rook_mask &= (~(np.uint64(1) << rook_num) & np.uint64(0xFFFFFFFFFFFFFFFF))
    return rook_mask


@njit # BISHOP
def square_to_bishop_mask(bishop_num):
    NOT_EDGES = np.uint64(0x007E7E7E7E7E7E00)  # mask to avoid edge wrap
    bishop_mask = np.uint64(0)
    rank, file = square_num_to_coords(bishop_num)

    # up-right diagonal
    for i, j in zip(range(rank + 1, 7), range(file + 1, 7)):
        bishop_mask |= np.uint64(1) << np.uint64(i * 8 + (7 - j))
    # down-left diagonal
    for i, j in zip(range(rank - 1, 0, -1), range(file - 1, 0, -1)):
        bishop_mask |= np.uint64(1) << np.uint64(i * 8 + (7 - j))
    # up-left diagonal
    for i, j in zip(range(rank + 1, 7), range(file - 1, 0, -1)):
        bishop_mask |= np.uint64(1) << np.uint64(i * 8 + (7 - j))
    # down-right diagonal
    for i, j in zip(range(rank - 1, 0, -1), range(file + 1, 7)):
        bishop_mask |= np.uint64(1) << np.uint64(i * 8 + (7 - j))

    # remove bishop square itself
    bishop_mask &= ~(np.uint64(1) << np.uint64(bishop_num))
    return bishop_mask


@njit # QUEEN
def square_to_queen_mask(queen_num):
    rook_mask = square_to_rook_mask(queen_num)
    bishop_mask = square_to_bishop_mask(queen_num)
    queen_mask = rook_mask | bishop_mask
    return queen_mask


@njit # GENERAL
def index_list_from_mask(mask):
    indices = np.empty(19,  dtype=np.uint8)

    count = 0
    for bit in range(64):
        if (mask >> bit) & 1:
            indices[count] = bit
            count += 1
    return indices, count # return count to show how many items in the array have a value


@njit # GENERAL
def create_all_blocker_configs(index_list, index_count):
    num_configs = 1 << index_count # = 2**index_count
    blocker_configs = np.empty(num_configs, dtype=np.uint64) #create empty array the size of all configs

    for config_id in range(num_configs): # 0-4096~ or 524,288
        config = np.uint64(0) # each config starts as 0
        for bit in range(index_count): # 0-12~ or 19
            if (config_id >> bit) & 1:  # check if this subset includes the index
                config |= np.uint64(1) << np.uint64(index_list[bit])
        blocker_configs[config_id] = config

    return blocker_configs


@njit # ROOK
def gen_rook_legal_bb(start_square, blocker_config):
    legal_bb = np.uint64(0)
    start_rank = start_square // 8
    start_file = start_square % 8

    for dir in (8, -8, 1, -1):  # up, down, right, left
        sqr = start_square
        while True:
            sqr += dir
            if sqr < 0 or sqr > 63:
                break

            rank = sqr // 8
            file = sqr % 8

            # break if wrapped horizontally
            if (dir == 1 or dir == -1) and rank != start_rank:
                break

            legal_bb |= np.uint64(1) << np.uint64(sqr)

            if (blocker_config >> np.uint64(sqr)) & np.uint64(1):
                break
    return legal_bb


@njit # BISHOP
def gen_bishop_legal_bb(start_square, blocker_config):
    legal_bb = np.uint64(0)
    start_rank = start_square // 8
    start_file = start_square % 8

    for dir in (9, 7, -9, -7):  # up-left, up-right, down-right, down-left
        sqr = start_square
        while True:
            sqr += dir
            rank = sqr // 8
            file = sqr % 8

            # out of bounds
            if sqr < 0 or sqr > 63:
                break

            # if wrapped (file jumped more than 1 between steps)
            if abs((sqr % 8) - ( (sqr - dir) % 8 )) != 1:
                break

            legal_bb |= np.uint64(1) << sqr

            if (blocker_config >> np.uint64(sqr)) & np.uint64(1):
                break

    return legal_bb


@njit # QUEEN
def gen_queen_legal_bb(start_square, blocker_config):
    legal_bb = np.uint64(0)
    start_rank = start_square // 8
    start_file = start_square % 8

    for dir in (8, 7, 1, -9, -8, -7, -1, 9):  # up, up-right, right, down-right, down, down-left, left, up-left
        sqr = start_square
        while True:
            sqr += dir
            rank = sqr // 8
            file = sqr % 8

            # out of bounds
            if sqr < 0 or sqr > 63:
                break

            # if wrapped (file jumped more than 1 between steps)
            if dir in (9, 7, -9, -7):
                if abs((sqr % 8) - ( (sqr - dir) % 8 )) != 1:
                    break

            elif dir in (-1, 1) and rank != start_rank:
                break

            legal_bb |= np.uint64(1) << sqr

            if (blocker_config >> np.uint64(sqr)) & np.uint64(1):
                break

    return legal_bb


@njit # ROOK
def create_rook_moves_table():
    rook_moves_table = np.zeros((64, 4096), dtype=np.uint64)

    for square in range(64):
        mask = square_to_rook_mask(square)
        index_list, count = index_list_from_mask(mask)
        blocker_configs = create_all_blocker_configs(index_list, count)

        for i, config in enumerate(blocker_configs):
            rook_moves_table[square, i] = gen_rook_legal_bb(square, config)

    return rook_moves_table


@njit # BISHOP
def create_bishop_moves_table():
    bishop_moves_table = np.zeros((64, 512), dtype=np.uint64)

    for square in range(64):
        mask = square_to_bishop_mask(square)
        index_list, count = index_list_from_mask(mask)
        blocker_configs = create_all_blocker_configs(index_list, count)

        for i, config in enumerate(blocker_configs):
            bishop_moves_table[square, i] = gen_bishop_legal_bb(square, config)

    return bishop_moves_table


@njit # QUEEN
def create_queen_moves_table():
    queen_moves_table = np.zeros((64, 524288), dtype=np.uint64)

    for square in range(64):
        mask = square_to_queen_mask(square)
        index_list, count = index_list_from_mask(mask)
        blocker_configs = create_all_blocker_configs(index_list, count)

        for i, config in enumerate(blocker_configs):
            queen_moves_table[square, i] = gen_queen_legal_bb(square, config)

    return queen_moves_table


# GENERAL
@njit
def generate_index(mask, blocker_config):
  index_list, num_indices = index_list_from_mask(mask)
  index = 0
  count = 0
  for o in range(num_indices):
      i = index_list[o]
      n = (blocker_config >> i) & 1
      index += n * 2**count
      count += 1
  return index


def render_bitboard(bitboard):
    bitboard = bin(bitboard)[2:].zfill(64)
    bit_count = 0
    for bit in bitboard:
        if bit_count == 8:
            bit_count = 0
            print()
        print(bit, end=' ')
        bit_count += 1
"""
############################################################
# THIS IS HOW ORDINARY MOVEGEN WILL WORK #
ROOK_TABLE   = create_rook_moves_table() # tables created at the start of the program
BISHOP_TABLE = create_bishop_moves_table()
QUEEN_TABLE  = create_queen_moves_table()

all_pieces_bb = random.randrange(0, 2**64) # the current position of the chess board

# we will loop through every piece of a certain color, generate all of its moves, and add them to a central moves list
# say that during this loop we land on a rook that's on square 25
# now, to access its legal moves we input its square and the index of the blocker config into our ROOK_TABLE
square = 25

mask = square_to_rook_mask(square) # generate the mask based on the rook's square using our function --> can we make THIS into a table?
blocker_config = mask & all_pieces_bb # the configuration of blockers comes from overlapping our mask with the board (we onyl care about how pieces are arranged on the rook's mask)
index = generate_index(mask, blocker_config) # we generate the index from the blocker config
legal_moves_bb = ROOK_TABLE[square, index]
#render_bitboard(legal_moves_bb)
# now extract moves from this legal_moves_bb and append them to a list of all legal moves for a given side
"""

###########################################################
# magic bitboard movegen will replace the generate_index function for something faster...

# (blocker_config * magic) >> shift         | THIS BECOMES THE INDEX
# ROOK_TABLE[64, index]

# first, find some suitable magic numbers for 1 square for the rook
# use the already established ROOK_TABLE to verify that no harmful overlaps are present

# rooks max is 12 moves, so start with shift of 52 (64-12) and then go up




BISHOP_TABLE = create_bishop_moves_table()

# Helper: generate a random 64-bit magic number with good entropy and some forced bits set
def random_magic():
    # Use two random 64-bit numbers ANDed together for more zero bits, then force some bits set
    a = random.getrandbits(64)
    b = random.getrandbits(64)
    magic = a & b
    # Force some bits set (e.g. set bits 0, 7, 15, 23, 31, 39, 47, 55, 63)
    for bit in (0, 7, 15, 23, 31, 39, 47, 55, 63):
        magic |= (1 << bit)
    # Convert to numpy.uint64 for consistency
    return np.uint64(magic)

# Helper: test if a magic number and shift are valid for given blockers
def test_magic(square, blocker_configs, magic, shift):
    table_len = len(blocker_configs)
    exp_table = [-1] * table_len
    for idx, blocker_config in enumerate(blocker_configs):
        # Compute index
        with np.errstate(over='ignore'):
            index = int(((blocker_config * magic) >> np.uint64(shift)) % table_len)
        move = int(gen_bishop_legal_bb(square, blocker_config))
        if exp_table[index] == -1:
            exp_table[index] = move
        elif exp_table[index] != move:
            return False
    return True

bishop_magics = []
bishop_shifts = []

for square in range(64):
    mask = square_to_bishop_mask(square)
    index_list, count = index_list_from_mask(mask)
    blocker_configs = create_all_blocker_configs(index_list, count)

    working_magics      = []
    accompanying_shifts = []
    print("SQUARE", square)
    for _ in range(10000):
        magic = random_magic()
        for shift in range(53, 61):
            if test_magic(square, blocker_configs, magic, shift):
                working_magics.append(magic)
                accompanying_shifts.append(shift)
    if accompanying_shifts:
        biggest_shift_index = accompanying_shifts.index(max(accompanying_shifts))
        bishop_shifts.append(max(accompanying_shifts))
        bishop_magics.append(working_magics[biggest_shift_index])
        print(bishop_shifts[square], bishop_magics[square])
    else:
        bishop_shifts.append(None)
        bishop_magics.append(None)
        print("No magic found")
    print()

print(len(bishop_magics), len(bishop_shifts))
print(bishop_magics)
print(bishop_shifts)

    # end = time.time()

    # print(working_magics)
    # print()
    # print(accompanying_shifts)
    # print()
    # print("maximum ----->", max(accompanying_shifts))
    # print()
    # print("TIME ELAPSED:", str(end-start)[:5], "sec")




# get the confirmed legal_moves_bb
















            





























# render_bitboard(ROOK_TABLE[44, 89])
# print('\n')
# render_bitboard(BISHOP_TABLE[12, 16])
# print('\n')
#render_bitboard(QUEEN_TABLE[36, 1])


# have now created tables for sliding pieces --> to access legal moves I must provide piece_square and blocker config
#           how do i quickly extract the blocker config from the current board position? --> efficiency super important here
#           use my square_to_piece_mask func to generate a mask, and then & it with the all_pieces_bb --> this gives blocker config --> convert this into the index for the table
#           but then need to refactor those functoins to make them as efficient as possible

# FUNCTIONS WHERE SPEED IS KEY
    # square_to_rook_mask()
    # generate_index




# after refactoring done, try making the sliding piece tables magic



""" m = square_to_queen_mask(36)
render_bitboard(m)
i, c = index_list_from_mask(m)
print(f'\n{i},   {c}')
b = create_all_blocker_configs(i, c)
l = gen_queen_legal_bb(36, b[2**15])
render_bitboard(l) """


""" l = [0, 9, 18, 27, 29, 23, 15, 45, 54, 63, 43, 50, 57]
n = 13
b = create_all_blocker_configs(l, n)
lg_bb = gen_bishop_legal_bb(36, b[0])
render_bitboard(lg_bb) """


r"""
8  63 62 61 60 59 58 57 56         
7  55 54 53 52 51 50 49 48
6  47 46 45 44 43 42 41 40
5  39 38 37 36 35 34 33 32
4  31 30 29 28 27 26 25 24
3  23 23 21 20 19 18 17 16
2  15 14 13 12 11 10  9  8          
1   7  6  5  4  3  2  1  0
    A  B  C  D  E  F  G  H
"""
#n = generate_pawn_moves(50, 0)
#print(n)
#n = 0x007E7E7E7E7E7E00
###n = square_to_rook_mask(36)
#render_bitboard(n)
#g = index_list_from_mask(n)
#print(g)
#print()
#l = create_all_blocker_configs(g)
#render_bitboard(l[1024])

#for i in l[:10]:
#    render_bitboard(i)
#    print()
#   print()
#l = create_all_blocker_configs(g)
#q = l[0]
#render_bitboard(q)

#n = ones_string(64)
#print(bin(n)[2:])

#indices = [12, 20, 28, 33, 34, 35, 37, 38, 44, 52]
#num     = 102
###num = bin(num)[2:] #10011110
#FINAL = 0
#for bit, index in zip(num[::-1], indices):
#    bit = int(bit)
#    #print(bit, index)
#    FINAL |= bit << index
#    #print(bin(FINAL)[2:])
#render_bitboard(FINAL)



#print(type(FINAL))
#print(FINAL)
#print(type(bin(FINAL)[2:]))
#print(bin(FINAL)[2:])
#print(type(int(bin(FINAL)[2:])))
#print(int(bin(FINAL)[2:]))




    #s = 0
    #print(s = bit << index)
    #s |= int(bit) << index
    #print(bin(s)[2:])
    #render_bitboard(s)
    #print()
    #print()

##square = 36
#n = square_to_rook_mask(square)
#g = index_list_from_mask(n)
#l = create_all_blocker_configs(g)

#p = gen_rook_legal_bb(square, l[1023])
#render_bitboard(l[1023])
#print()
#print()
#render_bitboard(p)
