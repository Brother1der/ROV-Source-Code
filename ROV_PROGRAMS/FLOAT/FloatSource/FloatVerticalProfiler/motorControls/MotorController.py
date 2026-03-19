### Last Modified 12/9/2025 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: This program is designed to operated as the controller for the polou VNH-5019 motor controller. 
# Alongside the Float 2.3.0 PCB 
# Requirements: Device with full python support, PWM outputs and GPIO Control
# ###

#Raspberry pi GPIO to handle the ability to update the output pins
import RPi.GPIO as GPIO

#Motor controller object
class MotorController:
    #Creating the motor controller object.
    def __init__(self,pwm_pin: int,ina_pin: int,inb_pin: int,pwm_freq: int):
        #Store Pin assignments
        self.pwm_pin = pwm_pin
        self.ina_pin = ina_pin
        self.inb_pin = inb_pin

        # Setup GPIO pins and configure GPIO Mode32
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pwm_pin, GPIO.OUT)
        GPIO.setup(ina_pin, GPIO.OUT)
        GPIO.setup(inb_pin, GPIO.OUT)

        #Configuring PWM
        self.pwm = GPIO.PWM(pwm_pin, pwm_freq)
        self.pwm.start(0)

    # Change motor direction:
    # CW  -> INA HIGH,  INB LOW
    # CCW -> INA LOW,   INB HIGH
    # Any other value stops the motor outputs
    def update_direction(self, direction):
        if direction == "CW":
            GPIO.output(self.ina_pin, GPIO.HIGH)
            GPIO.output(self.inb_pin, GPIO.LOW)
        elif direction == "CCW":
            GPIO.output(self.inb_pin, GPIO.HIGH)
            GPIO.output(self.ina_pin, GPIO.LOW)
        else:
            GPIO.output(self.inb_pin, GPIO.LOW)
            GPIO.output(self.ina_pin, GPIO.LOW)

    #Emergency stop that will stop motor and set speed to 0.
    def stop(self):
        self.update_direction("NONE")
        self.pwm.ChangeDutyCycle(0)
        GPIO.output(self.inb_pin, GPIO.LOW)
        GPIO.output(self.ina_pin, GPIO.LOW)

    #Setting the speed of the motor using pwm
    def set_speed(self, speed):
        self.pwm.ChangeDutyCycle(speed)
        
    #Close the pwm object being used
    def cleanup_motor_controller(self):
        self.pwm.stop()
        GPIO.cleanup()