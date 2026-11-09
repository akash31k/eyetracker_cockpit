"""
====================================================================
FILTER + TARGETS — Automated Test Suite
====================================================================
Run this script to:
  1. Measure filter noise reduction (before/after smoothing)
  2. Measure the actual added delay in milliseconds
  3. Test all target-detection edge cases with synthetic trajectories

Usage (Anaconda Prompt, tobii-env active):
  cd "C:\\Users\\akash\\.gemini\\antigravity\\scratch\\tobii-eye-spark-demo"
  python test_filter_targets.py

No hardware required — all tests use synthetic/simulated data.
====================================================================
"""

import math
import random
import time
import sys
import numpy as np

# ── Import our two new modules ─────────────────────────────────────
from filter  import GazeFilter, SMOOTH_WINDOW_N
from targets import TargetTracker, COCKPIT_TARGETS, HYSTERESIS_MARGIN_PX


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _pass(label: str):
    print(f"  [PASS]  {label}")

def _fail(label: str, detail: str = ""):
    print(f"  [FAIL]  {label}  {detail}")

def _section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

SAMPLE_RATE_HZ = 60.0
SCREEN_W = 1920
SCREEN_H = 1080


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 1 — FILTER: eye fusion rules
# ══════════════════════════════════════════════════════════════════
def test_fusion():
    _section("TEST 1 — Eye Fusion Rules")
    gf = GazeFilter(SCREEN_W, SCREEN_H, window=1)   # window=1 → no smoothing

    # Both valid → average
    r = gf.update((0.4, 0.5), True, (0.6, 0.5), True)
    expected_x = 0.5 * SCREEN_W
    if r is not None and abs(r[0] - expected_x) < 1:
        _pass("Both eyes valid → average")
    else:
        _fail("Both eyes valid → average", f"got {r}")

    # Left only valid
    gf._buf.clear()
    r = gf.update((0.3, 0.4), True, (float('nan'), float('nan')), False)
    if r is not None and abs(r[0] - 0.3 * SCREEN_W) < 1:
        _pass("Left only valid → use left")
    else:
        _fail("Left only valid → use left", f"got {r}")

    # Right only valid
    gf._buf.clear()
    r = gf.update((float('nan'), float('nan')), False, (0.7, 0.6), True)
    if r is not None and abs(r[0] - 0.7 * SCREEN_W) < 1:
        _pass("Right only valid → use right")
    else:
        _fail("Right only valid → use right", f"got {r}")

    # Both invalid → None
    gf._buf.clear()
    r = gf.update((float('nan'), float('nan')), False, (float('nan'), float('nan')), False)
    if r is None:
        _pass("Both invalid → None (blink)")
    else:
        _fail("Both invalid → None", f"got {r}")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 2 — FILTER: noise reduction
