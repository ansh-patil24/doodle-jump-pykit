"""
================================================================================
DOODLE JUMP - PyKit Explorer Game
================================================================================

A smooth-running platformer game with tilt controls for Microchip PyKit Explorer

GAME MECHANICS:
- Automatic jumping - player continuously bounces
- Tilt device left/right to control horizontal movement
- Land on platforms to keep climbing higher
- Fall off bottom = game over
- High score saved to NVM (persists across power cycles)

ARCHITECTURE: Model-View-Controller (MVC)
- Doodle_Jump_logic: Game state, physics, collisions (MODEL)
- display: LCD rendering and graphics (VIEW)
- Controller: IMU sensor input (CONTROLLER)

PERFORMANCE OPTIMIZATIONS:
- Platform recycling: Reuse objects instead of create/destroy
- Graphics reuse: Update positions, don't recreate rectangles
- Batched score updates: Update every 5 points to prevent flicker
- NVM write once: Save high score only on death to avoid lag

HARDWARE REQUIREMENTS:
- Microchip Curiosity PyKit Explorer
- ST7789 LCD Display (240x135)
- ICM20948 IMU Sensor
- CircuitPython 10.x

For detailed documentation, see CODE_DOCUMENTATION.md
================================================================================
"""

import pykit_explorer
from doodle_jump_controller import Controller
from doodle_jump_view import display
import struct
import microcontroller
import gc
import time
import random

# Constants - SCALED FOR 64x32 RGB MATRIX
GRAVITY = 0.3  # Slightly reduced for smaller screen
JUMP_VELOCITY = -6  # Reduced from -8
  # Screen Size
SCREEN_W = 64  # Changed from 240
SCREEN_H = 32  # Changed from 135
  # Player size
PLAYER_W = 4   # Small sprite size (4x4 pixels)
PLAYER_H = 4   # Small sprite size
  # Platform Size
PLATFORM_W = 12  # Smaller platforms for 64x32 display
PLATFORM_H = 2   # Height unchanged
  # Tilt Config (not used with button controls)
TILT_DEADZONE = 0.3
TILT_MAX = 10.0
  # Platform spacing
PLATFORM_SPACING = 7  # Reduced spacing = more platforms 

# NVM (Non-Volatile Memory) layout for persisting the high score across
# power cycles.  The first 4 bytes are a magic marker ("HSv1") so we can
# detect uninitialised NVM.  The next 2 bytes are the high score as an
# unsigned 16-bit integer (max 65535).
_NVM_MAGIC = b"HSv1"
_NVM_FMT   = "<4sH"                       # little-endian: 4-char + uint16
_NVM_SIZE  = struct.calcsize(_NVM_FMT)     # = 6 bytes

# ============================================================================
# GAME STATE CONSTANTS
# ============================================================================
# Game operates as a state machine with two primary states:
# - STATE_MENU: Start screen showing title, instructions, high score
# - STATE_PLAYING: Active gameplay where player controls bouncing sprite
# ============================================================================
STATE_MENU = 0       # Start screen, waiting for button press
STATE_PLAYING = 1    # Active gameplay


