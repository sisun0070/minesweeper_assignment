"""
Pygame presentation layer for Minesweeper.

This module owns:
- Renderer: all drawing of cells, header, and result overlays
- InputController: translate mouse input to board actions and UI feedback
- Game: orchestration of loop, timing, state transitions, and composition

The logic lives in components.Board; this module should not implement rules.
"""

import random
import sys
from dataclasses import dataclass

import pygame

import config
from components import Board
from pygame.locals import Rect


@dataclass
class UIButton:
    """Simple clickable UI element placed in the header region."""

    rect: Rect
    label: str
    kind: str
    value: str | None = None
    disabled: bool = False

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


class Renderer:
    """Draws the Minesweeper UI.

    Knows how to draw individual cells with flags/numbers, header info,
    and end-of-game overlays with a semi-transparent background.
    """

    def __init__(self, screen: pygame.Surface, board: Board):
        self.screen = screen
        self.board = board
        self.font = pygame.font.Font(config.font_name, config.font_size)
        self.header_font = pygame.font.Font(config.font_name, config.header_font_size)
        self.result_font = pygame.font.Font(config.font_name, config.result_font_size)
        self.button_font = pygame.font.Font(config.font_name, 18)

    def cell_rect(self, col: int, row: int) -> Rect:
        """Return the rectangle in pixels for the given grid cell."""
        x = config.margin_left + col * config.cell_size
        y = config.margin_top + row * config.cell_size
        return Rect(x, y, config.cell_size, config.cell_size)

    def draw_cell(self, col: int, row: int, highlighted: bool) -> None:
        """Draw a single cell, respecting revealed/flagged state and highlight."""
        cell = self.board.cells[self.board.index(col, row)]
        rect = self.cell_rect(col, row)
        if cell.state.is_revealed:
            pygame.draw.rect(self.screen, config.color_cell_revealed, rect)
            if cell.state.is_mine:
                pygame.draw.circle(self.screen, config.color_cell_mine, rect.center, rect.width // 4)
            elif cell.state.adjacent > 0:
                color = config.number_colors.get(cell.state.adjacent, config.color_text)  # Feature #2
                label = self.font.render(str(cell.state.adjacent), True, color)
                label_rect = label.get_rect(center=rect.center)
                self.screen.blit(label, label_rect)
        else:
            base_color = config.color_highlight if highlighted else config.color_cell_hidden
            pygame.draw.rect(self.screen, base_color, rect)
            if cell.state.is_flagged:
                flag_w = max(6, rect.width // 3)
                flag_h = max(8, rect.height // 2)
                pole_x = rect.left + rect.width // 3
                pole_y = rect.top + 4
                pygame.draw.line(self.screen, config.color_flag, (pole_x, pole_y), (pole_x, pole_y + flag_h), 2)
                pygame.draw.polygon(
                    self.screen,
                    config.color_flag,
                    [
                        (pole_x + 2, pole_y),
                        (pole_x + 2 + flag_w, pole_y + flag_h // 3),
                        (pole_x + 2, pole_y + flag_h // 2),
                    ],
                )
        pygame.draw.rect(self.screen, config.color_grid, rect, 1)

    def draw_header(
        self,
        remaining_mines: int,
        time_text: str,
        buttons: list[UIButton],
        selected_difficulty: str,
    ) -> None:
        """Draw the header bar containing remaining mines, time, and UI buttons."""
        pygame.draw.rect(
            self.screen,
            config.color_header,
            Rect(0, 0, config.width, config.margin_top - 4),
        )
        left_text = f"Mines: {remaining_mines}"
        right_text = f"Time: {time_text}"
        left_label = self.header_font.render(left_text, True, config.color_header_text)
        right_label = self.header_font.render(right_text, True, config.color_header_text)
        self.screen.blit(left_label, (10, 12))
        self.screen.blit(right_label, (config.width - right_label.get_width() - 10, 12))
        self._draw_buttons(buttons, selected_difficulty)

    def _draw_buttons(self, buttons: list[UIButton], selected_difficulty: str) -> None:
        """Render UI buttons for difficulty, hint, and restart actions."""
        for button in buttons:
            selected = button.kind == "difficulty" and button.value == selected_difficulty
            if button.disabled:
                color = config.color_button_disabled
            elif selected:
                color = config.color_button_selected
            else:
                color = config.color_button_bg
            pygame.draw.rect(self.screen, color, button.rect, border_radius=6)
            pygame.draw.rect(self.screen, config.color_grid, button.rect, 1, border_radius=6)
            label = self.button_font.render(button.label, True, config.color_button_text)
            label_rect = label.get_rect(center=button.rect.center)
            self.screen.blit(label, label_rect)

    def draw_result_overlay(self, text: str | None) -> None:
        """Draw a semi-transparent overlay with centered result text, if any."""
        if not text:
            return
        overlay = pygame.Surface((config.width, config.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, config.result_overlay_alpha))
        self.screen.blit(overlay, (0, 0))
        label = self.result_font.render(text, True, config.color_result)
        rect = label.get_rect(center=(config.width // 2, config.height // 2))
        self.screen.blit(label, rect)


class InputController:
    """Translates input events into game and board actions."""

    def __init__(self, game: "Game"):
        self.game = game

    def pos_to_grid(self, x: int, y: int):
        """Convert pixel coordinates to (col,row) grid indices or (-1,-1) if out of bounds."""
        if not (config.margin_left <= x < config.width - config.margin_right):
            return -1, -1
        if not (config.margin_top <= y < config.height - config.margin_bottom):
            return -1, -1
        col = (x - config.margin_left) // config.cell_size
        row = (y - config.margin_top) // config.cell_size
        if 0 <= col < self.game.board.cols and 0 <= row < self.game.board.rows:
            return int(col), int(row)
        return -1, -1

    def handle_mouse(self, pos, button) -> None:
        # ToDo:
        ui_button = self.game.button_at(pos)
        if ui_button and button == config.mouse_left:
            self.game.handle_button(ui_button)
            return
        col, row = self.pos_to_grid(pos[0], pos[1])
        if col == -1:
            return

        game = self.game
        board = game.board
        if button == config.mouse_left:
            game.highlight_targets.clear()

            if not game.started:  # Feature #1
                game.started = True
                game.start_ticks_ms = pygame.time.get_ticks()

            board.reveal(col, row)

        elif button == config.mouse_right:
            game.highlight_targets.clear()
            board.toggle_flag(col, row)

        elif button == config.mouse_middle:
            neighbors = board.neighbors(col, row)
            game.highlight_targets = {
                (nc, nr)
                for (nc, nr) in neighbors
                if not board.cells[board.index(nc, nr)].state.is_revealed
            }

            game.highlight_until_ms = pygame.time.get_ticks() + config.highlight_duration_ms

class Game:
    """Main application object orchestrating loop and high-level state."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.title)
        config.apply_difficulty(config.default_difficulty)
        self.difficulty = config.default_difficulty
        self.screen = pygame.display.set_mode(config.display_dimension)
        self.clock = pygame.time.Clock()
        self.board = Board(config.cols, config.rows, config.num_mines)
        self.renderer = Renderer(self.screen, self.board)
        self.input = InputController(self)
        self.highlight_targets = set()
        self.highlight_until_ms = 0
        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0
        self.hint_available = True
        self.buttons: list[UIButton] = []
        self._build_buttons()
        self.reset()

    def reset(self):  # Feature #5
        """Reset the game state and start a new board."""
        self._build_board()
        self.highlight_targets.clear()
        self.highlight_until_ms = 0
        self.started = False
        self.start_ticks_ms = 0
        self.end_ticks_ms = 0
        self.hint_available = True
        self._update_button_states()

    def _build_board(self) -> None:
        self.board = Board(config.cols, config.rows, config.num_mines)
        self.renderer.board = self.board

    def _build_buttons(self) -> None:  # Features #3, #4, #5
        """Create UI buttons positioned within the header area."""
        self.buttons = []
        btn_h = 32
        gap = 12
        diff_btn_w = 90
        diff_y = 60
        difficulties = list(config.difficulty_settings.keys())  # Feature #3
        total_width = len(difficulties) * diff_btn_w + (len(difficulties) - 1) * gap
        start_x = max(10, (config.width - total_width) // 2)
        for diff in difficulties:
            rect = Rect(start_x, diff_y, diff_btn_w, btn_h)
            self.buttons.append(UIButton(rect=rect, label=diff, kind="difficulty", value=diff))
            start_x += diff_btn_w + gap

        control_w = 140
        control_y = 100
        total_controls = control_w * 2 + gap
        start_x = max(10, (config.width - total_controls) // 2)
        hint_rect = Rect(start_x, control_y, control_w, btn_h)
        restart_rect = Rect(start_x + control_w + gap, control_y, control_w, btn_h)
        self.buttons.append(UIButton(rect=hint_rect, label="Hint", kind="hint"))
        self.buttons.append(UIButton(rect=restart_rect, label="Restart", kind="restart"))  # Feature #5

    def _update_button_states(self) -> None:
        """Enable or disable hint button based on availability and game status."""
        for button in self.buttons:
            if button.kind == "hint":
                button.disabled = (not self.hint_available) or self.board.game_over or self.board.win

    def button_at(self, pos: tuple[int, int]) -> UIButton | None:
        """Return the button at the given position, if any."""
        for button in self.buttons:
            if button.contains(pos):
                return button
        return None

    def handle_button(self, button: UIButton) -> None:
        """Handle UI button click actions."""
        if button.disabled:
            return
        if button.kind == "difficulty" and button.value:
            self.set_difficulty(button.value)
        elif button.kind == "hint":  # Feature #4
            self.use_hint()
        elif button.kind == "restart":  # Feature #5
            self.reset()

    def set_difficulty(self, name: str) -> None:  # Feature #3
        """Switch to a new difficulty setting and rebuild the game."""
        if name == self.difficulty:
            self.reset()
            return
        self.difficulty = name
        config.apply_difficulty(name)
        self.screen = pygame.display.set_mode(config.display_dimension)
        self.renderer.screen = self.screen
        self._build_buttons()
        self.reset()

    def use_hint(self) -> None:  # Feature #4
        """Reveal a safe cell exactly once per game."""
        if not self.hint_available or self.board.game_over or self.board.win:
            return
        safe_cells = [
            (cell.col, cell.row)
            for cell in self.board.cells
            if (not cell.state.is_mine and not cell.state.is_revealed and not cell.state.is_flagged)
        ]
        if not safe_cells:
            self.hint_available = False
            self._update_button_states()
            return
        if not self.started:
            self.started = True
            self.start_ticks_ms = pygame.time.get_ticks()
        target = random.choice(safe_cells)
        self.board.reveal(*target)
        self.hint_available = False
        self._update_button_states()

    def _elapsed_ms(self) -> int:  # Feature #1
        """Return elapsed time in milliseconds (stops when game ends)."""
        if not self.started:
            return 0
        if self.end_ticks_ms:
            return self.end_ticks_ms - self.start_ticks_ms
        return pygame.time.get_ticks() - self.start_ticks_ms

    def _format_time(self, ms: int) -> str:  # Feature #1
        """Format milliseconds as mm:ss string."""
        total_seconds = ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _result_text(self) -> str | None:
        """Return result label to display, or None if game continues."""
        if self.board.game_over:
            return "GAME OVER"
        if self.board.win:
            return "GAME CLEAR"
        return None

    def draw(self):
        """Render one frame: header, grid, result overlay."""
        if pygame.time.get_ticks() > self.highlight_until_ms and self.highlight_targets:
            self.highlight_targets.clear()
        self._update_button_states()
        self.screen.fill(config.color_bg)
        remaining = max(0, config.num_mines - self.board.flagged_count())
        time_text = self._format_time(self._elapsed_ms())
        self.renderer.draw_header(remaining, time_text, self.buttons, self.difficulty)
        now = pygame.time.get_ticks()
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                highlighted = (now <= self.highlight_until_ms) and ((c, r) in self.highlight_targets)
                self.renderer.draw_cell(c, r, highlighted)
        self.renderer.draw_result_overlay(self._result_text())
        pygame.display.flip()

    def run_step(self) -> bool:
        """Process inputs, update time, draw, and tick the clock once."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.input.handle_mouse(event.pos, event.button)
        if (self.board.game_over or self.board.win) and self.started and not self.end_ticks_ms:
            self.end_ticks_ms = pygame.time.get_ticks()
        self.draw()
        self.clock.tick(config.fps)
        return True


def main() -> int:
    """Application entrypoint: run the main loop until quit."""
    game = Game()
    running = True
    while running:
        running = game.run_step()
    pygame.quit()
    return 0


if __name__ == "__main__":

    raise SystemExit(main())
