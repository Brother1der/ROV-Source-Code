#thing that goes up and down for dive

#Imports
import time
import board
import os
import sys
import busio
from digitalio import DigitalInOut, Direction, Pull
import adafruit_ssd1306
import adafruit_rfm9x
from digitalio import DigitalInOut, Direction, Pull
from FloatVerticalProfiler.motorControls.MotorController import MotorController

# Motor controller pins (BCM pin numbers for RPi.GPIO)
PWM_PIN = 18
INA_PIN = 23
INB_PIN = 24
PWM_FREQ = 1000

# Hall effect sensor pins
MIN_LIMIT_PIN = board.D11  # bottom sensor (motor down limit)
MAX_LIMIT_PIN = board.D7   # top sensor (motor up limit)

# Motor directions
UP = "CCW"      # Motor direction to drain syringe (ascend)
DOWN = "CW"     # Motor direction to fill syringe (descend)

# Movement settings
MOVE_SPEED = 100
POLL_INTERVAL = 0.05
TIMEOUT_SECONDS = 30
WAIT_AFTER_BOTTOM_SECONDS = 10

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

def setup_sensor(pin):
    sensor = DigitalInOut(pin)
    sensor.direction = Direction.INPUT
    sensor.pull = Pull.DOWN
    return sensor


def wait_for_sensor(sensor, target_state, timeout):
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if sensor.value == target_state:
            return True
        time.sleep(POLL_INTERVAL)
    return False


def main():
    bottom_sensor = setup_sensor(MIN_LIMIT_PIN)
    top_sensor = setup_sensor(MAX_LIMIT_PIN)
    motor = MotorController(PWM_PIN, INA_PIN, INB_PIN, PWM_FREQ)

    time.sleep(180) #this is for waiting for the float to be sealed, sorry for not having the other pi at pool for radio functionality

    try:
        print("Moving down")
        motor.update_direction(DOWN)
        motor.set_speed(MOVE_SPEED)

        if not wait_for_sensor(bottom_sensor, True, TIMEOUT_SECONDS):
            raise RuntimeError("Bottom limit sensor did not trigger before timeout.")

        motor.stop()
        print("Motor stopped.")

        print(f"Waiting {WAIT_AFTER_BOTTOM_SECONDS} seconds")
        time.sleep(WAIT_AFTER_BOTTOM_SECONDS)

        print("Moving up")
        motor.update_direction(UP)
        motor.set_speed(MOVE_SPEED)

        if not wait_for_sensor(top_sensor, True, TIMEOUT_SECONDS):
            raise RuntimeError("Top limit sensor did not trigger before timeout.")

        motor.stop()
        print("Motor stopped.")

    except Exception as exc:
        print(f"Error: {exc}")
        motor.stop()
        raise
    finally:
        motor.cleanup_motor_controller()
        bottom_sensor.deinit()
        top_sensor.deinit()


if __name__ == "__main__":
    main()
