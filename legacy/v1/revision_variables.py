import pygame

# establish clock and frame rate
clock = pygame.time.Clock()
fps = 60

# set screen width, height, and border thickness (in px)
screen_width     = 800
screen_height    = 800
border_thickness = 20

# basic colors
white_color = (238, 215, 192)
black_color = (176, 124, 100)

# establish a pygame screen and its dimesions
# screen = pygame.display.set_mode((screen_width + border_thickness, screen_height + border_thickness))
screen = pygame.display.set_mode((screen_width, screen_height))


# create a library of loaded images for each piece type and their width/height in px
piece_dimensions = (100, 100)
piece_textures = {
    'K': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-king.png'), piece_dimensions),
    'Q': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-queen.png'), piece_dimensions),
    'R': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-rook.png'), piece_dimensions),
    'B': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-bishop.png'), piece_dimensions),
    'N': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-knight.png'), piece_dimensions),
    'P': pygame.transform.smoothscale(pygame.image.load('piece_textures/white-pawn.png'), piece_dimensions),
    'k': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-king.png'), piece_dimensions),
    'q': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-queen.png'), piece_dimensions),
    'r': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-rook.png'), piece_dimensions),
    'b': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-bishop.png'), piece_dimensions),
    'n': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-knight.png'), piece_dimensions),
    'p': pygame.transform.smoothscale(pygame.image.load('piece_textures/black-pawn.png'), piece_dimensions)
}
