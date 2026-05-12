### Last Modified 12/8/2025 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: This program is designed to test the motorController objects functionality
# Requirements: Device with full python support, PWM outputs and GPIO Control motorController class
###

from FloatSource.FloatVerticalProfiler.motorControls.MotorController import MotorController
import time

# Define GPIO pins (based on schematic)
PWM_PIN = 18     # Example: PWM1/GPIO13 from schematic
INA_PIN = 16     # INA input for direction
INB_PIN = 17     #INB input for direction
PWM_FREQ = 1000  #PWM frequencies for motor controller

#Tests the motor looping through cw stop and ccw
def motor_test_loop(motor: MotorController):

    #Clockwise test
    motor_direction = "CW"
    motor.update_direction( motor_direction)
    motor.set_speed(100)

    #Pausing to allow the motor to run
    time.sleep(2)

    #Motor sitting still
    motor.stop()

    #Letting motor sit still for 1 second
    time.sleep(2)

    #Testing counterclockwise direction
    motor_direction = "CCW"
    motor.update_direction(motor_direction)
    motor.set_speed(100)

    #Letting counterclockwise direction
    time.sleep(2)

    #Stopping motor
    motor.stop()

def main():
    #Creating motor controller object
    motor = MotorController(PWM_PIN, INA_PIN, INB_PIN, PWM_FREQ)

    #Runs the loop, has exception to exit on keyboard interrupt(control-c)
    try:
        while True:
            motor_test_loop(motor)
    except KeyboardInterrupt:
        print("Stopping motor")
    finally:
        motor.cleanup_motor_controller()

if __name__ == "__main__":
    main()