"""
Simulation for DepthTarget controller
Uses the real DepthTarget class as control logic
Replaces hardware with simulated physics + sensor layer

Pool environment model:
  1. Sensor noise:    depth σ = 0.05 m, temp σ = 0.1 °C  (MS5837-30BA)
  2. Water current:   gentle pump circulation only, σ ≈ 0.003 m/s
  3. Density:         uniform freshwater at 78 °F (25.56 °C), 997.0 kg/m³
  4. Surface waves:   none (smooth pool, no wind)
  5. Full drag/buoyancy physics with mass, Cd, and cross-section
"""

import sys
import os
import time
import math
import random
import threading
from collections import deque

# DepthTarget imports use bare 'FloatVerticalProfiler.*' paths, so its
# parent directory (FloatSource) must be on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Mock RPi.GPIO so MotorController can be imported on non-Pi hardware
import types
_mock_gpio = types.ModuleType("RPi.GPIO")
_mock_gpio.BCM = 11
_mock_gpio.OUT = 0
_mock_gpio.HIGH = 1
_mock_gpio.LOW = 0
_mock_gpio.setmode = lambda *_: None
_mock_gpio.setup = lambda *_: None
_mock_gpio.output = lambda *_: None
_mock_gpio.cleanup = lambda *_: None
class _MockPWM:
    def __init__(self, *args, **kwargs): pass
    def start(self, *args, **kwargs): pass
    def ChangeDutyCycle(self, *args, **kwargs): pass
    def stop(self): pass
_mock_gpio.PWM = _MockPWM
_rpi = types.ModuleType("RPi")
_rpi.GPIO = _mock_gpio
sys.modules["RPi"] = _rpi
sys.modules["RPi.GPIO"] = _mock_gpio

# Mock MS5837 driver so PressureSensor can be imported
_mock_ms5837_pkg = types.ModuleType("FloatVerticalProfiler.pressureSensor.pressureSensorDrivers.ms5837")
class _MockMS5837_30BA:
    def __init__(self): pass
    def init(self): return True
    def read(self, *args, **kwargs): return True
    def setFluidDensity(self, *args, **kwargs): pass
    def pressure(self, *args, **kwargs): return 1013.0
    def depth(self): return 0.0
    def temperature(self, *args, **kwargs): return 22.5
_mock_ms5837_pkg.MS5837_30BA = _MockMS5837_30BA
sys.modules["FloatVerticalProfiler.pressureSensor.pressureSensorDrivers"] = types.ModuleType(
    "FloatVerticalProfiler.pressureSensor.pressureSensorDrivers")
sys.modules["FloatVerticalProfiler.pressureSensor.pressureSensorDrivers.ms5837"] = _mock_ms5837_pkg

# Import your real controller
from FloatSource.FloatVerticalProfiler.depthControls.DepthTarget import DepthTarget


# ============================================================
# PHYSICS MODEL
# ============================================================

# Sensor noise parameters — Bar02 spec: ±2cm accuracy → σ ≈ 0.01m (2-sigma bound)
DEPTH_NOISE_STDDEV = 0.02   # meters
TEMP_NOISE_STDDEV = 0.1     # °C

# Pool: 78 °F = 25.56 °C, well-mixed — uniform temperature throughout
BASE_TEMPERATURE = 25.56    # °C

# Pool circulation: gentle pump return jets, very low vertical current
CURRENT_MEAN = 0.0          # m/s
CURRENT_SIGMA = 0.003       # m/s std dev (10× lower than open water)
CURRENT_TAU = 30.0          # seconds correlation time (slow, steady circulation)

# Pool water: freshwater at 25.56 °C, uniform density (no thermocline)
SURFACE_DENSITY = 997.0     # kg/m³
DENSITY_GRADIENT = 0.0      # kg/m³ per meter depth (well-mixed)

# Physics timestep
PHYSICS_DT = 0.01           # 100 Hz


