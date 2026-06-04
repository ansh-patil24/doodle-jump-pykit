# Doodle Jump - Complete Code Documentation

## Overview
This is a platformer game for the PyKit Explorer.

## Architecture: Model-View-Controller (MVC)

### Model (`Doodle_Jump_logic` class)
- **Purpose**: Contains all game logic and state
- **Responsibilities**:
  - Player physics (gravity, velocity, position)
  - Platform management and recycling
  - Collision detection
  - Audio effects
  - Score calculation
  - Camera scrolling logic

### View (`display` class)  
- **Purpose**: Handles all visual output
- **Responsibilities**:
  - Initialize LCD display
  - Render player sprite
  - Render platforms (with reuse optimization)
  - Display score (with update batching)
  - Show game over screen

### Controller (`Controller` class)
- **Purpose**: Reads and processes input
- **Responsibilities**:
  - Read IMU sensor data
  - Apply deadzone filtering
  - Convert tilt to movement

## Constants Explained

### Physics
- `GRAVITY = 0.4`: Acceleration per frame (pixels/frame²)
- `JUMP_VELOCITY = -8`: Initial bounce velocity (negative = upward)

### Screen  
- `SCREEN_W = 240`: Display width
- `SCREEN_H = 135`: Display height

### Player
- `PLAYER_W = 16`: Sprite width
- `PLAYER_H = 16`: Sprite height

### Platforms
- `PLATFORM_W = 40`: Width in pixels
- `PLATFORM_H = 6`: Height in pixels  
- `PLATFORM_SPACING = 35`: Vertical gap between platforms

### Controls
- `TILT_DEADZONE = 0.3`: Minimum tilt to register (prevents drift)
- `TILT_MAX = 10.0`: Maximum movement speed (pixels/frame)

## Game Loop Flow

```
Initialize → [Read Input → Update Physics → Check Death → Render] → Repeat
                                               ↓
                                            If Died → Save Score → Show Game Over → Reset
```

## NVM (Non-Volatile Memory) System

### Storage Format
- **Magic Marker** (4 bytes): "HSv1" - verifies data validity
- **High Score** (2 bytes): Unsigned 16-bit integer (0-65535)
- **Total**: 6 bytes

### Functions
1. `_nvm_available()`: Checks if board supports NVM
2. `_load_high_score()`: Reads saved score on startup
3. `_save_high_score()`: Writes score on game over

## Collision Detection

Uses Axis-Aligned Bounding Box (AABB) method:
1. Check horizontal overlap between player and platform
2. Check if player's feet are at platform height
3. Account for velocity to catch fast-falling player
4. Return true only if BOTH conditions met

## Camera Scrolling

### How It Works
1. Player moves naturally with physics
2. When player reaches SCROLL_THRESHOLD (1/4 from top):
   - Player locked at threshold
   - All platforms scroll down
   - Score increases based on scroll amount
3. Platforms that scroll off bottom are recycled to top
4. Creates illusion of infinite upward movement

### Why It's Smooth
- Camera moves by exact amount player moved (1:1 mapping)
- No discrete jumps or snapping
- Consistent speed matches player physics
- Platform positions updated continuously

## Memory Management

### Garbage Collection
- Called once at startup with `gc.collect()`
- Frees unused memory before game starts
- Important on microcontrollers with limited RAM

### Platform Management  
- Fixed number of platforms (determined by `PLATFORM_SPACING`)
- No dynamic allocation during gameplay
- All objects created once in initialization

### Score Display
- Single label object reused throughout
- Text property updated (no object recreation)
- Anchor point eliminates position recalculation

## Frame Rate

- Target: ~20 FPS (50ms per frame)
- `time.sleep(0.05)` controls frame timing
- Balance between animation and LCD refresh rate

## File Structure

```
code.py                     # Main game file
├── Imports                 # Hardware and standard libraries
├── Constants              # Game configuration values
├── NVM Configuration      # Persistent storage setup
├── Doodle_Jump_logic      # Model class (game logic)
├── Controller             # Input handling
├── display                # View class (rendering)
├── NVM Functions          # Load/save high scores
└── main()                 # Game loop
```
