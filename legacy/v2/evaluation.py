import math
from copy import deepcopy

class MaterialEval:
    
    def __init__(self):
        self.material_value_map = {
            'P': 100,
            'N': 300,
            'B': 320,
            'R': 500,
            'Q': 900,
            'K': 1000000000
        }

    


    '''def evaluate(self, boardFEN):
        Eval = 
        return Eval'''


    def count_material(self, boardFEN, color):
        value = 0

        if color == 'white':
            def is_right_col(piece):
                return piece.isupper()

        if color == 'black':
            def is_right_col(piece):
                return piece.islower()
        
        for piece in boardFEN:
            # ignore nums and '/'
            if piece in '12345678/': continue

            if is_right_col(piece):
                value += self.material_value_map[piece.upper()]
        
        return value

    
    def evaluate(self, boardFEN):
        white_val = self.count_material(boardFEN, 'white')
        black_val = self.count_material(boardFEN, 'black')
        Eval = white_val - black_val
        return Eval
            

class PieceSquareTableEval:

    def __init__(self):
        self.material_evaluator = MaterialEval()

        self.piece_square_tables = {
            'P': 
                { 'mg':   [ 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  ,
                            50 , 50 , 50 , 50 , 50 , 50 , 50 , 50 ,
                            10 , 10 , 20 , 30 , 30 , 20 , 10 , 10 ,
                            5  , 5  , 10 , 25 , 25 , 10 , 5  , 5  ,
                            0  , 0  , 0  , 20 , 20 , 0  , 0  , 0  ,
                            5  , -5 , -10,  0 ,  0 , -10, -5 ,  5 ,
                            5  , 10 , 10 , -20, -20, 10 , 10 ,  5 ,
                            0  , 0  , 0  , 0  , 0  , 0  , 0  ,  0  ],

                    'eg': [ 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  ,
                            150, 150, 150, 150, 150, 150, 150, 150,
                            75 , 75 , 75 , 75 , 75 , 75 , 75 , 75 ,
                            50 , 50 , 50 , 50 , 50 , 50 , 50 , 50 ,
                            25 , 25 , 25 , 25 , 25 , 25 , 25 , 25 ,
                            10 , 10 , 10 , 10 , 10 , 10 , 10 , 10 ,
                            0  , 0  ,  0 ,  0 ,  0 ,  0 ,  0 ,  0 ,
                            0  , 0  , 0  , 0  , 0  , 0  , 0  ,  0  ] },

            
            'N': 
                { 'mg':   [ -50, -40, -30, -30, -30, -30, -40, -50,
                            -40, -20, 0  , 0  , 0  , 0  , -20, -40,
                            -30,  0 , 10 , 15 , 15 , 10 ,  0 , -30,
                            -30,  5 , 15 , 20 , 20 , 15 ,  5 , -30,
                            -30,  0 , 15 , 20 , 20 , 15 ,  0 , -30,
                            -30,  5 , 10 , 15 , 15 , 10 ,  5 , -30,
                            -40, -20,  0 ,  5 ,  5 ,  0 , -20, -40,
                            -50, -40, -30, -30, -30, -30, -40, -50 ],

                    'eg': [ -50, -40, -30, -30, -30, -30, -40, -50,
                            -40, -20, 0  , 0  , 0  , 0  , -20, -40,
                            -30,  0 , 10 , 15 , 15 , 10 ,  0 , -30,
                            -30,  5 , 15 , 20 , 20 , 15 ,  5 , -30,
                            -30,  0 , 15 , 20 , 20 , 15 ,  0 , -30,
                            -30,  5 , 10 , 15 , 15 , 10 ,  5 , -30,
                            -40, -20,  0 ,  5 ,  5 ,  0 , -20, -40,
                            -50, -40, -30, -30, -30, -30, -40, -50 ] },



            'B': 
                { 'mg':   [ -20, -10, -10, -10, -10, -10, -10, -20,
                            -10,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -10,
                            -10,  0 ,  5 , 10 , 10 ,  5 ,  0 , -10,
                            -10,  5 ,  5 , 10 , 10 ,  5 ,  5 , -10,
                            -10,  0 , 10 , 10 , 10 , 10 ,  0 , -10,
                            -10, 10 , 10 , 10 , 10 , 10 , 10 , -10,
                            -10,  5 ,  0 ,  0 ,  0 ,  0 ,  5 , -10,
                            -20, -10, -10, -10, -10, -10, -10, -20 ],

                    'eg': [ -20, -10, -10, -10, -10, -10, -10, -20,
                            -10,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -10,
                            -10,  0 ,  5 , 10 , 10 ,  5 ,  0 , -10,
                            -10,  0 , 10 , 10 , 10 , 10 ,  0 , -10,
                            -10,  0 , 10 , 10 , 10 , 10 ,  0 , -10,
                            -10,  0 ,  5 , 10 , 10 ,  5 ,  0 , -10,
                            -10,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -10,
                            -20, -10, -10, -10, -10, -10, -10, -20 ] },


            
            'R': 
                { 'mg':   [ 0  , 0  , 0  , 0  , 0  , 0  , 0  , 0  ,
                            5  , 10 , 10 , 10 , 10 , 10,  10 ,  5 ,
                            -5 ,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -5 ,
                            -5 ,  0,   0 ,  0 ,  0 ,  0 ,  0 , -5 ,
                            -5 ,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -5 ,
                            -5 ,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -5 ,
                            -5 ,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -5 ,
                            0  ,  0 ,  0 ,  5 ,  5 ,  0 ,  0 ,  0  ],

                    'eg': [ -5 , -5 , -5 , -5 , -5 , -5 , -5 , -5 ,
                            -5 , 0  , 0  , 0  , 0  , 0  , 0  , -5 ,
                            -5 , 0  , 0  , 0  , 0  , 0  , 0  , -5 ,
                            -5 , 0  , 0  , 0  , 0  , 0  , 0  , -5 ,
                            -5 , 0  , 0  , 0  , 0  , 0  , 0  , -5 ,
                            -5 , 0  , 0  , 0  , 0  , 0  , 0  , -5 ,
                            -5 , 0  , 0  , 0  , 0  , 0  , 0  , -5 ,
                            -5 , -5 , -5 , -5 , -5 , -5 , -5 , -5 ,]},

            

            'Q':
                  { 'mg': [ -20, -10, -10, -5 , -5 , -10, -10, -20,
                            -10,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -10,
                            -10,  0 ,  5 ,  5 ,  5 ,  5 ,  0 , -10,
                            -5 ,  0 ,  5 ,  5 ,  5 ,  5 ,  0 , -5 ,
                            0  ,  0 ,  5 ,  5 ,  5 ,  5 ,  0 , -5 ,
                            -10,  5 ,  5 ,  5 ,  5 ,  5 ,  0 , -10,
                            -10,  0 ,  5 ,  0 ,  0 ,  0 ,  0 , -10,
                            -20, -10, -10, -5 , -5 , -10, -10,- 20 ],

                    'eg': [ -20, -10, -10, -5 , -5 , -10, -10, -20,
                            -10,  0 ,  0 ,  0 ,  0 ,  0 ,  0 , -10,
                            -10,  0 ,  5 ,  5 ,  5 ,  5 ,  0 , -10,
                            -5 ,  0 ,  5 ,  5 ,  5 ,  5 ,  0 , -5 ,
                            0  ,  0 ,  5 ,  5 ,  5 ,  5 ,  0 , -5 ,
                            -10,  5 ,  5 ,  5 ,  5 ,  5 ,  0 , -10,
                            -10,  0 ,  5 ,  0 ,  0 ,  0 ,  0 , -10,
                            -20, -10, -10, -5 , -5 , -10, -10,- 20 ] },

            
            'K': 
                  { 'mg': [ -30, -40, -40, -50, -50, -40, -40, -30,
                            -30, -40, -40, -50, -50, -40, -40, -30,
                            -30, -40, -40, -50, -50, -40, -40, -30,
                            -30, -40, -40, -50, -50, -40, -40, -30,
                            -20, -30, -30, -40, -40, -30, -30, -20,
                            -10, -20, -20, -20, -20, -20, -20, -10,
                            20 , 20 ,  0 ,  0 ,  0 ,  0 , 20 , 20 ,
                            20 , 30 , 10 ,  0 ,  0 , 10 , 30 , 20  ],

                    'eg': [  0,  10,  20,  30,  30,  20,  10,   0,
                            10,  20,  30,  40,  40,  30,  20,  10,
                            20,  30,  40,  50,  50,  40,  30,  20,
                            30,  40,  50,  60,  60,  50,  40,  30,
                            30,  40,  50,  60,  60,  50,  40,  30,
                            20,  30,  40,  50,  50,  40,  30,  20,
                            10,  20,  30,  40,  40,  30,  20,  10,
                             0,  10,  20,  30,  30,  20,  10,   0] }
                
        }

    
    def interpolate_pst_values(self, piece, square_num, total_material, pst):
        non_k_material = total_material - 2000000000
        normalized_mat = round((non_k_material / 7880), 3)

        mg_val = pst[piece.upper()]['mg'][square_num]
        eg_val = pst[piece.upper()]['eg'][square_num]

        interpolated_val = (mg_val * normalized_mat) + (eg_val * (1 - normalized_mat))
        
        return round(interpolated_val)

    
    def count_total_material(self, boardFEN):
        total_material = 0
        for piece in boardFEN:
            if piece in '12345678/': continue
            total_material += self.material_evaluator.material_value_map[piece.upper()]
        
        return total_material
            


    def piece_square_table_bonuses(self, boardFEN, color):
        value = 0
        total_material = self.count_total_material(boardFEN)


        if color == 'white':
            pst = deepcopy(self.piece_square_tables)
            def is_right_col(piece):
                return piece.isupper()

        if color == 'black':
            # flip the table
            pst = deepcopy(self.piece_square_tables)
            for piece in pst:
                for game_type in pst[piece]:
                    pst[piece][game_type] = pst[piece][game_type][::-1]
            def is_right_col(piece):
                return piece.islower()
        
        square_count = 0
        for piece in boardFEN:
            if piece == '/': continue
            elif piece in '12345678': square_count += int(piece)
            else:
                if is_right_col(piece):
                    value += self.interpolate_pst_values(piece, square_count, total_material, pst)
                square_count += 1

        return value



    def evaluate(self, boardFEN):
        material_eval = self.material_evaluator.evaluate(boardFEN)

        white_pt_bonus = self.piece_square_table_bonuses(boardFEN, 'white')
        black_pt_bonus = self.piece_square_table_bonuses(boardFEN, 'black')
        piece_table_eval = white_pt_bonus - black_pt_bonus

        final_eval = material_eval + piece_table_eval
        return final_eval


