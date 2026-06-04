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
from imu_sensor import IMUSensor
import board  # Provides board.D3 for button access
import digitalio  # For DigitalInOut button control
from audio_out import AudioOutput
from pwm_out import PWMOutput
from lcd_display import LCDDisplay, Colors
from audiocore import WaveFile
import struct
import microcontroller
import terminalio
import displayio  # For display groups and graphics
import gc
import time
import random

#Constants
GRAVITY = 0.4
JUMP_VELOCITY = -8
#Screen Size
SCREEN_W = 240
SCREEN_H = 135
#Player size
PLAYER_W = 16
PLAYER_H = 16
#Platform Size
PLATFORM_W = 40
PLATFORM_H = 6
#Tilt Config
TILT_DEADZONE = 0.3
TILT_MAX = 10.0
# Platform spacing
PLATFORM_SPACING = 35

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


class Doodle_Jump_logic :
   def __init__(self):
      self.player_x = 120
      self.player_y = 100
      self.velocity_y = 0
      self.platforms = []
      self.score = 0
      self.high_score = 0
      self.camera_y = 0
      self.high_score = _load_high_score()
      # Audio setup with robust AudioManager
      self._audio_manager = _AudioManager()
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

class Controller : 
   def __init__(self):
      self.imu = IMUSensor()
      
      # D3 button for starting game (active-LOW with pull-up)
      self._btn = digitalio.DigitalInOut(board.D3)
      self._btn.direction = digitalio.Direction.INPUT
      self._btn.pull = digitalio.Pull.UP

   def get_horizontal_movement(self):
      ax, ay, az = self.imu.acceleration
      if abs(ax) < TILT_DEADZONE:
         return 0
      dx = int(ax * 0.8)
      dx = max(-TILT_MAX, min(TILT_MAX, dx))

      return dx


   def button_pressed(self):
      """Check if D3 button is pressed (active-LOW inverted)."""
      return not self._btn.value
class display : 
   def __init__(self, model): 
      self.lcd = LCDDisplay()
      self.lcd.backlight_on()
      self.group, self.palatte = self.lcd.make_group(Colors.BLACK)
      self.score_label = self.lcd.add_label(self.group, text="0", x = SCREEN_W - 5, y = 5, color = 0xFFFFFF, scale = 2)
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
      import time
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

      black_background = self.lcd.draw_rect(0,0, SCREEN_W, SCREEN_H, fill=0x000000)
      self.group.append(black_background)

      title = self.lcd.add_label(self.group, text = "Game Over", x = SCREEN_W // 2, y = SCREEN_H // 2 - 20, color = 0xFFFFFF, scale = 2)

      score_text = self.lcd.add_label(self.group, text = f"Score: {score}", x = SCREEN_W // 2, y = SCREEN_H // 2 + 10, color = 0xFFFFFF, scale = 1)

      high_score_text = self.lcd.add_label(self.group, text = f"High Score: {high_score}", x = SCREEN_W // 2,  y = SCREEN_H // 2 + 30, color = 0xFFFFFF, scale = 1)

      time.sleep(3)

      self.group.remove(black_background)
      self.group.remove(title)
      self.group.remove(score_text)
      self.group.remove(high_score_text)

def main():
   gc.collect()
   print(f"Free RAM at start: {gc.mem_free()} bytes")

   
   model = Doodle_Jump_logic()
   model.reset()
   controller = Controller()
   view = display(model)  # Pass model for high score
   
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

if __name__ == "__main__":
   main()