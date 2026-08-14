#reciever end!!!

from machine import Pin, I2C
import time
import ssd1306
from sx1262 import SX1262


# Turn OLED on
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

# =========================
# SX1262 SETUP
# =========================

sx = SX1262(
    spi_bus=1,
    clk=9,
    mosi=10,
    miso=11,
    cs=8,
    irq=14,
    rst=12,
    gpio=13
)

sx.begin(
    freq=923,
    bw=500.0,
    sf=12,
    cr=8,
    syncWord=0x12,
    power=-5,
    currentLimit=60.0,
    preambleLength=8,
    implicit=False,
    implicitLen=0xFF,
    crcOn=True,
    txIq=False,
    rxIq=False,
    tcxoVoltage=1.7,
    useRegulatorLDO=False,
    blocking=True
)

# =========================
# STARTUP SCREEN
# =========================

oled.fill(0)
oled.text("LORA RX", 0, 0)
oled.text("923 MHz", 0, 12)
oled.text("WAITING...", 0, 24)
oled.show()

# =========================
# RECEIVE LOOP
# =========================

while True:

    msg, err = sx.recv()

    if len(msg) > 0:

        # Convert received bytes into text
        try:
            text = msg.decode("utf-8")
        except:
            text = str(msg)

        # Get radio status
        status = SX1262.STATUS[err]

        # Print to serial terminal too
        print("Received:", msg)
        print("Status:", status)

        # =========================
        # DISPLAY ON OLED
        # =========================

        oled.fill(0)

        oled.text("RECEIVED:", 0, 0)

        # Display first 10 characters
        oled.text(text[:10], 0, 8)

        # More of the message
        oled.text(text[10:20], 0, 16)

        # Status
        oled.text(status[:10], 0, 24)

        oled.show()