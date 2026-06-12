from adafruit_matrixportal.matrix import Matrix
from adafruit_display_shapes.rect import Rect
import displayio
import time
import terminalio
from adafruit_display_text import label
import adafruit_imageload

  # Screen dimensions for 64x32 RGB Matrix
SCREEN_W = 64
SCREEN_H = 32
PLATFORM_W = 12  # Smaller platforms
PLATFORM_H = 2   # Match code.py
PLAYER_W = 4     # Small sprite (4x4 pixels)
PLAYER_H = 4     # Small sprite


class _AudioManager:
    """Dummy audio manager - no audio on matrix display."""
    def __init__(self):
        self.enabled = False
        print("Audio disabled for matrix display")

    def play(self, sound_name):
        """No-op - audio disabled."""
        pass


class display:
    def __init__(self, model):
        print("Initializing RGB Matrix display...")

          # Initialize matrix instead of LCD
        self.matrix = Matrix(width=SCREEN_W, height=SCREEN_H, bit_depth=4)
        self.display_obj = self.matrix.display

          # Create main group
        self.group = displayio.Group()
        self.display_obj.root_group = self.group

          # Score label (smaller for matrix)
        self.score_label = label.Label(
            terminalio.FONT,
            text="0",
            color=0xFFFFFF,
            x=SCREEN_W - 5,  # Initial position for single digit
            y=4
        )
          # No anchor point - we'll calculate position dynamically
        self.group.append(self.score_label)

          # Player sprite - load the small 4x4 doodle sprite
        try:
            # Load sprite bitmap (4x4 pixels)
            sprite_bitmap, sprite_palette = adafruit_imageload.load(
                "/Sprites/doode_small.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            
            # Create sprite group for positioning
            self.player_sprite = displayio.Group(x=0, y=0)
            
            # Create a TileGrid for the sprite
            sprite_tile = displayio.TileGrid(
                sprite_bitmap,
                pixel_shader=sprite_palette,
                width=1,
                height=1,
                tile_width=4,
                tile_height=4
            )
            
            self.player_sprite.append(sprite_tile)
            self.group.append(self.player_sprite)
            print("Doodle 4x4 sprite loaded successfully!")
        except Exception as e:
            print(f"Error loading sprite: {e}")
            # Fallback to colored rectangle
            self.player_sprite = Rect(0, 0, PLAYER_W, PLAYER_H, fill=0x00FF00)
            self.group.append(self.player_sprite)

          # Track platforms
        self.platform_shapes = []
        self.platform_shapes_initialized = False
        self.last_displayed_score = 0

        # Start screen group
        self._start_group = displayio.Group()
        self.group.append(self._start_group)

          # Dark background
        start_bg_bmp = displayio.Bitmap(SCREEN_W, SCREEN_H, 1)
        start_bg_pal = displayio.Palette(1)
        start_bg_pal[0] = 0x000000  # Dark blue-gray
        self._start_group.append(displayio.TileGrid(start_bg_bmp, pixel_shader=start_bg_pal))

          # Title - line 1: "DOODLE" (6 chars * 6px = 36px)
        start_title = label.Label(
            terminalio.FONT,
            text="DOODLE",
            color=0x00FF00,
            scale=1
        )
        # terminalio.FONT chars are 6px wide, 8px tall with scale=1
        start_title.x = (SCREEN_W - len("DOODLE") * 6) // 2
        start_title.y = 4
        self._start_group.append(start_title)

          # Title - line 2: "JUMP" (4 chars * 6px = 24px)
        start_title2 = label.Label(
            terminalio.FONT,
            text="JUMP",
            color=0x00FF00,
            scale=1
        )
        start_title2.x = (SCREEN_W - len("JUMP") * 6) // 2
        start_title2.y = 12
        self._start_group.append(start_title2)

          # High score: "HI:999" (max ~6 chars * 6px = 36px)
        self._start_high_score_label = label.Label(
            terminalio.FONT,
            text=f"HI:{model.high_score}",
            color=0xFFFF00,
            scale=1
        )
        # Center dynamically based on text length
        self._start_high_score_label.x = (SCREEN_W - len(self._start_high_score_label.text) * 6) // 2
        self._start_high_score_label.y = 20
        self._start_group.append(self._start_high_score_label)

          # Blinking prompt: "PRESS" (5 chars * 6px = 30px)
        self._start_prompt = label.Label(
            terminalio.FONT,
            text="PRESS:BTN",
            color=0xFFFF00,
            scale=1
        )
        self._start_prompt.x = (SCREEN_W - len("PRESS:BTN") * 6) // 2
        self._start_prompt.y = 28
        self._start_group.append(self._start_prompt)

        self._start_blink_counter = 0
        self._start_group.hidden = True

          # Audio manager (disabled)
        self.audio_manager = _AudioManager()

        print("Matrix display initialized!")

    def render(self, model):
          # Update player position
        self.player_sprite.x = int(model.player_x)
        self.player_sprite.y = int(model.player_y)

          # Initialize platforms on first render
        if not self.platform_shapes_initialized:
            for px, py in model.platforms:
                platform = Rect(int(px), int(py), PLATFORM_W, PLATFORM_H, fill=0x0000FF)
                self.group.append(platform)
                self.platform_shapes.append(platform)
            self.platform_shapes_initialized = True
        else:
              # Update platform positions
            for i, (px, py) in enumerate(model.platforms):
                if i < len(self.platform_shapes):
                    self.platform_shapes[i].x = int(px)
                    self.platform_shapes[i].y = int(py)

          # Update score (every 5 points to reduce flicker)
        score_diff = abs(model.score - self.last_displayed_score)
        if score_diff >= 5 or model.score == 0:
            self.last_displayed_score = model.score
            self.score_label.text = str(model.score)
            # Dynamically position based on text length (6 pixels per char for terminalio)
            text_width = len(self.score_label.text) * 6
            self.score_label.x = SCREEN_W - text_width - 2


    def show_start_screen(self):
        """Show the start screen."""
        self._start_group.hidden = False

    def hide_start_screen(self):
        """Hide the start screen."""
        self._start_group.hidden = True
    
    def blink_start_prompt(self):
        """Animate the start prompt."""
        self._start_blink_counter += 1
        if self._start_blink_counter >= 60:
            self._start_blink_counter = 0

        if self._start_blink_counter < 30:
            self._start_prompt.color = 0xFFFF00
        else:
            self._start_prompt.color = 0x000020

    def update_start_high_score(self, score):
        """Update high score on start screen."""
        self._start_high_score_label.text = f"HI:{score}"
        # Recenter after text change
        self._start_high_score_label.x = (SCREEN_W - len(self._start_high_score_label.text) * 6) // 2

    def show_game_over(self, score, high_score):
        # Clear platforms
        for shape in self.platform_shapes:
            self.group.remove(shape)
        self.platform_shapes.clear()
        self.platform_shapes_initialized = False
        self.last_displayed_score = 0

        # Hide the top-right score label and player sprite
        self.score_label.color = 0x000000  # Make it invisible (black on black background)
        self.player_sprite.hidden = True  # Hide player sprite

          # Game over text - line 1
        game_over_label = label.Label(
            terminalio.FONT,
            text="GAME OVER",
            color=0xFF0000,
            scale=1
        )
        # Manual centering (4 chars * 6px = 24px)
        game_over_label.x = (SCREEN_W - len("GAME OVER") * 6) // 2
        game_over_label.y = 4
        self.group.append(game_over_label)

        # Score display with label
        score_text = f"SCORE:{score}"
        score_label = label.Label(
            terminalio.FONT,
            text=score_text,
            color=0xFFFFFF,
            scale=1
        )
        score_label.x = (SCREEN_W - len(score_text) * 6) // 2
        score_label.y = 14
        self.group.append(score_label)

        # High score display with label
        high_text = f"HI:{high_score}"
        high_label = label.Label(
            terminalio.FONT,
            text=high_text,
            color=0xFFFF00,
            scale=1
        )
        high_label.x = (SCREEN_W - len(high_text) * 6) // 2
        high_label.y = 24
        self.group.append(high_label)

        time.sleep(3)  # Show game over for 3 seconds

        self.group.remove(game_over_label)
        self.group.remove(score_label)
        self.group.remove(high_label)
        
        # Restore the top-right score label and player sprite visibility
        self.score_label.color = 0xFFFFFF
        self.player_sprite.hidden = False  # Show player sprite