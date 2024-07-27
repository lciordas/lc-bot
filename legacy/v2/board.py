import math
import pieces
from copy import deepcopy

class Board:
    def __init__(self):
        """"makes an empty board (8x8 full of Nones) --> main list has 8 nested lists which each have 8 items"""
        self.internal_board = []
        for i in range(8):
            empty_row = []
            for i in range(8):
                empty_row.append(None)
            self.internal_board.append(empty_row)


    def ASCII_representation(self):
        """visually draws the board from the values in the internal representation"""
        print(' ____ ____ ____ ____ ____ ____ ____ ____')
        for row in self.internal_board:
            piece_count = 0
            for piece in row:
                piece_count += 1
                if piece_count == 8:
                    if piece:
                        print('|', piece.ASCII_icon, ' |')
                    elif piece == None:
                        print('|    |')
                else:
                    if piece:
                        print('|', piece.ASCII_icon, ' ', end="")
                    elif piece == None:
                        print('|    ', end="")
            print('|____|____|____|____|____|____|____|____|')

#self.coords_to_num([row_count, col_count])
    def set_board(self, fen_string):
        """sample input: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"""
        """fills the positions in the internal board with piece objects and Nones"""
        row_count = 0
        rows = fen_string.split('/')
        for row in rows:
            col_count = 0
            for item in row:
                if item in '12345678':
                    for i in range(int(item)):
                        self.internal_board[row_count][col_count] = None
                        col_count += 1
                elif item in 'KQRBNPkqrbnp':
                    if item == 'K':
                        piece = pieces.King('white', self.coords_to_num([row_count, col_count]))
                        if piece.pos != 61: piece.moved = True
                    if item == 'Q': piece = pieces.Queen('white', self.coords_to_num([row_count, col_count]))
                    if item == 'R':
                        piece = pieces.Rook('white', self.coords_to_num([row_count, col_count]))
                        if piece.pos not in [57, 64]: piece.moved = True
                    if item == 'B': piece = pieces.Bishop('white', self.coords_to_num([row_count, col_count]))
                    if item == 'N': piece = pieces.Knight('white', self.coords_to_num([row_count, col_count]))
                    if item == 'P':
                        piece = pieces.Pawn('white', self.coords_to_num([row_count, col_count]))
                        if piece.pos not in [49, 50, 51, 52, 53, 54, 55, 56]:
                            piece.moved = True
                    if item == 'k':
                        piece = pieces.King('black', self.coords_to_num([row_count, col_count]))
                        if piece.pos != 5: piece.moved = True
                    if item == 'q': piece = pieces.Queen('black', self.coords_to_num([row_count, col_count]))
                    if item == 'r':
                        piece = pieces.Rook('black', self.coords_to_num([row_count, col_count]))
                        if piece.pos not in [1, 8]: piece.moved = True
                    if item == 'b': piece = pieces.Bishop('black', self.coords_to_num([row_count, col_count]))
                    if item == 'n': piece = pieces.Knight('black', self.coords_to_num([row_count, col_count]))
                    if item == 'p':
                        piece = pieces.Pawn('black', self.coords_to_num([row_count, col_count]))
                        if piece.pos not in [9, 10, 11, 12, 13, 14, 15, 16]:
                            piece.moved = True

                    self.internal_board[row_count][col_count] = piece
                    col_count += 1
            row_count += 1 # this func is where you would fix the piece.moved problem


    def dic_w_lists_to_list(self, dic):
        """combines all values of a dictionary into a single list (can comibine lists if they are the values)"""
        if isinstance(dic, list):
            return dic
        final_list = []
        for key in dic:
            for item in dic[key]:
                final_list.append(item)
        return final_list

    
    def set_x_board(self, square_list):
        """makes a new empty board, and uses the nums from input list to mark (place Xs on) specific squares"""
        self.x_board = []
        for i in range(8):
            empty_row = []
            for i in range(8):
                empty_row.append(None)
            self.x_board.append(empty_row)
        
        for sqr in square_list:
            row = self.num_to_coords(sqr)[0]
            col = self.num_to_coords(sqr)[1]
            self.x_board[row][col] = 'X'


    def ASCII_x_board(self):
        """visually displays the x_board"""
        print(' ____ ____ ____ ____ ____ ____ ____ ____')
        for row in self.x_board:
            piece_count = 0
            for piece in row:
                piece_count += 1
                if piece_count == 8:
                    if piece:
                        print('|', 'X', ' |')
                    elif piece == None:
                        print('|    |')
                else:
                    if piece:
                        print('|', 'X', ' ', end="")
                    elif piece == None:
                        print('|    ', end="")
            print('|____|____|____|____|____|____|____|____|')


    def coords_to_num(self, square_coords): # (x, y) --> 8x + (y+1)
        """takes in cooordinates (0-7) and returns a single num"""
        """x, y are flipped here, since row (up, down or y) is considered first --> [3,7] = 32"""
        x = square_coords[0] 
        y = square_coords[1]
        number = (x*8) + (y+1)
        return number

    
    def num_to_coords(self, square_num): # 32 --> (3, 7)
        """takes in a location num and switches it to coordinate form"""
        square_num = int(square_num)
        row = math.floor(square_num/8)
        if square_num % 8 == 0:
            row = int((square_num/8) - 1)

        col = (square_num % 8) - 1
        if square_num % 8 == 0:
            col = 7
        return [row, col]


    def num_to_piece_obj(self, num):
        """allows you to access the content of a square from the number"""
        """when called the function with a number input essentially becomes the piece object of that square"""
        # num_to_piece_obj(4).pos = 64
        row = self.num_to_coords(num)[0]
        col = self.num_to_coords(num)[1]
        piece = self.internal_board[row][col]
        return piece
    # num to coords (32 --> 3, 7) and take out cords from num_to_piece_obj which is just 32 --> piece_object


    def chess_notation_to_num(self, chess_notation): #e2
        """takes in chess coordinates and outputs number"""
        letter = chess_notation[0]
        number = int(chess_notation[1])
        for i in range(8):
            if "abcdefgh"[i] == letter:
                num = i+1
        num += abs(number-8)*8
        return num

    
    def make_move(self, start_sqr, end_sqr, mark_as_moved=True): #squares are nums
        """moves a piece obj from one location to another in the internal board and updates this piece's self-stored location"""
        start_sqr_coords = self.num_to_coords(start_sqr) # can potentially get rid of these 7 lines
        start_row = start_sqr_coords[0]#                   replace with num_to_piece_obj()
        start_col = start_sqr_coords[1]
        end_sqr_coords   = self.num_to_coords(end_sqr)
        end_row = end_sqr_coords[0]
        end_col = end_sqr_coords[1]

        piece = self.internal_board[start_row][start_col]
        piece.pos = end_sqr # updates pos of piece being moved (but does so before moving the piece in the internal_board)
        self.internal_board[end_row][end_col] = piece
        self.internal_board[start_row][start_col] = None
        if mark_as_moved:
            piece.moved = True #label the piece as having made a move
    
    def update_en_passantables(self, move_count):
        for i in range(1, 65): #for every pawn on the board (1-64)
            piece = self.num_to_piece_obj(i)
            if piece:
                if piece.piece_type == 'pawn':
                    if piece.en_passant_data['move_num']:
                        if move_count - piece.en_passant_data['move_num'] >= 2: #if the current movecount is 2 or more that the move_count when they became en_passantable
                            #they are no longer en_passantable
                            piece.en_passant_data['is_en_passantable'] = False 
                            piece.en_passant_data['move_num'] = None

    '''def update_potential_checking_pieces(self):
        for i in range(1, 65): # go thru all pieces to check if its a king
            if self.num_to_piece_obj(i) and self.num_to_piece_obj(i).piece_type == 'king':
                king = self.num_to_piece_obj(i)
                for i in range(1, 65): # go thru all pieces to get legal_moves | EXCEPT PAWNS AND KINGS
                    if self.num_to_piece_obj(i) and self.num_to_piece_obj(i).piece_type not in ['pawn', 'king']:
                        piece = self.num_to_piece_obj(i)
                        piece.get_moves()
                        list_of_moves = self.dic_w_lists_to_list(piece.legal_moves)
                        if king.pos in list_of_moves:
                            king.check_data['maybe_checking_pieces'].append(piece) #store the pieces that might be checking the king'''

    def basic_rules(self, s_sqr, e_sqr):
        move_permitted = True
        piece = self.num_to_piece_obj(s_sqr)

        piece_on_end_sqr = False
        if self.num_to_piece_obj(e_sqr):
            piece_being_captured = self.num_to_piece_obj(e_sqr)
            piece_on_end_sqr = True

        # To Pass: there is a piece on the start square
        if not piece:
            move_permitted = False
            return move_permitted

        # To Pass: end square is in legal moves list of piece
        piece.get_moves()
        legal_moves_list = self.dic_w_lists_to_list(piece.legal_moves)
        if e_sqr not in legal_moves_list: move_permitted = False

        # To Pass: end square is either empty or has a piece of opposite color
        if piece_on_end_sqr and piece_being_captured.color == piece.color:
            move_permitted = False

        return move_permitted


    def QRB_special_rules(self, s_sqr, e_sqr):
        move_permitted = True
        piece = self.num_to_piece_obj(s_sqr)

        piece_on_end_sqr = False
        if self.num_to_piece_obj(e_sqr):
            piece_being_captured = self.num_to_piece_obj(e_sqr)
            piece_on_end_sqr = True

        # contruct a list of all squares before the end square
        piece.get_moves()
        for direction in piece.legal_moves:
            direction_list = piece.legal_moves[direction]
            if e_sqr in direction_list:
                preceeding_sqrs = []
                for sqr in direction_list:
                    if sqr == e_sqr: break
                    preceeding_sqrs.append(sqr)
        #print('QRB_SPECIAL_MOVES FUNC')#
        #print('Proposed move:', s_sqr, '->', e_sqr)
        #print('Preceeding squares:')#
        #print(preceeding_sqrs)#
        #print('Objects on preceeding square:')
        # To Pass: all squares preceeding the end square are empty
        for number in preceeding_sqrs:
            preceeding_square = self.num_to_piece_obj(number)
            #print(preceeding_square)
            if preceeding_square: move_permitted = False

        return move_permitted


    def P_special_rules(self, s_sqr, e_sqr):
        move_permitted = True
        piece = self.num_to_piece_obj(s_sqr)

        piece_on_end_sqr = False
        if self.num_to_piece_obj(e_sqr):
            piece_being_captured = self.num_to_piece_obj(e_sqr)
            piece_on_end_sqr = True

        # determine whether the pawn intends to move straight or diagonally
        piece.get_moves()
        for direction in piece.legal_moves:
            direction_list = piece.legal_moves[direction]
            if e_sqr in direction_list:
                if direction in ['North', 'South']:
                    moving_straight   = True
                    moving_diagonally = False
                if direction in ['Northeast', 'Northwest', 'Southeast', 'Southwest']:
                    moving_straight   = False
                    moving_diagonally = True

        # apply special rules in the case that the pawn wants to move straight
        if moving_straight:
            if piece_on_end_sqr:
                move_permitted = False
                return move_permitted

            # determine if wants to move one or two squares
            if e_sqr in [s_sqr - 8, s_sqr + 8]:
                moving_1_sqr  = True
                moving_2_sqrs = False
            if e_sqr in [s_sqr - 16, s_sqr + 16]:
                moving_1_sqr  = False
                moving_2_sqrs = True

            # if moving 1 square
            if moving_1_sqr:

                # determine if the move is a promotion
                white_promotion = False
                black_promotion = False
                if piece.color == 'white' and e_sqr in [1, 2, 3, 4, 5, 6, 7, 8]:
                    white_promotion = True
                if piece.color == 'black' and e_sqr in [57, 58, 59, 60, 61, 62, 63, 64]:
                    black_promotion = True

                # carry out promotion logic
                if white_promotion or black_promotion:
                    #row = self.num_to_coords(s_sqr)[0]
                    #col = self.num_to_coords(s_sqr)[1]
                    #self.internal_board[row][col] = None #wipe the pawn
                    if white_promotion:
                        move_permitted = 'white_promotion'
                        return move_permitted
                        #e_sqr_row = row - 1
                        #self.internal_board[e_sqr_row][col] = pieces.Queen('white', e_sqr) #add queen at end square
                    if black_promotion:
                        move_permitted = 'black_promotion'
                        return move_permitted
                        #e_sqr_row = row + 1
                        #self.internal_board[e_sqr_row][col] = pieces.Queen('black', e_sqr) #add queen at end square
                
                # if not a promotion, make a normal move
                else:
                    return move_permitted

            # if moving 2 squares
            if moving_2_sqrs:
                if piece.moved:
                    move_permitted = False
                    return move_permitted
                elif piece.color == 'white' and self.num_to_piece_obj(e_sqr+8):
                    move_permitted = False
                    return move_permitted
                elif piece.color == 'black' and self.num_to_piece_obj(e_sqr-8):
                    move_permitted = False
                    return move_permitted
                else:
                    move_permitted = 'two_square_move'
                    return move_permitted
        
        # apply special rules in the case that the pawn wants to move diagonally
        elif moving_diagonally:

            # check if making an en passant move
            left_en_passant  = False
            right_en_passant = False
            #if there's a pawn on left or right of our pawn
            pawn_left  = False
            pawn_right = False
            left_sqr  = s_sqr - 1
            right_sqr = s_sqr + 1
            left_piece  = self.num_to_piece_obj(left_sqr)
            right_piece = self.num_to_piece_obj(right_sqr)

            if left_piece and left_piece.piece_type == 'pawn':
                pawn_left = True

            if right_piece and right_piece.piece_type == 'pawn':
                pawn_right = True

            # if the pawn on the side is able to be en_passanted & is of opposite color
            if pawn_left and left_piece.en_passant_data['is_en_passantable'] and left_piece.color != piece.color:
                left_en_passant = True

            if pawn_right and right_piece.en_passant_data['is_en_passantable'] and right_piece.color != piece.color:
                right_en_passant = True

          #ACTUALLY CARRY OUT EN PASSANT MOVE
            if left_en_passant or right_en_passant:
                if left_en_passant:
                    #just delete neighboring pawn and return make_move as true (then the pawn will move diagonally)
                    #row = self.num_to_coords(left_sqr)[0]
                    #col = self.num_to_coords(left_sqr)[1]
                    #self.internal_board[row][col] = None #wipe the pawn
                    move_permitted = 'left_en_passant'
                    return move_permitted

                elif right_en_passant:
                    #just delete neighboring pawn and return make_move as true (then the pawn will move diagonally)
                    #row = self.num_to_coords(right_sqr)[0]
                    #col = self.num_to_coords(right_sqr)[1]
                    #self.internal_board[row][col] = None #wipe the pawn
                    move_permitted = 'right_en_passant'
                    return move_permitted

            else:
                # pass move as long as square its moving to has a piece of opposite color
                if not piece_on_end_sqr:
                    move_permitted = False
                    return move_permitted
                elif piece_on_end_sqr and piece.color == piece_being_captured.color:
                    move_permitted = False
                    return move_permitted

                # determine if move is a promotion
                white_promotion = False
                black_promotion = False
                if piece.color == 'white' and e_sqr in [1, 2, 3, 4, 5, 6, 7, 8]:
                    white_promotion = True
                if piece.color == 'black' and e_sqr in [57, 58, 59, 60, 61, 62, 63, 64]:
                    black_promotion = True

                if white_promotion or black_promotion:
                    #row = self.num_to_coords(s_sqr)[0]
                    #col = self.num_to_coords(s_sqr)[1]
                    #self.internal_board[row][col] = None #wipe the pawn
                    if white_promotion:
                        move_permitted = 'white_promotion'
                        return move_permitted
                        #e_sqr_row = row - 1
                        #self.internal_board[e_sqr_row][col] = pieces.Queen('white', e_sqr) #add queen at end square
                    if black_promotion:
                        move_permitted = 'black_promotion'
                        return move_permitted
                        #e_sqr_row = row + 1
                        #self.internal_board[e_sqr_row][col] = pieces.Queen('black', e_sqr) #add queen at end square

                else:
                    return move_permitted


    def K_special_rules(self, s_sqr, e_sqr):
        move_permitted = True
        piece = self.num_to_piece_obj(s_sqr)

        piece_on_end_sqr = False
        if self.num_to_piece_obj(e_sqr):
            piece_being_captured = self.num_to_piece_obj(e_sqr)
            piece_on_end_sqr = True

        # determine if castling kingside or queenside
        kingside = False
        queenside = False
        if e_sqr == s_sqr + 2:
            kingside  = True
        elif e_sqr == s_sqr - 2:
            queenside = True

        if kingside:
            # check if all squares are clear between king and rook
            all_sqrs_clear = True
            for i in range(1, 3): # check if all sqrs between king and rook are empty
                in_between_square = self.num_to_piece_obj(s_sqr + i)
                if in_between_square: 
                    all_sqrs_clear = False
            
            if not all_sqrs_clear:
                move_permitted = False
                return move_permitted
            
            # make sure theres a rook in the corner
            rook_sqr = s_sqr + 3
            if rook_sqr in [64, 8]:
                rook = self.num_to_piece_obj(rook_sqr)
            else: rook = None
            rook_exists = False
            if rook and rook.piece_type == 'rook': rook_exists = True

            if not rook_exists:
                move_permitted = False
                return move_permitted
            
            # make sure neither the king or the rook have previously moved
            none_have_moved = True
            if piece.moved or rook.moved:
                none_have_moved = False

            if not none_have_moved:
                move_permitted = False
                return move_permitted

            # make sure your not in check
            in_check = False
            if self.check_board_for_checks(piece.color):
                in_check = True
            
            if in_check:
                move_permitted = False
                return move_permitted

            # make sure ur not castling through check
            castling_thru_check = False
            self.make_move(piece.pos, piece.pos + 1, False)
            if self.check_board_for_checks(piece.color):
                castling_thru_check = True
            self.make_move(piece.pos, piece.pos + 1, False)
            if self.check_board_for_checks(piece.color):
                castling_thru_check = True
            self.make_move(piece.pos, piece.pos - 2, False)
    

            if castling_thru_check:
                move_permitted = False
                return move_permitted


            # only move the rook
            if all_sqrs_clear and rook_exists and none_have_moved:
                move_permitted = 'kingside_castle'
                #self.make_move(rook_sqr, rook_sqr-2)
                return move_permitted

        elif queenside:
            # check if all squares are clear between king and rook
            all_sqrs_clear = True
            for i in range(1, 4): # check if all sqrs between king and rook are empty
                in_between_square = self.num_to_piece_obj(s_sqr - i)
                if in_between_square: 
                    all_sqrs_clear = False

            if not all_sqrs_clear:
                move_permitted = False
                return move_permitted
            
            # make sure theres a rook in the corner
            rook_sqr = s_sqr - 4
            if rook_sqr in [1, 57]:
                rook = self.num_to_piece_obj(rook_sqr)
            else: rook = None
            rook_exists = False
            if rook and rook.piece_type == 'rook': rook_exists = True

            if not rook_exists:
                move_permitted = False
                return move_permitted
            
            # make sure neither the king or the rook have previously moved
            none_have_moved = True
            if piece.moved or rook.moved:
                none_have_moved = False

            if not none_have_moved:
                move_permitted = False
                return move_permitted

            # make sure your not in check
            in_check = False
            if self.check_board_for_checks(piece.color):
                in_check = True
            
            if in_check:
                move_permitted = False
                return move_permitted

            # make sure your not castling thru a checked square
            # make sure ur not castling through check
            castling_thru_check = False
            self.make_move(piece.pos, piece.pos - 1, False)
            if self.check_board_for_checks(piece.color):
                castling_thru_check = True
            self.make_move(piece.pos, piece.pos - 1, False)
            if self.check_board_for_checks(piece.color):
                castling_thru_check = True
            self.make_move(piece.pos, piece.pos + 2, False)
    

            if castling_thru_check:
                move_permitted = False
                return move_permitted

            
            # only move the rook
            if all_sqrs_clear and rook_exists and none_have_moved:
                move_permitted = 'queenside_castle'
                #self.make_move(rook_sqr, rook_sqr+3)
                return move_permitted

            # only move the rook, then return True, makemove will take care of the king
            
        else:
            return move_permitted

    
    def check_board_for_checks(self, color): 
        '''looks at entire internal board to see if king is in check or not'''
        in_check = False
        #find the king
        for i in range(1, 65):
            piece = self.num_to_piece_obj(i)
            if piece and piece.piece_type == 'king' and piece.color == color:
                potentially_checking = []
                king_sqr = i
                king = self.num_to_piece_obj(i)
                break
        #check if king is in the legal_moves of any OPP COLOR pieces, if so add them to potentially checking list
        for i in range(1, 65):
            piece = self.num_to_piece_obj(i)
            if piece and piece.color != king.color:
                piece.get_moves()
                legal_list = self.dic_w_lists_to_list(piece.legal_moves)
                if king_sqr in legal_list:
                    potentially_checking.append(piece)
        
        #not in check if there are no potentially checking pieces
        if not potentially_checking:
            return in_check

        #check if any potentially checking piece can actually take the king
        for potentially_checking_piece in potentially_checking:
            if potentially_checking_piece.piece_type == 'knight':
                in_check = True
                return in_check

            elif potentially_checking_piece.piece_type in ['queen', 'rook', 'bishop']:
                if self.QRB_special_rules(potentially_checking_piece.pos, king_sqr):
                    in_check = True
                    return in_check

            elif potentially_checking_piece.piece_type == 'king':
                if self.K_special_rules(potentially_checking_piece.pos, king_sqr) == True:
                    in_check = True
                    return in_check

            elif potentially_checking_piece.piece_type == 'pawn':
                if self.P_special_rules(potentially_checking_piece.pos, king_sqr) in [True, 'white_promotion',  'black_promotion']:
                    in_check = True
                    return in_check
        return in_check


    def get_all_moves(self, color):
        master_list = []
        for i in range(1, 65):
            piece = self.num_to_piece_obj(i)
            if piece and piece.color == color:
                piece.get_moves()
                legal_list = self.dic_w_lists_to_list(piece.legal_moves)
                #print(piece.color, piece.piece_type, piece.pos)#
                #print(legal_list)
                if piece.piece_type == 'king':
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move) and self.K_special_rules(piece.pos, move) in [True, 'kingside_castle', 'queenside_castle']:
                            if self.K_special_rules(piece.pos, move) == True:
                                end_sqr_piece = self.num_to_piece_obj(move)
                                piece_pos = piece.pos
                                self.make_move(piece_pos, move, False)
                                if self.check_board_for_checks(color):
                                    self.make_move(move, piece_pos, False)
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    self.make_move(move, piece_pos, False)
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)

                            elif self.K_special_rules(piece.pos, move) == 'kingside_castle':
                                piece_pos = piece.pos
                                self.make_unmake_special_moves([piece_pos, move], 'kingside_castle', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'kingside_castle', color, 'unmaking')
                                    
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'kingside_castle', color, 'unmaking')
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)

                            elif self.K_special_rules(piece.pos, move) == 'queenside_castle':
                                piece_pos = piece.pos
                                self.make_unmake_special_moves([piece_pos, move], 'queenside_castle', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'queenside_castle', color, 'unmaking')
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'queenside_castle', color, 'unmaking')
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)
                            
                elif piece.piece_type in ['queen', 'rook', 'bishop']:
                    piece_pos = piece.pos
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move) and self.QRB_special_rules(piece.pos, move) in [True]:
                            end_sqr_piece = self.num_to_piece_obj(move)
                            self.make_move(piece_pos, move, False)
                            if self.check_board_for_checks(color):
                                self.make_move(move, piece_pos, False)
                                if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                            else:
                                self.make_move(move, piece_pos, False)
                                if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                move_notation = str(piece_pos) + '->' + str(move)
                                master_list.append(move_notation)
                
                elif piece.piece_type == 'knight':
                    piece_pos = piece.pos
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move):
                            end_sqr_piece = self.num_to_piece_obj(move)
                            self.make_move(piece_pos, move, False)
                            if self.check_board_for_checks(color):
                                self.make_move(move, piece_pos, False)
                                if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                            else:
                                self.make_move(move, piece_pos, False)
                                if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                move_notation = str(piece_pos) + '->' + str(move)
                                master_list.append(move_notation)

                elif piece.piece_type == 'pawn':
                    piece_pos = piece.pos
                    for move in legal_list:
                        if self.basic_rules(piece.pos, move) and self.P_special_rules(piece.pos, move) in [True, 'two_square_move', 'white_promotion', 'black_promotion', 'left_en_passant', 'right_en_passant']:
                            if self.P_special_rules(piece.pos, move) == True:
                                end_sqr_piece = self.num_to_piece_obj(move)
                                self.make_move(piece_pos, move, False)
                                if self.check_board_for_checks(color):
                                    self.make_move(move, piece_pos, False)
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    self.make_move(move, piece_pos, False)
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)
                            
                            elif self.P_special_rules(piece.pos, move) == 'two_square_move':
                                self.make_unmake_special_moves([piece_pos, move], 'two_square_move', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'two_square_move', color, 'unmaking')
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'two_square_move', color, 'unmaking')
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)

                            elif self.P_special_rules(piece.pos, move) == 'white_promotion':
                                end_sqr_piece = self.num_to_piece_obj(move)
                                self.make_unmake_special_moves([piece_pos, move], 'white_promotion', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'white_promotion', color, 'unmaking')
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'white_promotion', color, 'unmaking')
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)

                            elif self.P_special_rules(piece.pos, move) == 'black_promotion':
                                end_sqr_piece = self.num_to_piece_obj(move)
                                self.make_unmake_special_moves([piece_pos, move], 'black_promotion', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'black_promotion', color, 'unmaking')
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'black_promotion', color, 'unmaking')
                                    if end_sqr_piece:
                                        row = self.num_to_coords(move)[0]
                                        col = self.num_to_coords(move)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)

                            elif self.P_special_rules(piece.pos, move) == 'left_en_passant':
                                self.make_unmake_special_moves([piece_pos, move], 'left_en_passant', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'left_en_passant', color, 'unmaking')
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'left_en_passant', color, 'unmaking')
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)

                            elif self.P_special_rules(piece.pos, move) == 'right_en_passant':
                                self.make_unmake_special_moves([piece_pos, move], 'right_en_passant', color, 'making')
                                if self.check_board_for_checks(color):
                                    self.make_unmake_special_moves([piece_pos, move], 'right_en_passant', color, 'unmaking')
                                else:
                                    self.make_unmake_special_moves([piece_pos, move], 'right_en_passant', color, 'unmaking')
                                    move_notation = str(piece_pos) + '->' + str(move)
                                    master_list.append(move_notation)
                                              
        return master_list


    def make_unmake_special_moves(self, start_and_end_squares, special_move_type, piece_color, making_or_unmaking):
        start_sqr = int(start_and_end_squares[0])
        end_sqr = int(start_and_end_squares[1])
        piece = self.num_to_piece_obj(start_sqr)

        if special_move_type == 'two_square_move':
            if making_or_unmaking == 'making':
                piece.moved = True
                self.make_move(start_sqr, end_sqr, False)
                
            elif making_or_unmaking == 'unmaking':
                self.num_to_piece_obj(end_sqr).moved = False
                self.make_move(end_sqr, start_sqr, False)
                #piece.moved = False                

        elif special_move_type in ['white_promotion', 'black_promotion']:
            row = self.num_to_coords(start_sqr)[0]
            col = self.num_to_coords(start_sqr)[1]
            row2 = self.num_to_coords(end_sqr)[0]
            col2 = self.num_to_coords(end_sqr)[1]
            if making_or_unmaking == 'making':
                self.internal_board[row][col] = None                                 # wipe pawn
                self.internal_board[row2][col2] = pieces.Queen(piece_color, end_sqr) # add queen

            if making_or_unmaking == 'unmaking':
                self.internal_board[row][col] = pieces.Pawn(piece_color, start_sqr)  # add pawn
                self.internal_board[row2][col2] = None                               # wipe queen
                self.internal_board[row][col].moved = True

        elif special_move_type == 'left_en_passant':
            left_sqr  = start_sqr - 1
            row = self.num_to_coords(left_sqr)[0]
            col = self.num_to_coords(left_sqr)[1]
            left_pawn = self.num_to_piece_obj(left_sqr)
            if piece_color == 'white': opp_color = 'black'
            if piece_color == 'black': opp_color = 'white'
            if making_or_unmaking == 'making':
                self.internal_board[row][col] = None                            # wipe pawn
                self.make_move(start_sqr, end_sqr)                              # move pawn diagonally

            if making_or_unmaking == 'unmaking':
                self.make_move(end_sqr, start_sqr)                              # move pawn back diagonally
                self.internal_board[row][col] = left_pawn                       # add pawn back

        elif special_move_type == 'right_en_passant':
            right_sqr  = start_sqr + 1
            row = self.num_to_coords(right_sqr)[0]
            col = self.num_to_coords(right_sqr)[1]
            right_pawn = self.num_to_piece_obj(right_sqr)
            if piece_color == 'white': opp_color = 'black'
            if piece_color == 'black': opp_color = 'white'
            if making_or_unmaking == 'making':
                self.internal_board[row][col] = None                            # wipe pawn
                self.make_move(start_sqr, end_sqr)                              # move pawn diagonally

            if making_or_unmaking == 'unmaking':
                self.make_move(end_sqr, start_sqr)                              # move pawn back diagonally
                self.internal_board[row][col] = right_pawn

        elif special_move_type == 'kingside_castle':
            if making_or_unmaking == 'making':
                self.make_move(start_sqr, end_sqr, False)        # move king
                self.make_move(start_sqr+3, start_sqr+1, False)  # move rook

            if making_or_unmaking == 'unmaking':
                self.make_move(end_sqr, start_sqr, False)        # move king back
                self.make_move(start_sqr+1, start_sqr+3, False)  # move rook back

        elif special_move_type == 'queenside_castle':
            if making_or_unmaking == 'making':
                self.make_move(start_sqr, end_sqr, False)        # move king
                self.make_move(start_sqr-4, start_sqr-1, False)  # move rook

            if making_or_unmaking == 'unmaking':
                self.make_move(end_sqr, start_sqr, False)        # move king
                self.make_move(start_sqr-1, start_sqr-4, False)  # move rook

        #NONE OF THESE MARK THE PIECES AS MOVED, EVEN IF DONE AND NOT UNDONE

    
    def parse_move(self, arrow_move):
        two_square = arrow_move.split('->')
        for i in range(2):
            two_square[i] = int(two_square[i])
        return two_square


    '''def perft(depth):
        if depth == 1:
            return len(self.get_all_moves())
        elif depth > 1:
            count = 0
            for move in move_list:
                #make move
                count += self.perft(depth-1)
                #unmake move
            return count
        else:
            return 1'''

    
    def perft(self, to_move, depth):
        if to_move == 'white': opp_col = 'black'
        if to_move == 'black': opp_col = 'white'

        move_list = self.get_all_moves(to_move)
        new_move_list = []
        for move in move_list:
            move = self.parse_move(move)
            new_move_list.append(move)
        
        if depth == 1:
            return len(move_list)
        elif depth > 1:
            count = 0
            for move in new_move_list:
                start_sqr = int(move[0])
                end_sqr   = int(move[1])
                piece = self.num_to_piece_obj(start_sqr)

                piece_on_end_sqr = False
                if self.num_to_piece_obj(end_sqr):
                    piece_on_end_sqr = True
                    end_piece = self.num_to_piece_obj(end_sqr)

                    end_piece_coords = self.num_to_coords(end_sqr)
                    end_row = end_piece_coords[0]
                    end_col = end_piece_coords[1]


                move_type = True
                if piece.piece_type == 'pawn':
                    if not self.num_to_piece_obj(end_sqr):
                        if end_sqr - start_sqr in [-9, 7]:
                            move_type = 'right_en_passant'
                        elif end_sqr - start_sqr in [9, -7]:
                            move_type = 'left_en_passant'
                elif piece.piece_type == 'king':
                    if end_sqr - start_sqr == 2:
                        move_type = 'kingside_castle'
                    elif end_sqr - start_sqr == -2:
                        move_type = 'queenside_castle'
                
                if move_type in ['right_en_passant', 'left_en_passant', 'kingside_castle', 'queenside_castle']:

                    prev_board = deepcopy(self.internal_board)
                    self.make_unmake_special_moves(move, move_type, to_move, 'making')
                    piece.moved = True
                    count += self.perft(opp_col, depth-1)
                    self.internal_board = prev_board
                    
                
                elif move_type == True:
                    prev_board = deepcopy(self.internal_board)
                    self.make_move(start_sqr, end_sqr, True)
                    count += self.perft(opp_col, depth-1)
                    if depth == 3:
                        pass
                        #print(f'{self.num_to_chess_notation(start_sqr)}{self.num_to_chess_notation(end_sqr)}: {self.perft(opp_col, depth-1)}')
                    if depth == 2:
                        pass
                        #print(f'    {self.num_to_chess_notation(start_sqr)}{self.num_to_chess_notation(end_sqr)}: {self.perft(opp_col, depth-1)}')
                    self.internal_board = prev_board
            return count
        else:
            print('returned 1')
            return 1

    
    def num_to_chess_notation(self, num):
        num = int(num)
        row = self.num_to_coords(num)[0]
        col = self.num_to_coords(num)[1]

        letter = 'abcdefgh'[col]
        num = '87654321'[row]

        final = letter + num
        return final


    def final_make_move(self, start, end, color):
        # doesnt't check cuz moves passed in here are pre-checked
        piece = self.num_to_piece_obj(start)

        move_type = True
        if piece.piece_type == 'pawn':
            if end in [1, 2, 3, 4, 5, 6, 7, 8]:
                move_type = 'white_promotion'
            elif end in [57, 58, 59, 60, 61, 62, 63, 64]:
                move_type = 'white_promotion'

            if not self.num_to_piece_obj(end):
                if end - start in [-9, 7]:
                    move_type = 'right_en_passant'
                elif end - start in [9, -7]:
                    move_type = 'left_en_passant'
        elif piece.piece_type == 'king':
            if end - start == 2:
                move_type = 'kingside_castle'
            elif end - start == -2:
                move_type = 'queenside_castle'

        if move_type in ['right_en_passant', 'left_en_passant', 'kingside_castle', 'queenside_castle', 'white_promotion', 'black_promotion']:
            self.make_unmake_special_moves([start, end], move_type, color, 'making')

        elif move_type == True:
            self.make_move(start, end, True)


    def terminal_detect(self, color):
        if color == 'white': opp_col = 'black'
        elif color == 'black': opp_col = 'white'

        termination_type = False
        if not self.get_all_moves(color):
            if self.check_board_for_checks(color):
                termination_type = f'checkmate, {opp_col} wins'
            else:
                termination_type = 'draw by stalemate'

        
        # Insuficcient Mating Material
        white_pieces = {'king': 0, 'queen': 0, 'rook': 0, 'bishop': 0, 'knight': 0, 'pawn': 0}
        black_pieces = {'king': 0, 'queen': 0, 'rook': 0, 'bishop': 0, 'knight': 0, 'pawn': 0}

        for i in range(1, 65):
            piece = self.num_to_piece_obj(i)
            if piece:
                if piece.color == 'white':
                    white_pieces[piece.piece_type] += 1
                elif piece.color == 'black':
                    black_pieces[piece.piece_type] += 1
        
        white_condition = False
        black_condition = False

        sole_king = '100000'
        king_bishop = '100100'
        king_knight = '100010'

        white_binary = ''
        for p in ['king', 'queen', 'rook', 'bishop', 'knight', 'pawn']:
            white_binary += str(white_pieces[p])

        black_binary = ''
        for p in ['king', 'queen', 'rook', 'bishop', 'knight', 'pawn']:
            black_binary += str(black_pieces[p])

        white_insufficient = False
        if white_binary in ['100000', '100100', '100010']:
            white_insufficient = True

        black_insufficient = False
        if black_binary in ['100000', '100100', '100010']:
            black_insufficient = True

        if white_insufficient and black_insufficient:
            termination_type = 'draw by insuficcient material'
            return termination_type


        pieces = 0
        for i in range(1, 65):
            if self.num_to_piece_obj(i):
                pieces += 1
        if pieces <= 2:
            return True
        return termination_type


    def board_to_FEN(self):
        FEN_string = ''
        white_piece_to_letter = {'king': 'K', 'queen': 'Q', 'rook': 'R', 'bishop': 'B', 'knight': 'N', 'pawn': 'P'}
        black_piece_to_letter = {'king': 'k', 'queen': 'q', 'rook': 'r', 'bishop': 'b', 'knight': 'n', 'pawn': 'p'}

        for row in self.internal_board:
            FEN_row = ''
            count = 0
            row_count = 0
            for piece in row:
                row_count += 1

                if piece:
                    if count != 0:
                        FEN_row += str(count)
                        count = 0

                    if piece.color == 'white':
                        FEN_row += white_piece_to_letter[piece.piece_type]

                    elif piece.color == 'black':
                        FEN_row += black_piece_to_letter[piece.piece_type]
                else:
                    count += 1
                
                if row_count == 8 and count != 0:
                    FEN_row += str(count)
            
            FEN_string += FEN_row
            FEN_string += '/'
        
        FEN_string = FEN_string[:-1]
        return FEN_string


    def game_simul(self):
        move_count = 0
        while True:
            # implement turns
            if move_count % 2 == 0: player_turn = 'white'
            elif move_count % 2 == 1: player_turn = 'black'

            self.update_en_passantables(move_count)
            in_check = self.check_board_for_checks(player_turn) # checks if the player whose turn it is is in check
            all_moves = self.get_all_moves(player_turn) # puts all posssible moves for the side into a list

            # checkmate and stalemate
            if not all_moves: # if there are no possible moves to be made
                if in_check: # if the king is also in check
                    print('CHECKMATE')
                    break
                else:
                    print('STALEMATE')
                    break
            #############################
            #print(len(board.get_all_moves('white')))
            #print(board.get_all_moves('white'))
            #############################
            move = input("Make a move: ") #e2e4
            if move == "quit":
                break
            start_sqr = self.chess_notation_to_num(move[:2])
            end_sqr   = self.chess_notation_to_num(move[2:])

            selected_piece = self.num_to_piece_obj(start_sqr)

            if selected_piece: # checks that theres a piece on the start square
                if selected_piece.color == player_turn: # checks that youre only moving a piece on that player's turn
                    selected_piece.get_moves()
                    if self.basic_rules(start_sqr, end_sqr):
                        if selected_piece.piece_type == 'king':
            
                            if self.K_special_rules(start_sqr, end_sqr) == True:
                                end_sqr_piece = self.num_to_piece_obj(end_sqr)
                                self.make_move(start_sqr, end_sqr, False)
                                if self.check_board_for_checks(player_turn): # if this move puts u in check
                                    self.make_move(end_sqr, start_sqr, False) #undo move
                                    if end_sqr_piece:
                                        row = self.num_to_coords(end_sqr)[0]
                                        col = self.num_to_coords(end_sqr)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    selected_piece.moved = True
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.K_special_rules(start_sqr, end_sqr) == 'kingside_castle':
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'kingside_castle', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'kingside_castle', player_turn, 'unmaking')
                                else:
                                    selected_piece.moved = True                     # mark king as moved
                                    self.num_to_piece_obj(start_sqr+1).moved = True # mark rook as moved
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.K_special_rules(start_sqr, end_sqr) == 'queenside_castle':
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'queenside_castle', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'queenside_castle', player_turn, 'unmaking')
                                else:
                                    selected_piece.moved = True                     # mark king as moved
                                    self.num_to_piece_obj(start_sqr-1).moved = True # mark rook as moved
                                    move_count += 1
                                    self.ASCII_representation()

                        elif selected_piece.piece_type in ['queen', 'rook', 'bishop']:
                            if self.QRB_special_rules(start_sqr, end_sqr):
                                end_sqr_piece = self.num_to_piece_obj(end_sqr)
                                self.make_move(start_sqr, end_sqr)
                                if self.check_board_for_checks(player_turn): # if this move puts u in check
                                    self.make_move(end_sqr, start_sqr) #undo move
                                    if end_sqr_piece:
                                        row = self.num_to_coords(end_sqr)[0]
                                        col = self.num_to_coords(end_sqr)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    move_count += 1
                                    self.ASCII_representation()

                        elif selected_piece.piece_type == 'pawn':
                            if self.P_special_rules(start_sqr, end_sqr) == True:
                                end_sqr_piece = self.num_to_piece_obj(end_sqr)
                                self.make_move(start_sqr, end_sqr)
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo move
                                    self.make_move(end_sqr, start_sqr)
                                    if end_sqr_piece:
                                        row = self.num_to_coords(end_sqr)[0]
                                        col = self.num_to_coords(end_sqr)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.P_special_rules(start_sqr, end_sqr) == 'two_square_move':
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'two_square_move', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'two_square_move', player_turn, 'unmaking')
                                else:
                                    selected_piece.moved = True
                                    piece.en_passant_data['is_en_passantable'] = True
                                    piece.en_passant_data['move_num'] = move_count
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.P_special_rules(start_sqr, end_sqr) == 'white_promotion':
                                end_sqr_piece = self.num_to_piece_obj(end_sqr)
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'white_promotion', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'white_promotion', player_turn, 'unmaking')
                                    if end_sqr_piece:
                                        row = self.num_to_coords(end_sqr)[0]
                                        col = self.num_to_coords(end_sqr)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.P_special_rules(start_sqr, end_sqr) == 'black_promotion':
                                end_sqr_piece = self.num_to_piece_obj(end_sqr)
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'black_promotion', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'black_promotion', player_turn, 'unmaking')
                                    if end_sqr_piece:
                                        row = self.num_to_coords(end_sqr)[0]
                                        col = self.num_to_coords(end_sqr)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                                else:
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.P_special_rules(start_sqr, end_sqr) == 'left_en_passant':
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'left_en_passant', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'left_en_passant', player_turn, 'unmaking')
                                else:
                                    selected_piece.moved = True
                                    move_count += 1
                                    self.ASCII_representation()

                            elif self.P_special_rules(start_sqr, end_sqr) == 'right_en_passant':
                                self.make_unmake_special_moves([start_sqr, end_sqr], 'right_en_passant', player_turn, 'making')
                                if self.check_board_for_checks(player_turn): # if this move puts u in check undo it
                                    self.make_unmake_special_moves([start_sqr, end_sqr], 'right_en_passant', player_turn, 'unmaking')
                                else:
                                    selected_piece.moved = True
                                    move_count += 1
                                    self.ASCII_representation()

                        else:
                            end_sqr_piece = self.num_to_piece_obj(end_sqr)
                            self.make_move(start_sqr, end_sqr)
                            if self.check_board_for_checks(player_turn): # if this move puts u in check undo move
                                self.make_move(end_sqr, start_sqr)
                                if end_sqr_piece:
                                        row = self.num_to_coords(end_sqr)[0]
                                        col = self.num_to_coords(end_sqr)[1]
                                        self.internal_board[row][col] = end_sqr_piece # put piece back
                            else:
                                move_count += 1
                                self.ASCII_representation()




#board = Board()
#board.set_board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')
#board.set_board('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8')
#board.set_board('rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R')
#board.set_board('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R')
#board.set_board('2r5/6kp/p4n2/pNpP2P1/P1n5/r2B4/5N1P/2bK3R')
#board.set_board('rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R')
#board.set_board('r3k2r/8/6B1/8/8/6b1/8/R3K2R')
#board.set_board('r1bqkbnr/pppppppp/2n5/8/8/P7/1PPPPPPP/RNBQKBNR')
#board.set_board('rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R')
#board.set_board('8/8/3R4/8/3K4/5k2/8/8')


#board.ASCII_representation()
#print(board.perft('white', 6))

#board.game_simul()
#all_moves = board.get_all_moves('white')
#print(len(all_moves))
#print(all_moves)
#print(board.P_special_rules(56, 40))



#piece = pieces.King('white', 61)
#piece.get_moves()
#moves_list = board.dic_w_lists_to_list(piece.legal_moves)
#board.set_x_board(moves_list) #to set xboard need to conver legalmoved to list using function
#board.ASCII_x_board()
#print(moves_list)