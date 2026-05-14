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

# Configure RFM9x
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
rfm9x = adafruit_rfm9x.RFM9x(spi,CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

def send_data(filename):
    #Split file into 252-byte chunks and send over RFM9x
    with open(filename, "rb") as f:
        splits = []
        while True:
            chunk = f.read(252)
            if not chunk:
                break
            splits.append(chunk)
    
    for i, split_data in enumerate(splits):
        while True:
            print(f"Sending split {i+1}/{len(splits)}")
            rfm9x.send(split_data)
            rfm9x.send(b"ACK") # Send ACK to receiver to indicate that the split has been sent

            ack_received = False
            for _ in range(50):
                packet = rfm9x.receive(timeout=0.1)
                if packet == b"ACK":
                    ack_received = True
                    break

            if ack_received:
                print(f"Split {i+1} acknowledged")
                break

            print(f"Split {i+1} no ACK, retrying")
            time.sleep(0.5)
