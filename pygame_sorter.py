import math
import pygame
from win32api import GetSystemMetrics
import random
import sys

pygame.init()

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

BORDER_RADIUS = 4

SPEED = 10


ratio = 0.8
s_width = int(GetSystemMetrics(0) * ratio)
s_height = int(GetSystemMetrics(1) * ratio)


print(f'width; {s_width}')
print(f'height; {s_height}')

game_to_screen_ratio = 0.8


screen = pygame.display.set_mode((s_width, s_height))
clock = pygame.time.Clock()
running = True

# belt_y to szerokość taśmy (1500mm)
belt_x = s_width * game_to_screen_ratio
belt_y = s_height * game_to_screen_ratio


belt_bottom = s_height / 2 + belt_y / 2
belt_top = s_height / 2 - belt_y / 2
belt_left = s_width/2 - belt_x/2
belt_right = belt_x/2 + s_width/2

# "X" warstwy:
PALLET_X = belt_x * 0.4
board_width = 50

row_num = math.floor(PALLET_X/board_width)
rows = list(i for i in range(0, row_num * board_width, board_width))

block_list = []

set_blocks = []


MIN_BLOCK = 0.1*belt_y
MAX_BLOCK = 0.5*belt_y

cash_effect = pygame.mixer.Sound('cash.mp3')
wood_effect = pygame.mixer.Sound('wood.wav')


def new_block():
    block_lenght = random.randint(round(MIN_BLOCK), round(MAX_BLOCK))
    block_x = int(belt_right-board_width)
    block_y = int(belt_top + random.randint(0, belt_y - block_lenght))
    block_list.append(pygame.Rect(block_x, block_y, board_width, block_lenght))


def can_create():
    if len(block_list) == 0:
        return True
    for idx, block_pos in enumerate(block_list):
        if block_pos[0] > belt_right - 6*board_width:
            return False
    return True


def height(row_num=None):
    heights = [belt_bottom] * len(rows)
    for idx, row in enumerate(rows):
        # max_Y = belt_bottom - belt_top
        max_Y = belt_bottom
        for x, blocky in enumerate(set_blocks):
            if blocky[0] <= belt_left + row <= blocky[0] + board_width and blocky[1] < max_Y:
                max_Y = blocky[1]
                heights[idx] = blocky[1]

    if row_num is None:
        return heights
    else:
        return heights[row_num]


def clear(block_list):
    for idx, block in enumerate(block_list):
        if block[3] > height(-1)-belt_top and idx == 0:
            set_blocks.clear()
            cash_effect.play()


def placing(block):

    if len(set_blocks) == 0:
        return [(s_width/2 - belt_x/2), s_height/2 + belt_y/2 - block[3], block[2], block[3]]
    else:
        step = 0

        last_height = belt_bottom

        for idx, row_height in reversed(list(enumerate(height()))):
            if row_height - belt_top > block[3]:
                last_height = height(idx)
                if step <= board_width * row_num:
                    step = idx * board_width
                if step == 0 and height(-1)<belt_bottom:
                    print("czyszczenie")
                    clear(block_list)
                    step = 0
                try:
                    if min((height()[idx:-1])) < last_height:
                        # print(f'słupek docelowy: {last_height}, słupek najwyższy:{ min((height()[idx:-1])) - belt_top}, wysokość klocka:{ block[3]}')
                        last_height = min((height()[idx:-1]))
                except ValueError:
                    pass
            else:
                break

        return [belt_left + step, last_height-block[3], block[2], block[3]]


def draw_blocks():
    for block in block_list:
        pygame.draw.rect(screen, pygame.Color('burlywood3'), block, width=20, border_radius=BORDER_RADIUS)
    for block in set_blocks:
        pygame.draw.rect(screen, pygame.Color('burlywood4'), block, width=20, border_radius=BORDER_RADIUS)
    if len(block_list) > 0:
        pygame.draw.rect(screen, GREEN, placing(block_list[0]), width=20, border_radius=BORDER_RADIUS)


def update_block_pos():
    for idx, block_pos in enumerate(block_list):
        inflated = block_pos.inflate(SPEED, 0)
        if (placing(block_pos)[0]) <= block_pos[0] \
                and inflated.collidelist(block_list) == idx \
                and inflated.collidelist(set_blocks) < 0:

            block_pos[0] -= SPEED
            if idx == 0:
                block_pos[1] = placing(block_pos)[1]
            # if block_pos[1] > placing(block_pos)[1]:
            #     block_pos[1] -= SPEED
            # elif block_pos[1] < placing(block_pos)[1]:
            #     block_pos[1] += SPEED
        else:
            wood_effect.play()
            block_pos[1] = placing(block_pos)[1]
            set_blocks.append(block_list.pop(idx))



while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                set_blocks.clear()
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
                running = False
            elif event.key == pygame.K_LEFT:
                if can_create():
                    clear(block_list)
                    new_block()
            elif event.key == pygame.K_DOWN:
                print(height())
    if can_create():
        clear(block_list)
        new_block()
    screen.fill(BLACK)
    clear(block_list)
    # for row in rows:
    #     pygame.draw.line(screen, RED, (belt_left + row + board_width, belt_top), (belt_left + row + board_width, belt_bottom))
    pygame.draw.line(screen, RED, (belt_left + row_num * board_width, belt_top), (belt_left + row_num * board_width, belt_bottom))

    pygame.draw.rect(screen, RED,
                     ((s_width/2-belt_x/2, s_height/2 - belt_y/2),
                      (s_width*game_to_screen_ratio, s_height*game_to_screen_ratio)), width=6)
    draw_blocks()
    update_block_pos()

    pygame.display.flip()

    clock.tick(60)

