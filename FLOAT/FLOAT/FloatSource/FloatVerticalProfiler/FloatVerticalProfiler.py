### Last Modified 2/23/2026 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: Combine all of the functionality from the objects to have one main control script.
# Requirements: Device with full python support, PWM outputs and GPIO Control MS5837
# Pressure sensor and ROV_PROGRAMS Library
# ###

#IMPORTS
import time
import RPi.GPIO as GPIO

from FloatVerticalProfiler.pressureSensor import PressureSensorData
from FloatVerticalProfiler.depthControls.DepthTarget import DepthTarget
from FloatRadioControls.send_float_data import send_data

#CONSTANTS
DENSITY = 1000
HOLD_DURATION = 30
DEPTH_TOLERANCE = 0.33
START_DEPTH = 0.0
UP = "CW"      # Motor direction to drain syringe (ascend)
DOWN = "CCW"     # Motor direction to fill syringe (descend)
LOW_TARGET_DEPTH = 2.5
HIGH_TARGET_DEPTH = 0.4
SURFACE = -5
END_DEPTH = 1000

# Syringe physical dimensions
SYRINGE_RADIUS_MM = 20      # Inner radius of syringe barrel (40mm bore / 2)
SYRINGE_LENGTH_MM = 114     # Stroke length of the plunger
THREAD_PITCH_MM = 4         # Lead screw thread pitch
MOTOR_RPM = 200             # Rated no-load; loaded shaft speed at the lead screw is ~122 RPM

# Hall-effect limit switches on syringe (normally-closed, pull-up, active LOW)
MIN_LIMIT_PIN = 8                # syringe fully drained (max UP buoyancy)
MAX_LIMIT_PIN = 4               # syringe fully filled (max DOWN buoyancy)
LIMIT_TRIGGERED_LEVEL = 0           # GPIO.input value when switch is at limit

class FloatVerticalProfiler:
    def __init__(self):
        # Creating the pressure sensor
        self.sensor_data = PressureSensorData.PressureSensorData(DENSITY)

        # Creating depth target with syringe tracker for PD volume control
        self.depth_target = DepthTarget(self.sensor_data, UP, DOWN)

        # Limit switch GPIO setup (MotorController already called setmode(BCM); idempotent)
        GPIO.setmode(GPIO.BCM)
        for pin in (MIN_LIMIT_PIN, MAX_LIMIT_PIN):
            if pin is not None:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _limit_at_max(self):
        if MAX_LIMIT_PIN is None:
            return False
        return GPIO.input(MAX_LIMIT_PIN) == LIMIT_TRIGGERED_LEVEL

    def _limit_at_min(self):
        if MIN_LIMIT_PIN is None:
            return False
        return GPIO.input(MIN_LIMIT_PIN) == LIMIT_TRIGGERED_LEVEL

    def write_to_file(self, data: str, filename: str):
        with open(filename, 'w') as file:
            file.write(data)

    def go_to_surface(self):
        self.depth_target.go_to_target(SURFACE)

    def complete_profile(self):
            self.depth_target.go_to_target(LOW_TARGET_DEPTH, k_stop=800.0, hold_zone=0.33)
            self.depth_target.depth_hold(LOW_TARGET_DEPTH, duration=35.0, tolerance=0.33)

            self.depth_target.go_to_target(HIGH_TARGET_DEPTH, k_stop=650.0, max_compress_ml=15.0, max_expand_ml=2.0, hold_zone=0.29, max_vel=0.03)
            self.depth_target.depth_hold(HIGH_TARGET_DEPTH, duration=35.0, tolerance=0.29)

            self.depth_target.go_to_target(LOW_TARGET_DEPTH, k_stop=800.0, hold_zone=0.33)
            self.depth_target.depth_hold(LOW_TARGET_DEPTH, duration=35.0, tolerance=0.33)

            self.depth_target.go_to_target(HIGH_TARGET_DEPTH, k_stop=650.0, max_compress_ml=15.0, max_expand_ml=2.0, hold_zone=0.29, max_vel=0.03)
            self.depth_target.depth_hold(HIGH_TARGET_DEPTH, duration=35.0, tolerance=0.29)

    def sink_to_bottom(self, fill_duty=100, pulse_on=0.2, pulse_off=0.8, safety_timeout=180.0):
        # Drive syringe DOWN (filling) until the MAX hall switch triggers.
        # Pool depth is unknown — switch is the only termination. Falls back
        # to wall-clock timeout if the pin isn't wired yet.
        print("sink_to_bottom: pumping DOWN until MAX limit switch")
        deadline = time.time() + safety_timeout
        while not self._limit_at_max():
            if time.time() > deadline:
                print("sink_to_bottom: SAFETY TIMEOUT — stopping pump")
                break
            self.depth_target._drive(DOWN, fill_duty)
            time.sleep(pulse_on)
            self.depth_target.motorController.set_speed(0)
            time.sleep(pulse_off)
        self.depth_target.motorController.set_speed(0)
        print("sink_to_bottom: MAX limit reached, motor stopped")

    def wait_for_surface(self, surface_depth=0.5, dwell_secs=3.0, timeout=900.0):
        # Block (motor off) until depth < surface_depth for dwell_secs.
        # Rescue ROV lifts the float; we just monitor the pressure sensor.
        print(f"wait_for_surface: waiting for depth < {surface_depth}m for {dwell_secs}s")
        self.depth_target.motorController.set_speed(0)
        above_start = None
        deadline = time.time() + timeout
        while time.time() < deadline:
            depth = self.sensor_data.get_latest_depth()[1]
            if depth < surface_depth:
                above_start = above_start or time.time()
                if time.time() - above_start >= dwell_secs:
                    print(f"wait_for_surface: at surface ({depth:.2f}m), proceeding to send")
                    return
            else:
                above_start = None
            time.sleep(0.5)
        print("wait_for_surface: timeout — sending anyway")

    def send_data_until_ack(self, filename, max_attempts=20, retry_delay=5.0):
        # send_data loops per-chunk until ACK; this wraps the whole call so
        # the file is retransmitted if send_data ever raises.
        for attempt in range(1, max_attempts + 1):
            print(f"send attempt {attempt}/{max_attempts}")
            try:
                send_data(filename)
                return
            except Exception as exc:
                print(f"send_data raised: {exc!r}")
            time.sleep(retry_delay)
        print("send_data_until_ack: gave up after max_attempts")

    def cleanup(self):
        #Cleanup sensor threads and motor GPIO
        self.sensor_data.stop_data_collection()
        self.depth_target.motorController.cleanup_motor_controller()

    def perform_profiles(self):
        # Settle motion, then zero the syringe estimator at deployment trim
        # (water temp/chemistry varies day-to-day; ~50 g positive buoyancy expected).

        self.depth_target.settle()

        self.depth_target.calibrate_syringe()
        print("Going to target")
        # Two full profiles: 2.5m -> 0.4m -> 2.5m -> 0.4m, 35-s holds each
        self.complete_profile()

        # Pump syringe to MAX so float sinks to floor; rescue ROV retrieves it
        self.sink_to_bottom()

        # Once back at surface, transmit data until ACK
        self.wait_for_surface()
        float_data = self.sensor_data.package_data()
        self.write_to_file(str(float_data), "float_data.txt")
        self.send_data_until_ack("float_data.txt")

        self.cleanup()
