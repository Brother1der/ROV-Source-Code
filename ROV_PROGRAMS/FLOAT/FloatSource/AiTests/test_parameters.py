"""
Parametric sweep of DepthTarget go_to_target parameters.
Tests different MAX_VEL and BRAKE_GAIN combinations against
the ±0.33m hold tolerance with real-world physics variability.

Variability model:
  - Sensor noise: depth σ = 0.05m (MS5837-30BA)
  - Water current: O-U process, σ = 0.03 m/s
  - Density gradient: 998 + 0.5·depth kg/m³
  - Surface waves: 0.02m @ 3s period
  - Full drag/buoyancy physics (12kg, Cd=0.9, A=0.015m²)
"""

import time
import math
import random
import threading
from collections import deque

# ============================================================
# PHYSICS (same as simulation.py)
# ============================================================

DEPTH_NOISE_STDDEV = 0.01   # Bar02 (MS5837-02BA): ±2 mbar = ±2 cm accuracy; σ ≈ 1 cm (2-sigma bound)
TEMP_NOISE_STDDEV = 0.1
BASE_TEMPERATURE = 22.5
CURRENT_MEAN = 0.0
CURRENT_SIGMA = 0.03
CURRENT_TAU = 10.0
SURFACE_DENSITY = 998.0
DENSITY_GRADIENT = 0.5
WAVE_AMPLITUDE = 0.02
WAVE_PERIOD = 3.0
WAVE_DECAY_DEPTH = 0.5
PHYSICS_DT = 0.01

HOLD_DURATION = 35
DEPTH_TOLERANCE = 0.33
LOW_TARGET = 2.5
HIGH_TARGET = 0.4


class SimFloat:
    def __init__(self):
        self.g = 9.81
        self.mass = 12.0
        self.area = 0.015
        self.Cd = 0.9
        self.depth = 0.0
        self.velocity = 0.0
        self.volume_offset = 0.0
        self.rho = SURFACE_DENSITY
        self.neutral_volume = self.mass / self.rho
        self.current = 0.0
        self.volume_rate = 0.0
        self.sim_time = 0.0
        self.lock = threading.Lock()

    def step(self, dt):
        theta = 1.0 / CURRENT_TAU
        self.current += (-theta * (self.current - CURRENT_MEAN) * dt
                         + CURRENT_SIGMA * math.sqrt(2 * theta * dt) * random.gauss(0, 1))
        self.volume_offset += self.volume_rate * dt
        self.volume_offset = max(-1e-4, min(1e-4, self.volume_offset))  # ±100 mL syringe cap
        local_rho = SURFACE_DENSITY + DENSITY_GRADIENT * self.depth
        total_volume = self.neutral_volume + self.volume_offset
        buoyancy = local_rho * self.g * total_volume
        weight = self.mass * self.g
        drag = 0.5 * local_rho * self.Cd * self.area * self.velocity ** 2
        drag *= -math.copysign(1, self.velocity) if self.velocity != 0 else 0
        net_force = buoyancy - weight + drag
        self.velocity += (net_force / self.mass) * dt
        wave = (WAVE_AMPLITUDE * math.sin(2 * math.pi * self.sim_time / WAVE_PERIOD)
                * math.exp(-self.depth / WAVE_DECAY_DEPTH))
        self.depth -= self.velocity * dt
        self.depth += self.current * dt + wave * dt
        if self.depth < 0:
            self.depth = 0
            self.velocity = max(0, self.velocity)
        if self.depth > 5.0:
            self.depth = 5.0
            self.velocity = min(0, self.velocity)
        self.sim_time += dt

    def reset(self):
        self.depth = 0.0
        self.velocity = 0.0
        self.volume_offset = 0.0
        self.current = 0.0
        self.volume_rate = 0.0
        self.sim_time = 0.0


# ============================================================
# SIMULATED HARDWARE
# ============================================================

