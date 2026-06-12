# """
# ================================================================================
# DOODLE JUMP - Controller (Input Handling)
# ================================================================================
# Handles IMU sensor input and button controls for the Doodle Jump game.
# """

# from imu_sensor import IMUSensor
# import board
# import digitalio

# # Tilt configuration constants (from model)
# TILT_DEADZONE = 0.3
# TILT_MAX = 10.0


# class Controller:
#     def __init__(self):
#         self.imu = IMUSensor()

#         # D3 button for starting game (active-LOW with pull-up)
#         self._btn = digitalio.DigitalInOut(board.D3)
#         self._btn.direction = digitalio.Direction.INPUT
#         self._btn.pull = digitalio.Pull.UP

#     def get_horizontal_movement(self):
#         ax, ay, az = self.imu.acceleration
#         if abs(ax) < TILT_DEADZONE:
#             return 0
#         dx = int(ax * 0.8)
#         dx = max(-TILT_MAX, min(TILT_MAX, dx))

#         return dx

#     def button_pressed(self):
#         """Check if D3 button is pressed (active-LOW inverted)."""
#         return not self._btn.value
import board
import digitalio

  # Movement speed when button is pressed
MOVE_SPEED = 3  # Pixels per frame


class Controller:
    def __init__(self):
        # Remove IMU initialization - not needed for button controls
        # self.imu = IMUSensor()

        # D3 button for starting game (active-LOW with pull-up)
        self._btn = digitalio.DigitalInOut(board.D3)
        self._btn.direction = digitalio.Direction.INPUT
        self._btn.pull = digitalio.Pull.UP

          # D2 button for moving right (active-LOW with pull-up)
        self._move_btn = digitalio.DigitalInOut(board.D2)
        self._move_btn.direction = digitalio.Direction.INPUT
        self._move_btn.pull = digitalio.Pull.UP

    def get_horizontal_movement(self):
        """Return horizontal movement based on button press."""
        # If D2 button is pressed, move right
        if not self._move_btn.value:  # Active LOW
            return MOVE_SPEED
        else:
            return 0  # No movement

    def button_pressed(self):
        """Check if D3 button is pressed (active-LOW inverted)."""
        return not self._btn.value