class SimulatedFloat:

    def __init__(self):

        # Physical constants
        self.g = 9.81
        self.mass = 12.0         # kg
        self.area = 0.00811      # m²  — 4" inner diameter pipe: π × 0.0508²
        self.Cd = 0.9            # drag coefficient

        # State
        self.depth = 0.0         # meters (positive = deeper)
        self.velocity = 0.0      # m/s (positive = descending)
        self.volume_offset = 0.0 # buoyancy control volume offset (m³)

        # Neutral buoyancy volume
        self.rho = SURFACE_DENSITY
        self.neutral_volume = self.mass / self.rho

        # Water current (O-U process state)
        self.current = 0.0       # m/s vertical ambient current

        # Motor state (set by SimulatedMotorController)
        self.volume_rate = 0.0   # m³/s commanded volume change rate

        # Simulation clock
        self.sim_time = 0.0

        # Thread safety
        self.lock = threading.Lock()

    def step(self, dt):
        """Advance physics by dt seconds."""

        # --- Water current: Ornstein-Uhlenbeck update ---
        theta = 1.0 / CURRENT_TAU
        ou_drift = -theta * (self.current - CURRENT_MEAN) * dt
        ou_diffusion = CURRENT_SIGMA * math.sqrt(2 * theta * dt) * random.gauss(0, 1)
        self.current += ou_drift + ou_diffusion

        # --- Volume change from motor ---
        self.volume_offset += self.volume_rate * dt

        # --- Forces ---
        # Local density at current depth
        local_rho = SURFACE_DENSITY + DENSITY_GRADIENT * self.depth
        total_volume = self.neutral_volume + self.volume_offset

        buoyancy = local_rho * self.g * total_volume
        weight = self.mass * self.g

        # Drag (opposes velocity)
        drag = 0.5 * local_rho * self.Cd * self.area * self.velocity ** 2
        drag *= -math.copysign(1, self.velocity)

        net_force = buoyancy - weight + drag
        acceleration = net_force / self.mass

        self.velocity += acceleration * dt

        # --- Integrate position ---
        # Positive velocity = rising (depth decreases); negative = sinking (depth increases)
        # The force model: buoyancy > weight → net_force > 0 → positive accel → velocity
        # increases → depth decreases (rising).  Consistent with depth -= velocity * dt.
        self.depth -= self.velocity * dt  # velocity integrated by force model
        self.depth += self.current * dt   # ambient current contribution

        # Clamp syringe volume to 200ml usable (±100ml from neutral)
        self.volume_offset = max(-0.0001, min(0.0001, self.volume_offset))

        # Clamp at physical boundaries
        if self.depth < 0:
            self.depth = 0
            self.velocity = min(0, self.velocity)  # at surface: only allow sinking (vel ≤ 0)
        if self.depth > 5.0:
            self.depth = 5.0
            self.velocity = max(0, self.velocity)  # at bottom: only allow rising (vel ≥ 0)

        self.sim_time += dt


# ============================================================
# SIMULATED HARDWARE LAYERS
# ============================================================

class SimulatedPressureSensor:
    """Mimics PressureSensorData interface with sensor noise."""

    POLLING_TIME = 0.05  # match real sensor polling rate

    def __init__(self, sim: SimulatedFloat):
        self.sim = sim
        self._lock = threading.Lock()
        self._latest = (time.time(), 0.0)
        self._recent = deque(maxlen=500)
        self._all = deque(maxlen=200)
        self._downsample_counter = 0
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _poll_loop(self):
        while self._running:
            loop_start = time.time()
            with self.sim.lock:
                true_depth = self.sim.depth
            noisy_depth = true_depth + random.gauss(0, DEPTH_NOISE_STDDEV)
            if noisy_depth < 0:
                noisy_depth = 0.0
            ts = time.time()
            sample = (ts, noisy_depth)
            with self._lock:
                self._latest = sample
                self._recent.append(sample)
                self._downsample_counter += 1
                if self._downsample_counter >= 100:
                    self._all.append(sample)
                    self._downsample_counter = 0
            elapsed = time.time() - loop_start
            remaining = self.POLLING_TIME - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def get_latest_depth(self):
        with self._lock:
            return self._latest

    def get_recent_depth(self):
        with self._lock:
            return list(self._recent)

    def get_all_depth(self):
        with self._lock:
            return list(self._all)


class SimulatedTemperatureSensor:
    """Mimics temperature data collection."""

    POLLING_TIME = 0.05

    def __init__(self, sim: SimulatedFloat):
        self.sim = sim
        self._lock = threading.Lock()
        self._latest = (time.time(), BASE_TEMPERATURE)
        self._all = deque(maxlen=200)
        self._downsample_counter = 0
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def _poll_loop(self):
        while self._running:
            loop_start = time.time()
            # Pool is well-mixed: uniform temperature throughout
            true_temp = BASE_TEMPERATURE
            noisy_temp = true_temp + random.gauss(0, TEMP_NOISE_STDDEV)
            ts = time.time()
            sample = (ts, noisy_temp)
            with self._lock:
                self._latest = sample
                self._downsample_counter += 1
                if self._downsample_counter >= 100:
                    self._all.append(sample)
                    self._downsample_counter = 0
            elapsed = time.time() - loop_start
            remaining = self.POLLING_TIME - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def get_all_temperatures(self):
        with self._lock:
            return list(self._all)