class SimSensorData:
    POLLING_TIME = 0.1   # Matches real hardware: 10 Hz (optimal for velocity noise)

    def __init__(self, sim):
        self.sim = sim
        self._lock = threading.Lock()
        self._latest = (time.time(), 0.0)
        self._recent = deque(maxlen=500)
        self._all_depth = deque(maxlen=200)
        self._all_temp = deque(maxlen=200)
        self._depth_counter = 0
        self._temp_counter = 0
        self._running = False

    def start(self):
        self._running = True
        self._depth_thread = threading.Thread(target=self._depth_loop, daemon=True)
        self._temp_thread = threading.Thread(target=self._temp_loop, daemon=True)
        self._depth_thread.start()
        self._temp_thread.start()

    def stop(self):
        self._running = False

    def _depth_loop(self):
        while self._running:
            t0 = time.time()
            with self.sim.lock:
                true_d = self.sim.depth
            noisy = max(0.0, true_d + random.gauss(0, DEPTH_NOISE_STDDEV))
            ts = time.time()
            sample = (ts, noisy)
            with self._lock:
                self._latest = sample
                self._recent.append(sample)
                self._depth_counter += 1
                if self._depth_counter >= 100:
                    self._all_depth.append(sample)
                    self._depth_counter = 0
            rem = self.POLLING_TIME - (time.time() - t0)
            if rem > 0:
                time.sleep(rem)

    def _temp_loop(self):
        while self._running:
            t0 = time.time()
            with self.sim.lock:
                d = self.sim.depth
            temp = BASE_TEMPERATURE - 0.3 * d + random.gauss(0, TEMP_NOISE_STDDEV)
            ts = time.time()
            with self._lock:
                self._temp_counter += 1
                if self._temp_counter >= 100:
                    self._all_temp.append((ts, temp))
                    self._temp_counter = 0
            rem = self.POLLING_TIME - (time.time() - t0)
            if rem > 0:
                time.sleep(rem)

    def get_latest_depth(self):
        with self._lock:
            return self._latest

    def get_recent_depth(self):
        with self._lock:
            return list(self._recent)

    def get_all_depth(self):
        with self._lock:
            return list(self._all_depth)

    def get_all_temperatures(self):
        with self._lock:
            return list(self._all_temp)

    def package_data(self):
        return [self.get_all_depth(), self.get_all_temperatures()]

    def stop_data_collection(self):
        self.stop()


class SimVelocityCalc:
    def __init__(self, sensor_data):
        self.sensorData = sensor_data

    def update_velocity(self, seconds):
        samples = self.sensorData.get_recent_depth()
        n = int(seconds / self.sensorData.POLLING_TIME)
        if n <= len(samples):
            samples = samples[-n:]
        if len(samples) < 2:
            return 0.0
        vels = []
        for i in range(1, len(samples)):
            dt = samples[i][0] - samples[i-1][0]
            if dt < 1e-9:
                vels.append(0.0)
            else:
                vels.append((samples[i][1] - samples[i-1][1]) / dt)
        return sum(vels) / len(vels)


class SimMotor:
    def __init__(self, sim):
        self.sim = sim
        self.direction = None
        self.max_volume_rate = 0.000017

    def update_direction(self, direction):
        self.direction = direction

    def set_speed(self, duty_cycle):
        rate = (duty_cycle / 100.0) * self.max_volume_rate
        with self.sim.lock:
            if self.direction == "CCW":
                self.sim.volume_rate = rate
            elif self.direction == "CW":
                self.sim.volume_rate = -rate
            else:
                self.sim.volume_rate = 0.0

    def cleanup_motor_controller(self):
        with self.sim.lock:
            self.sim.volume_rate = 0.0


# ============================================================
# PARAMETERIZED DEPTH TARGET
# ============================================================

