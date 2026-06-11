"""
================================================================================
DOODLE JUMP - View (Display & Audio)
================================================================================
Handles all rendering and audio playback for the Doodle Jump game.
"""

from lcd_display import LCDDisplay, Colors
from audio_out import AudioOutput
from audiocore import WaveFile
import displayio
import time

# Screen dimensions (imported from model constants)
SCREEN_W = 240
SCREEN_H = 135
PLATFORM_W = 40
PLATFORM_H = 6
PLAYER_W = 16
PLAYER_H = 16


class _AudioManager:
    """Manage non-blocking WAV sound-effect playback with rate limiting.

    Opens and closes WAV files on each play to keep RAM usage low.
    Re-initializes the AudioOut device every 50 plays to prevent memory
    fragmentation on CircuitPython's heap.
    """
    _SOUNDS = {
        "jump": "/AudioFiles/doodle_jump.wav",
        "gameover": "/AudioFiles/doodle_jump_gameover.wav",
    }
    _MIN_INTERVAL = 0.08  # minimum seconds between plays (rate limiter)
    _REINIT_EVERY = 50    # re-create AudioOut every N plays

    def __init__(self):
        self.enabled = False
        self._audio = None
        self._file = None
        self._wave = None
        self._last_t = 0.0
        self._count = 0

        try:
            self._audio = AudioOutput()
            self.enabled = True
        except Exception as e:
            print(f"Audio init failed: {e}")

    def play(self, sound_name):
        """Play a sound effect with rate limiting and cleanup."""
        if not self.enabled or sound_name not in self._SOUNDS:
            return

        now = time.time()
        if now - self._last_t < self._MIN_INTERVAL:
            return  # Rate limit: too soon since last play

        try:
            self._cleanup()
            self._count += 1

            # Periodic reinitialization to prevent heap fragmentation
            if self._count % self._REINIT_EVERY == 0:
                try:
                    self._audio.deinit()
                    self._audio = AudioOutput()
                except Exception:
                    pass

            self._file = open(self._SOUNDS[sound_name], "rb")
            self._wave = WaveFile(self._file)
            self._audio._audio.play(self._wave)
            self._last_t = now
        except Exception as e:
            print(f"Audio error ({sound_name}): {e}")
            self._cleanup()

    def _cleanup(self):
        """Clean up audio resources."""
        try:
            if self._audio and self._audio._audio.playing:
                self._audio._audio.stop()
        except Exception:
            pass
        try:
            if self._file is not None:
                self._file.close()
        except Exception:
            pass
        self._file = None
        self._wave = None


