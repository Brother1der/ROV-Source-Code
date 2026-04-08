#Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
#Last modified: 6/11/2024
#Purpose: Split the float data into 252 byte chunks and send them over RFM9x
#Requirements: 2 RPis with RFM9x LoRa modules, one running this code to send the data, and the other running the receiver code to receive the data and save it to a file.

import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm9x
import time

filename = "float_data.txt"

# Configure RFM9x
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
rfm9x = adafruit_rfm9x.RFM9x(CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

def split_packet(filename): #split the file into 252 byte chunks for rfm9x
    splits = []
    with open(filename, "rb") as f:
        while True:
            chunk = f.read(252)
            if not chunk:
                break
            splits.append(chunk)
    return splits


splits = split_packet(filename)

for i, split_data in enumerate(splits):
    print(f"Sending split {i+1}/{len(splits)}")

    rfm9x.send(split_data)

    # Wait for ACK (simple)
    ack_received = False
    timeout = 0

    while not ack_received and timeout < 50:
        packet = rfm9x.receive(timeout=0.1)

        if packet == b"ACK":  # stricter check
            print(f"Split {i+1} acknowledged")
            ack_received = True

        timeout += 1

    if not ack_received:
        print(f"Split {i+1} failed (no ACK)")
        # optional retry
        rfm9x.send(split_data)
        time.sleep(0.1)