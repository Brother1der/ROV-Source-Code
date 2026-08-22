from sx1262 import SX1262
import time

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

    err = sx.send(msg)

    print("Send status:", SX1262.STATUS[err])