class Doodle_Jump_logic:
    def __init__(self, audio_manager):
        self.player_x = 120
        self.player_y = 100
        self.velocity_y = 0
        self.platforms = []
        self.score = 0
        self.high_score = 0
        self.camera_y = 0
        self.high_score = _load_high_score()
        # Audio manager passed from view
        self._audio_manager = audio_manager

    def reset(self):
        self.player_x = SCREEN_W // 2 - PLATFORM_W // 2
        self.player_y = SCREEN_H - 50
        self.velocity_y = JUMP_VELOCITY
        self.score = 0
        self.camera_y = 0

        self.platforms = []

        # Generate initial platforms
        self.platforms.append((self.player_x - 10, self.player_y + PLAYER_H + 5))
        y = SCREEN_H - 30
        while y > -SCREEN_H:
            x = random.randint(0, SCREEN_W - PLATFORM_W)
            self.platforms.append((x, y))
            y -= PLATFORM_SPACING

    def jump(self):
        event = None
        self.velocity_y += GRAVITY
        self.player_y += self.velocity_y

        SCROLL_THRESHOLD = SCREEN_H // 4

        if self.player_y < SCROLL_THRESHOLD and self.velocity_y < 0:
            scroll_amount = SCROLL_THRESHOLD - self.player_y
            self.player_y = SCROLL_THRESHOLD

            # Scroll all platforms down
            for i in range(len(self.platforms)):
                px, py = self.platforms[i]
                self.platforms[i] = (px, py + scroll_amount)

            self.camera_y += scroll_amount
            self.score = int(self.camera_y)
            if self.score > self.high_score:
                self.high_score = self.score

            # Recycle platforms that scrolled off the bottom
            highest_y = min(py for px, py in self.platforms) if self.platforms else 0

            for i, (px, py) in enumerate(self.platforms):
                if py > SCREEN_H + PLATFORM_H:
                    new_x = random.randint(0, SCREEN_W - PLATFORM_W)
                    new_y = highest_y - PLATFORM_SPACING
                    self.platforms[i] = (new_x, new_y)
                    highest_y = new_y

        if self.velocity_y > 0:
            for platform_x, platform_y in self.platforms:
                if self.player_lands_on(platform_x, platform_y):
                    self.velocity_y = JUMP_VELOCITY
                    event = "bounced"
                    break

        if self.player_y > SCREEN_H:
            return "died"

        return event

    def player_lands_on(self, platform_x, platform_y):
        player_feet = self.player_y + PLAYER_H

        player_left = self.player_x
        player_right = self.player_x + PLAYER_W

        platform_left = platform_x
        platform_right = platform_x + PLATFORM_W

        overlaps_horizontally = (player_right > platform_left and
                                player_left < platform_right)

        feet_at_platform = (player_feet >= platform_y and
                            player_feet <= platform_y + PLATFORM_H + self.velocity_y)

        return overlaps_horizontally and feet_at_platform

    def move_horizontal(self, dx):
        self.player_x += dx
        if self.player_x < 0:
            self.player_x = SCREEN_W

        if self.player_x > SCREEN_W:
            self.player_x = 0


def _nvm_available():
    """Check whether this board has Non-Volatile Memory support."""
    return getattr(microcontroller, "nvm", None) is not None


def _load_high_score():
    """Read the high score from NVM on startup.
       If NVM is uninitialised (no magic marker) or unavailable,
       defaults to 0.
    """
    if not _nvm_available() or len(microcontroller.nvm) < _NVM_SIZE:
        return 0
    raw = bytes(microcontroller.nvm[0:_NVM_SIZE])
    try:
        magic, hs = struct.unpack(_NVM_FMT, raw)
        return hs if magic == _NVM_MAGIC else 0
    except Exception:
        return 0


def _save_high_score(high_score):
    """Write the current high score to NVM so it survives power cycles."""
    if not _nvm_available() or len(microcontroller.nvm) < _NVM_SIZE:
        return
    try:
        microcontroller.nvm[0:_NVM_SIZE] = struct.pack(
            _NVM_FMT, _NVM_MAGIC, min(high_score, 65535))
    except Exception:
        pass


def main():
    gc.collect()
    print(f"Free RAM at start: {gc.mem_free()} bytes")

    # Create view first to get audio manager
    # Temporarily create model with None, then set audio after view is created
    model = Doodle_Jump_logic(audio_manager=None)
    controller = Controller()
    view = display(model)  # Pass model for high score

    # Now connect audio manager from view to model
    model._audio_manager = view.audio_manager

    model.reset()

    # Start in menu state
    state = STATE_MENU
    view.show_start_screen()

    while True:
        # ==================================================================
        # STATE: MENU
        # ==================================================================
        if state == STATE_MENU:
            # Plain background with text overlay
            view.blink_start_prompt()

            if controller.button_pressed():
                print("Starting game!")
                model.reset()
                view.hide_start_screen()  # Instant transition
                state = STATE_PLAYING
                time.sleep(0.2)  # Debounce
                continue

            time.sleep(0.05)
            continue

        # ==================================================================
        # STATE: PLAYING
        # ==================================================================
        # Phase 1: Input
        dx = controller.get_horizontal_movement()
        model.move_horizontal(dx)

        # Phase 2: Game logic
        event = model.jump()

        # Phase 3: Audio (deferred)
        if event == "bounced":
            model._audio_manager.play("jump")
        elif event == "died":
            model._audio_manager.play("gameover")
            _save_high_score(model.high_score)
            view.show_game_over(model.score, model.high_score)
            view.update_start_high_score(model.high_score)
            model.reset()
            view.show_start_screen()
            state = STATE_MENU
            continue

        # Phase 4: Rendering
        view.render(model)

        # Phase 5: Frame pacing
        time.sleep(0.05)


if __name__ == "__main__":
    main()