# Inject white noise at known amplitude, measure RMS before / after
# ══════════════════════════════════════════════════════════════════
def test_noise_reduction():
    _section("TEST 2 — Filter: Noise Reduction Measurement")

    NOISE_PX    = 15.0           # ± pixels of injected noise
    N_SAMPLES   = 300
    TRUE_X_NORM = 0.5
    TRUE_Y_NORM = 0.5
    gf = GazeFilter(SCREEN_W, SCREEN_H, window=SMOOTH_WINDOW_N)

    rng = random.Random(42)
    raw_errors, filtered_errors = [], []

    for _ in range(N_SAMPLES):
        noise_x = rng.gauss(0, NOISE_PX / SCREEN_W)
        noise_y = rng.gauss(0, NOISE_PX / SCREEN_H)
        lx = TRUE_X_NORM + noise_x
        ly = TRUE_Y_NORM + noise_y

        raw_errors.append(math.hypot(noise_x * SCREEN_W, noise_y * SCREEN_H))

        result = gf.update((lx, ly), True, (lx, ly), True)
        if result:
            fx, fy = result
            filtered_errors.append(math.hypot(fx - TRUE_X_NORM * SCREEN_W,
                                               fy - TRUE_Y_NORM * SCREEN_H))

    rms_raw      = math.sqrt(sum(e**2 for e in raw_errors)      / len(raw_errors))
    rms_filtered = math.sqrt(sum(e**2 for e in filtered_errors) / len(filtered_errors))
    reduction    = (1.0 - rms_filtered / rms_raw) * 100.0

    print(f"\n  Injected noise amplitude : ±{NOISE_PX:.0f} px")
    print(f"  Smoother window N        : {SMOOTH_WINDOW_N} samples")
    print(f"  RMS error BEFORE filter  : {rms_raw:.2f} px")
    print(f"  RMS error AFTER  filter  : {rms_filtered:.2f} px")
    print(f"  Noise reduction          : {reduction:.1f} %")
    print()

    if rms_filtered < rms_raw:
        _pass(f"Filter reduces noise by {reduction:.1f} %")
    else:
        _fail("Filter should reduce noise", f"before={rms_raw:.1f} after={rms_filtered:.1f}")

    # ── Write result for the report ────────────────────────────────
    print(f"\n  ★ Write in your report:")
    print(f"      Noise before filter: {rms_raw:.1f} px RMS")
    print(f"      Noise after  filter: {rms_filtered:.1f} px RMS")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 3 — FILTER: delay measurement
# Send a step (sudden jump) through the filter, measure how many
# samples until output reaches 90% of the final value
# ══════════════════════════════════════════════════════════════════
def test_filter_delay():
    _section("TEST 3 — Filter: Added Delay Measurement (Step Response)")

    gf = GazeFilter(SCREEN_W, SCREEN_H, window=SMOOTH_WINDOW_N)

    START_NORM = 0.3
    STEP_NORM  = 0.7
    THRESHOLD  = 0.9   # 90 % of step

    # Settle the filter with many samples at START position
    for _ in range(SMOOTH_WINDOW_N * 5):
        gf.update((START_NORM, 0.5), True, (START_NORM, 0.5), True)

    # Apply step, record how many samples to reach threshold
    start_x_px = START_NORM * SCREEN_W
    step_x_px  = STEP_NORM  * SCREEN_W
    amplitude  = step_x_px - start_x_px

    samples_to_90pct = None
    for i in range(1, 200):
        result = gf.update((STEP_NORM, 0.5), True, (STEP_NORM, 0.5), True)
        if result:
            reached = result[0] - start_x_px
            if reached >= THRESHOLD * amplitude:
                samples_to_90pct = i
                break

    theoretical_delay_ms = gf.theoretical_delay_ms

    if samples_to_90pct:
        measured_delay_ms = samples_to_90pct / SAMPLE_RATE_HZ * 1000.0
        print(f"\n  Window N                 : {SMOOTH_WINDOW_N} samples")
        print(f"  Theoretical delay        : {theoretical_delay_ms:.1f} ms  = (N-1)/2 / 60Hz")
        print(f"  Measured delay (90% step): {measured_delay_ms:.1f} ms  ({samples_to_90pct} samples)")
        print()
        _pass(f"Delay measured: {measured_delay_ms:.1f} ms")

        print(f"\n  ★ Write in your report:")
        print(f"      Filter window N      = {SMOOTH_WINDOW_N} samples")
        print(f"      Added delay          = {measured_delay_ms:.1f} ms (measured, 90% step response)")
        print(f"      Theoretical delay    = {theoretical_delay_ms:.1f} ms")
    else:
        _fail("Could not measure delay — step never reached 90%")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 4 — FILTER: behavior after a blink
