import pygame
import revision_variables as v
import gameboard_container

# gotta import a bunch of stuff: ssquares, and board (check if its a problem)

class Pieces:
    def __init__(self, color, square_num, display_dimensions = (100, 100)):
        self.color                = color
        self.square_num           = square_num
        self.display_dimensions   = display_dimensions

#(x-7) (x+1) (x+9)
#(x-8)   X   (x+8)
#(x-9) (x-1) (x+7)

    def queen_rook_bishop_moves(self, directions):
        direction_nums = []
        for direction in directions:
            if direction == 'North':     direction_nums.append(1)
            if direction == 'East':      direction_nums.append(8)
            if direction == 'South':     direction_nums.append(-1)
            if direction == 'West':      direction_nums.append(-8)
            if direction == 'Northeast': direction_nums.append(9)
            if direction == 'Southeast': direction_nums.append(7)
            if direction == 'Southwest': direction_nums.append(-9)
            if direction == 'Northwest': direction_nums.append(-7)
        legal_moves = []
        for dir_num in direction_nums:
            square_counter = int(self.square_num)
            while True:
                if gameboard_container.gameboard.get_square(num = square_counter + dir_num):
                    if gameboard_container.gameboard.get_square(num = square_counter + dir_num).piece_obj:
                        if gameboard_container.gameboard.get_square(num = square_counter + dir_num).piece_obj.color == square.piece_obj.color:
                            break
                        if gameboard_container.gameboard.get_square(num = square_counter + dir_num).piece_obj.color != square.piece_obj.color:
                            legal_moves.append(gameboard_container.gameboard.get_square(num = square_counter + dir_num))
                            break
                    if gameboard_container.gameboard.get_square(num = square_counter + dir_num).piece_obj == None:
                        legal_moves.append(gameboard_container.gameboard.get_square(num = square_counter + dir_num))
                        square_counter += dir_num

        return legal_moves

    
    def set_pieces(self, fen_string):
        # takes in fen notation and loops thorugh it to look for pieces
        # then adds the pieces to the internal board representation
        rows = reversed(fen_string.split('/')) # reveses FEN string because FEN string is written to work from top left down, but board representation is from bottom left up
        row_count = 0
        for row in rows:
            col_count = 0
            for item in row:
                if item in '12345678': # if the item is a number, that's how many blank squares there are before the next piece in the row
                    col_count += (int(item) - 1) # add the item to the count (but subtract 1 cuz an extra 1 is added at the bottom)
                elif item in 'KQRBNPkqrbnp':
                    if item == 'K'  : gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = king.King('white', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count])) # if we want to add custom piece dimensions, we need to first be abe to blit the CENTER of the piece texture to the CENTER of the pygame rect
                    elif item == 'Q': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = queen.Queen('white', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'R': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = rook.Rook('white', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'B': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = bishop.Bishop('white', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'N': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = knight.Knight('white', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'P': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = pawn.Pawn('white', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'k': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = king.King('black', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'q': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = queen.Queen('black', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'r': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = rook.Rook('black', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'b': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = bishop.Bishop('black', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'n': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = knight.Knight('black', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'p': gameboard_container.gameboard.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = pawn.Pawn('black', gameboard_container.gameboard.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                col_count += 1
            row_count += 1
                    


#when parentheses for class?