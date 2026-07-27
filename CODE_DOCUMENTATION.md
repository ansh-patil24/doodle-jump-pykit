# Doodle Jump - Complete Code Documentation

## Overview
This is a platformer game for the PyKit Explorer, built using the Model-View-Controller (MVC) architecture pattern with clean separation of concerns across three files.

## Architecture: Model-View-Controller (MVC)

The game is split into three separate files for maintainability and clarity:

### Model (`Doodle_Jump_logic` class in `code.py`)
- **Purpose**: Contains all game logic and state
- **File**: `code.py`
- **Responsibilities**:
  - Player physics (gravity, velocity, position)
  - Platform management and recycling
  - Collision detection
  - Score calculation and high score tracking
  - Camera scrolling logic
  - Progressive difficulty scaling
  - Triggering audio events through view's audio manager
- **Dependencies**: 
  - Receives audio manager reference from view
  - Uses NVM helper functions for persistent storage
- **Key Methods**:
  - `get_difficulty_params()`: Calculate gravity, jump velocity, sensitivity, and platform width based on score
  - `reset()`: Initialize game state for new game
  - `jump()`: Handle physics, scrolling, collisions - returns event ("bounced", "died", or None)
  - `move_horizontal(dx)`: Move player left/right with screen wrapping
  - `player_lands_on(x, y, platform_w)`: Collision detection for platform landing with dynamic width

### View (`display` class in `doodle_jump_view.py`)
- **Purpose**: Handles all visual output and audio playback
- **File**: `doodle_jump_view.py`
- **Responsibilities**:
  - Initialize LCD display
  - Render player sprite
  - Render platforms (with reuse optimization)
  - Display score (with update batching)
  - Show/hide start screen with animations
  - Show game over screen
  - Manage audio playback via `_AudioManager`
- **Contains**: 
  - `display` class for rendering
  - `_AudioManager` class for non-blocking audio
- **Audio Manager**:
  - Created in view's `__init__` as `self.audio_manager`
  - Accessible by model for playing sound effects
  - Handles rate limiting and memory management
  - Supports sounds: "jump", "gameover"
- **Key Methods**:
  - `render(model)`: Update all display elements based on model state
  - `show_start_screen()`: Display menu screen
  - `hide_start_screen()`: Hide menu and show game
  - `blink_start_prompt()`: Animate "Press Button" text
  - `show_game_over(score, high_score)`: Display end screen

### Controller (`Controller` class in `doodle_jump_controller.py`)
- **Purpose**: Reads and processes input
- **File**: `doodle_jump_controller.py`
- **Responsibilities**:
  - Read IMU sensor data for tilt controls
  - Read button state (D3 button)
  - Apply deadzone filtering
  - Convert tilt to horizontal movement
- **Hardware**: 
  - IMU sensor (accelerometer)
  - D3 button (active-LOW with pull-up)
- **Key Methods**:
  - `get_horizontal_movement()`: Returns tilt-based movement (-10 to +10)
  - `button_pressed()`: Returns True if D3 button is pressed

## File Structure

```
CIRCUITPY/
├── code.py                    # Model + Main Loop + NVM Functions
├── doodle_jump_view.py           # View (Display + AudioManager)
├── doodle_jump_controller.py     # Controller (IMU + Button Input)
├── pykit_explorer.py             # Hardware initialization
├── API/
│   ├── imu_sensor.py             # IMU sensor wrapper
│   ├── lcd_display.py            # LCD display wrapper
│   ├── audio_out.py              # Audio output wrapper
│   └── pwm_out.py                # PWM wrapper
├── Sprites/
│   └── doodle.bmp                # Player sprite (16x16)
├── AudioFiles/
│   ├── doodle_jump.wav           # Jump sound effect
│   └── doodle_jump_gameover.wav  # Game over sound
└── lib/
    └── (CircuitPython libraries)
```

## Code Organization Details

### Main Loop (`main()` in `code.py`)

