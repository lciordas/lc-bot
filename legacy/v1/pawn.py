import pygame
from revision_pieces import Pieces

class Pawn(Pieces):
    def __init__(self, color, location, display_dimensions = (100, 100)):
        super().__init__(color, location, display_dimensions)
        self.type = 'Pawn'
        if color == 'white':
            self.piece_texture = pygame.transform.smoothscale(pygame.image.load('piece_textures/white-pawn.png'), self.display_dimensions)
        elif color == 'black':
            self.piece_texture = pygame.transform.smoothscale(pygame.image.load('piece_textures/black-pawn.png'), self.display_dimensions)

    
    def calculate_moves(self):
        return self.queen_rook_bishop_moves(['North'])
