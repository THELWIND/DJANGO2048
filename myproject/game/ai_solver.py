import random
import copy

class Game2048AI:
    def __init__(self, logic_class):
        self.LogicClass = logic_class
        # Gradient map to encourage keeping high tiles in the top-left corner
        self.WEIGHT_MATRIX = [
            [4096, 1024, 256, 64],
            [16,   32,   64,  128],
            [8,    4,    2,   1],
            [0,    0,    0,   0]
        ]

    def get_best_move(self, grid):
        """
        Returns the best move ('left', 'right', 'up', 'down')
        based on Expectimax search with depth 2.
        """
        best_score = -float('inf')
        best_move = None
        directions = ['left', 'right', 'up', 'down']
        
        # Depth 2 is a good balance for Python web performance
        # Depth: 0 (Root) -> 1 (Random Tile) -> 2 (Move) -> Evaluate
        depth = 2 

        for direction in directions:
            # Simulate move
            sim_game = self.LogicClass()
            sim_game.matrix = copy.deepcopy(grid)
            sim_game.score = 0
            
            # We need to modify logic class to return 'changed' bool strictly for simulation
            # But here we can just use the move method and check if grid changed
            old_grid = copy.deepcopy(sim_game.matrix)
            sim_game.move(direction) # This adds a random tile in current logic, which interferes with expectimax
            
            # Wait, the current logic.py adds a random tile automatically inside move().
            # For Expectimax, we need to separate the "Move" phase from the "Random Tile" phase.
            # Since we can't easily change logic.py without breaking other things, 
            # we will check if the move was valid by comparing grids.
            
            if sim_game.matrix == old_grid:
                continue # Invalid move

            # Since logic.py's move() ALREADY added a random tile, 
            # we constitute this as one full "ply" (Player Move + Chance).
            # So we can just evaluate the resulting grid directly.
            
            score = self.expectimax(sim_game.matrix, depth - 1, is_player_turn=True)
            
            if score > best_score:
                best_score = score
                best_move = direction

        # If no move possible (should be handled by game over logic elsewhere), return random
        if best_move is None:
            return random.choice(directions)
            
        return best_move

    def expectimax(self, grid, depth, is_player_turn):
        if depth == 0:
            return self.evaluate(grid)

        if is_player_turn:
            # Maximize score
            best_val = -float('inf')
            for direction in ['left', 'right', 'up', 'down']:
                sim_game = self.LogicClass()
                sim_game.matrix = copy.deepcopy(grid)
                
                old_grid = copy.deepcopy(sim_game.matrix)
                
                # logic.move() executes move AND adds random tile. 
                # This simplifies our recursion significantly but reduces theoretical accuracy.
                # For a fast web AI, this "Simulation" approach is acceptable.
                sim_game.move(direction)
                
                if sim_game.matrix != old_grid:
                    val = self.expectimax(sim_game.matrix, depth - 1, True)
                    best_val = max(best_val, val)
            
            # If no moves, return evaluation
            return best_val if best_val != -float('inf') else self.evaluate(grid)
        
        else:
            # Expectation (Chance node) - Not strictly needed here because logic.py handles it
            # but for proper implementation we usually split. 
            # Given existing logic.py structure, we treat the "Move" function as a black box 
            # that transitions state completely.
            pass

    def evaluate(self, grid):
        """
        Heuristic function: Sum of (Tile Value * Weight)
        """
        score = 0
        penalty = 0
        
        for r in range(4):
            for c in range(4):
                val = grid[r][c]
                score += val * self.WEIGHT_MATRIX[r][c]
                
                # Penalty for non-monotonic rows/cols (optional, simplified here)
                
        # Bonus for empty tiles
        empty_count = sum(row.count(0) for row in grid)
        score += empty_count * 1000 
        
        return score
