### Last Modified 3/1/2026
# Built by Conner O'Reilly
# Purpose: Estimate float velocity from pressure sensor depth data.
# Method: 2-state constant-velocity Kalman filter
#   State: [depth, velocity]  Measurement: noisy depth reading
#   Benchmarked against EMA, windowed-mean, linreg, SGolay, median+linreg.
#   Kalman wins all noise scenarios (σ=2.5–20 mm) with zero lag.
###
from FloatVerticalProfiler.pressureSensor.PressureSensorData import PressureSensorData


class VelocityCalculator:
    """
    2-state Kalman filter for float velocity estimation.

    Kalman Filter Overview:
    - State vector: [depth, velocity] — position and rate-of-change
    - Measurement: noisy depth readings from pressure sensor (±2cm at 2-sigma)
    - Prediction: assume constant velocity (no acceleration) between measurements
    - Update: fuse sensor reading with prediction, trust proportional to noise levels

    Why Kalman instead of EMA/windowed mean?
    - EMA: lags sensor data by several samples; trades lag for noise reduction
    - Windowed mean: needs many samples (1-2 seconds); still has lag
    - Linreg/SGolay: polynomial fitting adds lag, doesn't adapt to sudden changes
    - Kalman: optimal linear filter for this problem; zero-sample lag, fast adaptation

    Kalman Filter Mechanics:
    1. PREDICT: assume velocity constant between measurements
       x_pred = F @ x  where F = [[1, dt], [0, 1]]
       P_pred = F @ P @ F.T + Q  (covariance expands due to uncertainty)

    2. UPDATE: fuse new sensor measurement (depth only)
       K = P @ H.T / (H @ P @ H.T + R)  (Kalman gain — how much to trust sensor)
       x = x_pred + K * (z - H @ x_pred)  (blend prediction with measurement)
       P = (I - K @ H) @ P_pred  (covariance shrinks as we learn)

    Tuning:
    - r_meas: sensor noise variance. Smaller → trust sensor more → less filtering
    - q_vel: process noise variance. Larger → allow velocity changes faster
    """
    def __init__(self, sensor_data: PressureSensorData):
        self.sensorData = sensor_data

        # ─── Kalman Filter Tuning (benchmark-optimised for float control) ───
        # r_meas = 0.0001 m² is σ² = (0.01m)² — the sensor worst-case noise floor
        #   Pressure sensor (MS5837) reads ±2mbar at 2-sigma confidence
        #   At freshwater: 1 mbar = 0.010224 m depth → ±2 mbar ≈ ±0.0204 m ≈ ±2 cm
        #   We use (0.01 m)² to set a half-width noise envelope
        self._r_meas = 0.0001

        # q_vel = 5e-4 m²/s — process noise on velocity per second
        #   Allows float to accelerate/decelerate when needed
        #   At max thrust (0.5 m/s²): expected accel variance = 0.25 m²/s²
        #   Scaling per second allows the filter to adapt dynamically
        self._q_vel  = 5e-4

        # ─── Filter State (initialised on first measurement) ───
        self._x = None          # state = [depth (m), velocity (m/s)] — positive vel = sinking
        self._P = [[1.0, 0.0],  # covariance matrix P = [[σ_depth², cov],
                   [0.0, 1.0]]  #                        [cov, σ_vel²]]
        self._last_time = None  # timestamp of last update (for dt calculation)

    def update_velocity(self) -> float:
        """
        Run one Kalman predict+update step using the latest depth reading.
        Returns the filtered velocity estimate (m/s, positive = sinking).

        Kalman Filter Cycle (standard EKF structure):
        1. Read latest sensor measurement (depth from pressure sensor)
        2. Predict next state assuming constant velocity:
           depth_pred = depth + velocity * dt
           velocity_pred = velocity  (unchanged)
           Also predict covariance growth (uncertainty increases due to process noise)
        3. Update: fuse measurement with prediction
           Kalman gain K = how much to trust the sensor vs prediction
           state = prediction + K * (measurement - predicted_measurement)
           covariance = (I - K*H) @ covariance_pred
        """
        samples = list(self.sensorData.get_recent_depth())
        if len(samples) < 1:
            return 0.0

        t_curr, d_curr = samples[-1]  # latest (timestamp, depth) pair

        # ─── Bootstrap on first call ───
        # Initialize the filter state with first measurement
        # Assume float is stationary at first reading (velocity = 0)
        if self._x is None:
            self._x = [d_curr, 0.0]
            self._last_time = t_curr
            return 0.0

        dt = t_curr - self._last_time
        if dt <= 1e-6:
            return self._x[1]  # no new data — return last estimate (prevents division by zero)
        self._last_time = t_curr

        # ════════════════════════════════════════════════════════════════════════
        # PREDICT PHASE: Assume constant velocity model F = [[1, dt], [0, 1]]
        # ════════════════════════════════════════════════════════════════════════
        # x_pred = F @ x = [[1, dt], [0, 1]] @ [depth, vel]
        x0_p = self._x[0] + self._x[1] * dt  # depth_pred = depth + velocity * dt
        x1_p = self._x[1]                     # velocity_pred = velocity (constant)

        # P_pred = F @ P @ F.T + Q
        # Expands covariance along the velocity direction (more uncertainty over time)
        P = self._P
        q_v = self._q_vel * dt  # scale process noise by timestep
        # Covariance matrix multiplication (manual 2x2):
        P00 = P[0][0] + dt * (P[1][0] + P[0][1]) + dt * dt * P[1][1]  # depth variance grows
        P01 = P[0][1] + dt * P[1][1]                                   # depth-velocity coupling
        P10 = P[1][0] + dt * P[1][1]                                   # velocity-depth coupling
        P11 = P[1][1] + q_v                                            # velocity variance grows

        # ════════════════════════════════════════════════════════════════════════
        # UPDATE PHASE: Fuse measurement with prediction using H = [1, 0]
        # Only depth is measured; velocity is inferred from depth changes
        # ════════════════════════════════════════════════════════════════════════
        # Innovation covariance: S = H @ P @ H.T + R = P00 + r_meas
        # This tells us expected measurement uncertainty (prediction error + sensor noise)
        S = P00 + self._r_meas

        # Kalman gain: K = P @ H.T @ S^-1
        # K[0] = P00 / S — how much to trust sensor for depth correction
        # K[1] = P10 / S — how much to adjust velocity based on depth measurement error
        K0 = P00 / S   # depth gain (typically 0.5–0.99, depends on noise)
        K1 = P10 / S   # velocity gain (typically 0.01–0.5)

        # Innovation (measurement residual):
        innov = d_curr - x0_p  # how far off was our prediction?
        # Update state: blend prediction with measurement
        self._x = [x0_p + K0 * innov,      # corrected depth
                   x1_p + K1 * innov]      # corrected velocity (inferred from depth error)

        # Update covariance: P = (I - K*H) @ P_pred = P_pred - K @ P_pred
        # Covariance shrinks after measurement (we know more now)
        self._P = [[P00 - K0 * P00,  P01 - K0 * P01],
                   [P10 - K1 * P00,  P11 - K1 * P01]]

        return self._x[1]  # return estimated velocity
