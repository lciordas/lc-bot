import pygame
pygame.init()

clock = pygame.time.Clock()
screen = pygame.display.set_mode((800, 800))

#king3 = pygame.image.load('king.png')
#king3 = pygame.transform.smoothscale(king3, (100, 100))
#v.screen.blit(king3, v.board['a'][1])


run = True
while run:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    
    
    

    pygame.display.flip()
    clock.tick(60)
print('abcdefg'[0])