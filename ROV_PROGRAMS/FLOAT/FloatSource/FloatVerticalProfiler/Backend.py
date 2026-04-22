#Last Modified: 4/21/2026
#Purpose: Backend for the float's website, sends signals between float and home.

#script imports
from FloatSource.FloatVerticalProfiler.FloatVerticalProfiler import FloatVerticalProfiler

#normal imports
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_ssd1306
import adafruit_rfm9x
import time

# Configure RFM9x
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
rfm9x = adafruit_rfm9x.RFM9x(CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

def start_vertical_profiler(self):
    rfm9x.send(b"start")
    print ("sent start signal")
    
    ack_received = False
    timeout = 0
    
    while not ack_received and timeout < 50:
        packet = rfm9x.receive(timeout=0.1)
        if packet == b"ACK":
            print("acknowledged")
            ack_received = True
        timeout += 1
    
    if not ack_received:
        print(f"Split {i+1} failed (no ACK)")
        rfm9x.send(b"start")
        time.sleep(0.1)