import random
import time
import copy

class Game2048Logic6x6:
    def __init__(self, size=6):
        self.size = size
        # Cell format: 0 (empty) or {'value': int, 'type': 'normal'|'bomb', 'deadline': float|None, 'max_time': int}
        self.matrix = [[0] * size for _ in range(size)]
        self.score = 0
        self.game_over_reason = None  # 'grid_full' or 'bomb_exploded'
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        empty_cells = [(r, c) for r in range(self.size) for c in range(self.size) if self.matrix[r][c] == 0]
        if empty_cells:
            r, c = random.choice(empty_cells)
            # New tiles are always normal 2 or 4
            self.matrix[r][c] = {'value': 2, 'type': 'normal'} if random.random() < 0.9 else {'value': 4, 'type': 'normal'}

    def get_value(self, cell):
        if cell == 0: return 0
        return cell['value']

    def compress(self, mat):
        new_mat = [[0] * self.size for _ in range(self.size)]
        changed = False
        for i in range(self.size):
            pos = 0
            for j in range(self.size):
                if mat[i][j] != 0:
                    new_mat[i][pos] = mat[i][j]
                    if j != pos:
                        changed = True
                    pos += 1
        return new_mat, changed

    def merge(self, mat):
        changed = False
        score_increment = 0
        current_time = time.time()
        
        for i in range(self.size):
            for j in range(self.size - 1):
                cell_current = mat[i][j]
                cell_next = mat[i][j+1]
                
                if cell_current != 0 and cell_next != 0 and cell_current['value'] == cell_next['value']:
                    # Merge happens
                    new_val = cell_current['value'] * 2
                    score_increment += new_val
                    
                    # Determine if new tile is a bomb
                    # Rules: 16 to 256, 80% chance
                    is_bomb = False
                    deadline = None
                    max_time = None
                    
                    if 16 <= new_val <= 256:
                        if random.random() < 0.5:
                            is_bomb = True
                            # Calculate time: 16->30s, 32->60s, ...
                            # 16=2^4 -> factor=1. 32=2^5 -> factor=2.
                            # log2(16)=4. 4-3=1. 30*1=30.
                            # log2(32)=5. 5-3=2. 30*2=60.
                            import math
                            factor = int(math.log2(new_val)) - 3
                            max_time = 30 * factor
                            deadline = current_time + max_time

                    new_cell = {
                        'value': new_val,
                        'type': 'bomb' if is_bomb else 'normal',
                        'deadline': deadline,
                        'max_time': max_time
                    }
                    
                    mat[i][j] = new_cell
                    mat[i][j+1] = 0
                    changed = True
                    
        return mat, changed, score_increment

    def reverse(self, mat):
        return [row[::-1] for row in mat]

    def transpose(self, mat):
        return [list(row) for row in zip(*mat)]

    def move_left(self):
        new_mat, changed1 = self.compress(self.matrix)
        new_mat, changed2, score_inc = self.merge(new_mat)
        self.score += score_inc
        new_mat, changed3 = self.compress(new_mat)
        self.matrix = new_mat
        return changed1 or changed2 or changed3

    def move_right(self):
        self.matrix = self.reverse(self.matrix)
        changed = self.move_left()
        self.matrix = self.reverse(self.matrix)
        return changed

    def move_up(self):
        self.matrix = self.transpose(self.matrix)
        changed = self.move_left()
        self.matrix = self.transpose(self.matrix)
        return changed

    def move_down(self):
        self.matrix = self.transpose(self.matrix)
        changed = self.move_right()
        self.matrix = self.transpose(self.matrix)
        return changed

    def check_bomb_explosion(self):
        current_time = time.time()
        for r in range(self.size):
            for c in range(self.size):
                cell = self.matrix[r][c]
                if cell != 0 and cell['type'] == 'bomb':
                    if cell['deadline'] and current_time > cell['deadline']:
                        return True
        return False

    def move(self, direction):
        # First, check if any bomb ALREADY exploded before move (though unlikely if frontend is polling)
        if self.check_bomb_explosion():
            return self.get_game_state(force_loss=True, reason='bomb_exploded')

        changed = False
        if direction == 'left': changed = self.move_left()
        elif direction == 'right': changed = self.move_right()
        elif direction == 'up': changed = self.move_up()
        elif direction == 'down': changed = self.move_down()

        if changed:
            self.add_random_tile()
        
        # Check AFTER move
        if self.check_bomb_explosion():
            return self.get_game_state(force_loss=True, reason='bomb_exploded')
            
        return self.get_game_state()

    def get_game_state(self, force_loss=False, reason=None):
        status = 'continue'
        
        if force_loss:
            status = 'lost'
            self.game_over_reason = reason
        elif self.check_bomb_explosion():
             status = 'lost'
             self.game_over_reason = 'bomb_exploded'
        elif not any(0 in row for row in self.matrix) and not self.can_merge():
            status = 'lost'
            self.game_over_reason = 'grid_full'
        elif any(65536 == (c['value'] if c!=0 else 0) for row in self.matrix for c in row):
             status = 'won'
             self.game_over_reason = 'target_reached'

        # Prepare grid for frontend (serialize)
        # We need to send relative time for countdown
        current_time = time.time()
        display_grid = []
        for r in range(self.size):
            row_data = []
            for c in range(self.size):
                cell = self.matrix[r][c]
                if cell == 0:
                    row_data.append(0)
                else:
                    remaining = 0
                    if cell['type'] == 'bomb':
                        remaining = max(0, cell['deadline'] - current_time)
                    
                    row_data.append({
                        'value': cell['value'],
                        'type': cell['type'],
                        'remaining': remaining,
                        'max_time': cell.get('max_time', 0)
                    })
            display_grid.append(row_data)

        return {
            'grid': display_grid,
            'score': self.score,
            'status': status,
            'reason': self.game_over_reason
        }

    def can_merge(self):
        for i in range(self.size):
            for j in range(self.size - 1):
                val1 = self.matrix[i][j]['value'] if self.matrix[i][j] != 0 else 0
                val2 = self.matrix[i][j+1]['value'] if self.matrix[i][j+1] != 0 else 0
                if val1 == val2 and val1 != 0: return True
                
                val1T = self.matrix[j][i]['value'] if self.matrix[j][i] != 0 else 0
                val2T = self.matrix[j+1][i]['value'] if self.matrix[j+1][i] != 0 else 0
                if val1T == val2T and val1T != 0: return True
        return False
