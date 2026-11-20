# Framework internals

How the supplied course code implements the rules. Paths are relative to the
project root. Line numbers are approximate; grep for the names if they drift.

## Contents
1. GameState and SudokuBoard API
2. The simulator's game loop
3. Oracle outcomes and messages
4. Board file format
5. Known framework quirks and bugs
6. Running games
7. This team's game_logic module

## 1. GameState and SudokuBoard API (`competitive_sudoku/sudoku.py`)

`Move(square, value)`: `square` is `(row, col)` zero-based, `value` in 1..N.
`str(move)` → `(0,3) -> 2`. Equality compares square and value.
`TabooMove` is a subclass of `Move` with nothing added.

`SudokuBoard(m, n)`: `m` rows per block, `n` columns per block, `N = m*n`.
- `squares`: flat list of N*N ints, `0` = empty (`SudokuBoard.empty`).
- `get(square)`, `put(square, value)`, `square2index((i, j)) = N*i + j`,
  `index2square(k)`.
- `region_height()` = m, `region_width()` = n, `board_width()`/`board_height()` = N.

`GameState` fields:
- `initial_board`, `board` (current position).
- `taboo_moves`: list of `TabooMove` declared so far.
- `moves`: full history, **including** taboo attempts.
- `scores`: `[score_p1, score_p2]`.
- `current_player`: 1 or 2 — the player to move. When `compute_best_move` is
  called this is always the agent itself.
- `allowed_squares1/2`: starting regions (`None` in classic).
- `occupied_squares1/2`: cells occupied by each player (`None` in classic).
- `occupied_squares()`: the list for `current_player`.
- `player_squares()`: empty allowed cells for `current_player` = empty cells of
  the starting region + empty 8-neighbours of occupied cells, deduplicated and
  sorted. Returns `None` in classic mode (meaning all empty cells). It is
  computed from scratch on each call and is comparatively slow (it dominated a
  profile of an alpha-beta search), so avoid calling it more than needed.

`SudokuAI` base (`competitive_sudoku/sudokuai.py`): `propose_move(move)` writes
the move into a shared list under a lock; `player_number` is set by the
simulator. `save`/`load` exist but storing information between turns is not
allowed in A1.

## 2. The simulator's game loop (`simulate_game.py`, `simulate_game()`)

- `number_of_moves` = number of empty cells at the start. The loop runs while
  fewer accepted moves than that have been played (taboo attempts do not count)
  and fewer than 2 players are in `finished_players`.
- Each turn: if `player_squares() == []` the player "cannot move": logged, added
  to `finished_players`, turn passes. **`finished_players` is never cleared**, so
  the game stops once each player has been stuck at least once, even if not at
  the same time. (The official rules just skip the turn; this difference is an
  edge case.)
- Otherwise `compute_best_move` runs in a separate process for `--time`
  seconds (default 0.5 in simulate_game.py, 3.0 in play_match.py), then the
  process is terminated and the last proposed move is read.
- Proposed `(0,0,0)` (nothing proposed) → "No move was supplied", proposer loses.
- Proposal already in `taboo_moves` → "is a taboo move", proposer loses.
- Otherwise the oracle is called with `--move` and `--allowed` (the player's
  allowed cells).
- After an accepted or taboo move: reward added to the mover's score,
  `current_player` flips.
- At the end the higher score wins; equal is a draw (0.5 - 0.5).

## 3. Oracle outcomes (`bin/solve_sudoku`, output parsed by simulate_game.py)

| Oracle output contains | Meaning | Effect |
|---|---|---|
| `Invalid move` | value out of range (0 or > N) | proposer loses ("is not a valid move") |
| `Illegal move` | cell non-empty, cell not allowed, or C0 duplicate | proposer loses ("is not a legal move") |
| `has no solution` | sudoku unsolvable after the move | taboo: not placed, 0 points, appended to `taboo_moves` and `moves` |
| `The score is X` | accepted | placed, cell occupied, X points |

(Verified by probing the oracle on a 4x4 board.) Already-taboo proposals are
caught by simulate_game.py before the oracle is called. The agent must never
invoke this executable.

## 4. Board file format (`boards/*.txt`)

```
rows = 2          # m: rows per block
columns = 3       # n: columns per block
board =
   .   2-   .   4-   .   .
   ...
moves = [(4,5) -> 1, ...]          # optional history
taboo-moves = [(1,3) -> 4, ...]    # optional
scores = [0, 0]                    # optional
```

`.` = empty; a value with `+` is occupied by player 1, `-` by player 2.
Supplied boards: `empty-2x2`, `empty-2x3`, `empty-3x3`, `empty-3x4`,
`empty-4x4`, `board-2x2`, `board-2x3`.

## 5. Known framework quirks and bugs

- `--playmode=classic` crashes in `pretty_print_sudoku_board` (sudoku.py
  ~line 163: `square in gamestate.occupied_squares1` with `None`), with or
  without `--board`, before any move. Classic games cannot be run as supplied.
- `--playmode=classic --board=board-2x3.txt` additionally fails parsing the
  `+`/`-` suffixes.
- `random_player` / `greedy_player` call the solver as a subprocess and can time
  out at `--time=0.5` on Windows ("No move was supplied"). Use a larger `--time`
  or `--warm-up` when testing against them.
- `play_match.py` does not pass `--playmode`; it always uses the default (`rows`).
- README mentions positional player arguments (v14 changelog), but this
  version of `simulate_game.py` uses `--first=` / `--second=`.

## 6. Running games

```
python simulate_game.py --help
python simulate_game.py --check                       # solver works?
python simulate_game.py --first=team59_A1 --second=greedy_player \
    --board=boards/empty-3x3.txt --time=1.0 --playmode=rows --quiet
python play_match.py team59_A1 greedy_player --board=boards/empty-3x3.txt --count=6
```

## 7. This team's game_logic module (`team59_A1/game_logic.py`)

Implements the rules for the agent (verified against the oracle over thousands
of moves):
- `legal_moves(state)`: all moves for `state.current_player` passing §3 checks
  1-5 of SKILL.md (empty, allowed, C0, not taboo). Only the allowed-cells part
  depends on the player.
- `apply_move(state, move) -> (new_state, reward)`: returns a copy (input is not
  mutated) with the value placed, the move appended, the cell added to the
  mover's occupied squares, the reward (0/1/3/7) added, and the turn passed —
  unless the opponent has no empty allowed cell, in which case the mover moves
  again (skip rule). Assumes the oracle accepts the move (minimax cannot know
  about future taboos).
- There is no `is_terminal`: in a state returned by `apply_move`, `legal_moves`
  is empty exactly when the game is over (board full / nobody can move) or the
  search reached an impossible dead end (possible because `apply_move` assumes
  every move is accepted). Minimax should evaluate the state as a leaf when
  `depth == 0 or not moves`.
- In minimax decide max/min by comparing `state.current_player` with the root
  player, not by depth parity, because skipped turns break alternation.

Read the file itself for the current version before relying on details here.
