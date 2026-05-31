import time
import sys
import random
import copy
import os
import shutil

# This single line forces Windows to process ANSI color codes!
os.system("") 

# --- ANSI escape codes for colors and cursor control ---
COLORS = {
    0: "\033[0m",        # Empty (Reset)
    1: "\033[46m  \033[0m",  # Cyan (I)
    2: "\033[44m  \033[0m",  # Blue (J)
    3: "\033[43m  \033[0m",  # Orange (L) -> using yellow/orange
    4: "\033[43m  \033[0m",  # Yellow (O)
    5: "\033[42m  \033[0m",  # Green (S)
    6: "\033[45m  \033[0m",  # Purple (T)
    7: "\033[41m  \033[0m"   # Red (Z)
}

# --- Tetromino Definitions ---
# 1=I, 2=J, 3=L, 4=O, 5=S, 6=T, 7=Z
SHAPES = [
    [], # Placeholder for 1-based indexing
    [[1, 1, 1, 1]], 
    [[2, 0, 0], [2, 2, 2]],
    [[0, 0, 3], [3, 3, 3]],
    [[4, 4], [4, 4]],
    [[0, 5, 5], [5, 5, 0]],
    [[0, 6, 0], [6, 6, 6]],
    [[7, 7, 0], [0, 7, 7]]
]

