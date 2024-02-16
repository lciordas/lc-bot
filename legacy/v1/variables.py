import pygame

clock = pygame.time.Clock()
FPS = 60

SCREEN_WIDTH       =  800
SCREEN_HEIGHT      =  800
BORDER_THICKNESS   =  20
ROWS               =  8
COLLUMS            =  8
WHITE_COLOR        = (238, 215, 192)
BLACK_COLOR        = (176, 124, 100)

screen = pygame.display.set_mode( (SCREEN_WIDTH + BORDER_THICKNESS, SCREEN_HEIGHT + BORDER_THICKNESS) )

q = 100 # CHANGE TO 100 AND LOOK AS SCALE(NOT SMOOTHSCALE)
piece_textures = {
    'K': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-king.png'), (q, q)),
    'Q': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-queen.png'), (q, q)),
    'R': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-rook.png'), (q, q)),
    'B': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-bishop.png'), (q, q)),
    'N': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-knight.png'), (q, q)),
    'P': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-pawn.png'), (q, q)),
    'k': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-king.png'), (q, q)),
    'q': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-queen.png'), (q, q)),
    'r': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-rook.png'), (q, q)),
    'b': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-bishop.png'), (q, q)),
    'n': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-knight.png'), (q, q)),
    'p': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-pawn.png'), (q, q))
}
