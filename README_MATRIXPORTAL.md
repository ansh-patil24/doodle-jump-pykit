# Doodle Jump - Adafruit MatrixPortal M4 Version

This branch contains a version of Doodle Jump optimized for the **Adafruit MatrixPortal M4** with a **64×32 RGB LED Matrix** display.

## Hardware Requirements

- **Adafruit MatrixPortal M4** (ATSAMD51J19 processor)
- **64×32 RGB LED Matrix Panel** (HUB75 interface)
- **2× Push Buttons** connected to D2 and D3
- **USB-C Power** (5V, recommended 2A+ for LED matrix)

## Hardware Differences from Original

| Component | PyKit Explorer (Original) | MatrixPortal M4 (This Version) |
|-----------|--------------------------|--------------------------------|
| **Display** | ST7789 LCD (240×135) | RGB LED Matrix (64×32) |
| **Input** | ICM-20948 IMU (tilt) | Push buttons (D2, D3) |
| **Audio** | I2S DAC | Not supported |
| **Processor** | SAMD51 | SAMD51 (same) |

## Game Scaling

All game elements have been scaled down to fit the smaller display:

| Element | Original | MatrixPortal |
|---------|----------|--------------|
| **Screen** | 240×135 px | 64×32 px |
| **Player** | 16×16 px | 4×4 px |
| **Platforms** | 40×6 px | 12×2 px |
| **Platform Spacing** | 35 px | 7 px |

## Controls

- **D3 Button**: Start game / Restart
- **D2 Button**: Move right (hold to continue moving)

Note: Horizontal movement is button-based instead of tilt-based due to MatrixPortal M4 not having an IMU sensor.

## Installation

1. Install CircuitPython 9.0+ on your MatrixPortal M4
2. Copy the following files to the CIRCUITPY drive:
   - `code.py`
   - `doodle_jump_controller.py`
   - `doodle_jump_view.py`
   - `Sprites/doode_small.bmp` (4×4 pixel sprite)
   
3. Install required libraries in `/lib/`:
   - `adafruit_matrixportal/`
   - `adafruit_display_shapes/`
   - `adafruit_display_text/`
   - `adafruit_imageload/`

4. Connect buttons:
   - D3 → Ground (start/restart button)
   - D2 → Ground (move right button)

## Key Code Changes

### Display Initialization
```python
from adafruit_matrixportal.matrix import Matrix
matrix = Matrix(width=64, height=32, bit_depth=4)
```

### Player Sprite
- Uses 4×4 pixel bitmap (`doode_small.bmp`)
- Loaded via `adafruit_imageload`
- Positioned with `displayio.Group`

### Text Rendering
- Uses `terminalio.FONT` (6px per character)
- Manual centering (no anchor point support)
- Compact layouts for small screen

### Collision Detection
- Frame-perfect platform detection
- Position snapping to prevent visual glitches
- Checks if player crossed platform surface

## Performance

- **Frame Rate**: ~20 FPS (50ms frame time)
- **Memory**: ~6KB heap for game objects
- **Display Update**: Hardware-accelerated via MatrixPortal library

## Known Limitations

- **No audio**: MatrixPortal M4 doesn't have audio output
- **Button-only input**: No tilt controls (no IMU sensor)
- **Lower resolution**: Text and sprites are minimal due to 64×32 display
- **Brightness**: LED matrix may need brightness adjustment in code

## Troubleshooting

### Display not working
- Check power supply (LED matrices need 2A+)
- Verify HUB75 cable connection
- Try reducing `bit_depth` to 2 or 3

### Buttons not responding
- Verify buttons are connected to D2 and D3
- Check pull-up resistors are enabled in code
- Test with multimeter for continuity

### Sprite not loading
- Confirm `Sprites/doode_small.bmp` exists
- Check file is exactly 4×4 pixels, 24-bit BMP
- Falls back to green rectangle if sprite fails

## Future Enhancements

- [ ] Add power-up platforms (different colors)
- [ ] Implement moving platforms
- [ ] Add scrolling background
- [ ] Support for 32×32 or 128×32 matrix sizes
- [ ] WiFi-based online leaderboard

## License

Same as parent repository.

## Credits

- Original Doodle Jump game concept by Lima Sky
- PyKit Explorer version by Ansh Patil
- MatrixPortal M4 port adapted with assistance from Claude Code
