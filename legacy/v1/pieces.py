import pygame
import variables as v
#import board
#import main

class Pieces():

    def __init__(self, board_pos):
        self.board_pos = board_pos
"""
#############################################

class King(Pieces):

    def __init__(self, board_pos):
        super().__init__(board_pos)

    def get_legal_moves():
        pass

#############################################

class Queen(Pieces):

    def __init__(self, board_pos):
        super().__init__(board_pos)

    def get_legal_moves():
        pass

#############################################
"""

class Rook(Pieces):

    def __init__(self, board_pos):
        super().__init__(board_pos)

    def get_legal_moves(self):
        import board
        import main
        legal_move_sqrs = []
        col_count = 0

        for col_let in 'abcdefgh':
            if col_let == self.board_pos[0]:
                break
            col_count +=1
        
        # GET EAST MOVES
        east_moves = [] # can remove later
        east_sqrs_added = 0
        east_col_count = col_count
        while True:
            east_col_count +=  1

            if east_col_count == 7 and east_sqrs_added == 0:
                break
            if east_col_count == 8:
                break
            
            east_moves.append(main.gameboard.internal_board['abcdefgh'[east_col_count]][int(self.board_pos[1])])
            east_sqrs_added += 1

        
        # GET WEST MOVES
        west_moves = [] # can remove later
        west_sqrs_added = 0
        west_col_count = col_count
        while True:
            west_col_count -=  1

            if west_col_count-1 == -1 and west_sqrs_added == 0:
                break
            if west_col_count-1 == 0:
                break
            
            west_moves.append(main.gameboard.internal_board['abcdefgh'[west_col_count]][int(self.board_pos[1])])
            west_sqrs_added += 1
        

        # GET NORTH MOVES
        north_moves = [] # can remove later
        north_sqrs_added = 0
        north_row_count = int(self.board_pos[1])
        while True:
            north_row_count +=  1

            if north_row_count == 8 and north_sqrs_added == 0:
                break
            if north_row_count == 9:
                break

            north_moves.append(main.gameboard.internal_board[self.board_pos[0]][north_row_count])
            north_sqrs_added += 1


        # GET SOUTH MOVES
        south_moves = [] # can remove later
        south_sqrs_added = 0
        south_row_count = int(self.board_pos[1])
        while True:
            south_row_count -=  1

            if south_row_count == 1 and south_sqrs_added == 0:
                break
            if south_row_count == 0:
                break

            south_moves.append(main.gameboard.internal_board[self.board_pos[0]][south_row_count])
            south_sqrs_added += 1

        # COMPILE ALL MOVES
        legal_move_sqrs.extend(east_moves)
        legal_move_sqrs.extend(west_moves)
        legal_move_sqrs.extend(north_moves)
        legal_move_sqrs.extend(south_moves)

        return legal_move_sqrs


"""
#############################################


class Bishop(Pieces):

    def __init__(self, self.board_pos):
        super().__init__(self.board_pos)

    def get_legal_moves():
        pass

#############################################


class Knight(Pieces):

    def __init__(self, self.board_pos):
        super().__init__(self.board_pos)

    def get_legal_moves():
        pass

#############################################


class Pawn(Pieces):

    def __init__(self, self.board_pos):
        super().__init__(self.board_pos)

    def get_legal_moves():
        pass
"""