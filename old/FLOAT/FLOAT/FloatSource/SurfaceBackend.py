#Last Modified: 4/21/2026
#Purpose: Backend(?) for the float's website, sends signals between float and home and then recieves the 252 byte packets and saves them

#script imports
from FloatVerticalProfiler import FloatVerticalProfiler

#normal imports
from typing import Optional, Callable
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
rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0) #configures the board along with the frequency
rfm9x.tx_power = 23
prev_packet = None

def start_vertical_profiler():
    """Send start signal to float and wait for acknowledgment"""
    rfm9x.send(b"start")
    print("Sent start signal")

    ack_received = False
    timeout = 0

    while not ack_received and timeout < 50:
        packet = rfm9x.receive(timeout=0.1)
        if packet == b"ACK":
            print("Start signal acknowledged")
            ack_received = True
        timeout += 1

    if not ack_received:
        print("Failed to receive ACK for start signal")
        return False

    return True

def receive_float_data(filename="received_float_data.txt", timeout_duration=30.0, on_first_packet: Optional[Callable[[], None]] = None):
    """
    Receive float data packets sent by send_float_data.py and save to file.
    Based on recieve_float_data.py functionality.
    Waits indefinitely for the first packet, then applies a 30-second timeout for subsequent packets.
    """
    print("Waiting for float data packets...")

    received_data = bytearray()
    last_receive_time = None
    first_packet_received = False

    while True:
        # Wait indefinitely for first packet, then use timeout for subsequent packets
        if first_packet_received:
            packet = rfm9x.receive(timeout=0.5)
        else:
            packet = rfm9x.receive(timeout=None)

        if packet is not None:
            print(f"Received packet ({len(packet)} bytes)")

            # Check if this is an ACK signal from sender (indicating end of transmission)
            if packet == b"ACK":
                print("Received end-of-transmission signal")
                break

            # Mark first packet as received
            if not first_packet_received:
                first_packet_received = True
                last_receive_time = time.time()
                print("First data packet received, starting 30-second timeout for subsequent packets")
                if on_first_packet is not None:
                    on_first_packet()

            # Append packet data
            received_data.extend(packet)

            # Send ACK back to sender
            rfm9x.send(b"ACK")
            print("ACK sent")

            # Reset timeout timer
            last_receive_time = time.time()

        # Break if no packets received for timeout_duration after first packet
        if first_packet_received and time.time() - last_receive_time > timeout_duration:
            print(f"Timeout: No data received for {timeout_duration} seconds")
            break

    # Save received data to file
    with open(filename, "wb") as f:
        f.write(received_data)

    print(f"File saved as {filename}")
    print(f"Total bytes received: {len(received_data)}")
    return filename

def main():
    """Main function to demonstrate the surface backend functionality"""
    print("Surface Backend Starting...")

    # Start the vertical profiler on the float
    if start_vertical_profiler():
        print("Float started successfully. Waiting for data...")

        # Receive the float data
        receive_float_data()

        print("Data reception complete.")
    else:
        main()

if __name__ == "__main__":
    main()