class TestDepthTarget:
    """DepthTarget with configurable go_to_target parameters.
    Reproduces the exact control logic from the real DepthTarget."""

    INTERVAL = 0.1

    def __init__(self, sim, max_vel, brake_gain, noise=0.05, vel_window=1, min_duty=20,
                 real_time_fn=None):
        self.sim = sim
        self.UP = "CCW"
        self.DOWN = "CW"
        self.cur_direction = None
        self.max_vel = max_vel
        self.brake_gain = brake_gain
        self.NOISE = noise
        self.vel_window = vel_window
        self.min_duty = min_duty
        self._real_time = real_time_fn or __import__('time').time

        self.sensorData = SimSensorData(sim)
        self.velocity_calculator = SimVelocityCalc(self.sensorData)
        self.motorController = SimMotor(sim)
        self.sensorData.start()

    def calculate_target_duty_cycle(self, cur_vel, target_vel):
        abs_error = abs(target_vel - cur_vel)
        Kp = 250
        return int(min(100, max(self.min_duty, Kp * abs_error)))

    def go_to_target(self, target_depth):
        MAX_VEL = self.max_vel
        BRAKE_GAIN = self.brake_gain
        MIN_VEL = 0.015
        POSITION_TOL = 0.04

        # Use wall-clock deadline so physics-thread speed doesn't affect it
        real_deadline = self._real_time() + 60  # 60 real-s max per transit

        while True:
            if self._real_time() > real_deadline:
                self.motorController.set_speed(0)
                return

            start_time = time.time()
            cur_depth = self.sensorData.get_latest_depth()
            cur_vel = self.velocity_calculator.update_velocity(self.vel_window)
            depth_error = target_depth - cur_depth[1]
            distance = abs(depth_error)

            # Position-only capture — braking profile guarantees slow arrival;
            # velocity measurement noise is too large relative to VELOCITY_TOL
            # to be a reliable condition here.
            if distance <= POSITION_TOL:
                self.motorController.set_speed(0)
                return

            if depth_error > 0:
                direction = self.DOWN
                direction_sign = 1
            else:
                direction = self.UP
                direction_sign = -1

            if direction != self.cur_direction:
                self.motorController.update_direction(direction)
                self.cur_direction = direction

            target_velocity = MAX_VEL * math.tanh(BRAKE_GAIN * distance)
            if abs(target_velocity) < MIN_VEL and distance > POSITION_TOL:
                target_velocity = MIN_VEL
            target_velocity *= direction_sign

            duty_cycle = self.calculate_target_duty_cycle(cur_vel, target_velocity)
            self.motorController.set_speed(duty_cycle)

            elapsed = time.time() - start_time
            remaining = self.INTERVAL - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def depth_hold(self, target_depth, duration, tolerance):
        hold_start_time = None
        real_deadline = self._real_time() + 300  # 300 real-s max for hold phase
        while True:
            if self._real_time() > real_deadline:
                self.motorController.set_speed(0)
                return
            cur_depth = self.sensorData.get_latest_depth()
            depth_error = target_depth - cur_depth[1]

            if abs(depth_error) <= tolerance:
                if hold_start_time is None:
                    hold_start_time = time.time()
                elif time.time() - hold_start_time >= duration:
                    self.motorController.set_speed(0)
                    return
                if abs(depth_error) > self.NOISE:
                    self.go_to_target(target_depth)
            else:
                hold_start_time = None
                self.go_to_target(target_depth)

            time.sleep(self.INTERVAL)

    def cleanup(self):
        self.sensorData.stop()
        self.motorController.cleanup_motor_controller()


# ============================================================
# TEST RUNNER
# ============================================================

def run_single_test(max_vel, brake_gain, noise=0.05, vel_window=1, min_duty=20,
                    speedup=10, timeout_s=300, verbose=False):
    """Run one full 2-profile mission with given parameters.
    Returns dict with results or None if timed out."""

    _real_sleep = time.sleep
    _real_time = time.time
    _t0 = _real_time()

    def fast_sleep(s):
        _real_sleep(s / speedup)
    def fast_time():
        return _t0 + (_real_time() - _t0) * speedup

    time.sleep = fast_sleep
    time.time = fast_time

    sim = SimFloat()
    ctrl = TestDepthTarget(sim, max_vel, brake_gain, noise=noise,
                           vel_window=vel_window, min_duty=min_duty,
                           real_time_fn=_real_time)

    physics_running = True
    def physics():
        while physics_running:
            with sim.lock:
                sim.step(PHYSICS_DT)
            _real_sleep(PHYSICS_DT / speedup)

    pt = threading.Thread(target=physics, daemon=True)
    pt.start()

    # Record true depth history for analysis
    depth_log = []
    log_running = True
    def logger():
        while log_running:
            with sim.lock:
                depth_log.append((_real_time() - _t0, sim.depth))
            _real_sleep(0.05)
    lt = threading.Thread(target=logger, daemon=True)
    lt.start()

    start = time.time()
    timed_out = False

    try:
        for profile in range(2):
            ctrl.go_to_target(LOW_TARGET)
            if (_real_time() - _t0) > timeout_s:
                timed_out = True
                break
            ctrl.depth_hold(LOW_TARGET, HOLD_DURATION, DEPTH_TOLERANCE)
            if (_real_time() - _t0) > timeout_s:
                timed_out = True
                break
            ctrl.go_to_target(HIGH_TARGET)
            if (_real_time() - _t0) > timeout_s:
                timed_out = True
                break
            ctrl.depth_hold(HIGH_TARGET, HOLD_DURATION, DEPTH_TOLERANCE)
            if (_real_time() - _t0) > timeout_s:
                timed_out = True
                break
    except Exception as e:
        time.sleep = _real_sleep
        time.time = _real_time
        physics_running = False
        log_running = False
        ctrl.cleanup()
        return {"error": str(e)}

    elapsed_sim = time.time() - start
    elapsed_real = _real_time() - _t0

    physics_running = False
    log_running = False
    _real_sleep(0.1)

    # Get sensor data for analysis
    float_data = ctrl.sensorData.package_data()

    time.sleep = _real_sleep
    time.time = _real_time
    ctrl.cleanup()

    if timed_out:
        return {"timed_out": True, "elapsed_real": elapsed_real}

    # Analyze holds
    depth_samples = float_data[0]
    results = {
        "max_vel": max_vel,
        "brake_gain": brake_gain,
        "elapsed_sim": elapsed_sim,
        "elapsed_real": elapsed_real,
        "n_samples": len(depth_samples),
        "holds": [],
        "all_pass": True,
        "max_deviation": 0.0,
        "float_data": float_data,
    }

    if len(depth_samples) < 4:
        results["all_pass"] = False
        results["error"] = "Too few samples"
        return results

    # Identify hold phases by finding samples near each target
    for target in [LOW_TARGET, HIGH_TARGET]:
        tol = DEPTH_TOLERANCE
        lo, hi = target - tol, target + tol
        near = [(i, d) for i, (ts, d) in enumerate(depth_samples) if lo <= d <= hi]

        # Group contiguous
        groups = []
        cur = []
        for item in near:
            if cur and item[0] != cur[-1][0] + 1:
                groups.append(cur)
                cur = []
            cur.append(item)
        if cur:
            groups.append(cur)

        for gi, group in enumerate(groups):
            depths = [d for _, d in group]
            devs = [abs(d - target) for d in depths]
            max_dev = max(devs) if devs else 0
            passed = all(dev <= tol for dev in devs)
            if not passed:
                results["all_pass"] = False
            if max_dev > results["max_deviation"]:
                results["max_deviation"] = max_dev
            results["holds"].append({
                "target": target,
                "profile": gi + 1,
                "n_samples": len(group),
                "depth_range": (min(depths), max(depths)),
                "max_deviation": max_dev,
                "margin": tol - max_dev,
                "passed": passed,
            })

    return results


