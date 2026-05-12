# DepthTarget Controller README

## OVERVIEW

This file defines the DepthTarget class. It controls a robotic float so it can:

1. Move to a specific depth in the water
2. Stop smoothly without overshooting
3. Hold that depth steadily for a set amount of time

The float changes depth by controlling a motor-driven syringe. The syringe changes buoyancy:

* Filling the syringe makes the float sink (less buoyant).
* Draining the syringe makes the float rise (more buoyant).

You can think of it like a small submarine ballast system.

## MAIN COMPONENTS

DepthTarget connects four major systems:

* PressureSensorData
  Provides current depth readings from the pressure sensor.

* VelocityCalculator
  Calculates how fast the float is moving up or down.

* AccelerationCalculator
  Calculates how quickly the velocity is changing.

* MotorController
  Drives the syringe motor using PWM (power percentage control).

The motor uses PWM (pulse width modulation), which means power is controlled as a percentage from 0 to 100.

## HIGH-LEVEL BEHAVIOR

The class provides three major behaviors:

1. go_to_target(depth)
2. depth_hold(target_depth, duration)
3. settle()

---

1. go_to_target(target_depth)

---

Purpose:
Move the float smoothly to a desired depth.

How it works (simple explanation):

Instead of running the motor at full power until the target is reached,
the controller:

1. Measures how far away the float is from the target.
2. Sets a target speed:

   * Far away from target -> move faster
   * Close to target -> move slower
3. If moving too fast -> brake.
4. If moving too slow -> drive.
5. If moving at the right speed -> coast (motor off).

This prevents overshoot and oscillation.

TANH VELOCITY PROFILE

The controller uses a tanh() curve to compute target velocity.

Effect:

* Far from target -> near maximum speed
* Closer to target -> gradually slows down
* Very close -> slows to near zero

This creates smooth arrivals instead of slamming to a stop.

PREDICTIVE STOPPING

The controller estimates stopping distance using:

```
stop_zone = k_stop * velocity^2
```

Meaning:

* The faster the float is moving,
* The earlier braking must begin.

This prevents the float from arriving too fast and overshooting.

PULSE-STYLE MOTOR CONTROL

The motor does not run continuously.

Instead:

* Motor ON for a short time (0.2 seconds)
* Motor OFF for a longer time (0.8 seconds)

Why?

The syringe stores buoyancy. If the motor runs too long, it over-compresses
or over-expands the syringe and causes rebound motion.

Short pulses:

* Limit volume change per cycle
* Allow the system to respond gradually
* Reduce oscillation

SAFETY SYSTEMS

There are two emergency protections:

1. Deep limit protection:
   If the float approaches a maximum depth (near 3 meters),
   it hard-brakes upward.

2. Surface protection:
   If the float gets too close to the surface (under 10 cm),
   it drives downward.

These prevent physical damage.

---

2. depth_hold(target_depth, duration)

---

Purpose:
Keep the float at a specific depth for a set amount of time.

This function uses a PD controller.

P (position term):
Corrects depth error.

D (velocity term):
Dampens motion if the float is moving too fast.

Rules used:

1. If the float is naturally drifting toward the target,
   the motor stays off (coast).

2. If slightly off target,
   apply gentle correction.

3. If too far from target,
   call go_to_target() to re-acquire depth.

This reduces motor chatter and keeps the float stable.

---

3. settle()

---

Purpose:
Return the syringe toward neutral buoyancy between movement legs.

Why this matters:

If the syringe remains partially compressed or expanded from a previous
movement, the next movement starts biased and unstable.

This function:

* Gently pumps toward neutral
* Waits until velocity is very small
* Stops when stable

This prevents cascading buoyancy errors.

## SYRINGE VOLUME ESTIMATOR

The class tracks an internal estimate:

```
syringe_est_mL
```

Meaning:

* Negative value -> compressed (sinking bias)
* Positive value -> expanded (rising bias)

This estimate is updated whenever the motor runs.

It helps:

* Prevent over-driving near the target
* Limit buoyancy swings
* Improve stability across multiple depth legs

It can be reset using:

```
calibrate_syringe()
```

Call this when the float is neutrally buoyant.

## HOW EVERYTHING WORKS TOGETHER

During movement:

1. Read depth.
2. Calculate velocity.
3. Compute desired velocity using tanh profile.
4. Compare actual velocity to desired velocity.
5. Decide to DRIVE, BRAKE, or COAST.
6. Run motor briefly (pulse).
7. Update syringe estimate.
8. Repeat until stable at target.

When at target:

1. Ensure depth is within tolerance.
2. Ensure velocity is near zero.
3. Wait several seconds to confirm stability.
4. Exit only when fully settled.

## WHY THIS CONTROLLER IS ROBUST

This design avoids common underwater float problems:

* Overshoot
* Oscillation
* Motor fighting buoyancy rebound
* Syringe over-accumulation
* Instability between legs

It achieves this using:

* Median filtering of depth readings
* Smoothed velocity estimation
* Predictive stopping physics
* Pulse-based actuation
* Buoyancy state tracking
* PD depth hold control
* Surface and deep safety limits

## TYPICAL USAGE FLOW

Example:

controller = DepthTarget(sensor_data, up="CCW", down="CW")

controller.calibrate_syringe()

controller.go_to_target(2.5)
controller.depth_hold(2.5, duration=35)

controller.go_to_target(0.0)

## SUMMARY

DepthTarget is the vertical motion controller for the float.

It:

* Moves smoothly to depth targets
* Stops gently
* Holds steady
* Prevents overshoot
* Protects against unsafe depths
* Maintains buoyancy balance across mission legs

Without this controller, the float would overshoot, oscillate,
and become unstable over time.