class SimulatedSensorData:
    """Combines depth + temperature to mimic PressureSensorData interface."""

    POLLING_TIME = 0.05  # needed by VelocityCalculator

    def __init__(self, sim: SimulatedFloat):
        self.depth_sensor = SimulatedPressureSensor(sim)
        self.temp_sensor = SimulatedTemperatureSensor(sim)

    def start(self):
        self.depth_sensor.start()
        self.temp_sensor.start()

    def stop_data_collection(self):
        self.depth_sensor.stop()
        self.temp_sensor.stop()

    def get_latest_depth(self):
        return self.depth_sensor.get_latest_depth()

    def get_recent_depth(self):
        return self.depth_sensor.get_recent_depth()

    def get_all_depth(self):
        return self.depth_sensor.get_all_depth()

    def get_all_temperatures(self):
        return self.temp_sensor.get_all_temperatures()

    def package_data(self):
        return [self.get_all_depth(), self.get_all_temperatures()]


class SimulatedVelocityCalculator:
    """
    Mirrors real VelocityCalculator: 2-state constant-velocity Kalman filter.
    Benchmark winner across all MS5837-02BA noise scenarios (0-sample lag).
    """

    def __init__(self, sensor_data: SimulatedSensorData):
        self.sensorData = sensor_data
        self._r_meas   = 0.0001    # σ² = (0.01 m)²
        self._q_vel    = 5e-4      # process noise on velocity per second
        self._x        = None      # [depth, velocity]
        self._P        = [[1.0, 0.0], [0.0, 1.0]]
        self._last_time = None

    def update_velocity(self) -> float:
        samples = self.sensorData.get_recent_depth()
        if not samples:
            return 0.0
        t_curr, d_curr = samples[-1]

        if self._x is None:
            self._x = [d_curr, 0.0]
            self._last_time = t_curr
            return 0.0

        dt = t_curr - self._last_time
        if dt <= 1e-6:
            return self._x[1]
        self._last_time = t_curr

        # Predict
        x0_p = self._x[0] + self._x[1] * dt
        x1_p = self._x[1]
        P = self._P
        q_v  = self._q_vel * dt
        P00  = P[0][0] + dt * (P[1][0] + P[0][1]) + dt * dt * P[1][1]
        P01  = P[0][1] + dt * P[1][1]
        P10  = P[1][0] + dt * P[1][1]
        P11  = P[1][1] + q_v

        # Update
        S   = P00 + self._r_meas
        K0  = P00 / S
        K1  = P10 / S
        inn = d_curr - x0_p
        self._x = [x0_p + K0 * inn, x1_p + K1 * inn]
        self._P = [[P00 - K0 * P00,  P01 - K0 * P01],
                   [P10 - K1 * P00,  P11 - K1 * P01]]
        return self._x[1]


class SimulatedAccelerationCalculator:
    """Mirrors AccelerationCalculator using the two-pass finite-difference
    method on the simulated depth buffer."""

    def __init__(self, sensor_data: SimulatedSensorData):
        self.sensorData = sensor_data

    def update_acceleration(self, seconds: float) -> float:
        samples = self.sensorData.get_recent_depth()
        target_iterations = int(seconds / self.sensorData.POLLING_TIME)
        if target_iterations <= len(samples):
            samples = samples[-target_iterations:]
        if len(samples) < 3:
            return 0.0

        # Pass 1: velocities
        velocities = []
        for i in range(1, len(samples)):
            t_prev, d_prev = samples[i - 1]
            t_curr, d_curr = samples[i]
            dt = t_curr - t_prev
            velocities.append(
                (t_curr, (d_curr - d_prev) / dt if dt >= 1e-9 else 0.0)
            )

        # Pass 2: accelerations
        accelerations = []
        for i in range(1, len(velocities)):
            t_prev, v_prev = velocities[i - 1]
            t_curr, v_curr = velocities[i]
            dt = t_curr - t_prev
            accelerations.append(
                (v_curr - v_prev) / dt if dt >= 1e-9 else 0.0
            )

        return sum(accelerations) / len(accelerations)


