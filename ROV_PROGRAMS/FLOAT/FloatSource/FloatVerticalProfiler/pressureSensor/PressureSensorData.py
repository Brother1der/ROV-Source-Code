### Last Modified 12/9/2025 by Conner O'Reilly
# Built by Conner O'Reilly
# Purpose: This program is designed to poll data from both the temperature and pressure sensor
# Requirements: Device with full python support 
###

#Importing the sensor and the sensor reader tool
from FloatSource.FloatVerticalProfiler.pressureSensor.PressureSensor import PressureSensor
from FloatSource.FloatVerticalProfiler.pressureSensor.SensorReader import SensorPoller


class PressureSensorData:
    POLLING_TIME = 0.1   # 10 Hz — matches control loop rate; lower dt → less velocity noise
    def __init__(self, density: float):
        """
        Initialize the depth/temperature sensor manager and start polling threads.

        This constructor creates a pressure sensor object, configures the fluid 
        density for accurate depth calculations, and initializes two SensorPoller 
        instances to continuously collect depth and temperature data at the 
        defined polling interval. Polling threads are started automatically.

        Args:
            density (float): The density of the fluid in kg/m³ used for converting 
                         pressure readings to depth.

        Raises:
            Exception: If sensor initialization or polling setup fails.
        """
        #Creating pressure sensor and setting density
        self.pressureSensor = PressureSensor()
        self.pressureSensor.set_fluid_density(density)

        #Starting data collection
        self.depthData = SensorPoller(self.pressureSensor.get_depth, self.POLLING_TIME)
        self.temperatureData = SensorPoller(self.pressureSensor.get_temperature, self.POLLING_TIME)
        self.depthData.start()
        self.temperatureData.start()

    # -------------------------
    # DEPTH GETTERS
    # -------------------------
    def get_latest_depth(self):
        """
        Reads the current depth from the sensor.
        Returns:
            tuple: (timestamp, depth in meters)
        """
        return self.depthData.get_latest()

    def get_recent_depth(self):
        """
        Reads the most recent depths at the full 20hz resolution. Max length of 5 seconds.
        Returns:
            deque: 500 indexes of (timestamp, depth in meters)
        """
        return self.depthData.get_recent()

    def get_all_depth(self):
        """
        Reads all depths at a limited 1/5hz resolution
        Returns:
            list: All depth data points, (timestamp, depth in meters)
        """
        return self.depthData.get_all()
    
    # -------------------------
    # TEMPERATURE GETTERS
    # -------------------------
    def get_latest_temperature(self):
        """
        Reads the most recent temperature data point
        Returns:
            tuple: (timestamp, temperature)
        """
        return self.temperatureData.get_latest()

    def get_recent_temperatures(self):
        """
        Reads the most recent temperatures at the full 20hz resolution. Max length of 5 seconds.
        Returns:
            deque: 500 indexes of (timestamp, temperature)
        """
        return self.temperatureData.get_recent()

    def get_all_temperatures(self):
        """
        Reads all temperatures at a limited 1/5hz resolution
        Returns:
            list: All temperature data points, (timestamp, temperature)
        """
        return self.temperatureData.get_all()

    def package_data(self):
        """
        Packages all low resolution data to be shipped to the surface computer
        Returns:
            list: All temperature and depth data points
        """
        depth_readings = self.get_all_depth()
        temperature_readings = self.get_all_temperatures()
        data_package = [depth_readings, temperature_readings]
        return data_package
        

    #Ends data collection
    def stop_data_collection(self):
        """
        Stop all active sensor polling threads.

        This method halts the background SensorPoller threads responsible for 
        collecting pressure/depth and temperature data. It should be called during 
        shutdown, cleanup, or before reinitializing sensors to ensure all polling 
        loops terminate safely.
        """
        self.depthData.stop()
        self.temperatureData.stop()
    