class PassedPawnEval(PieceSquareTableEval):

    def __init__(self):
        self.pst_evaluator = PieceSquareTableEval()
        self.passed_pawn_bonuses = [0, 90, 60, 40, 25, 15, 15, 0]

    
    def pawn_is_passed(self, boardFEN, piece_num, color):
        rowlist = boardFEN.split('/')
        
        for i in range(len(rowlist)):
            expandedrow = ''
            
            for char in rowlist[i]:
                if char not in '12345678': expandedrow += char
                else:
                    for _ in range(int(char)):
                        expandedrow += '1'
            rowlist[i] = expandedrow

        rownum = math.floor(piece_num / 8)
        colnum = piece_num % 8

        if rowlist[rownum][colnum].upper() != 'P':
            is_passed_p = False
            return is_passed_p        

        if color == 'white':
            is_passed_p    = True
            no_blocking_ps = True
            while no_blocking_ps:
                rownum -= 1
                if rownum < 0: break
                for x in [colnum, colnum+1, colnum-1]:
                    if x > 7 or x < 0: continue
                    if rowlist[rownum][x] == 'p':
                        is_passed_p = False
                        no_blocking_pawns = False
            return is_passed_p
        
        elif color == 'black':
            is_passed_p    = True
            no_blocking_ps = True
            while no_blocking_ps:
                rownum += 1
                if rownum > 7: break
                for x in [colnum, colnum+1, colnum-1]:
                    if x > 7 or x < 0: continue
                    if rowlist[rownum][x] == 'P':
                        is_passed_p = False
                        no_blocking_pawns = False
            return is_passed_p


    def get_passed_pawn_bonuses(self, boardFEN, color):
        value = 0

        if color == 'white':
            ppb = deepcopy(self.passed_pawn_bonuses)
            def is_right_col(piece):
                return piece.isupper()

        if color == 'black':
            ppb = deepcopy(self.passed_pawn_bonuses)
            ppb = ppb[::-1]
            def is_right_col(piece):
                return piece.islower()

        piece_num = 0
        row_num   = 0
        for piece in boardFEN:
            if piece in '12345678':
                piece_num += int(piece)
                continue
            if piece == '/':
                row_num   += 1
                continue

            if is_right_col(piece) and piece.upper() == 'P':
                # if the pawn is a passed pawn
                if self.pawn_is_passed(boardFEN, piece_num, color):
                    value += ppb[row_num]
            piece_num += 1

        return value


    def evaluate(self, boardFEN):
        material_and_pst_eval = self.pst_evaluator.evaluate(boardFEN)

        white_val = self.get_passed_pawn_bonuses(boardFEN, 'white')
        black_val = self.get_passed_pawn_bonuses(boardFEN, 'black')
        passed_p_eval = white_val - black_val

        final_eval = material_and_pst_eval + passed_p_eval
        return final_eval


