#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import random
from competitive_sudoku.sudoku import GameState
import competitive_sudoku.sudokuai

from .game_logic import legal_moves


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()

    # TODO: replace with alpha-beta minimax search (uses game_logic.legal_moves / apply_move).
    def compute_best_move(self, game_state: GameState) -> None:
        moves = legal_moves(game_state)
        if moves:
            self.propose_move(random.choice(moves))