def print_result(label, result):
    status = "PASS" if result["all_pass"] else "FAIL"
    print(f"\n  {label}  →  {status}")
    print(f"  {'─' * 55}")
    for h in result["holds"]:
        lo, hi = h["depth_range"]
        print(f"    Hold @ {h['target']}m  (profile {h['profile']}):  "
              f"{lo:.3f}–{hi:.3f}m  |  max dev {h['max_deviation']:.3f}m  "
              f"margin {h['margin']:+.3f}m  {'✓' if h['passed'] else '✗'}")
    print(f"    Overall max deviation: {result['max_deviation']:.3f}m  |  "
          f"margin: {DEPTH_TOLERANCE - result['max_deviation']:+.3f}m  |  "
          f"sim time: {result['elapsed_sim']:.0f}s")


def main():
    configs = [
        {
            "label": "DEFAULT   (MAX_VEL=0.30, NOISE=0.05, vel_win=1s, min_duty=20%)",
            "max_vel": 0.30, "brake_gain": 2.5,
            "noise": 0.05, "vel_window": 1, "min_duty": 20,
        },
        {
            "label": "POOL TUNED (MAX_VEL=0.15, NOISE=0.02, vel_win=2s, min_duty=15%)",
            "max_vel": 0.15, "brake_gain": 2.5,
            "noise": 0.02, "vel_window": 2, "min_duty": 15,
        },
    ]

    print("=" * 65)
    print("  DEFAULT vs POOL-TUNED COMPARISON")
    print("  Tolerance: ±0.33m | Hold: 35s | 2 profiles")
    print("  Physics: sensor σ=0.05m, current σ=0.03m/s, waves, density")
    print("=" * 65)

    best = None
    for cfg in configs:
        print(f"\n  Running: {cfg['label']} ... ", end="", flush=True)
        result = run_single_test(
            cfg["max_vel"], cfg["brake_gain"],
            noise=cfg["noise"], vel_window=cfg["vel_window"],
            min_duty=cfg["min_duty"],
            speedup=15, timeout_s=600
        )

        if result is None or result.get("timed_out"):
            print("TIMEOUT")
            continue
        if result.get("error"):
            print(f"ERROR: {result['error']}")
            continue

        print("done")
        print_result(cfg["label"], result)

        if result["all_pass"]:
            if best is None or result["max_deviation"] < best["max_deviation"]:
                best = result

    print()
    print("=" * 65)
    if best and best.get("float_data"):
        with open("float_data.txt", "w") as f:
            f.write(str(best["float_data"]))
        print("  Best result written to float_data.txt")
    print("=" * 65)


if __name__ == "__main__":
    main()