class IsoPawnEval(PassedPawnEval):

    def __init__(self):
        self.passed_p_evaluator = PassedPawnEval()
        self.iso_pawn_penalties = [0, -25, -50, -75, -100, -100, -100, -100, -100]

    
    def pawn_is_isolated(self, boardFEN, colnum, color):
        if str(colnum) not in '01234567':
            print('AGAGAAAAAAGGGAAAAA')
            print(colnum)
            print()

        rowlist = boardFEN.split('/')
        
        for i in range(len(rowlist)):
            expandedrow = ''
            
            for char in rowlist[i]:
                if char not in '12345678': expandedrow += char
                else:
                    for _ in range(int(char)):
                        expandedrow += '1'
            rowlist[i] = expandedrow
        
        if color == 'white':
            is_iso_pawn = True
            for row in rowlist:
                for x in [colnum+1, colnum-1]:
                    if x < 0 or x > 7: continue
                    if row[x] == 'P':
                        is_iso_pawn = False
                        return is_iso_pawn
            # print('EEEGEGEGEGGEGE')
            # print(colnum)
            # print()
            return is_iso_pawn

        if color == 'black':
            is_iso_pawn = True
            for row in rowlist:
                for x in [colnum+1, colnum-1]:
                    if x < 0 or x > 7: continue
                    if row[x] == 'p':
                        is_iso_pawn = False
                        return is_iso_pawn
            # print('SWEETDREAMSAREMADEOFTHISWHOAMITODISAGREETRAVELTHEWORLDANDTHESEVENSEASEVERYBODYSLOOKINFORSOMETHINGSOMEOFTHEMWANTTOUSEYOUSOMEOFTHEMWANTTOBEUSEDBYYOUSOMEOFTHEMWANTTOABUSEYOUSOMEOFTHEMWANTTOBEABUSED')
            # print(colnum)
            # print()
            return is_iso_pawn


    
    def get_iso_pawn_malus(self, boardFEN, color):
        iso_pawn_count = 0
        ipp = deepcopy(self.iso_pawn_penalties)

        if color == 'white':
            def is_right_col(piece):
                return piece.isupper()
        
        if color == 'black':
            def is_right_col(piece):
                return piece.islower()

        colnum = 0
        for piece in boardFEN:
            if colnum > 8 or colnum < 0:
                print('OOOOOGOOAOGOAOGOAGOGOBOOOOGA')
                print(colnum)
                print()
            if piece in '12345678':
                colnum += int(piece)
                continue
            if piece == '/':
                colnum = 0
                continue
            if is_right_col(piece) and piece.upper() == 'P':
                # if pawn is an isolated pawn
                if self.pawn_is_isolated(boardFEN, colnum, color):
                    iso_pawn_count += 1
            colnum += 1

        if iso_pawn_count > 6:
            print(iso_pawn_count)
            print(boardFEN)

        return ipp[iso_pawn_count]



    def evaluate(self, boardFEN):
        material_pst_passed_p_eval = self.passed_p_evaluator.evaluate(boardFEN)

        white_val = self.get_iso_pawn_malus(boardFEN, 'white')
        black_val = self.get_iso_pawn_malus(boardFEN, 'black')
        iso_pawn_malus = white_val - black_val

        final_eval = material_pst_passed_p_eval + iso_pawn_malus
        return final_eval


