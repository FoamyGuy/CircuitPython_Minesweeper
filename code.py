import board
import displayio
import adafruit_imageload
from displayio import Palette
from adafruit_pybadger import PyBadger
import time
import random
from analogio import AnalogIn
import digitalio
import adafruit_lis3dh
from adafruit_display_text import label
import terminalio


# set the WIDTH and HEIGHT variables.
# this assumes the map is rectangular.
MAP_HEIGHT = 10
MAP_WIDTH = 12


# Direction constants for comparison
UP = 0
DOWN = 1
RIGHT = 2
LEFT = 3

# GAME_STATE constants
PLAYING = 0
GAME_OVER = 1

GAME_STATE = PLAYING

# how many bombs should there be?
BOMB_COUNT = 12

# how long to wait between rendering frames
FPS_DELAY = 1/30

# how many tiles can fit on thes screen. Tiles are 16x16
SCREEN_HEIGHT_TILES = 8
SCREEN_WIDTH_TILES = 10

# hold full map state
ORIGINAL_MAP = {}

# hold the current map state as the player sees it
CURRENT_MAP = {}

# dictionary with tuple keys that map to tile type values
# e.x. {(0,0): "left_wall", (1,1): "floor"}
CAMERA_VIEW = {}

# how far offset the camera is from the CURRENT_MAP
# used to determine where things are at in the camera view vs. the MAP
CAMERA_OFFSET_X = 0
CAMERA_OFFSET_Y = 0

"""
Use the Accelerometer and an Analog Pin to get a random seed.
"""
i2c = None
# Accelerometer
if i2c is None:
    try:
        i2c = board.I2C()
    except RuntimeError:
        _accelerometer = None

if i2c is not None:
    int1 = digitalio.DigitalInOut(board.ACCELEROMETER_INTERRUPT)
    try:
        _accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19, int1=int1)
    except ValueError:
        _accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)

int1.deinit() # deinit or else pybadger throws exception

# accelerometer values
ax,ay,az = _accelerometer.acceleration

# otherwise unused analog pin
pin = AnalogIn(board.A4)
pin_val = pin.value
pin.deinit()

print("%s,%s,%s" % (ax,ay,az))

# big equation to generate random seed
val = int(abs((ax*ay*az) + (ax - az) * ((ay + az)* pin_val)))
print(val)
random.seed(val)


# hold the location of the player in tile coordinates
PLAYER_LOC = (0,0)

# return from CURRENT_MAP the tile name of the tile of the given coords
def get_tile(coords):
    return CURRENT_MAP[coords[0], coords[1]]

# return from TILES dict the tile object with stats and behavior for the tile at the given coords.
def get_tile_obj(coords):
    return TILES[CURRENT_MAP[coords[0], coords[1]]]

# get a random coordinate that is within the map
def get_random_loc():
    return (random.randint(0,MAP_WIDTH-1), random.randint(0,MAP_HEIGHT-1))

# show everything to the player
def reveal_all():
    CURRENT_MAP = ORIGINAL_MAP

# check to see if player has won the game
def check_win():
    global GAME_STATE
    uncleared_tile_count = 0
    for y in range(0,MAP_HEIGHT):
        for x in range(0, MAP_WIDTH):
            if CURRENT_MAP[x,y] == "regular" or CURRENT_MAP[x,y] == "flag":
                uncleared_tile_count += 1
    if BOMB_COUNT == uncleared_tile_count:
        text_area.text = "You Win\n =D"
        text_area.y = int(128/2 - 30)
        group.append(splash)
        time.sleep(2)
        group.remove(splash)
        GAME_STATE = GAME_OVER

# given a location, find all of the tiles touching  that location that need to
# be revealed. Used when the player reveals a "zero" tile.
def find_tiles_to_reveal(loc):
    zeros = []
    nonzeros = []
    non_zero_vals = []

    for val in NUMBER_MAP.values():
        if val != "zero":
            non_zero_vals.append(val)

    # row below
    if loc[1] + 1 < MAP_HEIGHT:
        for x in range(-1,2):
            if 0 <= loc[0]+x < MAP_WIDTH:
                if ORIGINAL_MAP[loc[0]+x, loc[1]+1] == "zero":
                    zeros.append((loc[0]+x, loc[1]+1))
                if ORIGINAL_MAP[loc[0]+x, loc[1]+1] in non_zero_vals:
                        nonzeros.append((loc[0]+x, loc[1]+1))

    # row above
    if loc[1] - 1 >= 0:
        for x in range(-1,2):
            if 0 <= loc[0]+x < MAP_WIDTH:
                if ORIGINAL_MAP[loc[0]+x, loc[1]-1] == "zero":
                    zeros.append((loc[0]+x, loc[1]-1))
                if ORIGINAL_MAP[loc[0]+x, loc[1]-1] in non_zero_vals:
                    nonzeros.append((loc[0]+x, loc[1]-1))

    # same row
    for x in range(-1,2):
        # skip self loc
        if x != 0:
            if 0 <= loc[0]+x < MAP_WIDTH:
                if ORIGINAL_MAP[loc[0]+x, loc[1]] == "zero":
                    zeros.append((loc[0]+x, loc[1]))
                if ORIGINAL_MAP[loc[0]+x, loc[1]] in non_zero_vals:
                    nonzeros.append((loc[0]+x, loc[1]))

    return zeros, nonzeros

    
