### Last Modified 2/24/2026
# Built by Conner O'Reilly
# Purpose: Calculate the acceleration of the float using pressure sensor depth data.
#          Applies a two-pass finite-difference method: first derives instantaneous
#          velocities from depth samples, then differentiates those to get acceleration.
# Requirements: Device with full python support. Pressure sensor float build.
###
from FloatVerticalProfiler.pressureSensor.PressureSensorData import PressureSensorData


class AccelerationCalculator:

    def __init__(self, sensor_data: PressureSensorData):
        """
        Initialize the AccelerationCalculator with a PressureSensorData instance.

        Args:
            sensor_data (PressureSensorData): Sensor data object providing access
                                              to buffered depth measurements.
        """
        self.sensorData = sensor_data

    def update_acceleration(self, seconds: float) -> float:
        """
        Compute the average acceleration over the last `seconds` seconds
        from the sensor's recent depth buffer.

        Uses a two-pass finite-difference method:
          Pass 1 — velocity:     v_i = (d_i - d_{i-1}) / dt_i
          Pass 2 — acceleration: a_i = (v_i - v_{i-1}) / dt_i

        Args:
            seconds (float): Time window in seconds over which to calculate
                             acceleration. Shorter windows (0.5 s) track fast
                             changes; longer windows smooth noise.

        Returns:
            float: Average acceleration in m/s². Positive = sinking faster /
                   rising slower. Returns 0.0 if fewer than 3 samples available.
        """
        samples = list(self.sensorData.get_recent_depth())

        # Trim to requested window
        target_iterations = int(seconds / self.sensorData.POLLING_TIME)
        if target_iterations <= len(samples):
            samples = samples[-target_iterations:]

        if len(samples) < 3:
            return 0.0

        # Pass 1: instantaneous velocities
        velocities = []
        for i in range(1, len(samples)):
            t_prev, d_prev = samples[i - 1]
            t_curr, d_curr = samples[i]
            dt = t_curr - t_prev
            velocities.append(
                (t_curr, (d_curr - d_prev) / dt if dt >= 1e-9 else 0.0)
            )

        # Pass 2: accelerations from consecutive velocity pairs
        accelerations = []
        for i in range(1, len(velocities)):
            t_prev, v_prev = velocities[i - 1]
            t_curr, v_curr = velocities[i]
            dt = t_curr - t_prev
            accelerations.append(
                (v_curr - v_prev) / dt if dt >= 1e-9 else 0.0
            )

        return sum(accelerations) / len(accelerations)