class MopUpEval(IsoPawnEval):

    def __init__(self):
        self.iso_p_evaloator = IsoPawnEval()
        self.chebyshev_bonuses = [0, 0, 50, 30, 20, 15, 10, 5]
        self.CMD = [
            6, 5, 4, 3, 3, 4, 5, 6,
            5, 4, 3, 2, 2, 3, 4, 5,
            4, 3, 2, 1, 1, 2, 3, 4,
            3, 2, 1, 0, 0, 1, 2, 3,
            3, 2, 1, 0, 0, 1, 2, 3,
            4, 3, 2, 1, 1, 2, 3, 4,
            5, 4, 3, 2, 2, 3, 4, 5,
            6, 5, 4, 3, 3, 4, 5, 6,
        ]


    def manhattan_distance(self, sqr1, sqr2):
        # make each sqr into a rownum and colnum
        x1 = sqr1 % 8
        y1 = math.floor(sqr1 / 8)

        x2 = sqr2 % 8
        y2 = math.floor(sqr2 / 8)

        manhatt_dist = abs(x2 - x1) + abs(y2 - y1)
        return manhatt_dist

    
    def chebyshev_distance(self, sqr1, sqr2):
        x1 = sqr1 % 8
        y1 = math.floor(sqr1 / 8)

        x2 = sqr2 % 8
        y2 = math.floor(sqr2 / 8)

        x_diff = abs(x2 - x1)
        y_diff = abs(y2 - y1)

        cheb_dist = max(x_diff, y_diff)
        return cheb_dist

    
    def get_mop_up_bonus(self, boardFEN):
        mop_up_eval = 0

        #board is free of pawns
        board_free_of_pawns = True
        for piece in boardFEN:
            if piece.upper() == 'P':
                board_free_of_pawns = False
                break

        #one side is up at least 5 in raw material
        up_5_mat = False
        white_material = self.iso_p_evaloator.passed_p_evaluator.pst_evaluator.material_evaluator.count_material(boardFEN, 'white')
        black_material = self.iso_p_evaloator.passed_p_evaluator.pst_evaluator.material_evaluator.count_material(boardFEN, 'black')
        if abs(white_material - black_material) >= 500:
            up_5_mat = True

        #5 or less pieces on board
        less_than_5_pieces = True
        piece_count = 0
        for piece in boardFEN:
            if piece in '12345678/': continue
            piece_count += 1
        if piece_count > 5:
            less_than_5_pieces = False
        
        if board_free_of_pawns and up_5_mat and less_than_5_pieces:
            if white_material - black_material > 0:
                color = 'white'
            elif white_material - black_material < 0:
                color = 'black'
            
            if color == 'white':
                def is_right_col(piece):
                    return piece.isupper()

            elif color == 'black':
                def is_right_col(piece):
                    return piece.islower()
            
            white_k_num = 0
            black_k_num = 0
            count = 0
            for piece in boardFEN:
                if piece == '/':
                    continue
                elif piece in '12345678':
                    count += int(piece)
                    continue
                elif piece.upper() == 'K':
                    if is_right_col(piece): white_k_num = count
                    if not is_right_col(piece): black_k_num = count
                count += 1
            
            if color == 'white': losing_king_num = black_k_num
            if color == 'black': losing_king_num = white_k_num
        
            king_manhattan_dist = self.manhattan_distance(white_k_num, black_k_num)
            king_chebyshev_dist = self.chebyshev_distance(white_k_num, black_k_num)
            losing_king_CMD = self.CMD[losing_king_num]

            mop_up_eval = (losing_king_CMD * 5) + (((14 - king_manhattan_dist) * 3) + self.chebyshev_bonuses[king_chebyshev_dist])

            if color == 'black': mop_up_eval = mop_up_eval * -1

        return mop_up_eval
        # should only work for one side at a time and sometimes not work at all
        #
        # CMD for opp color king (maybe 30x the board values)
        #  - will encourage away from center (especially corners)
        # ManhattDist and ChebDist for distance between the two kings (want it to be small)
        # - want both because while chebyshev is good, it encourages facing the king diagonally
        #   which is not wanted, that's why you add manhattan which is higher for diagonals than straights
        #       - (reward for this score being low (2 cheb 2 man is best))
        #       - since its somehow avg. of both, cant realy do the indec of list to get val
        # - to encourgae manhatt distance to be small, do 14 - manhatt dist (cuz 14 is max manhatt distance)
    

    def evaluate(self, boardFEN):
        material_pst_passed_p_iso_p_eval = self.iso_p_evaloator.evaluate(boardFEN)
        mop_up_eval = self.get_mop_up_bonus(boardFEN)

        final_eval = material_pst_passed_p_iso_p_eval + mop_up_eval
        return final_eval


