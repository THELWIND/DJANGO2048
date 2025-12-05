import random

class Game2048Logic:
    def __init__(self, size=4):
        self.size = size
        self.matrix = [[0] * size for _ in range(size)]
        self.score = 0
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        empty_cells = [(r, c) for r in range(self.size) for c in range(self.size) if self.matrix[r][c] == 0]
        if empty_cells:
            r, c = random.choice(empty_cells)
            self.matrix[r][c] = 2 if random.random() < 0.9 else 4

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
        for i in range(self.size):
            for j in range(self.size - 1):
                if mat[i][j] == mat[i][j + 1] and mat[i][j] != 0:
                    mat[i][j] *= 2
                    score_increment += mat[i][j]
                    mat[i][j + 1] = 0
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

    def move(self, direction):
        changed = False
        if direction == 'left': changed = self.move_left()
        elif direction == 'right': changed = self.move_right()
        elif direction == 'up': changed = self.move_up()
        elif direction == 'down': changed = self.move_down()

        if changed:
            self.add_random_tile()
        
        return self.get_game_state()

    def get_game_state(self):
        # Check Game Over logic
        if any(0 in row for row in self.matrix):
            status = 'continue'
        elif self.can_merge():
            status = 'continue'
        else:
            status = 'lost'
        
        return {
            'grid': self.matrix,
            'score': self.score,
            'status': status
        }

    def can_merge(self):
        for i in range(self.size):
            for j in range(self.size - 1):
                if self.matrix[i][j] == self.matrix[i][j+1]: return True
                if self.matrix[j][i] == self.matrix[j+1][i]: return True
        return False