# return a count of how many bombs are touching the given tile coordinates
def count_bombs(loc):
    cur_count = 0

    # row below
    if loc[1] + 1 < MAP_HEIGHT:
        for x in range(-1,2):
            if 0 <= loc[0]+x < MAP_WIDTH:
                if ORIGINAL_MAP[loc[0]+x, loc[1]+1] == "bomb":
                    cur_count += 1

    # row above
    if loc[1] - 1 >= 0:
        for x in range(-1,2):
            if 0 <= loc[0]+x < MAP_WIDTH:
                if ORIGINAL_MAP[loc[0]+x, loc[1]-1] == "bomb":
                    cur_count += 1

    # same row
    for x in range(-1,2):
        # skip self loc
        if x != 0:
            if 0 <= loc[0]+x < MAP_WIDTH:
                if ORIGINAL_MAP[loc[0]+x, loc[1]] == "bomb":
                    cur_count += 1


    return cur_count
    
# main dictionary that maps tile type strings to objects.
# each one stores the sprite_sheet index and any necessary
# behavioral stats (none needed for minesweeper)
TILES = {
    # empty strings default to black tile
    "": {
        "sprite_index": 13,
    },
    "regular": {
        "sprite_index": 14
    },
    "zero": {
        "sprite_index": 8
    },
    "one": {
        "sprite_index": 0
    },
    "two": {
        "sprite_index": 1
    },
    "three": {
        "sprite_index": 2
    },
    "four": {
        "sprite_index": 3
    },
    "five": {
        "sprite_index": 4
    },
    "six": {
        "sprite_index": 5
    },
    "seven": {
        "sprite_index": 6
    },
    "eight": {
        "sprite_index": 7
    },
    "zero": {
        "sprite_index": 8
    },
    "flag":{
        "sprite_index": 9
    },
    "question_mark":{
        "sprite_index": 10
    },
    "bomb":{
        "sprite_index": 11
    },
    "cursor": {
        "sprite_index": 12
    }

}

# mapping ints to word strings
NUMBER_MAP = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight"
}

# Badger object for easy button handling
badger = PyBadger()

# display object variable
display = board.DISPLAY

# Load the sprite sheet (bitmap)
sprite_sheet, palette = adafruit_imageload.load("/sprite_sheet.bmp",
                                                bitmap=displayio.Bitmap,
                                                palette=displayio.Palette)

# make bright pink be transparent so entities can be drawn on top of map tiles
palette.make_transparent(0)

# Create the castle TileGrid
castle = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                            width = 10,
                            height = 8,
                            tile_width = 16,
                            tile_height = 16)

# Create a Group to hold the sprites and add it
sprite_group = displayio.Group(max_size=10)

# Create a Group to hold the castle and add it
castle_group = displayio.Group()
castle_group.append(castle)

# Create a Group to hold the sprite and castle
group = displayio.Group()

# Add the sprite and castle to the group
group.append(castle_group)
group.append(sprite_group)


# Make the display context
splash = displayio.Group(max_size=10)