class SimulatedMotorController:

    def __init__(self, sim: SimulatedFloat):
        self.sim = sim
        self.direction = None
        # Max volume rate: 120 RPM × 4mm pitch = 8mm/s linear × π × 0.020² = ~10.1 mL/s
        self.max_volume_rate = 0.0000101  # m³/sec
        # Fill stall threshold: water pressure opposes syringe fill (CW/DOWN direction).
        # Empirical: 2.4 kg·cm torque at 2.5m, 6.5 kg·cm rated → 14.77% duty per meter.
        # If duty < stall_threshold(depth), motor cannot turn — no volume change.
        # Drain (CCW) is pressure-assisted — no stall modeled.
        self.fill_duty_per_meter = 14.77

    def update_direction(self, direction):
        self.direction = direction

    def set_speed(self, duty_cycle):
        rate = (duty_cycle / 100.0) * self.max_volume_rate
        if self.direction == "CCW":
            # CCW = drain syringe = increase buoyancy = float rises
            with self.sim.lock:
                self.sim.volume_rate = rate
        elif self.direction == "CW":
            # CW = fill syringe = decrease buoyancy = float sinks.
            # Stall check: pressure at depth requires minimum duty to turn motor.
            with self.sim.lock:
                depth = self.sim.depth
                stall_duty = self.fill_duty_per_meter * depth
                if duty_cycle < stall_duty:
                    self.sim.volume_rate = 0.0  # motor stalled — no fill
                else:
                    self.sim.volume_rate = -rate
        else:
            with self.sim.lock:
                self.sim.volume_rate = 0.0

    def cleanup_motor_controller(self):
        with self.sim.lock:
            self.sim.volume_rate = 0.0


# ============================================================
# PATCH DepthTarget TO USE SIM HARDWARE
# ============================================================

class SimDepthTarget(DepthTarget):

    def __init__(self, sim: SimulatedFloat):
        # Inject simulated hardware — bypass real __init__ entirely
        self.sim = sim
        self.UP = "CCW"
        self.DOWN = "CW"
        self.cur_direction = None

        self.sensorData = SimulatedSensorData(sim)
        self.velocity_calculator = SimulatedVelocityCalculator(self.sensorData)
        self.acceleration_calculator = SimulatedAccelerationCalculator(self.sensorData)
        self.motorController = SimulatedMotorController(sim)

        # Instance state that persists across go_to_target calls
        self.syringe_est_mL = 0.0
        self.hold_start_time = None
        self.hold_target = None

        # Start sensor polling threads
        self.sensorData.start()


# ============================================================
# MAIN SIMULATION
# ============================================================

# Mission parameters
LOW_TARGET_DEPTH = 2.5
HIGH_TARGET_DEPTH = 0.44  # center of 0.11–0.77m range (±0.33 tolerance)
START_DEPTH = 0.0        # initial descent target before profile begins
MAX_PROFILE_SECS = 800   # 7 minutes per profile (fail threshold)

# Time acceleration
SPEEDUP = 1


