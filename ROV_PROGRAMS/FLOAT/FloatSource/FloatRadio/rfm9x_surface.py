#Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
#Last modified: 6/11/2024
#Purpose: Receive 252 byte packet(s) and combine them into one then save to a file. I need to ask conner about the frontend's work with this. 
#Requirements: 2 RPis with RFM9x LoRa modules, one running this code to send the data, and the other running the receiver code to receive the data and save it to a file.

import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm9x
import time

filename = "received_float_data.txt"

CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
rfm9x = adafruit_rfm9x.RFM9x(CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

print("Waiting for packets...")

received_data = bytearray()
last_receive_time = time.time()

while True:
    packet = rfm9x.receive(timeout=0.5)

    if packet is not None:
        print(f"Received packet ({len(packet)} bytes)")

        # Append packet data
        received_data.extend(packet)

        # Send ACK back
        rfm9x.send(b"ACK")
        print("ACK sent")

        # Reset timeout timer
        last_receive_time = time.time()

with open(filename, "wb") as f:
    f.write(received_data)

print(f"File saved as {filename}")
print(f"Total bytes received: {len(received_data)}")