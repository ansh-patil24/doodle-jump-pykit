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
from audio_out import AudioOutput
from pwm_out import PWMOutput
from lcd_display import LCDDisplay, Colors
import struct
import microcontroller
import terminalio
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

   def get_horizontal_movement(self):
      ax, ay, az = self.imu.acceleration
      if abs(ax) < TILT_DEADZONE:
         return 0
      dx = int(ax * 0.8)
      dx = max(-TILT_MAX, min(TILT_MAX, dx))

      return dx

class display : 
   def __init__(self): 
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
   view = display()

   while True: 
      dx = controller.get_horizontal_movement()
      model.move_horizontal(dx)
      event = model.jump()
      if event == "died":
         # Save high score to NVM only once when game ends (before game over screen)
         _save_high_score(model.high_score)
         view.show_game_over(model.score, model.high_score)
         model.reset()
      view.render(model)
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
