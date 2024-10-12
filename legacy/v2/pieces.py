class Pieces:
    def __init__(self, color, piece_type, pos):
        self.color       = color
        self.piece_type  = piece_type
        self.pos         = pos
        self.moved       = False


    def queen_rook_bishop_moves(self, directions):
        self.legal_moves          = {}
        direction_map = {
            'North'    :-8,
            'East'     : 1,
            'South'    : 8,
            'West'     :-1,
            'Northeast':-7,
            'Southeast': 9,
            'Southwest': 7,
            'Northwest':-9
        }
        for direction in directions:
            moves_list = []
            northern_breach = False
            southern_breach = False
            eastern_breach  = False
            western_breach  = False
            temp_pos = int(self.pos)
            while True:
                num = direction_map[direction]
                temp_pos += num
                if temp_pos <= 0: northern_breach = True
                if temp_pos > 64: southern_breach = True
                if (temp_pos - num) % 8 == 0 and num in [-7, 1, 9]: eastern_breach = True
                if (temp_pos - num) % 8 == 1 and num in [-9, -1, 7]: western_breach = True

                if northern_breach or southern_breach or eastern_breach or western_breach:
                    break
                moves_list.append(temp_pos)
            self.legal_moves[direction] = moves_list
   

class King(Pieces):
    def __init__(self, color, pos, piece_type='king'):
        super().__init__(color, piece_type, pos)
        self.check_data = {'in_check': False, 'checking_pieces':[]}
        # can make this into check data where the checking pieces are stored
        # then can only look at legal_moves of the stored checking pieces
        # and determine that the king is allowed to make any move that takes his square out of the legal_moves of those pieces
        # if move made brings king out of legal moves of checking pieces & no new checks arise --> allow the move
        # if move out of legal moves of checking pieces, check that your not moving into any other checks
        #           if you are, don't allow
        # for checkmate: try all posibble 
        if self.color == 'white':
            self.ASCII_icon = 'K'
        if self.color == 'black':
            self.ASCII_icon = 'k'
    
    def get_moves(self):
        self.legal_moves = {}
        direction_map = {
            'North'    :[-8],
            'East'     : [1, 2],
            'South'    : [8],
            'West'     :[-1, -2],
            'Northeast':[-7],
            'Southeast': [9],
            'Southwest': [7],
            'Northwest':[-9]
        }
        for direc in direction_map:
            dir_moves = []
            for num in direction_map[direc]:
                new_pos = self.pos + num

                northern_breach = False
                southern_breach = False
                eastern_breach  = False
                western_breach  = False

                if new_pos <= 0: northern_breach = True
                if new_pos > 64: southern_breach = True
                if num in [-7, 1, 9, -9, -1, 7]:
                    if (new_pos - num) % 8 == 0 and num in [-7, 1, 9] : eastern_breach = True
                    if (new_pos - num) % 8 == 1 and num in [-9, -1, 7]: western_breach = True
                if num in [2, -2]:
                    if (new_pos - num) % 8 == 7 and num == 2 : eastern_breach = True
                    if (new_pos - num) % 8 == 2 and num == -2: western_breach = True

                if northern_breach or southern_breach or eastern_breach or western_breach:
                    break
                dir_moves.append(new_pos)
            self.legal_moves[direc] = dir_moves


class Queen(Pieces):
    def __init__(self, color, pos, piece_type='queen'):
        super().__init__(color, piece_type, pos)
        if self.color == 'white':
            self.ASCII_icon = 'Q'
        if self.color == 'black':
            self.ASCII_icon = 'q'
    
    def get_moves(self):
        super().queen_rook_bishop_moves(['North', 'East', 'South', 'West', 'Northeast', 'Southeast', 'Southwest', 'Northwest'])


class Rook(Pieces):
    def __init__(self, color, pos, piece_type='rook'):
        super().__init__(color, piece_type, pos)
        if self.color == 'white':
            self.ASCII_icon = 'R'
        if self.color == 'black':
            self.ASCII_icon = 'r'
    
    def get_moves(self):
        super().queen_rook_bishop_moves(['North', 'East', 'South', 'West'])


class Bishop(Pieces):
    def __init__(self, color, pos, piece_type='bishop'):
        super().__init__(color, piece_type, pos)
        if self.color == 'white':
            self.ASCII_icon = 'B'
        if self.color == 'black':
            self.ASCII_icon = 'b'
    
    def get_moves(self):
        super().queen_rook_bishop_moves(['Northeast', 'Southeast', 'Southwest', 'Northwest'])


class Knight(Pieces):
    def __init__(self, color, pos, piece_type='knight'):
        super().__init__(color, piece_type, pos)
        if self.color == 'white':
            self.ASCII_icon = 'N'
        if self.color == 'black':
            self.ASCII_icon = 'n'
    
    def get_moves(self):
        self.legal_moves = []
        direction_nums = [-15, -6, 10, 17, 15, 6, -10, -17]
        for num in direction_nums:
            new_pos = self.pos + num

            northern_breach = False
            southern_breach = False
            eastern_breach  = False
            western_breach  = False

            if new_pos <= 0: northern_breach = True
            if new_pos > 64: southern_breach = True
            if (new_pos - num) % 8 == 0 and num in [-15, -6, 10, 17]: eastern_breach = True
            if (new_pos - num) % 8 == 7 and num in [-6, 10]: eastern_breach = True
            if (new_pos - num) % 8 == 1 and num in [15, 6, -10, -17]: western_breach = True
            if (new_pos - num) % 8 == 2 and num in [6, -10]: western_breach = True

            if northern_breach or southern_breach or eastern_breach or western_breach:
                continue
            self.legal_moves.append(new_pos)


class Pawn(Pieces):
    def __init__(self, color, pos, piece_type='pawn'):
        super().__init__(color, piece_type, pos)
        self.en_passant_data = {'is_en_passantable': False, 'move_num': None}
        if self.color == 'white':
            self.ASCII_icon = 'P'
        if self.color == 'black':
            self.ASCII_icon = 'p'
    
    def get_moves(self):
        self.legal_moves = {}

        direction_map = {
            'North'    :[-8, -16],
            'South'    :[8, 16],
            'Northeast':[-7],
            'Southeast': [9],
            'Southwest': [7],
            'Northwest':[-9]
        }

        if self.color == 'white':
            direction_list = ['North', 'Northwest', 'Northeast']
        if self.color == 'black':
            direction_list = ['South', 'Southeast', 'Southwest']

        for direction in direction_list:
            legal_list = []
            for num in direction_map[direction]:
                new_pos = self.pos + num

                northern_breach = False
                southern_breach = False
                eastern_breach  = False
                western_breach  = False

                if new_pos <= 0: northern_breach = True
                if new_pos > 64: southern_breach = True
                if self.color == 'white':
                    if (new_pos - num) % 8 == 0 and num in [-7]: eastern_breach = True
                    if (new_pos - num) % 8 == 1 and num in [-9]: western_breach = True
                if self.color == 'black':
                    if (new_pos - num) % 8 == 0 and num in [9]: eastern_breach = True
                    if (new_pos - num) % 8 == 1 and num in [7]: western_breach = True

                if northern_breach or southern_breach or eastern_breach or western_breach:
                    continue
                legal_list.append(new_pos)
            self.legal_moves[direction] = legal_list