```python
def main():
    # 1. Initialize MVC components
    model = Doodle_Jump_logic(audio_manager=None)
    controller = Controller()
    view = display(model)
    
    # 2. Connect audio manager from view to model
    model._audio_manager = view.audio_manager
    
    # 3. State machine: STATE_MENU or STATE_PLAYING
    state = STATE_MENU
    
    while True:
        if state == STATE_MENU:
            # Menu state: blink prompt, wait for button
            view.blink_start_prompt()
            if controller.button_pressed():
                state = STATE_PLAYING
        
        elif state == STATE_PLAYING:
            # Playing state: input → logic → audio → render
            dx = controller.get_horizontal_movement()
            model.move_horizontal(dx)
            event = model.jump()
            
            if event == "bounced":
                model._audio_manager.play("jump")
            elif event == "died":
                model._audio_manager.play("gameover")
                _save_high_score(model.high_score)
                view.show_game_over(model.score, model.high_score)
                state = STATE_MENU
            
            view.render(model)
            time.sleep(0.05)  # Frame pacing
```

### Audio Manager Connection Flow

1. Model created with `audio_manager=None` parameter
2. View created (automatically creates `self.audio_manager = _AudioManager()`)
3. Main connects them: `model._audio_manager = view.audio_manager`
4. Model can now call `self._audio_manager.play("jump")`

This design allows the view to own audio resources while the model triggers playback based on game events.

## Constants Explained

All constants are defined in `code.py`:

### Difficulty Scaling (Dynamic)
The game uses progressive difficulty that scales with score:

- `BASE_GRAVITY = 0.484`: Starting gravity (10% faster than original 0.4)
- `MAX_GRAVITY = 0.9`: Gravity at max difficulty
- `BASE_JUMP_VELOCITY = -8.8`: Starting jump velocity (10% faster than original -8)
- `MAX_JUMP_VELOCITY = -12`: Jump velocity at max difficulty
- `MAX_DIFFICULTY_SCORE = 1000`: Score at which max difficulty is reached
- `BASE_PLATFORM_W = 40`: Starting platform width
- `MIN_PLATFORM_W = 25`: Platform width at max difficulty

The difficulty uses an ease-out curve (`factor ** 0.7`) for smooth progression - fast ramp-up early, gradual approach to max.

### Screen  
- `SCREEN_W = 240`: Display width
- `SCREEN_H = 135`: Display height

### Player
- `PLAYER_W = 16`: Sprite width
- `PLAYER_H = 16`: Sprite height

### Platforms
- `PLATFORM_W = 40`: Base width in pixels (used for generation)
- `PLATFORM_H = 6`: Height in pixels  
- `PLATFORM_SPACING = 35`: Vertical gap between platforms

### Controls
- `TILT_DEADZONE = 0.3`: Minimum tilt to register (prevents drift)
- `TILT_MAX = 10.0`: Maximum movement speed (pixels/frame)
- Control sensitivity scales from 1.0x to 1.5x based on difficulty

### Game States
- `STATE_MENU = 0`: Start/menu screen
- `STATE_PLAYING = 1`: Active gameplay

## Game Loop Flow

```
Initialize MVC → Connect Audio → Set STATE_MENU
                       ↓
     ┌─────────────────┴──────────────────┐
     │                                     │
     ▼                                     ▼
[STATE_MENU]                        [STATE_PLAYING]
Blink prompt                        Read Input (Controller)
Wait for button                     Update Physics (Model)
     │                              Check Collisions (Model)
     │ button pressed               Trigger Audio (Model → View)
     └──────────►                   Render Graphics (View)
                                    Frame Sleep (0.05s)
                                         │
                                         │ player died
                                         ├──► Save Score (NVM)
                                         ├──► Show Game Over (View)
                                         └──► Return to STATE_MENU
```

## NVM (Non-Volatile Memory) System

Located in `code.py` as module-level helper functions.

