### Last Modified 3/1/2026
# Built by Conner O'Reilly
# Purpose: Control logic for moving to and holding at target depths using syringe actuation.
# Combines sensor data processing (velocity, acceleration) with predictive PD control.
#
# Requirements: Device with full python support. Pressure sensor float build.
###
from FloatVerticalProfiler.pressureSensor.PressureSensorData import PressureSensorData
from FloatVerticalProfiler.dataCalculations.VeloctiyCalculator import VelocityCalculator
from FloatVerticalProfiler.dataCalculations.AccelerationCalculator import AccelerationCalculator
from FloatVerticalProfiler.motorControls.MotorController import MotorController
import time
import math

class DepthTarget:

    UP = "CCW"
    DOWN = "CW"

    PWM_PIN = 18
    INA_PIN = 16
    INB_PIN = 17
    PWM_FREQ = 1000

    INTERVAL = 0.3  # control loop period (s)

    # Physical syringe volume limit: π × r² × L (r=20mm, L=114mm) ≈ 143.3 mL.
    # Estimator is clamped to this range so gate checks reflect reality even
    # when the motor stalls at a limit without a wired hall-effect switch.
    SYRINGE_MAX_ML = math.pi * (0.020 ** 2) * 0.114 * 1e6  # ≈ 143.3 mL

    def __init__(self, sensor_data: PressureSensorData, up: str, down: str):
        self.UP = up
        self.DOWN = down
        self.cur_direction = None

        self.sensorData = sensor_data
        self.velocity_calculator = VelocityCalculator(sensor_data)
        self.acceleration_calculator = AccelerationCalculator(sensor_data)
        self.motorController = MotorController(
            self.PWM_PIN, self.INA_PIN, self.INB_PIN, self.PWM_FREQ
        )

        # Syringe volume estimator — persists across go_to_target calls.
        # Negative = compressed (sinks), positive = expanded (rises).
        # Call calibrate_syringe() when float is neutrally buoyant to zero it.
        self.syringe_est_mL = 0.0

        # Hold timer — starts counting when float first enters the
        # LOW_TARGET zone (±0.33m) during a descent leg, persists across calls
        # so we don't waste time re-settling after the transition.
        self.hold_start_time = None
        self.hold_target = None

    def calibrate_syringe(self):
        """Zero the syringe estimator. Call when float is neutrally buoyant."""
        self.syringe_est_mL = 0.0

    def _update_syringe(self, delta_mL: float):
        """Update and clamp the syringe estimator to physical limits."""
        self.syringe_est_mL = max(
            -self.SYRINGE_MAX_ML,
            min(self.SYRINGE_MAX_ML, self.syringe_est_mL + delta_mL)
        )

    def settle(self, timeout=25.0):
        """
        Bring float to rest with syringe near neutral between legs.

        Key insight: if syringe offset already opposes the float's motion
        (compressed + rising, or expanded + sinking), buoyancy will naturally
        decelerate the float — COAST and let physics work. Never make the
        syringe offset WORSE just to fight velocity.

        Priority order:
        1. COAST_BUOY: syringe opposes motion → let buoyancy decelerate
        2. SYR_PUMP: pump syringe toward neutral (dominant error source)
        3. VEL_DAMP: if syringe near neutral but still moving, gently oppose
        4. DONE: both settled
        """
        FILL_DUTY_PER_METER = 14.77
        VEL_THRESH = 0.015       # above Kalman noise floor (~0.01 m/s)
        SYR_THRESH = 0.5
        SYR_DUTY = 15
        VEL_DAMP_DUTY = 25
        PULSE_ON = 0.4
        EMERGENCY_DEPTH = 4
        start = time.time()
        print(f"  settle: starting syr={self.syringe_est_mL:+.1f}mL")

        while time.time() - start < timeout:
            depth, vel, _ = self._read()

            if depth > EMERGENCY_DEPTH:
                print(f"  settle: EMERGENCY depth={depth:.3f} > {EMERGENCY_DEPTH}m, aborting")
                break

            abs_vel = abs(vel)
            abs_syr = abs(self.syringe_est_mL)
            rising = vel < 0  # Kalman: negative vel = rising

            # Check: does syringe buoyancy naturally oppose current motion?
            # Compressed (syr<-1) opposes rising; expanded (syr>+1) opposes sinking
            syringe_opposes = (rising and self.syringe_est_mL < -1.0) or \
                              (not rising and self.syringe_est_mL > 1.0 and abs_vel > VEL_THRESH)

            if abs_vel > VEL_THRESH and syringe_opposes:
                # COAST_BUOY: buoyancy is fighting the motion — let physics decelerate
                self.motorController.set_speed(0)
                print(f"  settle: depth={depth:.3f} vel={vel:+.3f} syr={self.syringe_est_mL:+.1f}mL COAST_BUOY")
                time.sleep(0.5)

            elif abs_syr > SYR_THRESH:
                # SYR_PUMP: pump syringe toward neutral (reduces dominant error)
                direction = self.DOWN if self.syringe_est_mL > 0 else self.UP
                effective_duty = SYR_DUTY
                if direction == self.DOWN:
                    stall_threshold = int(FILL_DUTY_PER_METER * depth)
                    effective_duty = max(SYR_DUTY, stall_threshold + 1)
                    effective_duty = min(85, effective_duty)
                self._drive(direction, effective_duty)
                time.sleep(PULSE_ON)
                self.motorController.set_speed(0)
                stall_thr = int(FILL_DUTY_PER_METER * depth) if direction == self.DOWN else 0
                if effective_duty >= stall_thr:
                    rate_mL_s = (effective_duty / 100.0) * 10.1
                    delta = -(rate_mL_s * PULSE_ON) if direction == self.DOWN else (rate_mL_s * PULSE_ON)
                    self._update_syringe(delta)
                print(f"  settle: depth={depth:.3f} vel={vel:+.3f} syr={self.syringe_est_mL:+.1f}mL SYR_PUMP {direction} {effective_duty}%")
                time.sleep(0.3)

            elif abs_vel > VEL_THRESH:
                # VEL_DAMP: syringe near neutral but still moving — gently oppose
                direction = self.DOWN if vel < 0 else self.UP
                duty = int(min(VEL_DAMP_DUTY, 600 * abs_vel))
                effective_duty = duty
                if direction == self.DOWN:
                    stall_threshold = int(FILL_DUTY_PER_METER * depth)
                    effective_duty = max(duty, stall_threshold + 1)
                    effective_duty = min(85, effective_duty)
                self._drive(direction, effective_duty)
                time.sleep(PULSE_ON)
                self.motorController.set_speed(0)
                stall_thr = int(FILL_DUTY_PER_METER * depth) if direction == self.DOWN else 0
                if effective_duty >= stall_thr:
                    rate_mL_s = (effective_duty / 100.0) * 10.1
                    delta = -(rate_mL_s * PULSE_ON) if direction == self.DOWN else (rate_mL_s * PULSE_ON)
                    self._update_syringe(delta)
                print(f"  settle: depth={depth:.3f} vel={vel:+.3f} syr={self.syringe_est_mL:+.1f}mL VEL_DAMP {direction} {effective_duty}%")
                time.sleep(0.3)

            else:
                print(f"  settle: done depth={depth:.3f} vel={vel:+.3f} syr={self.syringe_est_mL:+.1f}mL")
                break

        self.motorController.set_speed(0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _drive(self, direction: str, duty: int):
        if direction != self.cur_direction:
            self.motorController.update_direction(direction)
            self.cur_direction = direction
        self.motorController.set_speed(duty)

    def _wait(self, loop_start: float):
        remaining = self.INTERVAL - (time.time() - loop_start)
        if remaining > 0:
            time.sleep(remaining)

    def _read(self):
        # Median of last 9 depth samples to suppress ±2cm sensor noise.
        # 9 samples at 50ms polling = 450ms window; median noise ≈ σ/3 ≈ 0.007m.
        recent = self.sensorData.get_recent_depth()
        if len(recent) >= 9:
            last9 = sorted(s[1] for s in recent[-9:])
            depth = last9[4]  # middle value = median of 9
        elif len(recent) >= 5:
            last5 = sorted(s[1] for s in recent[-5:])
            depth = last5[2]  # middle value = median of 5
        else:
            depth = self.sensorData.get_latest_depth()[1]

        # VelocityCalculator uses EMA on consecutive samples — call with no args.
        vel = self.velocity_calculator.update_velocity()
        acc = self.acceleration_calculator.update_acceleration(0.3)
        return depth, vel, acc

    # ------------------------------------------------------------------
    # Go to target depth
    # ------------------------------------------------------------------

    def go_to_target(self, target_depth, k_stop=200.0, hold_zone=None, max_compress_ml=2.0, max_expand_ml=2.0, max_vel=0.05):
        """
        Move to target_depth using predictive PD control. Utilizes a tanh curve for profiling.

        Args:
            target_depth (float): Desired depth in meters (positive down).
            k_stop (float): Predictive braking gain — larger means earlier braking.
            hold_zone (float): If set, once within ±hold_zone meters of target, switch to depth_hold mode.
            max_compress_ml (float): Max syringe compression before DRIVE is gated (mid-target safety).
            max_expand_ml (float): Max syringe expansion before BRAKE is gated (mid-target safety).
            max_vel (float): Max cruise velocity in m/s (tuning parameter for transit speed
        """

        POSITION_TOL = hold_zone if hold_zone else 0.06
        MAX_VEL = max_vel
        BRAKE_GAIN = 2.0           # tanh profile: avoids premature mid-transit braking
        MIN_VEL = 0.005
        MIN_DUTY = 0               # CRITICAL: allow motor to stop when vel_err ≈ 0
        MAX_DUTY = 85
        MAX_DRIVE_DUTY = 15        # limits syringe drain per pulse cycle
        MAX_BRAKE_DUTY = 50        # prevents excessive rebound buoyancy
        KP_VEL = 600               # duty per m/s
        VEL_HYST = 0.020           # wider than Kalman noise to prevent chatter
        EMERGENCY_DEPTH = 2.85
        MIN_SAFE_DEPTH = 0.10

        PULSE_ON = 0.2             # motor active time (s)
        PULSE_OFF = 0.8            # coast time (s)

        K_STOP = k_stop            # predictive stop zone: radius = k_stop × v²

        VEL_EXIT = 0.010           # exit velocity threshold
        MIN_SETTLE_SECS = 5.0      # sustained settle time guarantees ≤2.5 mL syringe offset
        ZONE_TIMEOUT = 30.0        # hard timeout fallback

        MAX_COMPRESS_ML = max_compress_ml
        MAX_EXPAND_ML = max_expand_ml
        GATE_RADIUS = 1.0          # syringe gate applies only near target

        # Fill compensation: water pressure opposes syringe fill (DOWN direction).
        # Empirical: 2.4 kg·cm torque needed at 2.5m → scales linearly with depth.
        # duty_offset = (2.4/2.5 × depth) / 6.5 rated × 100 = 14.77% per meter
        # Drain (UP) is pressure-assisted — no offset needed.
        FILL_DUTY_PER_METER = 14.77

        zone_entry = None
        settled_start = None   # time when vel first dropped below VEL_EXIT

        while True:
            start = time.time()
            depth, vel, _ = self._read()
            error = target_depth - depth

            # Emergency depth safety: hard-brake if float drifts past safety margin
            if depth > EMERGENCY_DEPTH and target_depth <= EMERGENCY_DEPTH:
                self._drive(self.UP, MAX_DUTY)
                print(f"  go_to: EMERGENCY BRAKE depth={depth:.3f} > {EMERGENCY_DEPTH}m")
                elapsed = time.time() - start
                time.sleep(max(0, PULSE_ON - elapsed))
                continue

            # Surface safety: hard-brake DOWN if too shallow.
            # Skip when: target IS the surface, OR far from target (transit start, not overshoot).
            if depth < MIN_SAFE_DEPTH and target_depth > MIN_SAFE_DEPTH and abs(error) < 1.0:
                self._drive(self.DOWN, MAX_DUTY)
                print(f"  go_to: SURFACE SAFETY depth={depth:.3f} < {MIN_SAFE_DEPTH}m, driving DOWN {MAX_DUTY}%")
                elapsed = time.time() - start
                time.sleep(max(0, PULSE_ON - elapsed))
                self.motorController.set_speed(0)
                time.sleep(PULSE_OFF)
                if MAX_DUTY > 0:
                    rate_mL_s = (MAX_DUTY / 100.0) * 10.1
                    self._update_syringe(-(rate_mL_s * PULSE_ON))
                continue

            # Exit: within position tolerance AND velocity settled for MIN_SETTLE_SECS (or timed out)
            if abs(error) <= POSITION_TOL:
                if zone_entry is None:
                    zone_entry = time.time()
                    # Start hold timer on first zone entry — persists across calls
                    if hold_zone and self.hold_start_time is None:
                        self.hold_start_time = time.time()
                        self.hold_target = target_depth
                        print(f"  go_to: HOLD TIMER STARTED at depth={depth:.3f}m (zone ±{hold_zone}m)")
                # When hold_zone is set, exit once velocity is manageable for depth_hold.
                if hold_zone:
                    if abs(vel) <= VEL_EXIT:
                        self.motorController.set_speed(0)
                        print(f"TARGET ZONE REACHED: depth={depth:.3f}m vel={vel:+.3f} target={target_depth}m (±{hold_zone}m)")
                        break
                    if (time.time() - zone_entry) >= ZONE_TIMEOUT:
                        self.motorController.set_speed(0)
                        print(f"TARGET ZONE REACHED (timeout): depth={depth:.3f}m vel={vel:+.3f} target={target_depth}m (±{hold_zone}m)")
                        break
                if abs(vel) <= VEL_EXIT:
                    if settled_start is None:
                        settled_start = time.time()
                    if (time.time() - settled_start) >= MIN_SETTLE_SECS:
                        self.motorController.set_speed(0)
                        print(f"TARGET REACHED: depth={depth:.3f}m vel={vel:+.3f} target={target_depth}m")
                        break
                else:
                    settled_start = None
                if (time.time() - zone_entry) >= ZONE_TIMEOUT:
                    self.motorController.set_speed(0)
                    print(f"TARGET REACHED (timeout): depth={depth:.3f}m vel={vel:+.3f} target={target_depth}m")
                    break
            else:
                zone_entry = None
                settled_start = None

            want_down = error > 0
            dir_sign = 1 if want_down else -1

            # Target velocity: tanh profile — full speed far out, ramps to zero near target
            target_vel = dir_sign * max(MIN_VEL, MAX_VEL * math.tanh(BRAKE_GAIN * abs(error)))

            abs_vel = abs(vel)
            vel_err = target_vel - vel

            # Overspeeding: moving faster than desired velocity profile
            if want_down:
                overspeeding = vel > target_vel + VEL_HYST
            else:
                overspeeding = vel < target_vel - VEL_HYST

            # Predictive stop zone: brake if can't decelerate in time (K_STOP × v²)
            moving_toward = (want_down and vel > 0) or (not want_down and vel < 0)
            in_stop_zone = abs(error) < K_STOP * abs_vel * abs_vel and moving_toward

            if in_stop_zone or overspeeding:
                # BRAKE mode: proportional duty decreases naturally as float slows
                direction = self.UP if want_down else self.DOWN
                duty = int(min(MAX_BRAKE_DUTY, max(MIN_DUTY, KP_VEL * abs_vel)))
                # Syringe gate: prevent over-expansion/compression near target
                near_target = abs(error) < GATE_RADIUS
                if near_target and direction == self.UP and self.syringe_est_mL > MAX_EXPAND_ML:
                    duty = 0
                    mode = "COAST"
                elif near_target and direction == self.DOWN and self.syringe_est_mL < -MAX_COMPRESS_ML:
                    duty = 0
                    mode = "COAST"
                else:
                    mode = "BRAKE"
            else:
                # DRIVE mode: fill only when too slow
                drive_vel_err = dir_sign * vel_err
                if drive_vel_err <= 0:
                    duty = 0
                    direction = self.DOWN if want_down else self.UP
                    mode = "COAST"
                else:
                    direction = self.DOWN if want_down else self.UP
                    going_wrong_way = (want_down and vel < -MIN_VEL) or (not want_down and vel > MIN_VEL)
                    # Syringe gate prevents worsening state near target
                    near_target = abs(error) < GATE_RADIUS
                    if near_target and direction == self.DOWN and self.syringe_est_mL < -MAX_COMPRESS_ML:
                        duty = 0
                        mode = "COAST"
                    elif near_target and direction == self.UP and self.syringe_est_mL > MAX_EXPAND_ML:
                        duty = 0
                        mode = "COAST"
                    else:
                        cap = MAX_DUTY if going_wrong_way else MAX_DRIVE_DUTY
                        duty = int(min(cap, max(MIN_DUTY, KP_VEL * drive_vel_err)))
                        mode = "DRIVE" if not going_wrong_way else "RECOVER"

            # Fill compensation: pressure opposes fill (DOWN only).
            # DRIVE/RECOVER: full offset (sustained fill needs to overcome stall).
            # BRAKE: stall-clearing minimum only (prevents over-compression).
            effective_duty = duty
            fill_offset = 0
            if direction == self.DOWN and duty > 0:
                stall_threshold = int(FILL_DUTY_PER_METER * depth)
                if mode in ("DRIVE", "RECOVER"):
                    fill_offset = stall_threshold
                else:  # BRAKE — just bridge the gap to stall
                    fill_offset = max(0, stall_threshold - duty)
                effective_duty = min(MAX_DUTY, duty + fill_offset)

            self._drive(direction, effective_duty)

            print(f"  go_to: depth={depth:.3f} err={error:+.3f} "
                  f"tvel={target_vel:+.3f} vel={vel:+.3f} sdist={K_STOP*abs_vel*abs_vel:.3f} "
                  f"duty={effective_duty}({duty}+{fill_offset}) {mode} syr={self.syringe_est_mL:+.1f}mL")

            elapsed = time.time() - start
            time.sleep(max(0, PULSE_ON - elapsed))
            self.motorController.set_speed(0)
            time.sleep(PULSE_OFF)

            # Syringe accounting: only credit volume if motor actually ran (above stall)
            if effective_duty > 0:
                stall_thr = int(FILL_DUTY_PER_METER * depth) if direction == self.DOWN else 0
                if effective_duty >= stall_thr:
                    rate_mL_s = (effective_duty / 100.0) * 10.1
                    delta = -(rate_mL_s * PULSE_ON) if direction == self.DOWN else (rate_mL_s * PULSE_ON)
                    self._update_syringe(delta)

    # ------------------------------------------------------------------
    # Hold at target depth
    # ------------------------------------------------------------------

    def depth_hold(self, target_depth: float, duration: float = 35.0, tolerance: float = 0.33, max_fill_ml: float = 15.0):
        """
        Hold at target_depth for `duration` seconds (wall-clock, always counting).

        PD control with coast-when-approaching logic:

          Coast rule: if error × vel > 0, the float is naturally moving toward
          target — motor off, let physics work.

          PD rule:  correction = Kd × (−vel) + Kp × error
            Kd (velocity term) damps residual motion immediately on arrival.
            Kp (position term) restores trim after slow drift.
          Positive correction → DOWN (CW, fill syringe, less buoyant)
          Negative correction → UP  (CCW, drain syringe, more buoyant)

          If |error| > tolerance: call go_to_target to re-acquire.
        """
        Kd        = 300    # velocity damping (reduced from 800 to prevent overshoot)
        Kp        = 20     # position restore (reduced from 50 to prevent oscillation)
        DEADBAND  = 10     # minimum correction threshold
        MAX_DUTY  = 65     # high enough for fill compensation to clear stall at 2.5m depth
        MIN_DUTY  = 10
        MIN_DEPTH = 0.10
        FILL_DUTY_PER_METER = 14.77  # fill compensation: 14.77% per meter depth

        # Credit time already spent in zone during go_to_target approach
        if self.hold_start_time is not None and self.hold_target == target_depth:
            already_in_zone = time.time() - self.hold_start_time
            print(f"  hold: crediting {already_in_zone:.1f}s already in zone")
        else:
            already_in_zone = 0.0
        hold_timer = already_in_zone
        self.hold_start_time = None
        self.hold_target = None

        while hold_timer < duration:
            t = time.time()
            depth, vel, _ = self._read()
            hold_timer += self.INTERVAL

            error = target_depth - depth

            # Surface safety: if too shallow, drive DOWN at full power
            # Skip when target IS the surface or far from target (transit, not overshoot)
            if depth < MIN_DEPTH and target_depth > MIN_DEPTH and abs(error) < 1.0:
                SURFACE_DUTY = 85
                self._drive(self.DOWN, SURFACE_DUTY)
                rate_mL_s = (SURFACE_DUTY / 100.0) * 10.1
                self._update_syringe(-(rate_mL_s * self.INTERVAL))
                print(f"  hold: SURFACE SAFETY depth={depth:.3f} < {MIN_DEPTH}m, driving DOWN {SURFACE_DUTY}% syr={self.syringe_est_mL:+.1f}mL")
                self._wait(t)
                continue

            if abs(error) > tolerance:
                print(f"  hold: DRIFT {error:+.3f}m outside ±{tolerance}m, re-acquiring")
                self.go_to_target(target_depth, hold_zone=tolerance)
                continue

            if error * vel > 0:
                # Float moving toward target naturally — coast
                self.motorController.set_speed(0)
                print(f"  hold: depth={depth:.3f} vel={vel:+.3f} COAST  ({hold_timer:.0f}/{duration:.0f}s)")
            else:
                # PD control: damp velocity and restore position
                correction = Kd * (-vel) + Kp * error
                if abs(correction) < DEADBAND:
                    self.motorController.set_speed(0)
                    print(f"  hold: depth={depth:.3f} vel={vel:+.3f} OK  ({hold_timer:.0f}/{duration:.0f}s)")
                else:
                    direction = self.DOWN if correction > 0 else self.UP
                    duty = int(min(MAX_DUTY, max(MIN_DUTY, abs(correction))))
                    effective_duty = duty
                    if direction == self.DOWN:
                        if self.syringe_est_mL < -max_fill_ml:
                            self.motorController.set_speed(0)
                            print(f"  hold: depth={depth:.3f} vel={vel:+.3f} FILL_CAP syr={self.syringe_est_mL:+.1f}mL")
                            self._wait(t)
                            continue
                        fill_offset = int(FILL_DUTY_PER_METER * depth)
                        effective_duty = min(MAX_DUTY, duty + fill_offset)
                    self._drive(direction, effective_duty)
                    # Syringe accounting: only credit if motor above stall threshold
                    stall_thr = int(FILL_DUTY_PER_METER * depth) if direction == self.DOWN else 0
                    if effective_duty >= stall_thr:
                        rate_mL_s = (effective_duty / 100.0) * 10.1
                        delta = -(rate_mL_s * self.INTERVAL) if direction == self.DOWN else (rate_mL_s * self.INTERVAL)
                        self._update_syringe(delta)
                    print(f"  hold: depth={depth:.3f} vel={vel:+.3f} err={error:+.3f} "
                          f"PD={correction:+.1f} {direction} {effective_duty}%({duty}+fill)  ({hold_timer:.0f}/{duration:.0f}s) syr={self.syringe_est_mL:+.1f}mL")

            self._wait(t)

        self.motorController.set_speed(0)
