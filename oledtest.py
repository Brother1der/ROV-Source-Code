from machine import Pin, I2C
import time
import ssd1306

# Turn OLED power ON
vext = Pin(36, Pin.OUT)
vext.value(0)

time.sleep_ms(100)

# Reset OLED
rst = Pin(21, Pin.OUT)
rst.value(0)
time.sleep_ms(50)
rst.value(1)
time.sleep_ms(100)

# OLED I2C
i2c = I2C(
    0,
    scl=Pin(18),
    sda=Pin(17),
    freq=100000
)

# 64x32 OLED at 0x3C
oled = ssd1306.SSD1306_I2C(
    64,
    32,
    i2c,
    addr=0x3C
)

oled.fill(0)
oled.text("HELLO!", 0, 0)
oled.text("HELTEC", 0, 12)
oled.text("V3", 0, 24)
oled.show()