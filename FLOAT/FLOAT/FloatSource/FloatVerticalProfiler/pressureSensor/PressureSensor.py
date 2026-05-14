### Last Modifed 12/9/2025 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: This program is designed to provide usable data from the ms5837 pressure sensor via I2C
# Requirements: Device with full python support smbus2 library
###
# Import the MS5837 sensor driver from the provided library
from FloatVerticalProfiler.pressureSensor.pressureSensorDrivers import ms5837
import threading
import time


# Define a class to interface with the MS5837 pressure sensor
class PressureSensor:
    def __init__(self):
        """
        Initialize the MS5837 pressure sensor interface.

        This constructor creates an MS5837-30BA sensor object, attempts to 
        initialize communication with the sensor, and performs an initial read 
        to verify that the sensor is operational. If either initialization or 
        the first read attempt fails, the program will print an error message 
        and exit.

        Raises:
            SystemExit: If the sensor cannot be initialized or does not return
                    valid data during the initial read.
        """
        # Create a sensor object for the MS5837-02BA variant (Bar02)
        self.sensor = ms5837.MS5837_02BA()

        # Retry init() + first read() until both succeed. Transient I2C errors
        # (loose connector, bus contention at startup) are common; one failed
        # boot shouldn't kill the float. Rebuild the sensor object each round
        # so a failed SMBus open also gets retried.
        attempt = 0
        retry_delay = 1.0
        while True:
            attempt += 1
            try:
                if self.sensor.init() and self.sensor.read():
                    break
                print(f"Sensor init/read failed on attempt {attempt}, retrying in {retry_delay:g}s...")
            except Exception as exc:
                print(f"Sensor init attempt {attempt} raised {exc!r}, retrying in {retry_delay:g}s...")
            time.sleep(retry_delay)
            self.sensor = ms5837.MS5837_02BA()
        print(f"Sensor ready (attempt {attempt}).")

        # Lock to serialize I2C access from multiple polling threads
        self._lock = threading.Lock()

    def set_fluid_density(self, density):
        """
        Sets the fluid density used by the sensor for depth calculations.
        Default is 1000 kg/m^3 (approximate density of freshwater).
        """
        self.sensor.setFluidDensity(density)# kg/m^3
    
    def get_pressure(self):
        """
        Reads the current pressure from the sensor.
        Returns:
            float: Pressure in millibar (or sensor-specific units)
        """
        with self._lock:
            self.sensor.read(ms5837.OSR_8192)
            return self.sensor.pressure()

    def get_depth(self):
        """
        Reads the current depth from the sensor based on fluid density.
        Triggers a full I2C read (D1 + D2) at OSR_8192 (~20.5 ms).
        At 10 Hz polling this leaves ~80 ms of margin per interval.
        Temperature is updated as a side effect — call get_temperature()
        after this to get the matched reading with no extra I2C traffic.
        Returns:
            float: Depth in meters (calculated from pressure)
        """
        with self._lock:
            self.sensor.read(ms5837.OSR_8192)
            return self.sensor.depth()

    def get_temperature(self):
        """
        Returns the temperature from the most recent get_depth() read.
        Does NOT trigger a new I2C transaction — avoids double-read
        contention when depth and temperature pollers run concurrently.
        Returns:
            float: Temperature in degrees Celsius
        """
        with self._lock:
            return self.sensor.temperature()