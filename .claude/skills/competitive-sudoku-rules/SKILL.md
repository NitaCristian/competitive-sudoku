---
name: competitive-sudoku-rules
description: Authoritative reference for the rules of Competitive Sudoku (the course's rules_full.pdf), the Assignment A1 constraints, and exactly how the course framework (simulate_game.py, competitive_sudoku/sudoku.py, the solve_sudoku oracle) enforces them. Use this skill whenever the user asks anything about how the game works, whether a move is legal, allowed, taboo or losing, how scoring/points/regions work, who moves next, skipped turns, when the game ends, play modes (rows/border/random/classic), GameState fields, or what the agent is and isn't allowed to do (solver use, threads, numpy, time limits, saving state) — and also whenever writing or reviewing move generation, apply_move, evaluation functions, minimax/alpha-beta, or tests for this project, even if the user doesn't say "rules".
---

# Competitive Sudoku: rules and framework

This project is a university course assignment: build an AI for a two-player
"Competitive Sudoku" game. Answers about the rules must be exact, because a
single rule mistake in the agent (e.g. proposing a move on a non-allowed square)
loses the game instantly. When the official rules and the framework's actual
behaviour differ, say so explicitly and say which one applies in practice
(the framework is what grades and runs the games).

For framework internals (GameState API, simulator loop, oracle messages, board
file format, known framework bugs) read `references/framework.md`.

## 1. The board

- Grid of N x N cells with N = m * n. Blocks are m rows x n columns.
  In code: `board.m` = rows per block (`region_height()`), `board.n` = columns
  per block (`region_width()`), `board.N` = N. Blocks need not be square
  (2x3 gives a 6x6 board with 2-row, 3-column blocks; 3x2 is different).
- Three region types: rows, columns, blocks; N of each. Every cell is in exactly
  one of each.
- Cells are empty (`SudokuBoard.empty == 0`) or hold 1..N.
- **C0**: values within any region must be unique.
- Coordinates are zero-based `(row, col)`; flat index `k = row * N + col`.
  Block of `(i, j)`: top-left `((i // m) * m, (j // n) * n)`,
  block number `(i // m) * m + (j // n)`.
- Puzzles need not have a unique solution; starting from a completely empty
  grid is expected. Code must work for any m, n > 1.

## 2. Start

- Both players start with 0 points. Player 1 moves first.
- Each player has a **starting region**. In the official rules (and the default
  `rows` play mode) player 1 starts on the **top row** (row 0) and player 2 on
  the **bottom row** (row N-1). Other modes exist in the framework; see §7.

## 3. A turn

The active player proposes one move: `(square, value)`. A proposal must satisfy
all of the following, otherwise **the proposer immediately loses the game**:

1. the cell is empty;
2. the value is in 1..N;
3. placing it respects C0 (value not already in that row, column or block);
4. the cell is **allowed** for that player: it is in their starting region, or
   it is adjacent, *including diagonally* (8-neighbourhood), to a cell the
   player already occupies;
5. the (cell, value) pair has not previously been declared taboo.

Also losing in the framework: proposing no move at all before time runs out.

Allowed cells are *derived*, not stored: starting region + 8-neighbours of
occupied cells, filtered to empty cells. They can overlap between players
(a cell can be allowed for both). Only cells the player *occupies* (cells
where their move was accepted) extend their area; cells filled by the
opponent and taboo attempts do not. When a game starts from a board file,
pre-filled cells marked `+` count as occupied by player 1 and `-` by player 2.

If the active player has **no empty allowed cell**, they skip their turn
automatically (they do not propose a move and do not lose).

## 4. The oracle and taboo moves

After a proposal passes the checks in §3, the oracle checks whether the sudoku
is still **solvable** (can be completed to a full valid grid) with the move.

- **Solvable** → the move is played: value placed, the cell becomes *occupied*
  by the player, points are scored (§5).
- **Unsolvable** → the (cell, value) pair is declared **taboo**: the value is
  *not* placed, the cell is *not* occupied, the player scores 0, and the pair is
  appended to `game_state.taboo_moves` (and to `game_state.moves`).

Either way, the turn then passes to the opponent.

Key consequences:
- A taboo move is not a loss; it costs a turn. Proposing a pair that is
  *already* taboo is a loss.
- Taboo is per (cell, value) pair and permanent for the rest of the game, for
  both players.
- A taboo move can be played deliberately as a "pass" (useful when every real
  move would set the opponent up to score).
- Since the board is always kept solvable, every empty cell has at least one
  value that is not taboo-worthy. So a player with an empty allowed cell always
  has at least one move the oracle would accept.
- The agent cannot know in advance which legal moves are taboo-worthy: it may
  not call the solver, and A1 says not to solve the sudoku. It can only avoid
  moves already in `taboo_moves`.

Example (4x4): row 0 has empty cells A and B, and only 3 and 4 are missing.
A's column already contains 4, so A must be 3 and B must be 4. Playing 3 in B
violates no rule (no duplicate yet) but leaves A with no possible value → taboo.

## 5. Scoring

A move **completes** a region if the cell was the last empty cell of that
region. One move can complete up to three regions (its row, column and block):

| Regions completed | Points |
|---|---|
| 0 | 0 |
| 1 | 1 |
| 2 | 3 |
| 3 | 7 |

Check completion *after* placing the value: count how many of the cell's row,
column and block are now full. Points go to the player who made the move,
regardless of who filled the other cells in the region. Taboo moves score 0.

## 6. End of the game

- A player proposes a losing move (§3) → they lose immediately (the simulator
  reports the opponent as winner; score is irrelevant).
- The grid is completely filled → highest score wins; equal scores tie.
- Framework addition: the simulator also stops when both players have been
  unable to move (see `references/framework.md`).

## 7. Play modes (framework `--playmode`, default `rows`)

| Mode | Starting region P1 | Starting region P2 |
|---|---|---|
| `rows` (official rules) | row 0 | row N-1 |
| `border` | whole outer border | whole outer border (same set) |
| `random` | N random cells | N other random cells |
| `classic` | no restriction: every empty cell is allowed | same |

In `classic`, `allowed_squares1/2` and `occupied_squares1/2` are `None`, and
`game_state.player_squares()` returns `None` (meaning "all empty squares").
In the supplied framework classic mode crashes in the board printer, so it
cannot actually be played via `simulate_game.py`. This team plays only the
competitive (restricted) modes.

## 8. Time controls (anytime agent)

- The agent does not know how much time it has. It may call
  `self.propose_move(move)` as often as it likes; the **last** proposal when
  time runs out is used. When time is up, the process running
  `compute_best_move` is killed.
- So: propose a legal move immediately, then keep improving (e.g. iterative
  deepening) and re-propose. Never risk proposing nothing.

## 9. Assignment A1 constraints (what the agent may do)

- Implement `compute_best_move(self, game_state)` in `teamXX_A1/sudokuai.py`
  (this team: `team59_A1`). Core logic must be **minimax with alpha-beta
  pruning**; iterative deepening, quiescence search and transposition tables
  are allowed extensions.
- Generate **all** legal moves (§3 checks 1-5); you need an evaluation
  function (e.g. score difference).
- Do **not** (yet) solve the sudoku and restrict search to "solution" moves;
  A1 is about searching all legal moves.
- Only the Python standard library and NumPy 1.22.3. Grading server runs
  **Python 3.10.9**: no newer syntax/features.
- **Not allowed**: invoking `bin/solve_sudoku` (or reverse-engineering it);
  multiple threads/processes; GPU.
- No information may be stored between turns: a new `SudokuAI` instance is
  made each turn and only `game_state` may be used (the base class's
  save/load is not for A1).
- All code (and any data files) must live inside the team's module folder and
  run via `simulate_game.py` without changes to the framework.
- Submission: zip the folder itself (not just its contents), e.g.
  `team59_A1.zip`, upload to Canvas → M1 (Momotor).

## How to answer

- Cite the rule (section above) and, when relevant, the framework location
  (file:line) where it is enforced.
- If the question is about a concrete position, work through §3 checks one by
  one, then the oracle (§4), then scoring (§5), then whose turn is next.
- Point out any place where the user's assumption differs from the rules
  (common ones: diagonal adjacency counts; opponent-filled cells don't extend
  your area; taboo ≠ loss, but repeating a taboo = loss; points are 1/3/7 not
  1/2/3; a stuck player skips instead of losing).
