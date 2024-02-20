import pygame

screen = pygame.display.set_mode((640, 480))
clock = pygame.time.Clock()            #get a pygame clock object
player_image = pygame.image.load('piece_textures/white-knight.png').convert_alpha()
player_pos   = player_image.get_rect()
background = pygame.image.load('piece_textures/background.png').convert()
screen.blit(background, (0, 0))

mapped_to_mouse = False

run = True
while run == True:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            if pygame.mouse.get_pos()[0] > player_pos.left and pygame.mouse.get_pos()[0] < player_pos.right and pygame.mouse.get_pos()[1] > player_pos.top and pygame.mouse.get_pos()[1] < player_pos.bottom:
                mapped_to_mouse = True
                print('down')

        if event.type == pygame.MOUSEBUTTONUP:
            mapped_to_mouse = False
            print('up')

    if mapped_to_mouse == True:
        print('function active')
        screen.blit(background, player_pos, player_pos)
        player_pos.center = pygame.mouse.get_pos()
        screen.blit(player_image, player_pos)
    

    pygame.display.update()
    clock.tick(60)