### Storage Format
- **Magic Marker** (4 bytes): "HSv1" - verifies data validity
- **High Score** (2 bytes): Unsigned 16-bit integer (0-65535)
- **Total**: 6 bytes
- **Format**: `_NVM_FMT = "<4sH"` (little-endian)

### Functions
1. `_nvm_available()`: Checks if board supports NVM
2. `_load_high_score()`: Reads saved score on startup (called in model `__init__`)
3. `_save_high_score(score)`: Writes score on game over (called in main loop)

### Usage
```python
# On startup (in model __init__)
self.high_score = _load_high_score()

# On game over (in main loop)
if event == "died":
    _save_high_score(model.high_score)
```

## Audio System (`_AudioManager` in `doodle_jump_view.py`)

### Design Goals
- Non-blocking playback (doesn't freeze game)
- Low memory footprint
- Automatic resource cleanup
- Rate limiting to prevent audio spam

### How It Works
1. Opens WAV file on demand
2. Plays through `AudioOutput` device
3. Immediately closes file to free memory
4. Tracks last play time for rate limiting
5. Reinitializes audio device every 50 plays to prevent heap fragmentation

### Rate Limiting
- `_MIN_INTERVAL = 0.08`: Minimum 80ms between sound effects
- Prevents audio spam when player bounces rapidly
- Ensures clean playback without overlapping

### Memory Management
- Files opened/closed on each play (no persistent file handles)
- Audio device reinitialized every 50 plays
- Cleanup on exceptions to prevent resource leaks

## Collision Detection

Located in `Doodle_Jump_logic.player_lands_on()` method.

Uses Axis-Aligned Bounding Box (AABB) method:
1. **Horizontal Overlap**: Check if player's horizontal bounds overlap platform's bounds
2. **Vertical Contact**: Check if player's feet are at platform height
3. **Velocity Compensation**: Account for velocity to catch fast-falling player
4. Return true only if BOTH conditions met

```python
def player_lands_on(self, platform_x, platform_y):
    player_feet = self.player_y + PLAYER_H
    overlaps_horizontally = (player_right > platform_left and 
                            player_left < platform_right)
    feet_at_platform = (player_feet >= platform_y and
                        player_feet <= platform_y + PLATFORM_H + self.velocity_y)
    return overlaps_horizontally and feet_at_platform
```

## Camera Scrolling

Located in `Doodle_Jump_logic.jump()` method.

### How It Works
1. Player moves naturally with physics
2. When player reaches `SCROLL_THRESHOLD` (1/4 from top):
   - Player locked at threshold
   - All platforms scroll down by exact amount
   - Camera offset (`camera_y`) increases
   - Score = camera offset
3. Platforms that scroll off bottom are recycled to top
4. Creates illusion of infinite upward movement

### Why It's Smooth
- Camera moves by exact amount player moved (1:1 mapping)
- No discrete jumps or snapping
- Consistent speed matches player physics
- Platform positions updated continuously

### Platform Recycling
```python
# When platform scrolls off bottom
if py > SCREEN_H + PLATFORM_H:
    new_x = random.randint(0, SCREEN_W - PLATFORM_W)
    new_y = highest_y - PLATFORM_SPACING
    self.platforms[i] = (new_x, new_y)
```

## Memory Management

### Garbage Collection
- Called once at startup with `gc.collect()` in `main()`
- Frees unused memory before game starts
- Important on microcontrollers with limited RAM (~192KB)

### Platform Management  
- Fixed number of platforms (determined by `PLATFORM_SPACING`)
- No dynamic allocation during gameplay
- Platforms stored as tuples: `(x, y)`
- Recycled by updating tuple values (no creation/deletion)

### Graphics Optimization (in View)
- Platform shapes created once: `self.platform_shapes = []`
- Only positions updated each frame: `shape.x = new_x`
- No `append()` or `remove()` calls during gameplay
- Prevents heap fragmentation from repeated allocations

### Score Display
- Single label object reused throughout
- Text property updated (no object recreation)
- Anchor point set to (1.0, 0.0) for right-alignment
- Updates batched: only when score changes by 5+ points

## Start Screen System

Located in `display.__init__()` and related methods in `doodle_jump_view.py`.

### Components
- Separate display group (`self._start_group`)
- Can be shown/hidden with `hidden` property
- Contains:
  - Dark background
  - "DOODLE JUMP" title (green, scale 3)
  - Doodle sprite preview
  - "TILT : MOVE" instructions
  - High score display (yellow, scale 2)
  - Blinking "PRESS BUTTON TO START" prompt
  - Credit line

### Animation
- Blink counter cycles 0-59
- Prompt visible for frames 0-29 (yellow)
- Prompt hidden for frames 30-59 (dark blue)
- Called every frame in menu state: `view.blink_start_prompt()`

## Frame Rate

- **Target**: ~20 FPS (50ms per frame)
- **Control**: `time.sleep(0.05)` at end of game loop
- **Balance**: Animation smoothness vs LCD refresh rate
- **Note**: No sleep in menu state blink loop (runs at full speed)

## Performance Optimizations

### 1. Platform Recycling
- Reuse platform objects instead of create/destroy
- Prevents memory allocation during gameplay
- Faster than constantly creating new tuples

### 2. Graphics Reuse
- Platform rectangles created once
- Only update `.x` and `.y` properties
- Avoids displayio group mutations

### 3. Batched Score Updates
- Only update text when score changes by 5+
- Reduces string allocations
- Prevents LCD flicker from constant updates

### 4. NVM Write Once
- High score saved only on death
- Not saved every time it increases
- Avoids lag from NVM writes during gameplay

### 5. Right-Aligned Score
- Anchor point set to (1.0, 0.0)
- Score stays right-aligned as digits increase
- No recalculation of x position needed

### 6. Audio Rate Limiting
- 80ms minimum between sound effects
- Prevents audio spam
- Reduces file I/O overhead

## Import Dependencies

### `code.py` (Model + Main)
```python
import pykit_explorer              # Board initialization
from doodle_jump_controller import Controller
from doodle_jump_view import display
import struct                      # NVM data packing
import microcontroller            # NVM access
import gc                         # Garbage collection
import time                       # Frame timing
import random                     # Platform generation
```

### `doodle_jump_view.py` (View)
```python
from lcd_display import LCDDisplay, Colors
from audio_out import AudioOutput
from audiocore import WaveFile
import displayio                  # Graphics groups
import time                       # Audio timing
```

### `doodle_jump_controller.py` (Controller)
```python
from imu_sensor import IMUSensor
import board                      # Pin definitions
import digitalio                  # Button input
```

## Debugging Tips

### Print Free Memory
```python
import gc
gc.collect()
print(f"Free RAM: {gc.mem_free()} bytes")
```

### Check NVM Contents
```python
import microcontroller
print(bytes(microcontroller.nvm[0:6]))  # Should show b'HSv1' + 2 bytes
```

### Test Collision Detection
Add to model's `player_lands_on()`:
```python
if result:
    print(f"Landed on platform at ({platform_x}, {platform_y})")
```

### Monitor Frame Rate
```python
import time
start = time.monotonic()
# ... game loop iteration ...
print(f"Frame time: {(time.monotonic() - start) * 1000:.1f}ms")
```

## Common Modifications

### Change Difficulty Scaling
```python
# Slower difficulty ramp-up
MAX_DIFFICULTY_SCORE = 2000  # Takes longer to reach max difficulty

# Faster difficulty ramp-up
MAX_DIFFICULTY_SCORE = 500   # Reaches max difficulty quickly

# Adjust max difficulty
MAX_GRAVITY = 1.2            # Even faster at max
MAX_JUMP_VELOCITY = -14      # Even faster jumps at max
MIN_PLATFORM_W = 20          # Even smaller platforms at max

# Adjust starting difficulty
BASE_GRAVITY = 0.4           # Original slower start
BASE_JUMP_VELOCITY = -8      # Original slower start
```

### Add Different Platform Types
In model's `reset()` and platform recycling:
```python
# Store platform type with position
self.platforms.append((x, y, "normal"))  # or "moving", "breakable"

# In view's render(), draw different colors:
if platform_type == "normal":
    color = 0x00FF00  # Green
elif platform_type == "breakable":
    color = 0xFF0000  # Red
```

### Change Screen Wrap Behavior
In model's `move_horizontal()`:
```python
# Current: wrap to opposite side
if self.player_x < 0:
    self.player_x = SCREEN_W

# Alternative: stop at edges
if self.player_x < 0:
    self.player_x = 0
if self.player_x > SCREEN_W - PLAYER_W:
    self.player_x = SCREEN_W - PLAYER_W
```

## Testing Checklist

- [ ] Player bounces on platforms correctly
- [ ] Tilt controls work in both directions
- [ ] Screen wrapping works (player appears on opposite side)
- [ ] Score increases as player climbs
- [ ] High score persists after power cycle
- [ ] Game over screen appears when player falls
- [ ] Start screen button works
- [ ] Audio plays for jump and game over
- [ ] No memory errors during long gameplay
- [ ] Frame rate stays consistent (~20 FPS)

## Known Limitations

1. **Fixed Platform Count**: Number of platforms determined by `PLATFORM_SPACING`, cannot dynamically increase
2. **No Platform Variety**: All platforms are identical (green rectangles)
3. **Simple Physics**: No acceleration/deceleration for horizontal movement
4. **Audio Limited**: Only 2 sound effects (jump, gameover)
5. **Single Player Only**: No multiplayer or leaderboards

## Future Enhancement Ideas

1. **Power-ups**: Springs for extra jump, shields, double jump
2. **Enemy Platforms**: Moving platforms, disappearing platforms
3. ~~**Progressive Difficulty**: Increase GRAVITY or PLATFORM_SPACING as score increases~~ ✅ Implemented!
4. **Visual Effects**: Particle effects, background parallax
5. **More Sounds**: Background music, special platform sounds
6. **Touch Controls**: Use touchscreen instead of/in addition to tilt
7. **Themes**: Different visual styles (space, underwater, etc.)
8. **Achievements**: Track statistics beyond just high score

## Progressive Difficulty System

The game now features progressive difficulty that scales with score:

### How It Works
1. `get_difficulty_params()` calculates current values based on score
2. Uses an ease-out curve (`factor ** 0.7`) for smooth progression
3. Fast ramp-up in early game, gradual approach to max difficulty

### What Scales
| Parameter | At Score 0 | At Score 1000+ |
|-----------|------------|----------------|
| Gravity | 0.484 | 0.9 |
| Jump Velocity | -8.8 | -12 |
| Platform Width | 40px | 25px |
| Control Sensitivity | 1.0x | 1.5x |

### Implementation
```python
def get_difficulty_params(self):
    factor = min(1.0, self.score / MAX_DIFFICULTY_SCORE)
    eased = factor ** 0.7  # Ease-out curve
    
    gravity = BASE_GRAVITY + (MAX_GRAVITY - BASE_GRAVITY) * eased
    jump_vel = BASE_JUMP_VELOCITY + (MAX_JUMP_VELOCITY - BASE_JUMP_VELOCITY) * eased
    sensitivity = 1.0 + 0.5 * eased
    platform_w = BASE_PLATFORM_W - (BASE_PLATFORM_W - MIN_PLATFORM_W) * eased
    
    return gravity, jump_vel, sensitivity, int(platform_w)
```

The main loop applies these values:
- Gravity and jump velocity are used in `jump()` for physics
- Sensitivity multiplies the controller input
- Platform width is used for both collision detection and rendering