class KingTropismEval(MopUpEval):

    def __init__(self):
        self.mop_up_evaluator = MopUpEval()


    def get_tropism_bonus(self, boardFEN, color):
        # bonus for closeness of queens and knights to opp col king # distance measured using chebyshev
        if color == 'white':
            def is_right_col(piece):
                return piece.isupper()
        elif color == 'black':
            def is_right_col(piece):
                return piece.islower()

        enemy_king_pos = 0
        queen_exists = False
        knight1_exists = False
        knight2_exists = False
        queen_pos = None
        knight1_pos = None
        knight2_pos = None

        count = 0
        for piece in boardFEN:
            if piece == '/': continue
            elif piece in '12345678':
                count += int(piece)
                continue
            if piece.upper() == 'K' and not is_right_col(piece):
                enemy_king_pos = count
            elif piece.upper() == 'Q' and is_right_col(piece):
                queen_exists = True
                queen_pos = count
            elif piece.upper() == 'N' and is_right_col(piece):
                if knight1_exists:
                    knight2_exists = True
                    knight2_pos = count
                else:
                    knight1_exists = True
                    knight1_pos = count
                # if theres already one knight on board, assign pos to second knight
            count += 1

        # now check for each piece's existence and if it exists, calculate the chebyshev distance from enemy king
        tropism_bonus = 0
        mini_count = 0
        pieces_pos = [queen_pos, knight1_pos, knight2_pos]
        for condition in [queen_exists, knight1_exists, knight2_exists]:
            if condition:
                # if each piece exists, get its distance from enemy king
                cheb_dist = self.mop_up_evaluator.chebyshev_distance(pieces_pos[mini_count], enemy_king_pos)
                tropism_bonus += (7 - cheb_dist) * 4
            mini_count += 1

        return tropism_bonus


    def evaluate(self, boardFEN):
        material_pst_passed_p_iso_p_mop_up_eval = self.mop_up_evaluator.evaluate(boardFEN)

        white_val = self.get_tropism_bonus(boardFEN, 'white')
        black_val = self.get_tropism_bonus(boardFEN, 'black')
        king_tropism_bonus = white_val - black_val

        final_eval = material_pst_passed_p_iso_p_mop_up_eval + king_tropism_bonus
        return final_eval