# Buffer must be cleared; output must NOT return pre-blink position
# ══════════════════════════════════════════════════════════════════
def test_blink_recovery():
    _section("TEST 4 — Filter: Recovery After Blink")
    gf = GazeFilter(SCREEN_W, SCREEN_H, window=SMOOTH_WINDOW_N)

    # Pre-blink: looking at x=0.2
    for _ in range(SMOOTH_WINDOW_N * 3):
        gf.update((0.2, 0.5), True, (0.2, 0.5), True)

    # Blink (both invalid)
    for _ in range(6):
        r = gf.update((float('nan'), float('nan')), False, (float('nan'), float('nan')), False)
    if r is None:
        _pass("During blink → returns None")
    else:
        _fail("During blink → should return None", f"got {r}")

    # First sample after blink: looking at x=0.8 (moved during blink)
    r = gf.update((0.8, 0.5), True, (0.8, 0.5), True)
    if r is not None:
        post_x = r[0]
        # Should be near 0.8 * SCREEN_W, NOT pulled toward pre-blink 0.2
        if post_x > 0.6 * SCREEN_W:
            _pass(f"After blink buffer cleared → first sample at correct position ({post_x:.0f} px)")
        else:
            _fail("Buffer not cleared — post-blink position polluted by pre-blink data",
                  f"x={post_x:.0f} px (expected >{0.6*SCREEN_W:.0f})")
    else:
        _fail("After blink → first valid sample returned None")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 5 — TARGETS: basic entry/exit
# ══════════════════════════════════════════════════════════════════
def test_target_basic():
    _section("TEST 5 — Targets: Basic Entry and Exit")
    tracker = TargetTracker(COCKPIT_TARGETS)

    # Find PFD center
    pfd = next(t for t in COCKPIT_TARGETS if t.id == "PFD")
    cx, cy = pfd.center

    # Look at PFD
    t = tracker.update(cx, cy)
    if t and t.id == "PFD":
        _pass("Looking at PFD center → PFD active")
    else:
        _fail("Looking at PFD center", f"got {t}")

    # Look at background (middle of screen where there's no target)
    t = tracker.update(790, 550)   # centre of screen, between targets
    if t is None:
        _pass("Looking at background → None")
    else:
        _fail("Looking at background → should be None", f"got {t.id if t else t}")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 6 — TARGETS: hysteresis (edge between two targets)
# Gaze lands on the border. With hysteresis, the FIRST target entered
# should remain active, NOT jump to the adjacent one.
# ══════════════════════════════════════════════════════════════════
def test_target_hysteresis():
    _section("TEST 6 — Targets: Hysteresis (No Spurious Changes at Border)")
    tracker = TargetTracker(COCKPIT_TARGETS)

    # PFD right edge / NAV_DISPLAY left edge ≈ x=590, y=250
    # First gaze: clearly inside PFD
    pfd = next(t for t in COCKPIT_TARGETS if t.id == "PFD")
    nav = next(t for t in COCKPIT_TARGETS if t.id == "NAV_DISPLAY")

    t = tracker.update(pfd.x2 - 10, 250)   # 10 px inside PFD right edge
    if t and t.id == "PFD":
        _pass("Gaze enters PFD from inside")
    else:
        _fail("Gaze should enter PFD", f"got {t}")

    # Now slide gaze to PFD-NAV border (just outside PFD core but inside expanded)
    border_x = (pfd.x2 + nav.x1) / 2.0
    t = tracker.update(border_x, 250)
    if t and t.id == "PFD":
        _pass(f"Gaze at border ({border_x:.0f} px) → stays in PFD (hysteresis)")
    else:
        _fail(f"Gaze at border should stay in PFD (hysteresis margin={HYSTERESIS_MARGIN_PX}px)",
              f"got {t.id if t else None}")

    # Gaze jumps clearly into NAV_DISPLAY (past expanded zone)
    tracker.reset()
    t = tracker.update(nav.x1 + 20, 250)   # 20 px inside NAV core
    if t and t.id == "NAV_DISPLAY":
        _pass("Gaze clearly inside NAV_DISPLAY → NAV active")
    else:
        _fail("Gaze inside NAV should activate NAV", f"got {t}")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 7 — TARGETS: synthetic gaze trajectory with
