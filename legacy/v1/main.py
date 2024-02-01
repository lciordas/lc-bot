import sys
import pygame
import time
import board
import variables as v
#import pieces

pygame.init()
gameboard = board.Board()
gameboard.internally_represent_board()

#gameboard.set_pieces('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')
gameboard.set_pieces('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR')

newMove = True
highlighted_squares = []

active_square = None
run = True
while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if newMove == True:
                start_and_end = []
                highlighted_squares = []
                for let in 'abcdefgh':
                    for num in '12345678':
                        if gameboard.internal_board[let][int(num)][1] == None:
                            continue
                        if gameboard.internal_board[let][int(num)][0].collidepoint(event.pos):
                            start_and_end.append(gameboard.internal_board[let][int(num)])
                            if gameboard.internal_board[let][int(num)][1] != None:
                                highlighted_squares.append(gameboard.internal_board[let][int(num)])
                            newMove = False
                break

            if newMove == False:
                for let in 'abcdefgh':
                    for num in '12345678':
                        if gameboard.internal_board[let][int(num)][0].collidepoint(event.pos):
                            start_and_end.append(gameboard.internal_board[let][int(num)])
                            if len(highlighted_squares) > 0:
                                highlighted_squares.append(gameboard.internal_board[let][int(num)])
                            gameboard.move_piece(*start_and_end)
                            newMove = True


    ########################################


    gameboard.display_board(*highlighted_squares)


    ########################################
    pygame.display.flip()
    v.clock.tick(v.FPS)