class MobilityEval(KingTropismEval):

    def __init__(self):
        self.king_tropism_evaluator = KingTropismEval()


    def get_legal_moves(self, boardFEN, color):
        import board
        board = board.Board()
        board.set_board(boardFEN)
        legal_moves = board.get_all_moves(color)
        
        return legal_moves

    
    def get_mobility_score(self, boardFEN, color):
        legal_move_len = len(self.get_legal_moves(boardFEN, color))
        return round(legal_move_len * 3)

    
    def evaluate(self, boardFEN):
        material_pst_passed_p_iso_p_mop_up_king_tropism_eval = self.king_tropism_evaluator.evaluate(boardFEN)

        white_val = self.get_mobility_score(boardFEN, 'white')
        black_val = self.get_mobility_score(boardFEN, 'black')
        mobility_score = white_val - black_val

        final_eval = material_pst_passed_p_iso_p_mop_up_king_tropism_eval + mobility_score
        return final_eval


class CenterControlEval(KingTropismEval):

    def __init__(self):
        self.king_tropism_evaluator = KingTropismEval()


    def get_num_central_peices(self, boardFEN, color):
        #get num pieces in central 8 sqrs
        if color == 'white':
            def is_right_col(piece):
                return piece.isupper()
        if color == 'black':
            def is_right_col(piece):
                return piece.islower()

        rowlist = boardFEN.split('/')
        
        for i in range(len(rowlist)):
            expandedrow = ''
            
            for char in rowlist[i]:
                if char not in '12345678': expandedrow += char
                else:
                    for _ in range(int(char)):
                        expandedrow += '1'
            rowlist[i] = expandedrow

        central8sqrs = []
        for row in [3, 4]:
            for col in [2, 3, 4, 5]:
                central8sqrs.append(rowlist[row][col])

        num_central_pieces = 0
        for piece in central8sqrs:
            if piece.upper() in 'KQRBNP' and is_right_col(piece):
                num_central_pieces += 1
        
        return num_central_pieces

    
    '''def get_num_attacking_center_pieces(self, boardFEN, color):
        import board
        board = board.Board()
        board.set_board(boardFEN)
        legal_moves = board.get_all_moves(color)

        center_attacking_pieces = []
        for move in legal_moves:
            sqr1 = move.split('->')[0]
            sqr2 = move.split('->')[1]
            if sqr2 in [27, 28, 29, 30, 35, 36, 37, 38]:
                if sqr1 not in center_attacking_pieces:
                    center_attacking_pieces.append(sqr1)

        return len(center_attacking_pieces)'''


    def count_total_pieces(self, boardFEN):
        total_material = 0
        for piece in boardFEN:
            if piece in '12345678/': continue
            total_material += 1
        
        return total_material

    
    def get_center_control_bonus(self, boardFEN, color):
        num_central_pieces          = self.get_num_central_peices(boardFEN, color)
        #num_center_attacking_pieces = self.get_num_attacking_center_pieces(boardFEN, color)

        center_control_bonus = (num_central_pieces * 3) #+ (num_center_attacking_pieces * 5)

        total_material = self.count_total_pieces(boardFEN)
        if total_material < 18: # 60% threshold, this dials down influence of center control bonus towards the endgame
            center_control_bonus = int(center_control_bonus * round(total_material/18, 3))

        return center_control_bonus


    def evaluate(self, boardFEN):
        material_pst_passed_p_iso_p_mop_up_king_tropism_eval = self.king_tropism_evaluator.evaluate(boardFEN)

        white_val = self.get_center_control_bonus(boardFEN, 'white')
        black_val = self.get_center_control_bonus(boardFEN, 'black')
        center_control_bonus = white_val - black_val

        final_eval = material_pst_passed_p_iso_p_mop_up_king_tropism_eval + center_control_bonus
        return final_eval


