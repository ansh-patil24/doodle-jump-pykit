# Doodle Jump - CircuitPython Game

An implementation of Doodle Jump for the Microchip Curiosity PyKit Explorer, built with CircuitPython.

![Game Preview](Sprites/doodle.bmp)

## 🎮 Game Features

- **Tilt Controls**: Use the built-in IMU sensor to move left and right by tilting the device
- **Score Tracking**: Keep track of your current score and high score
- **Endless Gameplay**: Platforms are generated infinitely as you climb higher
- **Screen Wrapping**: Move off one side of the screen to appear on the other

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
   ├── code.py
   ├── pykit_explorer.py
   ├── API/
   │   ├── imu_sensor.py
   │   ├── lcd_display.py
   │   ├── audio_out.py
   │   └── pwm_out.py
   ├── Sprites/
   │   └── doodle.bmp
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

1. **Start**: The game begins automatically when powered on
2. **Move**: Tilt the device left or right to control the player
3. **Jump**: The player automatically jumps - you just control horizontal movement
4. **Goal**: Jump from platform to platform and climb as high as possible
5. **Game Over**: If you fall off the bottom of the screen, your score is displayed
6. **Continue**: The game automatically restarts after the game over screen

## 🎨 Game Mechanics

- **Gravity**: 0.4 pixels/frame²
- **Jump Velocity**: -8 pixels/frame (upward)
- **Platform Spacing**: 35 pixels apart vertically
- **Platform Size**: 40x6 pixels (green rectangles)
- **Player Size**: 16x16 pixels
- **Screen**: 240x135 pixels
- **Tilt Sensitivity**: Configurable deadzone (0.3) and max speed (10 pixels/frame)

## 🏗️ Code Structure

The game follows an MVC (Model-View-Controller) pattern:

- **`Doodle_Jump_logic`** (Model): Game state, physics, collision detection, scoring
- **`display`** (View): Rendering graphics, updating sprites, showing game over screen
- **`Controller`**: Reading IMU sensor and converting to player movement

## 📝 Configuration Constants

You can adjust these in `code.py`:

```python
GRAVITY = 0.4           # Downward acceleration
JUMP_VELOCITY = -8      # Initial jump speed
PLATFORM_SPACING = 35   # Distance between platforms
TILT_DEADZONE = 0.3     # Minimum tilt to register
TILT_MAX = 10.0         # Maximum movement speed
```

## 📜 License

This project is built on the PyKit Ruler CircuitPython Module Library.

## 🙏 Credits

- Game concept inspired by the original Doodle Jump by Lima Sky
- Built with CircuitPython and Adafruit libraries
- Runs on Microchip Curiosity PyKit Explorer hardware

## 🚀 Future Enhancements

- [ ] Audio effects
- [ ] Difficulty scaling with player score
- [ ] Loading Screen
- [ ] Different platform types (moving, breakable, springs)
- [ ] Enemy obstacles
- [ ] Power-ups
- [ ] Multiple themes/sprites

---

**Enjoy the game! Try to beat your high score!** 🎮
