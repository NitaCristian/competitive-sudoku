#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

from competitive_sudoku.sudoku import GameState, Move
import competitive_sudoku.sudokuai

from .game_logic import legal_moves, apply_move, evalGameState, completed_regions, REWARDS

INF = float('inf')

class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI using minimax search with alpha-beta pruning and iterative deepening.
    """

    def __init__(self):
        super().__init__()
        self.me = 1

    def evaluate(self, state: GameState) -> float:
        """
        Score of `state` from OUR point of view (higher = better for us).
        evalGameState scores from player 1's point of view, so flip it if we are player 2.
        """
        score = evalGameState(state)
        return score if self.me == 1 else -score

    def compute_best_move(self, game_state: GameState) -> None:
        self.me = game_state.current_player

        moves = legal_moves(game_state)
        if not moves:
            return

        children = []
        for move in moves:
            child, reward = apply_move(game_state, move)
            children.append((move, child, reward))
        children.sort(key=lambda c: -c[2])

        best_move = children[0][0]
        self.propose_move(best_move)

        empty_squares = game_state.board.squares.count(0)
        for depth in range(1, empty_squares + 1):
            children.sort(key=lambda c: c[0] != best_move)

            alpha = -INF
            depth_best_move, depth_best_value = None, -INF
            for move, child, _ in children:
                value = self.alphabeta(child, depth - 1, alpha, INF)
                if value > depth_best_value:
                    depth_best_move, depth_best_value = move, value
                alpha = max(alpha, value)

            best_move = depth_best_move
            self.propose_move(best_move)

    def alphabeta(self, state: GameState, depth: int, alpha: float, beta: float) -> float:
        """
        Minimax value of `state` searched `depth` plies deep, with alpha-beta pruning.
        Whether this is a MAX or MIN node is decided by whose turn it is, not by alternating
        levels, because apply_move can give a player two turns in a row when the opponent
        has no square to play on.
        """
        if depth == 0:
            return self.evaluate(state)

        moves = legal_moves(state)
        if not moves:  # board full or player stuck
            return self.evaluate(state)

        moves.sort(key=lambda mv: -self.immediate_reward(state, mv))

        if state.current_player == self.me:  # MAX node
            value = -INF
            for move in moves:
                child, _ = apply_move(state, move)
                value = max(value, self.alphabeta(child, depth - 1, alpha, beta))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break  # beta cut-off
            return value
        else:  # MIN node
            value = INF
            for move in moves:
                child, _ = apply_move(state, move)
                value = min(value, self.alphabeta(child, depth - 1, alpha, beta))
                beta = min(beta, value)
                if alpha >= beta:
                    break  # alpha cut-off
            return value

    @staticmethod
    def immediate_reward(state: GameState, move: Move) -> int:
        """Points `move` would score, computed by placing the value temporarily (no copy)."""
        board = state.board
        k = board.square2index(move.square)
        board.squares[k] = move.value
        reward = REWARDS[completed_regions(board, move.square)]
        board.squares[k] = 0
        return reward