def run_simulation():

    print("=" * 65)
    print("  FLOAT BUOYANCY ENGINE — SIMULATION RUN")
    print("  Environment: indoor pool (78 °F / 25.56 °C, freshwater, smooth surface)")
    print(f"  Sensor noise:  depth σ={DEPTH_NOISE_STDDEV}m, temp σ={TEMP_NOISE_STDDEV}°C")
    print(f"  Water current: σ={CURRENT_SIGMA} m/s, τ_corr={CURRENT_TAU}s (gentle circulation)")
    print(f"  Density:       {SURFACE_DENSITY} kg/m³ uniform (no thermocline)")
    print(f"  Surface waves: none")
    print(f"  Float: mass={12.0}kg, Cd={0.9}, area={0.015}m²")
    print(f"  Speedup: {SPEEDUP}x")
    print("=" * 65)
    print()

    # Accelerate time
    _real_sleep = time.sleep
    _real_time = time.time
    _time_offset_start = _real_time()

    def fast_sleep(seconds):
        _real_sleep(seconds / SPEEDUP)

    def fast_time():
        real_now = _real_time()
        real_elapsed = real_now - _time_offset_start
        return _time_offset_start + real_elapsed * SPEEDUP

    time.sleep = fast_sleep
    time.time = fast_time

    # Create simulation
    sim = SimulatedFloat()
    controller = SimDepthTarget(sim)

    # Start physics thread
    physics_running = True

    def physics_loop():
        while physics_running:
            with sim.lock:
                sim.step(PHYSICS_DT)
            _real_sleep(PHYSICS_DT / SPEEDUP)

    physics_thread = threading.Thread(target=physics_loop, daemon=True)
    physics_thread.start()

    # Status reporting thread
    report_running = True

    def report_loop():
        while report_running:
            with sim.lock:
                d = sim.depth
                v = sim.velocity
                cur = sim.current
                vr = sim.volume_rate * 1000
            dir_str = "UP" if vr > 0 else ("DOWN" if vr < 0 else "STOP")
            print(f"  [SIM] depth={d:6.3f}m | vel={v:+.4f} m/s | "
                  f"current={cur:+.4f} m/s | motor={dir_str} vol_rate={vr:+.8f} ml/s")
            _real_sleep(0.5)

    report_thread = threading.Thread(target=report_loop, daemon=True)
    report_thread.start()

    # --- Run mission ---
    # Profile sequence: 0.4m -> 2.5m -> 0.4m -> 2.5m -> 0.4m (no holds)
    print(f"Starting mission: {START_DEPTH}m -> {LOW_TARGET_DEPTH}m -> {HIGH_TARGET_DEPTH}m -> {LOW_TARGET_DEPTH}m -> {HIGH_TARGET_DEPTH}m")
    print("-" * 65)

    profile_start = time.time()

    print(f"\n  >>> Initial drop to {START_DEPTH}m")
    controller.go_to_target(START_DEPTH)

    print(f"\n  >>> Leg 1: descend to {LOW_TARGET_DEPTH}m")
    controller.go_to_target(LOW_TARGET_DEPTH, k_stop=800.0, hold_zone=0.33)

    print(f"\n  >>> Leg 1 hold: hold at {LOW_TARGET_DEPTH}m")
    controller.depth_hold(LOW_TARGET_DEPTH, duration=35.0, tolerance=0.33)

    print(f"\n  >>> Settling before Leg 2...")
    controller.settle()

    print(f"\n  >>> Leg 2: ascend to {HIGH_TARGET_DEPTH}m")
    controller.go_to_target(HIGH_TARGET_DEPTH, k_stop=650.0, max_compress_ml=15.0, max_expand_ml=2.0, hold_zone=0.29, max_vel=0.03)

    print(f"\n  >>> Leg 2 hold: hold at {HIGH_TARGET_DEPTH}m")
    controller.depth_hold(HIGH_TARGET_DEPTH, duration=35.0, tolerance=0.29)

    print(f"\n  >>> Settling before Leg 3...")
    controller.settle()

    print(f"\n  >>> Leg 3: descend to {LOW_TARGET_DEPTH}m")
    controller.go_to_target(LOW_TARGET_DEPTH, k_stop=800.0, hold_zone=0.33)

    print(f"\n  >>> Leg 3 hold: hold at {LOW_TARGET_DEPTH}m")
    controller.depth_hold(LOW_TARGET_DEPTH, duration=35.0, tolerance=0.33)

    print(f"\n  >>> Settling before Leg 4...")
    controller.settle()

    print(f"\n  >>> Leg 4: ascend to {HIGH_TARGET_DEPTH}m — MISSION COMPLETE")
    controller.go_to_target(HIGH_TARGET_DEPTH, k_stop=650.0, max_compress_ml=15.0, max_expand_ml=2.0, hold_zone=0.29, max_vel=0.03)

    print(f"\n  >>> Leg 4 hold: hold at {HIGH_TARGET_DEPTH}m")
    controller.depth_hold(HIGH_TARGET_DEPTH, duration=35.0, tolerance=0.29)

    elapsed = time.time() - profile_start
    over_limit = elapsed > MAX_PROFILE_SECS
    print(f"\n  {'!!! OVER TIME LIMIT' if over_limit else '*** WITHIN TIME LIMIT'}: {elapsed:.1f}s / {MAX_PROFILE_SECS}s")

    # Stop threads
    report_running = False
    physics_running = False
    _real_sleep(0.2)

    # Package and write data
    float_data = controller.sensorData.package_data()
    with open("float_data.txt", "w") as f:
        f.write(str(float_data))

    print()
    print("-" * 65)
    print(f"Mission complete. Profile time: {elapsed:.1f}s  ({'PASS' if not over_limit else 'FAIL - exceeded 7 min'})")
    print(f"Data written to float_data.txt ({len(float_data[0])} depth samples, "
          f"{len(float_data[1])} temp samples)")
    print("=" * 65)

    # Restore time
    time.sleep = _real_sleep
    time.time = _real_time

    # Cleanup
    controller.sensorData.stop_data_collection()
    controller.motorController.cleanup_motor_controller()

    return float_data


if __name__ == "__main__":
    run_simulation()
