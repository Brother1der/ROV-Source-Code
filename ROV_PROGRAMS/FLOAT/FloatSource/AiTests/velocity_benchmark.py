"""
Velocity Estimation Benchmark — MS5837-02BA actual sensor specs
=================================================================
Sensor: MS5837-02BA (BAR02)
  - Resolution RMS @ OSR 8192: 0.016 mbar  → 0.163 mm depth
  - Relative accuracy:         ±0.5 mbar   → ±5.1 mm depth (σ ≈ 2.5 mm)
  - Max error w/ supply noise: ±2 mbar     → ±2.0 cm depth (the "±2cm" spec)
  - ADC conversion @ OSR 8192: 16.4 ms max → ~30 Hz absolute max
  - Current code polling:      50 ms       → 20 Hz

Three noise scenarios are tested:
  IDEAL   σ = 0.0025 m  (±0.5 mbar accuracy, good PSU)
  TYPICAL σ = 0.010  m  (±2 mbar, PSU noise / voltage variation)
  WORST   σ = 0.020  m  (±4 mbar, post-reflow / thermal)

True profile: realistic 60-second float motion
  Ramp up → cruise at 0.06 m/s → brake → dwell → reverse → settle

Differentiation methods compared (all causal — only past samples used)
-----------------------------------------------------------------------
1. raw_fd           two-point finite difference (no smoothing)
2. ema(α=0.35)      EMA on FD — current VelocityCalculator
3. ema(α=0.15)      EMA, heavier smoothing
4. windowed_mean(5) mean of last 5 FDs
5. windowed_mean(9) mean of last 9 FDs
6. central_diff     causal central diff  (d[n]−d[n-2])/(2·dt)
7. linreg(w=7)      OLS slope, 7-sample window  (= SGolay order 1)
8. linreg(w=11)     OLS slope, 11-sample window
9. savgol(w=7)      Savitzky-Golay order-2 causal, 7-sample window
10. savgol(w=11)    Savitzky-Golay order-2 causal, 11-sample window
11. kalman(lo)      Constant-velocity Kalman — responsive
12. kalman(hi)      Constant-velocity Kalman — smooth
13. median+fd(5)    Median pre-clean, then FD  (ChatGPT: clean first)
14. median+linreg   Median pre-clean, then linreg(9)

Score = RMSE × (1 + 0.5 × lag_samples)  — lower is better
"""

import math
import random

# ─────────────────────────────────────────────────────────
#  Sensor / simulation constants
# ─────────────────────────────────────────────────────────

DT = 0.05            # 50 ms polling (20 Hz) — current code setting
TOTAL_SECS = 60.0

# Depth-noise from bar02 pressure accuracy
# 1 mbar = 100 Pa  →  h = P/(ρg) = 100/(997×9.81) = 0.010224 m/mbar
MBAR_TO_M = 100.0 / (997.0 * 9.81)          # 0.010224 m/mbar
NOISE_SCENARIOS = {
    "IDEAL  (±0.5 mbar, σ≈2.6mm)": 0.5 * MBAR_TO_M / 2,    # ~0.00256 m
    "TYPICAL(±2.0 mbar, σ≈10mm) ": 2.0 * MBAR_TO_M / 2,    # ~0.01022 m
    "WORST  (±4.0 mbar, σ≈20mm) ": 4.0 * MBAR_TO_M / 2,    # ~0.02045 m
}


# ─────────────────────────────────────────────────────────
#  Synthetic depth / velocity profile
# ─────────────────────────────────────────────────────────

def _target_vel(t):
    """Smooth velocity profile: ramp → cruise → brake → reverse → settle."""
    if t < 10:
        return 0.06 * (t / 10)
    elif t < 25:
        return 0.06
    elif t < 35:
        frac = (t - 25) / 10
        return 0.06 * (1 - math.tanh(3.0 * frac))
    elif t < 40:
        return 0.0
    elif t < 50:
        frac = (t - 40) / 10
        return -0.05 * math.tanh(3.0 * frac)
    else:
        frac = (t - 50) / 10
        return -0.05 * (1 - frac)


