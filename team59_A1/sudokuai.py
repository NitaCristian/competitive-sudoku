#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

from collections import defaultdict
import random
from competitive_sudoku.sudoku import GameState
import competitive_sudoku.sudokuai

from .game_logic import legal_moves
import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove, Square
import competitive_sudoku.sudokuai
from typing import Tuple
import math


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()

     #very simple difference of the scores
    def evalGameState(game_state: GameState, technique = 'naive'):
      if technique == 'naive':
          return game_state.scores[0] - game_state.scores[1]

    # TODO: replace with alpha-beta minimax search (uses game_logic.legal_moves / apply_move).
    def compute_best_move(self, game_state: GameState) -> None:
        moves = legal_moves(game_state)
        if moves:
            self.propose_move(random.choice(moves))
    # N.B. This is a very naive implementation.
    def compute_best_move_differenImplementation(self, game_state: GameState) -> None:
        N = game_state.board.N

        # Check whether a cell is empty, a value in that cell is not taboo, and that cell is allowed
        def possible(i, j, value):
            return game_state.board.get((i, j)) == SudokuBoard.empty \
                   and not TabooMove((i, j), value) in game_state.taboo_moves \
                       and (i, j) in game_state.player_squares()

        all_moves = [Move((i, j), value) for i in range(N) for j in range(N)
                     for value in range(1, N+1) if possible(i, j, value)]


        def checkForbiddenValues(game_state: GameState, N: int):

            boxSize = math.isqrt(N)
            forbiddenRows = defaultdict(set)
            forbiddenColumns = defaultdict(set)
            forbiddenBoxes = defaultdict(set)
            # forbiddenRows = {}
            # forbiddenColumns = {}
            # forbiddenBoxes = {}

            for i in range(N):
                for j in range(N):
                    targetSquare = (i, j)
                    value = game_state.board.get(targetSquare)
                    if value != 0:
                      forbiddenRows[i].add(value)
                      forbiddenColumns[j].add(value)
                      forbiddenBoxes[(i // boxSize, j // boxSize)].add(value)
            return forbiddenRows, forbiddenColumns, forbiddenBoxes

            #print(game_state.board)

        notAllowedRowVals, notAllowedColVals, notAllowedBoxes = checkForbiddenValues(game_state, N)

        #python simulate_game.py --first=team59_A1; just for quick access
        def filterLegalMoves(all_moves: list[Move], game_state: GameState, notAllowedRow, notAllowedCol, notAllowedBox):
            boxSize = math.isqrt(N)
            legal_moves = []
            for move in all_moves:
                notPasses = 0
                if move.value in notAllowedRow[move.square[0]]:
                  notPasses = 1
                if move.value in notAllowedCol[move.square[1]]:
                  notPasses = 1
                if move.value in notAllowedBox[(move.square[0] // boxSize, move.square[1] // boxSize)]:
                  notPasses = 1
                if notPasses == 0:
                   legal_moves.append(move)

            return legal_moves








        print("Current game state: ", self.evalGameState(game_state))
        # print("Current occupied squares: ")
        #checkForbiddenValues(game_state, N)
        all_moves = filterLegalMoves(all_moves, game_state, notAllowedRowVals, notAllowedColVals, notAllowedBoxes)
        # print("Player 1 all moves")
        print([(move.square, move.value) for move in all_moves])
        move = random.choice(all_moves)

        self.propose_move(move)
        while True:
            time.sleep(0.2)
            self.propose_move(random.choice(all_moves))
