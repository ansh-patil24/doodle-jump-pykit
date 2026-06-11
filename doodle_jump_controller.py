"""
================================================================================
DOODLE JUMP - Controller (Input Handling)
================================================================================
Handles IMU sensor input and button controls for the Doodle Jump game.
"""

from imu_sensor import IMUSensor
import board
import digitalio

# Tilt configuration constants (from model)
TILT_DEADZONE = 0.3
TILT_MAX = 10.0


class Controller:
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
