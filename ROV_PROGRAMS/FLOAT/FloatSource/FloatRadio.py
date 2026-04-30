import os
import sys
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm9x

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

from FloatVerticalProfiler.FloatVerticalProfiler import FloatVerticalProfiler
from FloatRadio import send_float_data

START_SIGNAL = b"start"
ACK_SIGNAL = b"ACK"
RECEIVE_TIMEOUT = 0.5
WAIT_POLL_SECONDS = 0.2


def wait_for_signal() -> None:
    print("Waiting for start signal...")
    while True:
        packet = rfm9x.receive(timeout=RECEIVE_TIMEOUT)
        if packet is None:
            print(".", end="", flush=True)
            time.sleep(WAIT_POLL_SECONDS)
            continue

        print(f"\nReceived packet: {packet!r}")
        if packet == START_SIGNAL:
            print("Start signal received.")
            rfm9x.send(ACK_SIGNAL)
            print("ACK sent.")
            return

        print("Unexpected packet received, ignoring.")


def main() -> None:
    wait_for_signal()
    profiler = FloatVerticalProfiler()

    try:
        profiler.perform_profiles()
    except Exception as exc:
        print(f"Error running profile: {exc!r}")

if __name__ == "__main__":
    main()