class KingSafetyEval(CenterControlEval):

    def __init__(self):
        self.center_control_evaluator = CenterControlEval()


    def get_num_adjacent_king_sqrs(self, boardFEN, color):
        if color == 'white':
            def is_right_col(piece):
                return piece.isupper()
        if color == 'black':
            def is_right_col(piece):
                return piece.islower()
        
        rowlist = boardFEN.split('/')
        for i in range(len(rowlist)):
            expandedrow = ''
            
            for char in rowlist[i]:
                if char not in '12345678': expandedrow += char
                else:
                    for _ in range(int(char)):
                        expandedrow += '1'
            rowlist[i] = expandedrow
        
        #find the num of the king square
        king_sqr = None
        count = 0
        for row in rowlist:
            for piece in row:
                if piece.upper() == 'K' and is_right_col(piece):
                    king_sqr = count
                count += 1
        
        king_rownum = math.floor(king_sqr/8)
        king_colnum = king_sqr % 8

        adjacent_pieces = 0
        all_directions = [[0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1], [1, 1], [1, 0], [1, -1]]
        for direc in all_directions:
            newrow = king_rownum + direc[0]
            newcol = king_colnum + direc[1]
            if newrow > 7 or newrow < 0:
                adjacent_pieces += 1
                continue
            if newcol > 7 or newcol < 0:
                adjacent_pieces += 1
                continue
            border_piece = rowlist[newrow][newcol]
            if border_piece.upper() in 'KQRBNP' and is_right_col(border_piece):
                adjacent_pieces += 1
        
        # were also counting edges as neighboring pieces

        return adjacent_pieces


        
    def get_king_safety_bonus(self, boardFEN, color):
        num_adjacent_pieces = self.get_num_adjacent_king_sqrs(boardFEN, color)
        return num_adjacent_pieces * 10


    def check_for_termination(self, boardFEN):
        import board
        board = board.Board()
        board.set_board(boardFEN)

        white_moves = board.get_all_moves('white')
        black_moves = board.get_all_moves('black')

        white_in_check = board.check_board_for_checks('white')
        black_in_check = board.check_board_for_checks('black')

        if not white_moves and not white_in_check:
            return 'stalemate'
        if not black_moves and not black_in_check:
            return 'stalemate'
        if not white_moves and white_in_check:
            return 'black wins by checkmate'
        if not black_moves and black_in_check:
            return 'white wins by checkmate'
        
    
    def evaluate(self, boardFEN):
        termination = self.check_for_termination(boardFEN)
        if termination:
            if termination == 'stalemate':
                final_eval = 0
                return final_eval
            if termination == 'white wins by checkmate':
                final_eval = 1000000
                return final_eval
            if termination == 'black wins by checkmate':
                final_eval = -1000000
                return final_eval

        material_pst_passed_p_iso_p_mop_up_king_tropism_mobility_center_control_eval = self.center_control_evaluator.evaluate(boardFEN)

        white_val = self.get_king_safety_bonus(boardFEN, 'white')
        black_val = self.get_king_safety_bonus(boardFEN, 'black')
        king_safety_bonus = white_val - black_val

        final_eval = material_pst_passed_p_iso_p_mop_up_king_tropism_mobility_center_control_eval + king_safety_bonus
        return final_eval


