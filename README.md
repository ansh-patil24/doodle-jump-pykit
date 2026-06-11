# Doodle Jump - CircuitPython Game

An implementation of Doodle Jump for the Microchip Curiosity PyKit Explorer, built with CircuitPython using the MVC (Model-View-Controller) architecture pattern.

![Game Preview](Sprites/doodle.bmp)

## 🎮 Game Features

- **Tilt Controls**: Use the built-in IMU sensor to move left and right by tilting the device
- **Score Tracking**: Keep track of your current score and high score (persists across power cycles!)
- **Endless Gameplay**: Platforms are generated infinitely as you climb higher
- **Screen Wrapping**: Move off one side of the screen to appear on the other
- **Start Screen**: Menu with high score display and button to start
- **Sound Effects**: Jump and game over audio feedback

## 🔧 Hardware Requirements

- **Microchip Curiosity PyKit Explorer** board
- **ST7789 LCD Display** (240x135 pixels)
- **ICM20948 9-Axis IMU Sensor** (for tilt controls)
- **CircuitPython 10.x**

## 📦 Installation

1. Install CircuitPython 10.x on your PyKit Explorer board
2. Copy all files maintaining the directory structure:
   ```
   CIRCUITPY/
   ├── code.py                     # Main game logic (Model + Main loop)
   ├── doodle_jump_view.py         # Display and audio (View)
   ├── doodle_jump_controller.py   # Input handling (Controller)
   ├── pykit_explorer.py
   ├── API/
   │   ├── imu_sensor.py
   │   ├── lcd_display.py
   │   ├── audio_out.py
   │   └── pwm_out.py
   ├── Sprites/
   │   └── doodle.bmp
   ├── AudioFiles/
   │   ├── doodle_jump.wav
   │   └── doodle_jump_gameover.wav
   └── lib/
       ├── adafruit_st7789.mpy
       ├── adafruit_icm20x.mpy
       ├── adafruit_display_shapes/
       ├── adafruit_display_text/
       ├── adafruit_imageload/
       └── adafruit_register/
   ```
3. The game should start automatically!

## 🎯 How to Play

1. **Start**: Press the D3 button on the start screen to begin
2. **Move**: Tilt the device left or right to control the player
3. **Jump**: The player automatically jumps - you just control horizontal movement
4. **Goal**: Jump from platform to platform and climb as high as possible
5. **Game Over**: If you fall off the bottom of the screen, your score is displayed
6. **Continue**: Press the button to return to the start screen and play again

## 🎨 Game Mechanics

- **Gravity**: 0.4 pixels/frame²
- **Jump Velocity**: -8 pixels/frame (upward)
- **Platform Spacing**: 35 pixels apart vertically
- **Platform Size**: 40x6 pixels (green rectangles)
- **Player Size**: 16x16 pixels
- **Screen**: 240x135 pixels
- **Tilt Sensitivity**: Configurable deadzone (0.3) and max speed (10 pixels/frame)

## 🏗️ Code Structure

The game follows an MVC (Model-View-Controller) pattern with clean separation across three files:

### **Model** (`code.py`)
- Contains `Doodle_Jump_logic` class
- Handles game state, physics, collision detection, scoring
- Manages platform recycling and camera scrolling
- Persists high score to NVM (Non-Volatile Memory)
- Triggers audio events through view's audio manager

### **View** (`doodle_jump_view.py`)
- Contains `display` class and `_AudioManager` class
- Renders graphics: player sprite, platforms, score, start/game over screens
- Manages non-blocking audio playback with rate limiting
- Optimizes rendering to prevent flicker and improve performance

### **Controller** (`doodle_jump_controller.py`)
- Contains `Controller` class
- Reads IMU sensor data for tilt controls
- Reads D3 button for menu navigation
- Applies deadzone filtering and converts tilt to movement

### Main Loop (`code.py`)
- Coordinates MVC components
- State machine: `STATE_MENU` ⟷ `STATE_PLAYING`
- Runs at ~20 FPS (50ms per frame)

For detailed architecture and implementation details, see [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md).

## 📝 Configuration Constants

You can adjust these in `code.py`:

```python
GRAVITY = 0.4           # Downward acceleration
JUMP_VELOCITY = -8      # Initial jump speed
PLATFORM_SPACING = 35   # Distance between platforms
TILT_DEADZONE = 0.3     # Minimum tilt to register
TILT_MAX = 10.0         # Maximum movement speed
```

## 🎵 Audio System

The game includes non-blocking audio with automatic resource management:
- **Jump Sound**: Plays when landing on platforms
- **Game Over Sound**: Plays when falling off screen
- **Rate Limiting**: Prevents audio spam (80ms minimum between plays)
- **Memory Management**: Files opened/closed on each play to conserve RAM

## 💾 High Score Persistence

High scores are saved to NVM (Non-Volatile Memory) and persist across:
- Power cycles
- Code updates
- Board resets

The score is saved only on game over (not continuously) to avoid lag.

## 🔧 Performance Optimizations

- **Platform Recycling**: Reuse objects instead of create/destroy
- **Graphics Reuse**: Update positions, don't recreate rectangles
- **Batched Score Updates**: Update every 5 points to prevent flicker
- **Audio Rate Limiting**: Prevents file I/O overhead
- **Single Frame Sleep**: Consistent 20 FPS timing

## 📜 License

This project is built on the PyKit Ruler CircuitPython Module Library.

## 🙏 Credits

- Game concept inspired by the original Doodle Jump by Lima Sky
- Built with CircuitPython and Adafruit libraries
- Runs on Microchip Curiosity PyKit Explorer hardware

## 🚀 Future Enhancements

- [ ] Difficulty scaling with player score
- [ ] Different platform types (moving, breakable, springs)
- [ ] Enemy obstacles
- [ ] Power-ups
- [ ] Multiple themes/sprites
- [ ] Background music

## 📚 Documentation

- [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) - Detailed code architecture and implementation guide
- Inline code comments explain complex logic

---

**Enjoy the game! Try to beat your high score!** 🎮
