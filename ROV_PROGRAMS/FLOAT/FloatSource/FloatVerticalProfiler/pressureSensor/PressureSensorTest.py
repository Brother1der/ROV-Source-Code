### Last Modified 12/8/2025 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: This program is designed to test the pressure sensors ability to read depth and temperature
# Requirements: Device with full python support 
###

# Import the pressureSensorData class, which handles asynchronous polling of pressure and temperature
from FloatVerticalProfiler.pressureSensor.PressureSensorData import PressureSensorData
import time  # Import time module for delays and timestamps

# Set the fluid density used for depth calculations (kg/m^3)
DENSITY = 1000  # Typical density for freshwater

def main():
    """
    Main function to test the pressure sensor data class.
    Continuously prints current depth and temperature.
    """
    
    # Create an instance of pressureSensorData
    # This will start the asynchronous polling of depth and temperature
    sensor_data = PressureSensorData(DENSITY)

    # Infinite loop to repeatedly read and print sensor values
    while True: 
        # Get the most recent depth reading from the sensorData object
        # get_latest_depth() returns a (timestamp, value) tuple
        print("Current depth: " + str(sensor_data.get_latest_depth()))
        
        # Get the most recent temperature reading
        # Note: You need to call this on the instance, not the class itself
        print("Current temperature: " + str(sensor_data.get_latest_temperature()))
        
        # Wait for 1 second before reading again
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Test stopped")