# Draw a green background
color_bitmap = displayio.Bitmap(160, 128, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x000077

bg_sprite = displayio.TileGrid(color_bitmap,
                               pixel_shader=color_palette,
                               x=0, y=0)

splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(160-30, 128-30, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0xAA0088 # Purple
inner_sprite = displayio.TileGrid(inner_bitmap,
                                  pixel_shader=inner_palette,
                                  x=15, y=15)
splash.append(inner_sprite)

# Draw a label
text_group = displayio.Group(max_size=64, scale=1, x=24, y=24)


# add some space when we initialize so we can set the text to something longer later
text_area = label.Label(terminalio.FONT, text=" "*64, color=0xFFFF00)
text_group.append(text_area) # Subgroup for text scaling
splash.append(text_group)


# Generate a random map and store it in ORIGINAL_MAP
# load CURRENT_MAP with "regular" tiles
def init_map():
    # we want to affect the global vars
    global CURRENT_MAP
    global ORIGINAL_MAP

    # empty them out
    CURRENT_MAP = {}
    ORIGINAL_MAP = {}
    
    # list that will hold bomb coordinates
    bombs = []

    # while we don't have enough bombs yet
    while len(bombs) < BOMB_COUNT:
        # generate a random location
        loc = get_random_loc()
        
        # if there isn't already a bomb at the location
        if loc not in bombs:
            # add it to the list
            bombs.append(loc)
    
    #print(bombs)
    
    # for each row
    for y in range(0,MAP_HEIGHT):
        # for each column
        for x in range(0, MAP_WIDTH):
            # if this spot has a bomb
            if (x,y) in bombs:
                # set it in the ORIGINAL_MAP
                ORIGINAL_MAP[x,y] = "bomb"
            else: # no bomb
                # set it to "zero" for now in the ORIGINAL_MAP
                ORIGINAL_MAP[x,y] = "zero"
                
            # set this tile to "regular" in the CURRENT_MAP
            CURRENT_MAP[x,y] = "regular"

    # for each row
    for y in range(0,MAP_HEIGHT):
        # for each column
        for x in range(0, MAP_WIDTH):
            # if this spot is not a bomb
            if (x,y) not in bombs:
                # get a count of how many bombs are touching this tile
                bomb_count = count_bombs((x,y))
                # set it in the ORIGINAL_MAP
                ORIGINAL_MAP[x,y] = NUMBER_MAP[bomb_count]



# make the first map
init_map()

# Create the sprite TileGrid
sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
    width = 1,
    height = 1,
    tile_width = 16,
    tile_height = 16,
    default_tile = TILES["cursor"]['sprite_index'])


# position of the cursor
PLAYER_LOC = (4,3)

# add sprite to the group
sprite_group.append(sprite)

# Add the Group to the Display
display.show(group)

# variables to store previous value of button state
prev_up = False
prev_down = False
prev_left = False
prev_right = False

prev_a = False
prev_b = False


# set the appropriate tiles into the CAMERA_VIEW dictionary
# based on given starting coords and size passed as parameters
def set_camera_view(startX, startY, width, height):
    global CAMERA_OFFSET_X
    global CAMERA_OFFSET_Y
    
    # set the offset variables for use in other parts of the code
    CAMERA_OFFSET_X = startX
    CAMERA_OFFSET_Y = startY

    # loop over the rows and indexes in the desired size section
    for y_index, y in enumerate(range(startY, startY+height)):
        # loop over columns and indexes in the desired size section
        for x_index, x in enumerate(range(startX, startX+width)):
            #print("setting camera_view[%s,%s]" % (x_index,y_index))
            try:
                # set the tile at the current coordinate of the MAP into the CAMERA_VIEW
                CAMERA_VIEW[x_index,y_index] = CURRENT_MAP[x,y]
            except KeyError:
                # if coordinate is out of bounds set it to empty by default
                CAMERA_VIEW[x_index,y_index] = ""

# draw the current CAMERA_VIEW dictionary and the player cursor
def draw_camera_view():

    # loop over y tile coordinates
    for y in range(0, SCREEN_HEIGHT_TILES):
        # loop over x tile coordinates
        for x in range(0, SCREEN_WIDTH_TILES):
            # tile name at this location
            tile_name = CAMERA_VIEW[x,y]

            # if tile exists in the main dictionary
            if tile_name in TILES.keys():
                # set the sprite index of this tile into the castle dictionary
                castle[x, y] = TILES[tile_name]['sprite_index']

            else: # tile type not found in main dictionary
                # default to empty tile
                castle[x, y] = TILES[""]['sprite_index']

            # if the player is at this x,y tile coordinate accounting for camera offset
            if PLAYER_LOC == ((x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y)):
                # set player sprite screen coordinates
                sprite.x = x*16
                sprite.y = y*16



# variable to store timestamp of last drawn frame
last_update_time = 0


# main loop
while True:
    # auto dim the screen
    badger.auto_dim_display(delay=10)

    # set the current button values into variables
    cur_up = badger.button.up
    cur_down = badger.button.down
    cur_right = badger.button.right
    cur_left = badger.button.left

    cur_a =  badger.button.a
    cur_b =  badger.button.b


    # check for up button press / release
    if not cur_up and prev_up:
        # set new player location. Using max to keep them from moving outside the map
        PLAYER_LOC = (PLAYER_LOC[0], max(0, PLAYER_LOC[1]-1))


    # check for down button press / release
    if not cur_down and prev_down:
        # set new player location. Using min to keep them from moving outside the map
        PLAYER_LOC = (PLAYER_LOC[0], min(MAP_HEIGHT-1, PLAYER_LOC[1]+1))


    # check for right button press / release
    if not cur_right and prev_right:
        # set new player location. Using min to keep them from moving outside the map
        PLAYER_LOC = (min(MAP_WIDTH-1, PLAYER_LOC[0]+1), PLAYER_LOC[1])


    # check for left button press / release
    if not cur_left and prev_left:
        # set new player location. Using max to keep them from moving outside the map
        PLAYER_LOC = (max(0, PLAYER_LOC[0]-1), PLAYER_LOC[1])
    
    # if a button has been released
    if not cur_a and prev_a:
        print("a btn")
        
        
        if GAME_STATE == GAME_OVER:
            # start a new game by making new map
            init_map()
            GAME_STATE = PLAYING
        else: # GAME_STATE is PLAYING
            # if the selected tile has not already been revealed
            if CURRENT_MAP[PLAYER_LOC] == "regular":
                #print("cur is reg")
                
                # if the tile is a number but not "zero"
                if ORIGINAL_MAP[PLAYER_LOC] in NUMBER_MAP.values() and ORIGINAL_MAP[PLAYER_LOC] != "zero":
                    # reveal the tile
                    CURRENT_MAP[PLAYER_LOC] = ORIGINAL_MAP[PLAYER_LOC]
                
                # if the tile is a "zero"
                if ORIGINAL_MAP[PLAYER_LOC] == "zero":
                    # reveal the tile
                    CURRENT_MAP[PLAYER_LOC] = ORIGINAL_MAP[PLAYER_LOC]
                    
                    # list to store coordinates already checked
                    already_handled = []
                    
                    # find tiles to reveal
                    zeros, non_zeros = find_tiles_to_reveal(PLAYER_LOC)
                    
                    # loop over non-zero tiles
                    for coords in non_zeros:
                        # reveal this tile
                        CURRENT_MAP[coords] = ORIGINAL_MAP[coords]
                        # add coordinates to the list of already handled, so we can skip it in the future.
                        already_handled.append(coords)
                    
                    # while there are still "zero" tiles to reveal
                    while len(zeros) > 0:
                        print(zeros)
                        
                        # find tiles to reveal around the first "zero" tile in the list
                        new_zeros, new_non_zeros = find_tiles_to_reveal(zeros[0])

                        # loop over non-zero tiles
                        for coords in new_non_zeros:
                            # reveal this tile
                            CURRENT_MAP[coords] = ORIGINAL_MAP[coords]
                            # add coordinates to the list of already handled, so we can skip it in the future.
                            already_handled.append(coords)
                        
                        # loop over "zero" tiles found
                        for new_zero in new_zeros:
                            # if it's not already in the list waiting to be checked, and it hasn't already been checked
                            if new_zero not in zeros and new_zero not in already_handled:
                                # add it to the list to get checked
                                zeros.append(new_zero)
                        
                        # reveal the first "zero" tile
                        CURRENT_MAP[zeros[0]] = ORIGINAL_MAP[zeros[0]]
                        # add coords to list of already handled so we an skip it later
                        already_handled.append(zeros[0])
                        # remove the first "zero" tile from the list so we'll check the next one in the next iteration
                        zeros.remove(zeros[0])

                # if the tile was a "bomb"
                if ORIGINAL_MAP[PLAYER_LOC] == "bomb":
                    print("player lost, revealing")
                    # reveal full map
                    CURRENT_MAP = ORIGINAL_MAP
                    # set GAME_STATE to GAME_OVER
                    GAME_STATE = GAME_OVER

    # if the b button has been released
    if not cur_b and prev_b:
        # if the tile hasn't been revealed
        if CURRENT_MAP[PLAYER_LOC] == "regular":
            # set the tile to "flag"
            CURRENT_MAP[PLAYER_LOC] = "flag"
        # if the tile is a flag
        elif CURRENT_MAP[PLAYER_LOC] == "flag":
            # set the tile back to "regular" so it can be revealed with the a button
            CURRENT_MAP[PLAYER_LOC] = "regular"

    # set previos button values for comparison in the next iteration of main loop
    prev_up = cur_up
    prev_down = cur_down
    prev_right = cur_right
    prev_left = cur_left

    prev_a = cur_a
    prev_b = cur_b

    # current time
    now = time.monotonic()

    # if it has been long enough based on FPS delay
    if now > last_update_time + FPS_DELAY:

        # set camera to centered(ish) on player and bound by MAP and SCREEN size.
        set_camera_view(
            max(min(PLAYER_LOC[0]-4,MAP_WIDTH-SCREEN_WIDTH_TILES),0),
            max(min(PLAYER_LOC[1]-3,MAP_HEIGHT-SCREEN_HEIGHT_TILES),0),
            10,
            8
        )

        # draw the camera
        draw_camera_view()

        if GAME_STATE != GAME_OVER:
            # check for win
            check_win()

        # store the last update time
        last_update_time = now