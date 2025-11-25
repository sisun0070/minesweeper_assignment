"""
Core game logic for Minesweeper.

This module contains pure domain logic without any pygame or pixel-level
concerns. It defines:
- CellState: the state of a single cell
- Cell: a cell positioned by (col,row) with an attached CellState
- Board: grid management, mine placement, adjacency computation, reveal/flag

The Board exposes imperative methods that the presentation layer (run.py)
can call in response to user inputs, and does not know anything about
rendering, timing, or input devices.
"""

import random
from typing import List, Tuple


class CellState:
    """Mutable state of a single cell.

    Attributes:
        is_mine: Whether this cell contains a mine.
        is_revealed: Whether the cell has been revealed to the player.
        is_flagged: Whether the player flagged this cell as a mine.
        adjacent: Number of adjacent mines in the 8 neighboring cells.
    """

    def __init__(self, is_mine: bool = False, is_revealed: bool = False, is_flagged: bool = False, adjacent: int = 0):
        self.is_mine = is_mine
        self.is_revealed = is_revealed
        self.is_flagged = is_flagged
        self.adjacent = adjacent


class Cell:
    """Logical cell positioned on the board by column and row."""

    def __init__(self, col: int, row: int):
        self.col = col
        self.row = row
        self.state = CellState()


class Board:
    """Minesweeper board state and rules.

    Responsibilities:
    - Generate and place mines with first-click safety
    - Compute adjacency counts for every cell
    - Reveal cells (iterative flood fill when adjacent == 0)
    - Toggle flags, check win/lose conditions
    """

    def __init__(self, cols: int, rows: int, mines: int):
        self.cols = cols
        self.rows = rows
        self.num_mines = mines
        self.cells: List[Cell] = [Cell(c, r) for r in range(rows) for c in range(cols)]
        self._mines_placed = False
        self.revealed_count = 0
        self.game_over = False
        self.win = False

    def index(self, col: int, row: int) -> int:
        """Return the flat list index for (col,row)."""
        return row * self.cols + col

    def is_inbounds(self, col: int, row: int) -> bool:
        # TODO: Return True if (col,row) is inside the board bounds.
        return 0 <= col < self.cols and 0 <= row < self.rows

    def neighbors(self, col: int, row: int) -> List[Tuple[int, int]]:
        # TODO: Return list of valid neighboring coordinates around (col,row).
        deltas = [
            (-1, -1), (0, -1), (1, -1),
            (-1, 0),            (1, 0),
            (-1, 1),  (0, 1),  (1, 1),
        ]
        result: List[Tuple[int, int]] = []
        for dc, dr in deltas:
            nc, nr = col + dc, row + dr
            if self.is_inbounds(nc, nr):
                result.append((nc, nr))
        return result


    def place_mines(self, safe_col: int, safe_row: int) -> None:
        # TODO: Place mines randomly, guaranteeing the first click and its neighbors are safe. And Compute adjacency counts
        all_positions = [(c, r) for r in range(self.rows) for c in range(self.cols)]

        forbidden = {(safe_col, safe_row)} | set(self.neighbors(safe_col, safe_row))
        pool = [p for p in all_positions if p not in forbidden]
        random.shuffle(pool)

        for (c, r) in pool[: self.num_mines]:
            self.cells[self.index(c, r)].state.is_mine = True

        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[self.index(c, r)]
                if cell.state.is_mine:
                    continue
                count = 0
                for (nc, nr) in self.neighbors(c, r):
                    if self.cells[self.index(nc, nr)].state.is_mine:
                        count += 1
                cell.state.adjacent = count

        self._mines_placed = True

    def reveal(self, col: int, row: int) -> None:
        # TODO: Reveal a cell; if zero-adjacent, iteratively flood to neighbors.
        if not self.is_inbounds(col, row):
            return
        if self.game_over or self.win:
            return

        # 첫 클릭이면 이 시점에 지뢰 배치
        if not self._mines_placed:
            self.place_mines(col, row)

        cell = self.cells[self.index(col, row)]
        # 이미 열린 칸이거나 깃발 꽂힌 칸이면 무시
        if cell.state.is_revealed or cell.state.is_flagged:
            return

        # 지뢰를 밟은 경우
        if cell.state.is_mine:
            cell.state.is_revealed = True
            self.game_over = True
            self._reveal_all_mines()
            return

        # flood fill (스택을 이용한 반복적 방식)
        stack = [(col, row)]
        while stack:
            c, r = stack.pop()
            if not self.is_inbounds(c, r):
                continue
            cur = self.cells[self.index(c, r)]
            if cur.state.is_revealed or cur.state.is_flagged:
                continue
            if cur.state.is_mine:
                continue  # 안전장치

            cur.state.is_revealed = True
            self.revealed_count += 1

            # 주변 지뢰가 0이면 이웃 칸들도 연쇄적으로 열기
            if cur.state.adjacent == 0:
                for (nc, nr) in self.neighbors(c, r):
                    neigh = self.cells[self.index(nc, nr)]
                    if not neigh.state.is_revealed and not neigh.state.is_flagged:
                        stack.append((nc, nr))

        self._check_win()

    def toggle_flag(self, col: int, row: int) -> None:
        # TODO: Toggle a flag on a non-revealed cell.
        # if not self.is_inbounds(col, row):
        #     return
        
        pass

    def flagged_count(self) -> int:
        # TODO: Return current number of flagged cells.
        pass

    def _reveal_all_mines(self) -> None:
        """Reveal all mines; called on game over."""
        for cell in self.cells:
            if cell.state.is_mine:
                cell.state.is_revealed = True

    def _check_win(self) -> None:
        """Set win=True when all non-mine cells have been revealed."""
        total_cells = self.cols * self.rows
        if self.revealed_count == total_cells - self.num_mines and not self.game_over:
            self.win = True
            for cell in self.cells:
                if not cell.state.is_revealed and not cell.state.is_mine:
                    cell.state.is_revealed = True




