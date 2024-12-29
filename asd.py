import fcntl
import os
import sys
import time
import random

queue = []
event_handlers = {}

# Add a handler to a list of handlers for this type of event
def add_handler(event_type, handler):
	ehl = event_handlers.get(event_type, [])
	ehl.append(handler)
	event_handlers[event_type] = ehl

# Read one message from a queue, and process it
def read_queue(queue):
	msg = queue.pop()
	ehl = event_handlers.get(msg['type'], None)
	if ehl:
		for handler in ehl:
			handler(msg)

# Set keyboard IO to be non-blocking
def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

set_non_blocking(sys.stdin.fileno())

# this is way more complicated in python than it has any reason to be
def _find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys, tty
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch

getch = _find_getch()

# Get current clock time in milliseconds
def get_clock():
    return round(time.time() * 1000)

last_timestamp = get_clock()

# Snake board
board = [[-1] * 16]
board += [[-1] + ([0]*14) + [-1] for _ in range(14)]
board += [[-1] * 16]
snake_direction = 1
snake_pos_x = 8
snake_pos_y = 8
snake_length = 4

# Spawn apple on board
def apple():
    global board
    x = random.randint(1, 15)
    y = random.randint(1, 15)
    while board[y][x] != 0:
        x = random.randint(1, 15)
        y = random.randint(1, 15)
    board[y][x] = -2

apple()

# Render snake board
def render():
    # Clear screen and move cursor to home
    print("\033[2J\033[H")
    for index, line in enumerate(board):
        for char in line:
            if char == -2:
                print("*", end="")
            if char == -1:
                print("#", end="")
            if char > 0:
                print("+", end="")
            if char == 0:
                print(".", end="")
        if index == 0:
            print(f'   SCORE: {snake_length - 4}', end="")
        print("\n", end="")

# Update snake board
def update():
    global snake_direction
    global snake_pos_x
    global snake_pos_y
    global snake_length
    global board
    # Update next snake position
    if snake_direction == 1:
        snake_pos_y -= 1
    if snake_direction == 2:
        snake_pos_x += 1
    if snake_direction == 3:
        snake_pos_y += 1
    if snake_direction == 4:
        snake_pos_x -= 1
    # Place a tile with the snake's length at the board point
    try:
        tile = board[snake_pos_y][snake_pos_x]
        if tile not in [0,-2]:
            queue.append({"type": "game_over"})
        if tile == -2:
            snake_length += 1
            apple()
        board[snake_pos_y][snake_pos_x] = snake_length
    except IndexError:
        queue.append({"type": "game_over"})
    for y, line in enumerate(board):
        for x, tile in enumerate(line):
            # Update snake tail
            if tile > 0:
                board[y][x] = tile - 1

# Add event handlers
def _game_over(_):
    print("\033[2J\033[H")
    print("Game over!")
    print(f'Your final score: {snake_length - 4}')
    exit(0)

add_handler("game_over", _game_over)

def _exit(_):
    exit(0)
add_handler("exit", _exit)

def _timer(_):
    update()
    render()

add_handler("timer", _timer)

def _key(msg):
    global snake_direction
    if msg['key'] == 'w':
        snake_direction = 1
    if msg['key'] == 'd':
        snake_direction = 2
    if msg['key'] == 's':
        snake_direction = 3
    if msg['key'] == 'a':
        snake_direction = 4

add_handler('key', _key)

# Source events here
while True:
    # Source events for keypresses
    char = getch()
    if char:
        queue.append({"type": "key", "key": char})
        if ord(char) == 3:
            queue.append({"type": "exit"})
    # Source events for timer in seconds
    if get_clock() - last_timestamp > 500:
        queue.append({"type": "timer"})
        last_timestamp = get_clock()
    while len(queue) > 0:
	    read_queue(queue)

