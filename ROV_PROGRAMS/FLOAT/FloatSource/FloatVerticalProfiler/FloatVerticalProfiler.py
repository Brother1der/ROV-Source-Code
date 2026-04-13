### Last Modified 2/23/2026 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: Combine all of the functionality from the objects to have one main control script.
# Requirements: Device with full python support, PWM outputs and GPIO Control MS5837
# Pressure sensor and ROV_PROGRAMS Library
# ###

#IMPORTS
from FloatSource.FloatVerticalProfiler.pressureSensor import PressureSensorData
from FloatSource.FloatVerticalProfiler.depthControls.DepthTarget import DepthTarget
from FloatSource.FloatRadio import rfm9x_float

#CONSTANTS
DENSITY = 1000
HOLD_DURATION = 35
DEPTH_TOLERANCE = 0.33
START_DEPTH = 0.0
UP = "CCW"      # Motor direction to drain syringe (ascend)
DOWN = "CW"     # Motor direction to fill syringe (descend)
LOW_TARGET_DEPTH = 2.5
HIGH_TARGET_DEPTH = 0.4
SURFACE = -5

# Syringe physical dimensions
SYRINGE_RADIUS_MM = 20      # Inner radius of syringe barrel (40mm bore / 2)
SYRINGE_LENGTH_MM = 159     # Stroke length of the plunger
THREAD_PITCH_MM = 4         # Lead screw thread pitch
MOTOR_RPM = 120             # Motor speed

# Hall effect limit switch GPIO pins (set to None until hardware is wired)
MIN_LIMIT_PIN = None
MAX_LIMIT_PIN = None

class FloatVerticalProfiler:
    def __init__(self):
        # Creating the pressure sensor
        self.sensor_data = PressureSensorData.PressureSensorData(DENSITY)

        # Creating depth target with syringe tracker for PD volume control
        self.depth_target = DepthTarget(self.sensor_data, UP, DOWN)

    def write_to_file(self, data: str, filename: str):
        with open(filename, 'w') as file:
            file.write(data)

    def go_to_surface(self):
        self.depth_target.go_to_target(SURFACE)

    def complete_profile(self):
            #Descending to starting depth to neutralize float(set to neutrally bouyant)
            self.depth_target.go_to_target(START_DEPTH)

            #Complete first leg of profile going to 2.5m with a hold and then returning to neutral buoyancy
            self.depth_target.go_to_target(LOW_TARGET_DEPTH, k_stop=800.0, hold_zone=0.33)
            self.depth_target.depth_hold(LOW_TARGET_DEPTH, duration=35.0, tolerance=0.33)
            self.depth_target.settle()

            #Complete the second leg of the profile going from 2.5 to 0.4m with a hold and then returning to neutral buoyancy
            self.depth_target.go_to_target(HIGH_TARGET_DEPTH, k_stop=650.0, max_compress_ml=15.0, max_expand_ml=2.0, hold_zone=0.29, max_vel=0.03)
            self.depth_target.depth_hold(HIGH_TARGET_DEPTH, duration=35.0, tolerance=0.29)
            self.depth_target.settle()

            #Complete the third leg of the profile going from 0.4 to 2.5m with a hold and then returning to neutral buoyancy
            self.depth_target.go_to_target(LOW_TARGET_DEPTH, k_stop=800.0, hold_zone=0.33)
            self.depth_target.depth_hold(LOW_TARGET_DEPTH, duration=35.0, tolerance=0.33)
            self.depth_target.settle()

            #Complete the final leg of the profile going from 2.5 to 0.4m with a hold and then returning to neutral buoyancy
            self.depth_target.go_to_target(HIGH_TARGET_DEPTH, k_stop=650.0, max_compress_ml=15.0, max_expand_ml=2.0, hold_zone=0.29, max_vel=0.03)
            self.depth_target.depth_hold(HIGH_TARGET_DEPTH, duration=35.0, tolerance=0.29)


    def cleanup(self):
        #Cleanup sensor threads and motor GPIO
        self.sensor_data.stop_data_collection()
        self.depth_target.motorController.cleanup_motor_controller()

    def perform_profiles(self):
        #Completing two profiles
        self.complete_profile()

        #Printing out sensor data
        float_data = self.sensor_data.package_data()
        self.write_to_file(str(float_data), "float_data.txt")

    def send_data(self):
        #Runs the function to send the sensor data
        rfm9x_float.send_data("float_data.txt")

        self.cleanup()