class display:
    def __init__(self, model):
        self.lcd = LCDDisplay()
        self.lcd.backlight_on()
        self.group, self.palatte = self.lcd.make_group(Colors.BLACK)
        self.score_label = self.lcd.add_label(self.group, text="0", x=SCREEN_W - 5, y=5, color=0xFFFFFF, scale=2)
        # Set right-aligned anchor point for score to avoid repositioning
        self.score_label.anchor_point = (1.0, 0.0)
        self.player_group = self.lcd.load_sprite("/Sprites/doodle.bmp", 16, 16, x=0, y=0)
        self.group.append(self.player_group)
        # Track platforms by index, not coordinates
        self.platform_shapes = []
        # Initialize platform graphics (will match model platform count)
        self.platform_shapes_initialized = False
        # Track last displayed score to avoid unnecessary updates
        self.last_displayed_score = 0

        # ========================================================================
        # START SCREEN INITIALIZATION
        # ========================================================================
        # Separate group for start screen that can be shown/hidden easily
        self._start_group = displayio.Group()
        self.group.append(self._start_group)

        # Plain dark background (not frozen game)
        start_bg_bmp = displayio.Bitmap(SCREEN_W, SCREEN_H, 1)
        start_bg_pal = displayio.Palette(1)
        start_bg_pal[0] = 0x000000  # Dark blue-gray
        self._start_group.append(displayio.TileGrid(start_bg_bmp, pixel_shader=start_bg_pal))

        # Title
        start_title = self.lcd.add_label(self._start_group, text="DOODLE JUMP",
            x=SCREEN_W // 2, y=25, color=0x00FF00, scale=3)
        start_title.anchor_point = (0.5, 0.5)

        # Doodle sprite
        start_sprite = self.lcd.load_sprite("/Sprites/doodle.bmp", 16, 16,
            x=SCREEN_W//2 - 8, y=45)
        self._start_group.append(start_sprite)

        # Instructions
        instructions = self.lcd.add_label(self._start_group, text="TILT : MOVE",
            x=SCREEN_W // 2, y=75, color=0x88AACC, scale=1)
        instructions.anchor_point = (0.5, 0.5)

        # High score
        self._start_high_score_label = self.lcd.add_label(self._start_group,
            text=f"HIGH SCORE: {model.high_score}",
            x=SCREEN_W // 2, y=95, color=0xFFFF00, scale=2)
        self._start_high_score_label.anchor_point = (0.5, 0.5)

        # Blinking prompt
        self._start_prompt = self.lcd.add_label(self._start_group,
            text="PRESS BUTTON TO START", x=SCREEN_W // 2, y=115,
            color=0xFFFF00, scale=1)
        self._start_prompt.anchor_point = (0.5, 0.5)

        # Credit line
        credit = self.lcd.add_label(self._start_group,
            text="PyKit Explorer Edition", x=SCREEN_W // 2, y=128,
            color=0x445566, scale=1)
        credit.anchor_point = (0.5, 0.5)

        # Blink counter
        self._start_blink_counter = 0
        self._start_group.hidden = True  # Start hidden

        # Create audio manager that model can access
        self.audio_manager = _AudioManager()

    def render(self, model):
        # Update player position
        self.player_group.x = model.player_x
        self.player_group.y = int(model.player_y)

        # Initialize platform graphics on first render
        if not self.platform_shapes_initialized:
            for px, py in model.platforms:
                platform = self.lcd.draw_rect(int(px), int(py), PLATFORM_W, PLATFORM_H, fill=0x00FF00)
                self.group.append(platform)
                self.platform_shapes.append(platform)
            self.platform_shapes_initialized = True
        else:
            # Just update positions of existing graphics - NO creation/deletion
            for i, (px, py) in enumerate(model.platforms):
                if i < len(self.platform_shapes):
                    self.platform_shapes[i].x = int(px)
                    self.platform_shapes[i].y = int(py)

        # Update score text only when it changes by 5+ to reduce flicker
        score_diff = abs(model.score - self.last_displayed_score)
        if score_diff >= 5 or model.score == 0:
            self.last_displayed_score = model.score
            self.score_label.text = str(model.score)

    def slide_start_screen_up(self):
        """Slide entire loading screen up off screen over 0.5 seconds.
        Background, sprite, and all text move together.
        """
        for step in range(10):
            self._start_group.y -= 15  # Slide text up
            time.sleep(0.05)

    def show_start_screen(self):
        """Show the start/loading screen."""
        self._start_group.y = 0  # Reset position after slide animation
        self._start_group.hidden = False

    def hide_start_screen(self):
        """Hide the start screen."""
        self._start_group.hidden = True

    def blink_start_prompt(self):
        """Animate the start prompt by blinking it."""
        self._start_blink_counter += 1
        if self._start_blink_counter >= 60:
            self._start_blink_counter = 0
        # Toggle between yellow (visible) and dark blue (hidden)
        if self._start_blink_counter < 30:
            self._start_prompt.color = 0xFFFF00
        else:
            self._start_prompt.color = 0x000020

    def update_start_high_score(self, score):
        """Update high score on start screen."""
        self._start_high_score_label.text = f"HIGH SCORE: {score}"

    def show_game_over(self, score, high_score):
        # Clear all platforms
        for shape in self.platform_shapes:
            self.group.remove(shape)
        self.platform_shapes.clear()
        self.platform_shapes_initialized = False
        # Reset score tracker for next game
        self.last_displayed_score = 0

        black_background = self.lcd.draw_rect(0, 0, SCREEN_W, SCREEN_H, fill=0x000000)
        self.group.append(black_background)

        title = self.lcd.add_label(self.group, text="Game Over", x=SCREEN_W // 2, y=SCREEN_H // 2 - 20, color=0xFFFFFF, scale=2)

        score_text = self.lcd.add_label(self.group, text=f"Score: {score}", x=SCREEN_W // 2, y=SCREEN_H // 2 + 10, color=0xFFFFFF, scale=1)

        high_score_text = self.lcd.add_label(self.group, text=f"High Score: {high_score}", x=SCREEN_W // 2, y=SCREEN_H // 2 + 30, color=0xFFFFFF, scale=1)

        time.sleep(3)

        self.group.remove(black_background)
        self.group.remove(title)
        self.group.remove(score_text)
        self.group.remove(high_score_text)
