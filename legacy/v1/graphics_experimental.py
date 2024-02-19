import pygame

pygame.init()

clock = pygame.time.Clock()
fps = 60

screen = pygame.display.set_mode((200, 200))

#()()()()()()(()()()()()()()()()()()()()()()()()()()()()()()()#
rect1  = pygame.Rect(0, 0, 100, 100)
left   = rect1.left
right  = rect1.right
top    = rect1.top
bottom = rect1.bottom 
#()()()()()()(()()()()()()()()()()()()()()()()()()()()()()()()#


run = True
while run:
    pos = pygame.mouse.get_pos()
    #print(pos)
    #print(left, right, top, bottom)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.MOUSEBUTTONDOWN:    
            if pos[0] >= left and pos[0] <= right and pos[1] >= top and pos[1] <= bottom:
                print('the cursor has clicked inside the rect')
            else: print('the cursor has clicked outside the rect')
#_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_#
    

#_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_#

    pygame.display.flip()
    clock.tick(fps)

# <Event(1025-MouseButtonDown {'pos': (102, 106), 'button': 1, 'touch': False, 'window': None})>
# pygame.mous.get_pressed() ---> returns a tuple that says which of 3 mouse buttons are being pressed
    # if left button being pressed, tuple looks like this: (True, False, False)