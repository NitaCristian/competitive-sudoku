#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

from competitive_sudoku.sudoku import GameState, Move
import competitive_sudoku.sudokuai

from .game_logic import (
    legal_moves,
    apply_move,
    completed_regions,
    REWARDS,
)

INF = float("inf")


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
        score = self.evalGameState(game_state=state, N=state.board.N, technique="non-naive")
        return score if self.me == 1 else -score

    def evalGameState(self, game_state: GameState, N: int, technique="naive"):
        scoreDiff = game_state.scores[0] - game_state.scores[1]
        if technique == "naive":
            return scoreDiff

        m = game_state.board.m
        n = game_state.board.n
        full = set(range(1, N + 1))
        squares = game_state.board.squares

        def reachableCells(allowed, occupied):
            """
            Empty cells a player may play on: empty cells of their starting region plus
            empty (diagonal) neighbours of cells they occupy. Same result as
            GameState.player_squares(), but much faster (no sorting, no method calls per cell).
            """
            if allowed is None:  # classic mode: every empty cell
                return [divmod(k, N) for k, v in enumerate(squares) if v == 0]
            cells = {(i, j) for i, j in allowed if squares[i * N + j] == 0}
            for r, c in occupied:
                for i in range(max(r - 1, 0), min(r + 2, N)):
                    for j in range(max(c - 1, 0), min(c + 2, N)):
                        if squares[i * N + j] == 0:
                            cells.add((i, j))
            return cells

        rows = [set() for _ in range(N)]
        cols = [set() for _ in range(N)]
        blocks = [set() for _ in range(N)]
        rowEmpty, colEmpty, blockEmpty = [0] * N, [0] * N, [0] * N

        for k, v in enumerate(squares):
            i, j = divmod(k, N)
            b = (i // m) * m + j // n
            if v != 0:
                rows[i].add(v)
                cols[j].add(v)
                blocks[b].add(v)
            else:
                rowEmpty[i] += 1
                colEmpty[j] += 1
                blockEmpty[b] += 1

        def features(cells):
            capture = 0
            safety = 0
            mobility = 0
            for i, j in cells:
                if squares[i * N + j] != 0:
                    continue
                b = (i // m) * m + j // n
                if not (full - rows[i] - cols[j] - blocks[b]):
                    continue
                mobility += 1
                completeCheck = (
                    (rowEmpty[i] == 1) + (colEmpty[j] == 1) + (blockEmpty[b] == 1)
                )
                if completeCheck:
                    capture += REWARDS[completeCheck]
                elif not (rowEmpty[i] == 2 or colEmpty[j] == 2 or blockEmpty[b] == 2):
                    safety += 1
            return capture, safety, mobility

        captureSelf, safetySelf, mobilitySelf = features(
            reachableCells(game_state.allowed_squares1, game_state.occupied_squares1)
        )
        captureEnemy, safetyEnemy, mobilityEnemy = features(
            reachableCells(game_state.allowed_squares2, game_state.occupied_squares2)
        )

        if game_state.current_player == 1:
            threat = captureSelf - 0.5 * captureEnemy
        else:
            threat = 0.5 * captureSelf - captureEnemy

        riskWeights = (1.0, 1.0, 0.3, 0.05)  # tuple, not set
        return (
            riskWeights[0] * scoreDiff
            + riskWeights[1] * threat
            + riskWeights[2] * (safetySelf - safetyEnemy)
            + riskWeights[3] * (mobilitySelf - mobilityEnemy)
        )

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

    def alphabeta(
        self, state: GameState, depth: int, alpha: float, beta: float
    ) -> float:
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