# spurious-change count (the key metric from the spec)
# ══════════════════════════════════════════════════════════════════
def test_spurious_changes():
    _section("TEST 7 — Targets: Spurious Change Count (Edge Trajectory)")

    tracker = TargetTracker(COCKPIT_TARGETS)

    pfd = next(t for t in COCKPIT_TARGETS if t.id == "PFD")
    nav = next(t for t in COCKPIT_TARGETS if t.id == "NAV_DISPLAY")

    # Build a trajectory that hovers on the PFD/NAV border with noise
    # True intent: stay on PFD. Noise: ±30 px around PFD right edge
    rng      = random.Random(0)
    N        = 120   # 2 seconds at 60 Hz
    border   = pfd.x2
    noise_px = 30    # realistic gaze noise amplitude

    changes        = 0
    prev_id        = None
    for i in range(N):
        x = border + rng.gauss(0, noise_px)   # noisy gaze near border
        y = 250.0
        t = tracker.update(x, y)
        tid = t.id if t else None
        if tid != prev_id and prev_id is not None:
            changes += 1
        prev_id = tid

    print(f"\n  Trajectory: {N} samples, noisy hover at PFD/NAV border")
    print(f"  Noise amplitude: ±{noise_px} px,  Hysteresis margin: {HYSTERESIS_MARGIN_PX} px")
    print(f"  Target changes (spurious flips): {changes}")
    print()

    # Spec says "few spurious changes [to be set]" — flag if > 5
    ALLOWED_SPURIOUS = 5
    if changes <= ALLOWED_SPURIOUS:
        _pass(f"Spurious changes ({changes}) within allowed limit (≤ {ALLOWED_SPURIOUS})")
    else:
        _fail(f"Too many spurious changes ({changes} > {ALLOWED_SPURIOUS})",
              "Consider increasing HYSTERESIS_MARGIN_PX in targets.py")

    print(f"\n  ★ Write in your report:")
    print(f"      Spurious target changes on border trajectory = {changes}")
    print(f"      Hysteresis margin used = {HYSTERESIS_MARGIN_PX} px")


# ══════════════════════════════════════════════════════════════════
# TEST BLOCK 8 — TARGETS: action type check
# ══════════════════════════════════════════════════════════════════
def test_action_types():
    _section("TEST 8 — Targets: Action Types (Reversible vs Consequential)")
    tracker = TargetTracker(COCKPIT_TARGETS)

    # Find one of each type
    rev = next((t for t in COCKPIT_TARGETS if t.action_type == "reversible"),    None)
    con = next((t for t in COCKPIT_TARGETS if t.action_type == "consequential"), None)

    if rev:
        cx, cy = rev.center
        t = tracker.update(cx, cy)
        if t and t.action_type == "reversible":
            _pass(f"{rev.id} → action_type='reversible'")
        else:
            _fail(f"{rev.id} should be reversible", f"got {t}")
    else:
        print("  [SKIP] No reversible target defined")

    tracker.reset()

    if con:
        cx, cy = con.center
        t = tracker.update(cx, cy)
        if t and t.action_type == "consequential":
            _pass(f"{con.id} → action_type='consequential'")
        else:
            _fail(f"{con.id} should be consequential", f"got {t}")
    else:
        print("  [SKIP] No consequential target defined")


# ══════════════════════════════════════════════════════════════════
# MAIN — run all tests and print summary
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print()
    print("=" * 60)
    print("  TOBII COCKPIT -- filter.py + targets.py TEST SUITE")
    print("=" * 60)

    test_fusion()
    test_noise_reduction()
    test_filter_delay()
    test_blink_recovery()
    test_target_basic()
    test_target_hysteresis()
    test_spurious_changes()
    test_action_types()

    print("\n" + "=" * 60)
    print("  All tests done. Copy the [*] figures into your report.")
    print("  Adjust SMOOTH_WINDOW_N in filter.py and")
    print("  HYSTERESIS_MARGIN_PX in targets.py, then re-run.")
    print("=" * 60 + "\n")
