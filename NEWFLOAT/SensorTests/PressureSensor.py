"""
basically i think that this doesnt need more than one file so i combined it and fixed imports for stick
"""

import ms5837
import threading
import time
from collections import deque

# provides usable data from the ms5837 pressure sensor via I2C
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

# read the sensor data at a given polling rate with adjustments for compute time
class SensorPoller:
    """
    A class to poll sensor data asynchronously in a background thread at a fixed interval.

    Features:
    - Continuously reads a sensor using a provided read function.
    - Stores a small recent sample buffer for immediate calculations.
    - Stores a downsampled long-term sample list for logging/graphing.
    """
        
    MAX_ALL_SAMPLES = 200  # Cap for downsampled long-term storage (~15 minutes at 1 sample/5s)

    def __init__(self, read_fn, interval=0.1):
        """
        Initialize the SensorPoller.

        Args:
            read_fn (function): A callable that returns the sensor reading.
            interval (float): Time between readings in seconds (default 0.1s → 10Hz).
        """
        self.read_fn = read_fn                # Function to call to get sensor value
        self.interval = interval              # Desired time between readings
        self.running = False                  # Flag to control the polling loop
        self.latest_value = None              # Most recent sensor reading
        self.recent_samples = deque(maxlen=500)  # Rolling window of recent readings (small table)
        self.all_samples = deque(maxlen=self.MAX_ALL_SAMPLES)  # Downsampled long-term readings (large table)
        self.thread = None                    # Creating the thread to be used later
        self._lock = threading.Lock()         # Lock to protect shared data

    def start(self):
        """
        Start polling the sensor in a separate daemon thread.
        """
        self.running = True
        # Create a background thread that runs the _loop method
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()  # Start the thread

    def stop(self):
        """
        Stop polling the sensor and wait for the thread to finish cleanly.
        """
        self.running = False  # Signal the loop to stop
        if self.thread is not None:
            self.thread.join()  # Wait until the thread has fully stopped

    def get_latest(self):
        """Return the most recent sensor reading, thread-safe."""
        with self._lock:
            return self.latest_value

    def get_recent(self):
        """Return a list copy of recent samples, thread-safe."""
        with self._lock:
            return list(self.recent_samples)

    def get_all(self):
        """Return a list copy of all downsampled samples, thread-safe."""
        with self._lock:
            return list(self.all_samples)

    def _loop(self):
        """
        Internal method run in a background thread.
        Polls the sensor at a fixed interval and stores readings.
        """
        add_data_to_list = 0 # Counter used to downsample for long-term storage
        #Main polling loop
        while self.running:
            # Record start time of this loop iteration
            loop_start = time.time() 
            try:
                # Read the sensor using the provided function and get time
                value = self.read_fn()
                timestamp = time.time()
                #Format data into tuple
                sample = (timestamp, value)
                with self._lock:
                    self.latest_value = sample
                    #Update the full resolution table
                    self.recent_samples.append(sample)
                    #Check to see if updating the long term table is necessary
                    add_data_to_list += 1
                    if add_data_to_list >= 100:
                        self.all_samples.append(sample)
                        add_data_to_list = 0
            except Exception as e:
                print("Sensor error:", e)
            #Handling polling rate
            cur_time = time.time() #Current time
            time_delta = cur_time - loop_start #Processing time for reading data and storing
            remaining_time = self.interval - time_delta #Remaining time in wait loop
            #Waiting the remaining time if needed
            if remaining_time > 0:
                time.sleep(remaining_time)
            
