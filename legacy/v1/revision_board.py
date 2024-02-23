import pygame
import revision_variables as v
#import king, queen, rook, bishop, knight, pawn
import squares

class Board:
    # A singleton class to manage everthing to do with the board:
    # internal representaion, digital display, piece positions, etc.

    def __init__(self, # sets all the variables to defaults from the variables module
                 screen           = v.screen,
                 white_color      = v.white_color,
                 black_color      = v.black_color,
                 piece_textures   = v.piece_textures):

        # I can now use all of these variables without getting them as input in functions
        self.screen           = screen
        self.white_color      = white_color
        self.black_color      = black_color
        self.piece_textures   = piece_textures

        self.internal_board   = {}
        # creates a 3x nested dictionary to represent the board internaly
        # coll(letter) --> row(number) -->  square(pygame rect & piece object)
        rect_left    = 0            # initial coordinates for left side of rect
        w_h          = (100, 100)   # dimensions of rectangle (width, height)
        square_count = 1
        for col in 'abcdefgh':
            rect_top    = 700    # initial coordinates for top side of rect (700 becuase rect is 100 tall)
            self.internal_board[col] = {}     # defning an empty dictionary as a value for each collum
            for row in '12345678':
                # makes a new instance of the square class to represent each square on the board
                # the square class stores color (for display), pygame Rect objetcs (for display), and piece objects (for internal + display)
                self.internal_board[col][row] = squares.Square(pygame_rect = pygame.Rect((rect_left, rect_top), w_h), piece_obj = None, color = self.determine_color(col, row), number = square_count)
                square_count += 1
                rect_top -= 100 # subtracts 100 from the top coord of the sqr so that the next sqr is 100 px higher up
            rect_left += 100 # adds 100 to the coord of the left side of the sqr so that the nect col is 100 px to the right of the previous one

    
    def get_square(self, col = 'a', row = '1', num = None):
        # simple way to retrieve square objects from the internal board
        # makes it wasy to pivot the structure of the internal representation if needed
        # 2 different ways of accesign squares ---> by col,row: get_square(col='a', row='1') and by num: get_square(num=17)
        if num == None:
            return self.internal_board[col][row]
        else:
            for col in 'abcdefgh':
                for row in '12345678':
                    if self.internal_board[col][row].number == num:
                        return self.internal_board[col][row]

    
    def col_row_to_num_conversion(self, col, row):
        requested_square = self.get_square(col=col, row=row)
        return requested_square.number


    def row_to_col_num_conversion(self, num):
        requested_square = self.get_square(num=num)
        for col in 'abcdefgh':
            for row in '12345678':
                if self.get_square(col=col, row=row).number == requested_square.num:
                    return f'{col}{row}'


    def determine_color(self, col, row):
        # uses shorthand if-else statements to determine the color of any given square (black or white)
        if col in 'aceg': # cols a, c, e, g all start with white sqrs (so start white & alternate)
            self.color = v.white_color if int(row)%2 == 0 else v.black_color
        else:
            self.color = v.black_color if int(row)%2 == 0 else v.white_color
             # rest of the cols (b, d, f, g) start with black squares so switch logic
        return self.color


    def display_board_pieces(self):
        # displays the chess board by looping thru the dict and drawing each pygame Rect to the screen
        for col in 'abcdefgh':
            for row in '12345678':
                square = self.get_square(col=col, row=row)
                pygame.draw.rect(self.screen, square.color, square.pygame_rect) # accesses the pygame Rect and the sqr color from the internal board using the get_square method
                                                  # use self.get_square rather than get_square because the method being used is inside the class

        # loops thru dict again to check if each sqr has a piece on it that should be rendered
        for col in 'abcdefgh':
            for row in '12345678':
                square = self.get_square(col=col, row=row)
                if square.piece_obj != None: # if the reserved space for a piece_obj is not empty
                    self.screen.blit(square.piece_obj.piece_texture, square.pygame_rect)


    """def set_board(self, fen_string):
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
                    if item == 'K'  : self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = king.King('white', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count])) # if we want to add custom piece dimensions, we need to first be abe to blit the CENTER of the piece texture to the CENTER of the pygame rect
                    elif item == 'Q': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = queen.Queen('white', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'R': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = rook.Rook('white', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'B': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = bishop.Bishop('white', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'N': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = knight.Knight('white', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'P': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = pawn.Pawn('white', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'k': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = king.King('black', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'q': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = queen.Queen('black', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'r': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = rook.Rook('black', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'b': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = bishop.Bishop('black', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'n': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = knight.Knight('black', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                    elif item == 'p': self.get_square(col=str('abcdefgh'[col_count]), row=str('12345678'[row_count])).piece_obj = pawn.Pawn('black', self.col_row_to_num_conversion('abcdefgh'[col_count], '12345678'[row_count]))
                col_count += 1
            row_count += 1"""

    
    def get_square_from_coords(self, mouse_coords): # mouse_coords are an (x, y) tuple
        # returns what square a mouse interacted with by comparing the mouse's coordinates to those of each square on the board
        for col in 'abcdefgh':
            for row in '12345678':
                square = self.get_square(col=col, row=row)
                # below line checks if the coordinates are within each square's edges
                if mouse_coords[0] > square.pygame_rect.left and mouse_coords[0] < square.pygame_rect.right and mouse_coords[1] > square.pygame_rect.top and mouse_coords[1] < square.pygame_rect.bottom:
                    # > instead of >= in above line makes it so that only 1 sqr can be selected at a time, but leaves 'dead spots' on the borders of sqrs
                    return square

    
    def approve_move(self, start_square, end_square):
        # runs through proposed moves and only allows them to happen if they are legal (boolean return)
        if end_square == None: # if the user drags the mous off the screen, thus making the requested square not exist ---> fixes bug where mouse released off screen with piece selected would result in a crash
            return False
        if start_square.piece_obj == None: # an empty square wants to move somewhere ---> No
            return False
        if start_square.piece_obj and end_square.piece_obj == None: # a piece wants to move to an empty square ---> Yes
            return True
        if start_square.piece_obj and end_square.piece_obj: # a piece wants to move to a square with another piece (take the piece) --> Sometimes
            return True if start_square.piece_obj.color != end_square.piece_obj.color else False 
                # only allowed if the piece being taken is of opposite color from the taker piece

    
    def make_move(self, start_square, end_square):
        # moves a piece on the board by adding the piece_obj to the destination square and removing it from the starting square (modifies the internal board)
        end_square.piece_obj   = start_square.piece_obj
        start_square.piece_obj = None
        #update piece square_num to the current square's number
        end_square.piece_obj.square_num = end_square.number
     

    
    def make_piece_follow_mouse(self, clicked_square):
        if clicked_square.piece_obj != None:
            # sets the piece position to the mouse position
            # intended to be used in a while True loop so it runs continually until terminated
            texture   = clicked_square.piece_obj.piece_texture.convert_alpha() #not certain about convert_alpha
            piece_pos =  texture.get_rect() # making a new rect might be bad

            self.display_board_pieces()# redraw entire board
            pygame.draw.rect(self.screen, clicked_square.color, clicked_square.pygame_rect) # draw extra square on top of the piece currently joined to the mouse pointer
            piece_pos.center = pygame.mouse.get_pos() # piece coordsinates now are made equal to pointer coordinates (follows mouse around)
            self.screen.blit(texture, piece_pos) # draws the piece texture to the screen