### Last Modified 12/9/2025 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: This program is designed to read the sensor data at a given polling rate with adjustments for compute time
# Requirements: Device with full python support 
###
# Import modules for threading, time measurement, and efficient sample storage
import threading
import time
from collections import deque

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
            
