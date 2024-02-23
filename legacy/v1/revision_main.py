import pygame
import revision_variables as v
import gameboard_container
import revision_pieces as pieces

pygame.init()

piece_instance = pieces.Pieces(None, None)

#()()()()()()(()()()()()()()()()()()()()()()()()()()()()()()()#

# makes a board obj from the board class, and thus automatically gets the internal representation of the board (cuz its in the __init__ method)
#gameboard = board.Board()

piece_instance.set_pieces('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR') # sets the board using the set_board method and FEN notation

piece_following_mouse = False

#()()()()()()(()()()()()()()()()()()()()()()()()()()()()()()()#

run = True
while run:
    pos = pygame.mouse.get_pos()
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            run = False

        # VERY WEIRD bug WHERE SOMETIMES THE CLICKING JUST DOESN'T WORK AND IT ONLY ACCEPTS DOUBLE CLICKS, TO FIX THIS JUST KEEP CLOSING AND RE-RUNNING THE PROGRAM
        if event.type == pygame.MOUSEBUTTONDOWN:
            clicked_square = gameboard_container.gameboard.get_square_from_coords(pos)
            if clicked_square.piece_obj:
                piece_following_mouse = True
                legal_moves = clicked_square.piece_obj.calculate_moves()
                print(legal_moves)

        if event.type == pygame.MOUSEBUTTONUP:
            released_square = gameboard_container.gameboard.get_square_from_coords(pos)
            piece_following_mouse = False
            if gameboard_container.gameboard.approve_move(clicked_square, released_square) and released_square in legal_moves:
                gameboard_container.gameboard.make_move(clicked_square, released_square)
            
#_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_#
    gameboard_container.gameboard.display_board_pieces() # important that this line goes before the if piece_following_mouse line

    if piece_following_mouse:
        gameboard_container.gameboard.make_piece_follow_mouse(clicked_square)
#_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_#

    pygame.display.flip() # updates the screen
    v.clock.tick(v.fps)   # limits framerate to fps value (60 fps)