import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import RFM9x
import adafruit_rfm9x

filename = "float_data.txt"

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