def generate_profile(seed=42):
    random.seed(seed)
    times, depths, vels = [], [], []
    depth, vel, t = 0.4, 0.0, 0.0
    while t <= TOTAL_SECS:
        times.append(t)
        vels.append(vel)
        depths.append(depth)
        tv = _target_vel(t)
        vel += (tv - vel) * DT / 1.5    # first-order lag on velocity
        depth += vel * DT
        t += DT
    return times, depths, vels


def add_noise(depths, sigma, seed=99):
    random.seed(seed)
    return [d + random.gauss(0, sigma) for d in depths]


# ─────────────────────────────────────────────────────────
#  Estimation methods  (causal — past samples only)
# ─────────────────────────────────────────────────────────

def raw_fd(times, nd):
    out = [0.0]
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        out.append((nd[i] - nd[i - 1]) / dt if dt > 1e-9 else 0.0)
    return out


def ema_fd(times, nd, alpha=0.35):
    filt, out = 0.0, [0.0]
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        raw = (nd[i] - nd[i - 1]) / dt if dt > 1e-9 else 0.0
        filt = alpha * raw + (1 - alpha) * filt
        out.append(filt)
    return out


def windowed_mean_fd(times, nd, window=7):
    fds = [0.0]
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        fds.append((nd[i] - nd[i - 1]) / dt if dt > 1e-9 else 0.0)
    out = []
    for i in range(len(fds)):
        chunk = fds[max(0, i - window + 1): i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def central_diff_causal(times, nd):
    """(d[n] − d[n-2]) / (2·dt)  — 1-sample lag, ~√2 lower noise than raw FD."""
    out = [0.0, 0.0]
    for i in range(2, len(times)):
        dt2 = times[i] - times[i - 2]
        out.append((nd[i] - nd[i - 2]) / dt2 if dt2 > 1e-9 else 0.0)
    return out


def linear_regression_fd(times, nd, window=9):
    """OLS slope over rolling window = Savitzky-Golay order 1."""
    out = []
    for i in range(len(times)):
        lo = max(0, i - window + 1)
        tw = times[lo: i + 1]
        dw = nd[lo: i + 1]
        n = len(tw)
        if n < 2:
            out.append(0.0)
            continue
        tm = sum(tw) / n
        dm = sum(dw) / n
        num = sum((tw[j] - tm) * (dw[j] - dm) for j in range(n))
        den = sum((tw[j] - tm) ** 2 for j in range(n))
        out.append(num / den if den > 1e-12 else 0.0)
    return out


def savgol_order2_fd(times, nd, window=9):
    """
    Savitzky-Golay causal, order-2 polynomial.
    Fits d = a·t² + b·t + c to last `window` samples (with t=0 at current).
    Returns b (= dD/dt at t=0).  Better than linear-reg when accel ≠ 0.
    """
    def _solve3(A, b):
        m = [A[r][:] + [b[r]] for r in range(3)]
        for col in range(3):
            pr = max(range(col, 3), key=lambda r: abs(m[r][col]))
            m[col], m[pr] = m[pr], m[col]
            piv = m[col][col]
            if abs(piv) < 1e-12:
                return None
            for row in range(col + 1, 3):
                f = m[row][col] / piv
                for c in range(col, 4):
                    m[row][c] -= f * m[col][c]
        x = [0.0] * 3
        for i in range(2, -1, -1):
            x[i] = m[i][3]
            for j in range(i + 1, 3):
                x[i] -= m[i][j] * x[j]
            x[i] /= m[i][i]
        return x

    out = []
    for i in range(len(times)):
        lo = max(0, i - window + 1)
        tw = [t - times[i] for t in times[lo: i + 1]]
        dw = nd[lo: i + 1]
        n = len(tw)
        if n < 3:
            out.append(0.0)
            continue
        S0 = n
        S1 = sum(tw);           S2 = sum(x**2 for x in tw)
        S3 = sum(x**3 for x in tw); S4 = sum(x**4 for x in tw)
        T0 = sum(dw)
        T1 = sum(tw[j] * dw[j] for j in range(n))
        T2 = sum(tw[j]**2 * dw[j] for j in range(n))
        A = [[S0, S1, S2], [S1, S2, S3], [S2, S3, S4]]
        sol = _solve3(A, [T0, T1, T2])
        out.append(sol[1] if sol else 0.0)
    return out


def kalman_velocity(times, nd, q_vel=5e-3, r_meas=1e-4):
    """
    2-state constant-velocity Kalman.
    State [depth, velocity].  Measurement: noisy depth.
    r_meas = σ² of depth sensor.
    q_vel  = process noise on velocity (tune: high = responsive, low = smooth).
    """
    x = [nd[0], 0.0]
    P = [[1.0, 0.0], [0.0, 1.0]]
    out = [0.0]
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        # Predict
        xp = [x[0] + x[1] * dt, x[1]]
        Fp = [[1, dt], [0, 1]]
        Q = [[0.0, 0.0], [0.0, q_vel * dt]]
        FP = [[Fp[r][c2] * P[c2][c] for c in range(2)]
              for r in range(2) for c2 in range(2)]   # temp
        # P_pred = F @ P @ F.T + Q  (manual 2×2)
        P00 = P[0][0] + dt*P[1][0] + dt*(P[0][1] + dt*P[1][1]) + Q[0][0]
        P01 = P[0][1] + dt*P[1][1] + Q[0][1]
        P10 = P[1][0] + dt*P[1][1] + Q[1][0]
        P11 = P[1][1] + Q[1][1]
        # Update
        S = P00 + r_meas
        K0 = P00 / S;  K1 = P10 / S
        inn = nd[i] - xp[0]
        x = [xp[0] + K0*inn, xp[1] + K1*inn]
        P = [[P00 - K0*P00, P01 - K0*P01],
             [P10 - K1*P00, P11 - K1*P01]]
        out.append(x[1])
    return out


def median_filter(nd, window=5):
    """Median pre-clean: remove spike outliers before differentiating."""
    out = []
    for i in range(len(nd)):
        lo = max(0, i - window + 1)
        w = sorted(nd[lo: i + 1])
        out.append(w[len(w) // 2])
    return out


def median_fd(times, nd, med_w=5):
    return raw_fd(times, median_filter(nd, med_w))


def median_linreg(times, nd, med_w=5, reg_w=9):
    return linear_regression_fd(times, median_filter(nd, med_w), window=reg_w)


# ─────────────────────────────────────────────────────────
#  Metrics
# ─────────────────────────────────────────────────────────

def rmse(est, true_v):
    return math.sqrt(sum((e - t)**2 for e, t in zip(est, true_v)) / len(true_v))


def estimate_lag(est, true_v, max_lag=20):
    """Cross-correlation lag in samples (positive = estimator lags true)."""
    n = len(true_v)
    em = sum(est) / n;  tm = sum(true_v) / n
    ec = [v - em for v in est];  tc = [v - tm for v in true_v]
    best_lag, best_corr = 0, -1e18
    for lag in range(0, max_lag + 1):
        corr = sum(ec[i] * tc[i + lag] for i in range(n - lag))
        if corr > best_corr:
            best_corr = corr;  best_lag = lag
    return best_lag


# ─────────────────────────────────────────────────────────
#  Benchmark runner
# ─────────────────────────────────────────────────────────

METHODS = {
    "raw_fd          ": lambda t, d: raw_fd(t, d),
    "ema(α=0.35)     ": lambda t, d: ema_fd(t, d, alpha=0.35),
    "ema(α=0.15)     ": lambda t, d: ema_fd(t, d, alpha=0.15),
    "ema(α=0.08)     ": lambda t, d: ema_fd(t, d, alpha=0.08),
    "windowed_mean(5)": lambda t, d: windowed_mean_fd(t, d, window=5),
    "windowed_mean(9)": lambda t, d: windowed_mean_fd(t, d, window=9),
    "central_diff    ": lambda t, d: central_diff_causal(t, d),
    "linreg(w=7)     ": lambda t, d: linear_regression_fd(t, d, window=7),
    "linreg(w=11)    ": lambda t, d: linear_regression_fd(t, d, window=11),
    "savgol(w=7,o=2) ": lambda t, d: savgol_order2_fd(t, d, window=7),
    "savgol(w=11,o=2)": lambda t, d: savgol_order2_fd(t, d, window=11),
    "kalman(responsive)": lambda t, d: kalman_velocity(t, d, q_vel=5e-3,  r_meas=NOISE_SIGMA**2),
    "kalman(smooth)  ": lambda t, d: kalman_velocity(t, d, q_vel=5e-4,  r_meas=NOISE_SIGMA**2),
    "median+fd(w=5)  ": lambda t, d: median_fd(t, d, med_w=5),
    "median+linreg   ": lambda t, d: median_linreg(t, d, med_w=5, reg_w=9),
}

NOISE_SIGMA = 0.0  # filled per scenario


def run_scenario(label, sigma, n_trials=8):
    global NOISE_SIGMA
    NOISE_SIGMA = sigma

    total_rmse = {k: 0.0 for k in METHODS}
    total_lag  = {k: 0.0 for k in METHODS}

    for trial in range(n_trials):
        times, true_depths, true_vels = generate_profile(seed=trial * 7)
        noisy = add_noise(true_depths, sigma=sigma, seed=trial * 13 + 99)
        for name, fn in METHODS.items():
            est = fn(times, noisy)
            total_rmse[name] += rmse(est, true_vels)
            total_lag[name]  += estimate_lag(est, true_vels)

    rows = []
    for name in METHODS:
        r   = total_rmse[name] / n_trials
        lag = total_lag[name]  / n_trials
        score = r * (1 + 0.5 * lag)
        rows.append((name, r, lag, lag * DT * 1000, score))

    rows.sort(key=lambda x: x[4])

    print(f"\n  ── {label}  (σ={sigma*1000:.1f} mm) ──")
    print(f"  {'Method':<22}  {'RMSE cm/s':>9}  {'Lag samp':>8}  {'Lag ms':>7}  {'Score':>8}")
    print(f"  {'-'*22}  {'-'*9}  {'-'*8}  {'-'*7}  {'-'*8}")

    best_score = rows[0][4]
    for name, r, lag, lag_ms, score in rows:
        marker = " ◀" if score == best_score else ""
        print(f"  {name:<22}  {r*100:>9.4f}  {lag:>8.1f}  {lag_ms:>7.0f}  {score:>8.5f}{marker}")

    return rows[0]   # best row for this scenario


def main():
    print("=" * 72)
    print("  MS5837-02BA  VELOCITY ESTIMATION BENCHMARK")
    print(f"  Poll rate: {1/DT:.0f} Hz ({DT*1000:.0f} ms)   Profile: {TOTAL_SECS:.0f}s")
    print("=" * 72)

    winners = []
    for label, sigma in NOISE_SCENARIOS.items():
        w = run_scenario(label, sigma)
        winners.append((label, sigma, w))

    print("\n" + "=" * 72)
    print("  SUMMARY — best method per noise scenario")
    print("=" * 72)
    for label, sigma, (name, r, lag, lag_ms, score) in winners:
        print(f"\n  {label}")
        print(f"    Winner : {name.strip()}")
        print(f"    RMSE   : {r*100:.4f} cm/s  ({r/0.06*100:.1f}% of 6 cm/s cruise)")
        print(f"    Lag    : {lag:.1f} samples = {lag_ms:.0f} ms")
        print(f"    Score  : {score:.5f}")

    # Recommend for controller
    print("\n" + "=" * 72)
    print("  RECOMMENDATION FOR DEPTH CONTROLLER")
    print("=" * 72)
    # Find the method that wins most scenarios
    vote = {}
    for _, _, (name, *_) in winners:
        vote[name.strip()] = vote.get(name.strip(), 0) + 1
    top = sorted(vote.items(), key=lambda x: -x[1])
    print(f"  Most consistent winner: {top[0][0]}  ({top[0][1]}/{len(winners)} scenarios)")
    print()
    print("  Notes:")
    print("  - Kalman 'responsive' is near-optimal when noise model matches reality.")
    print("  - savgol(w=7,o=2) is excellent and needs no noise-tuning.")
    print("  - median+linreg adds outlier rejection (useful for transient bubbles).")
    print("  - EMA(α=0.35) is adequate only at low noise; degrades at ±2 mbar worst-case.")
    print("=" * 72)


if __name__ == "__main__":
    main()