#evaluator2 = PieceSquareTableEval()
#evaluator3 = PassedPawnEval()
#evaluator1 = MaterialEval()
#evaluator4 = IsoPawnEval()
#evaluator5 = MopUpEval()
#evaluator6 = KingTropismEval()
#evaluator7 = MobilityEval()
#evaluator8 = CenterControlEval()
#evaluator9 = KingSafetyEval()
#
#
#
#
#print(evaluator1.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator2.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator3.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator4.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator5.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator6.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator7.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator8.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))
#print(evaluator9.evaluate('r6r/1pknb1p1/2p1bp2/4p2p/2P1N1PP/1P2PPB1/1K2B3/3R3R'))









#print(evaluator.evaluate('k7/8/8/8/N7/8/8/K7'))
#print(evaluator2.evaluate('k7/8/8/8/N7/8/8/K7'))

#r7/2p2p2/1kb5/1qb3B1/8/3P4/1PP1P1PP/R1BQK1NR
#k7/8/8/8/2n5/8/8/7K






# 0  1  2  3  4  5  6  7
# 8  9  10 11 12 13 14 15
# 16 17 18 19 20 21 22 23
# 24 25 26 27 28 29 30 31
# 32 33 34 35 36 37 38 39
# 40 41 42 43 44 45 46 47
# 48 49 50 51 52 53 54 55
# 56 57 58 59 60 61 62 63


#
#
#
#
#
 #
 #
 #
 #
  #
  #
  #
   #
   #
    ##
      ###
          ####
              #####
                  ######
                          #######
                              ########