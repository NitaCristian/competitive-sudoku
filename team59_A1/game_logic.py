from typing import List, Optional, Tuple

from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, Square

# Points scored for completing 0, 1, 2 or 3 regions with a single move.
REWARDS = (0, 1, 3, 7)


def block_origin(board: SudokuBoard, square: Square) -> Square:
    """Returns the top-left square of the block containing `square`."""
    i, j = square
    m, n = board.m, board.n
    return (i // m) * m, (j // n) * n


def allowed_cells(state: GameState) -> List[Square]:
    """Returns the empty squares the current player may fill in."""
    squares = state.player_squares()
    if squares is None:
        return [
            state.board.index2square(k)
            for k, v in enumerate(state.board.squares)
            if v == SudokuBoard.empty
        ]
    return squares


def legal_moves(state: GameState) -> List[Move]:
    """
    Returns all moves for the current player that do not immediately lose the game:
    the square is empty and allowed for the player, the value does not already appear in
    the square's row, column or block, and the move is not taboo.
    """
    board = state.board
    N, m, n = board.N, board.m, board.n
    squares = board.squares

    # Values already present in every row, column and block.
    rows = [set() for _ in range(N)]
    cols = [set() for _ in range(N)]
    blocks = [set() for _ in range(N)]
    for k, value in enumerate(squares):
        if value != SudokuBoard.empty:
            i, j = divmod(k, N)
            rows[i].add(value)
            cols[j].add(value)
            blocks[(i // m) * m + j // n].add(value)

    taboo = {(t.square, t.value) for t in state.taboo_moves}
    all_values = range(1, N + 1)

    moves = []
    for square in allowed_cells(state):
        i, j = square
        used = rows[i] | cols[j] | blocks[(i // m) * m + j // n]
        for value in all_values:
            if value not in used and (square, value) not in taboo:
                moves.append(Move(square, value))
    return moves


def completed_regions(board: SudokuBoard, square: Square) -> int:
    """
    Returns how many of the row, column and block containing `square` are completely
    filled. Call this after the value has been placed on `square`.
    """
    N, m, n = board.N, board.m, board.n
    squares = board.squares
    empty = SudokuBoard.empty
    i, j = square

    row_full = all(squares[i * N + c] != empty for c in range(N))
    col_full = all(squares[r * N + j] != empty for r in range(N))
    bi, bj = block_origin(board, square)
    block_full = all(squares[r * N + c] != empty
                     for r in range(bi, bi + m) for c in range(bj, bj + n))
    return row_full + col_full + block_full


def _copy_state(state: GameState) -> GameState:
    """A cheap copy of `state`: everything apply_move changes is copied, the rest is shared."""
    board = SudokuBoard(state.board.m, state.board.n)
    board.squares = state.board.squares[:]

    def copy_list(squares: Optional[List[Square]]) -> Optional[List[Square]]:
        return None if squares is None else squares[:]

    return GameState(
        initial_board=state.initial_board,       # never changes, shared
        board=board,
        taboo_moves=state.taboo_moves,           # not changed by apply_move, shared
        moves=state.moves[:],
        scores=state.scores[:],
        current_player=state.current_player,
        allowed_squares1=state.allowed_squares1,  # starting regions never change, shared
        allowed_squares2=state.allowed_squares2,
        occupied_squares1=copy_list(state.occupied_squares1),
        occupied_squares2=copy_list(state.occupied_squares2),
    )


def has_allowed_cell(state: GameState) -> bool:
    """Returns True if the current player has at least one empty square they may play on."""
    return len(allowed_cells(state)) > 0


def is_board_full(state: GameState) -> bool:
    return SudokuBoard.empty not in state.board.squares


def apply_move(state: GameState, move: Move) -> Tuple[GameState, int]:
    """
    Plays `move` for the current player and returns (new_state, reward). `state` is not
    modified.
    """
    new_state = _copy_state(state)
    player = state.current_player

    new_state.board.put(move.square, move.value)
    new_state.moves.append(move)

    occupied = new_state.occupied_squares()
    if occupied is not None:
        occupied.append(move.square)

    reward = REWARDS[completed_regions(new_state.board, move.square)]
    new_state.scores[player - 1] += reward

    new_state.current_player = 3 - player
    if not is_board_full(new_state) and not has_allowed_cell(new_state):
        new_state.current_player = player
        if not has_allowed_cell(new_state):
            new_state.current_player = 3 - player  # nobody can move; game over

    return new_state, reward
