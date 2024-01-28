import pygame
import variables as v
#import pieces

class Board:

    def __init__(self,
                display_surface  = v.screen, 
                border_thickness = v.BORDER_THICKNESS, 
                white_color      = v.WHITE_COLOR, 
                black_color      = v.BLACK_COLOR,
                piece_textures   = v.piece_textures):

        self.display_surface  = display_surface
        self.border_thickness = border_thickness
        self.white_color      = white_color
        self.black_color      = black_color
        self.piece_textures   = piece_textures

    

    def internally_represent_board(self):
        board = {}
        x = 0
        for char in 'abcdefgh':
            col = [[None, None]]
            y = 700
            for i in range(8):
                col.append([pygame.Rect(x + self.border_thickness/2, y + self.border_thickness/2, 100, 100), None])
                y -= 100
            board[char] = col
            x += 100
        self.internal_board = board
    
# display_visuals()
    def display_board(self, *args):
        count = 0
        for letter in self.internal_board:
            for sq in self.internal_board[letter]:
                if sq[0] == None: continue
                color = self.white_color
                if count % 2 == 0: color = self.black_color
                pygame.draw.rect(self.display_surface, color, sq[0])
                count += 1
                for arg in args:
                    if sq == arg:

                        s = pygame.Surface((100,100))
                        s.set_alpha(190)
                        s.fill((58,175,220))
                        self.display_surface.blit(s, (sq[0][0], sq[0][1]))

                        #pygame.draw.rect(self.display_surface, ((58,175,220)), sq[0])

                if sq[1] != None:
                    texture_rect = self.piece_textures[sq[1]].get_rect()
                    texture_rect.center = sq[0].center
                    self.display_surface.blit(self.piece_textures[sq[1]], texture_rect)
            count += 1



    def set_pieces(self, FEN_string):
        rows = FEN_string.split('/')
        row_count = 1
        for row in reversed(rows):
            col_count = 1
            for char in row:
                letter = 'xabcdefgh'[col_count]
                if char in '12345678':
                    col_count += int(char)
                if col_count > 8:
                    break
                if char in 'KQRBNPkqrbnp':
                    self.internal_board[letter][row_count][1] = char
                    col_count += 1
            row_count += 1


    def move_piece(self, start_sq, end_sq):
        import pieces
        # blit the piece texture of the selected piece to the selected square (gameboard.internal_board['b'][7])
        if start_sq == end_sq:
            return
        elif start_sq[1] == None:
            return
        elif start_sq[1] == 'r' or start_sq[1] == 'R':
            rook = pieces.Rook('e5')
            if end_sq in rook.get_legal_moves():
                texture_rect = self.piece_textures[start_sq[1]].get_rect()
                texture_rect.center = end_sq[0].center
                end_sq[1] = start_sq[1]
                start_sq[1] = None
                return
            else:
                return
        texture_rect = self.piece_textures[start_sq[1]].get_rect()
        texture_rect.center = end_sq[0].center
        end_sq[1] = start_sq[1]
        start_sq[1] = None

## FIX: SAME START AND END SQUARE
# NOTHING ON START SQUARE