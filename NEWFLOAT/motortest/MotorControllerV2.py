from machine import Pin, PWM
import time

class MotorController:
    def __init__(self, pwm_pin: int, ina_pin: int, inb_pin: int):
        self.pwm = PWM(Pin(pwm_pin))
        self.ina = Pin(ina_pin, Pin.OUT)
        self.inb = Pin(inb_pin, Pin.OUT)

        # Start with motor stopped
        self.pwm.duty_u16(0)
        self.ina.value(0)
        self.inb.value(0)

    # Change motor direction
    # CW  -> INA HIGH, INB LOW
    # CCW -> INA LOW, INB HIGH
    # Anything else stops the motor
    def update_direction(self, direction):
        if direction == "CW":
            self.ina.value(1)
            self.inb.value(0)
        elif direction == "CCW":
            self.ina.value(0)
            self.inb.value(1)
        else:
            self.ina.value(0)
            self.inb.value(0)

    def update_speed(self, speed):
        self.pwm.duty_u16(speed)

    def stop(self):
        self.update_direction("NONE")
        self.pwm.duty_u16(0)