class TetrisAI:
    def __init__(self):
        # Get current terminal dimensions
        term_cols, term_lines = shutil.get_terminal_size()
        # HEIGHT: Total lines minus 4 (1 for score, 1 top border, 1 bottom border, 1 safety buffer)
        self.rows = max(1, term_lines - 6)
        # WIDTH: Total columns minus 4 (for left/right borders), divided by 2 (since pieces are 2 chars wide)
        self.cols = max(1, (term_cols - 8) // 2)
        self.board = [[0] * self.cols for _ in range(self.rows)]
        self.score = 0
        self.lines = 0
        self.high_score = 0
        self.record_lines = 0
        
        # Heuristic Weights (Based on Dellacherie's algorithm)
        self.weight_lines = 0.760666
        self.weight_holes = -0.35663
        self.weight_bumpiness = -0.184483
        self.weight_height = -0.510066

    def rotate(self, shape):
        """Rotates a 2D array 90 degrees clockwise."""
        return [list(row) for row in zip(*shape[::-1])]

    def check_collision(self, board, shape, offset):
        """Checks if a shape at a given (x,y) offset collides with the board bounds or blocks."""
        off_x, off_y = offset
        for cy, row in enumerate(shape):
            for cx, cell in enumerate(row):
                if cell:
                    x = cx + off_x
                    y = cy + off_y
                    if x < 0 or x >= self.cols or y >= self.rows:
                        return True
                    if y >= 0 and board[y][x]:
                        return True
        return False

    def get_drop_y(self, board, shape, x):
        """Calculates the lowest valid y-coordinate for a shape dropping at column x."""
        y = 0
        while not self.check_collision(board, shape, (x, y)):
            y += 1
        return y - 1

    def place_shape(self, board, shape, offset):
        """Places a shape on the board and returns the modified board and lines cleared."""
        new_board = copy.deepcopy(board)
        off_x, off_y = offset
        for cy, row in enumerate(shape):
            for cx, cell in enumerate(row):
                if cell:
                    new_board[cy + off_y][cx + off_x] = cell

        # Check for cleared lines
        cleared = 0
        final_board = []
        for row in new_board:
            if all(cell != 0 for cell in row):
                cleared += 1
            else:
                final_board.append(row)
        
        # Add empty lines at the top for those cleared
        for _ in range(cleared):
            final_board.insert(0, [0] * self.cols)
            
        return final_board, cleared

    def evaluate_board(self, board, lines_cleared):
        """Calculates a heuristic score for a given board state."""
        heights = [0] * self.cols
        holes = 0
        aggregate_height = 0

        for col in range(self.cols):
            for row in range(self.rows):
                if board[row][col] != 0:
                    height = self.rows - row
                    heights[col] = height
                    aggregate_height += height
                    
                    # Count holes below the top block of this column
                    for r in range(row + 1, self.rows):
                        if board[r][col] == 0:
                            holes += 1
                    break

        bumpiness = sum(abs(heights[i] - heights[i + 1]) for i in range(self.cols - 1))

        score = (self.weight_lines * lines_cleared) + \
                (self.weight_holes * holes) + \
                (self.weight_bumpiness * bumpiness) + \
                (self.weight_height * aggregate_height)
                
        return score

    def get_best_move(self, shape):
        """Tests all rotations and columns to find the highest scoring placement."""
        best_score = -float('inf')
        best_move = None # (rotation_count, x_position, final_y)

        current_shape = shape
        for rotation in range(4):
            for x in range(-2, self.cols): # Start at -2 to allow pieces to spawn at the left edge
                if not self.check_collision(self.board, current_shape, (x, 0)):
                    y = self.get_drop_y(self.board, current_shape, x)
                    new_board, lines = self.place_shape(self.board, current_shape, (x, y))
                    score = self.evaluate_board(new_board, lines)

                    if score > best_score:
                        best_score = score
                        best_move = (rotation, x, y)
            
            current_shape = self.rotate(current_shape)

        return best_move

    def draw(self, active_shape=None, offset=None):
        """Draws the board to the terminal without stuttering."""
        # Move cursor to home position (0,0) without clearing the screen to prevent flicker
        sys.stdout.write("\033[H")
        
        display_board = copy.deepcopy(self.board)
        
        # Overlay the active falling piece
        if active_shape and offset:
            off_x, off_y = offset
            for cy, row in enumerate(active_shape):
                for cx, cell in enumerate(row):
                    if cell and 0 <= cy + off_y < self.rows and 0 <= cx + off_x < self.cols:
                        display_board[cy + off_y][cx + off_x] = cell

        # Draw the frame
        out = f" SCORE:\t{self.score}\t"
        out += f" HIGH SCORE:\t{self.high_score}\n"
        out += f" LINES:\t{self.lines}\t"
        out += f" RECORD LINES:\t{self.record_lines}\n"
        out += " ╔" + "══" * self.cols + "╗\n"
        for row in display_board:
            out += " ║"
            for cell in row:
                if cell == 0:
                    out += " ."# Empty space
                else:
                    out += COLORS[cell]
            out += "║\n"
        out += " ╚" + "══" * self.cols + "╝\n"
        
        sys.stdout.write(out)
        sys.stdout.flush()

    def run(self):
        """Main perpetual loop."""
        # Hide terminal cursor and clear screen completely ONCE at the start
        sys.stdout.write("\033[?25l")
        sys.stdout.write("\033[2J") 
        
        try:
            while True:
                # Get current terminal dimensions
                term_cols, term_lines = shutil.get_terminal_size()

                if (max(1, (term_cols - 8) // 2) != self.cols) or (max(1, term_lines - 6) != self.rows):
                    # HEIGHT: Total lines minus 4 (1 for score, 1 top border, 1 bottom border, 1 safety buffer)
                    self.rows = max(1, term_lines - 6)
                    # WIDTH: Total columns minus 4 (for left/right borders), divided by 2 (since pieces are 2 chars wide)
                    self.cols = max(1, (term_cols - 8) // 2)
                    self.board = [[0] * self.cols for _ in range(self.rows)]
                    # Hide terminal cursor and clear screen completely ONCE at the start
                    sys.stdout.write("\033[?25l")
                    sys.stdout.write("\033[2J") 
                    os.system('cls' if os.name == 'nt' else 'clear')

                # 1. Spawn a random piece
                piece_type = random.randint(1, 7)
                shape = SHAPES[piece_type]
                
                # 2. AI calculates the absolute best final position
                best_move = self.get_best_move(shape)
                
                # If no valid moves exist, the board is full (Game Over). Reset and loop perpetually.
                if not best_move:
                    self.draw()
                    sys.stdout.write(" GAME OVER\n")
                    sys.stdout.flush()
                    # Clear the screen once on reset so the new borders draw cleanly
                    # Hide terminal cursor and clear screen completely ONCE at the start
                    self.high_score = self.score if self.score > self.high_score else self.high_score
                    self.record_lines = self.lines if self.lines > self.record_lines else self.record_lines
                    self.score = 0
                    self.lines = 0
                    self.board = [[0] * self.cols for _ in range(self.rows)]
                    sys.stdout.write("\033[?25l")
                    sys.stdout.write("\033[2J") 
                    time.sleep(5)
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue

                best_rot, best_x, final_y = best_move
                
                # Apply rotation
                for _ in range(best_rot):
                    shape = self.rotate(shape)

                # 3. Animate the drop for "watchability"
                current_y = 0
                while current_y < final_y:
                    self.draw(shape, (best_x, current_y))
                    time.sleep(0.001) # Speed of the falling piece
                    current_y += 1

                # 4. Lock the piece in place
                self.board, cleared = self.place_shape(self.board, shape, (best_x, final_y))
                self.lines += cleared
                if cleared > 0:
                    self.score += (cleared ** 2) * 100
                
                self.draw()
                # time.sleep(0.001) # Pause briefly after locking

        except KeyboardInterrupt:
            # Show cursor again on exit
            sys.stdout.write("\033[?25h\n")
            sys.exit(0)

if __name__ == "__main__":
    game = TetrisAI()
    game.run()