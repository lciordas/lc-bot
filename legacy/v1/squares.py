import pygame

class Square:

    def __init__(self, pygame_rect, piece_obj, color, number):
        self.pygame_rect = pygame_rect
        self.piece_obj   = piece_obj
        self.color       = color
        self.number      = number