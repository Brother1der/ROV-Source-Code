#sending end!!!

from machine import Pin, I2C
import time
import ssd1306
from sx1262 import SX1262
import time

vext = Pin(36, Pin.OUT)
vext.value(0)

time.sleep_ms(100)

rst = Pin(21, Pin.OUT)
rst.value(0)
time.sleep_ms(50)
rst.value(1)
time.sleep_ms(100)

i2c = I2C(
    0,
    scl=Pin(18),
    sda=Pin(17),
    freq=100000
)

oled = ssd1306.SSD1306_I2C(
    64,
    32,
    i2c,
    addr=0x3C
)

oled.fill(0)
oled.text("LORA RX", 0, 0)
oled.text("923 MHz", 0, 12)
oled.show()

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

msg = b"Hello World!"

print("Sending:", msg)
oled.fill(0)
oled.text("LORA RX", 0, 0)
oled.text("Sending", msg, 0, 12)
oled.show()

err = sx.send(msg)

print("Send status:", SX1262.STATUS[err])
    