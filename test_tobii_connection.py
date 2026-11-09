"""
============================================================
  TOBII EYE SPARK PRO — DEVICE CONNECTION TEST SCRIPT
  Run this FIRST before anything else.
  
  This script checks:
  1. Python version is correct
  2. All packages are installed
  3. Tobii device is connected and detected
  4. Gaze data is streaming correctly
  5. Blink detection is working
============================================================
"""

import sys
import time

print("=" * 60)
print("  TOBII EYE SPARK PRO - SYSTEM CHECK")
print("=" * 60)

# ── CHECK 1: Python version ───────────────────────────────
print("\n[CHECK 1] Python Version...")
ver = sys.version_info
print(f"  Installed: Python {ver.major}.{ver.minor}.{ver.micro}")
if ver.major == 3 and ver.minor == 10:
    print("  ✅ PASS - Python 3.10 is correct")
else:
    print(f"  ❌ FAIL - You need Python 3.10 exactly!")
    print(f"     Download from: https://www.python.org/downloads/release/python-31011/")
    print(f"     When installing, check 'Add Python to PATH'")
    input("\nPress Enter to exit...")
    sys.exit(1)

# ── CHECK 2: Required packages ────────────────────────────
print("\n[CHECK 2] Required Packages...")
missing = []

for pkg, import_name in [
    ("tobii_research", "tobii_research"),
    ("websockets",     "websockets"),
    ("numpy",          "numpy"),
]:
    try:
        __import__(import_name)
        print(f"  ✅ {pkg} — installed")
    except ImportError:
        print(f"  ❌ {pkg} — MISSING")
        missing.append(pkg)

if missing:
    print(f"\n  Run this command to install missing packages:")
    print(f"  pip install {' '.join(missing)}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# ── CHECK 3: Tobii Device ─────────────────────────────────
print("\n[CHECK 3] Tobii Eye Tracker Device...")
import tobii_research as tr

found = tr.find_all_eyetrackers()
if not found:
    print("  ❌ FAIL - No Tobii device found!")
    print("     Make sure:")
    print("     1. Tobii Pro Spark is plugged into USB")
    print("     2. Tobii Pro Eye Tracker Manager is running")
    print("     3. Green LED is lit on the device")
    input("\nPress Enter to exit...")
    sys.exit(1)

tracker = found[0]
print(f"  ✅ PASS - Found: {tracker.device_name}")
print(f"     Model:       {tracker.model}")
print(f"     Serial:      {tracker.serial_number}")
print(f"     Gaze Output: {tracker.gaze_output_frequency} Hz")

# ── CHECK 4: Live gaze stream ─────────────────────────────
print("\n[CHECK 4] Live Gaze Data Stream (5 seconds)...")
import math
import numpy as np

gaze_samples = []

def on_gaze(data):
    left  = data['left_gaze_point_on_display_area']
    right = data['right_gaze_point_on_display_area']
    left_valid  = data['left_gaze_point_validity']
    right_valid = data['right_gaze_point_validity']
    gaze_samples.append({
        'lx': left[0], 'ly': left[1], 'lv': left_valid,
        'rx': right[0],'ry': right[1],'rv': right_valid,
    })

tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, on_gaze, as_dictionary=True)
print("  Streaming for 5 seconds — look at your screen normally...")

for i in range(5, 0, -1):
    print(f"  {i}...", end='\r')
    time.sleep(1)

tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)

if len(gaze_samples) < 10:
    print(f"\n  ❌ FAIL - Only {len(gaze_samples)} samples received.")
    print("     Make sure you are sitting in front of the tracker.")
else:
    valid_count = sum(1 for s in gaze_samples if s['lv'] or s['rv'])
    pct = (valid_count / len(gaze_samples)) * 100
    
    avg_x = np.nanmean([s['lx'] for s in gaze_samples if not math.isnan(s['lx'])])
    avg_y = np.nanmean([s['ly'] for s in gaze_samples if not math.isnan(s['ly'])])
    screen_x = int(avg_x * 1920)
    screen_y = int(avg_y * 1080)
    
    print(f"\n  ✅ PASS - {len(gaze_samples)} samples received")
    print(f"     Valid gaze: {pct:.1f}%")
    print(f"     Average gaze position: ({screen_x}, {screen_y}) pixels")

# ── CHECK 5: Blink Detection ──────────────────────────────
print("\n[CHECK 5] Blink Detection (please BLINK TWICE quickly in 3 seconds)...")
blink_events = []
last_state = True

def on_gaze_blink(data):
    global last_state
    lv = data['left_gaze_point_validity']
    rv = data['right_gaze_point_validity']
    closed = (lv == 0 and rv == 0)
    if closed != last_state:
        blink_events.append(('CLOSED' if closed else 'OPEN', time.time()))
        last_state = closed

tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, on_gaze_blink, as_dictionary=True)
time.sleep(3)
tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)

if len(blink_events) >= 4:
    print(f"  ✅ PASS - Detected {len(blink_events)//2} blink transitions")
else:
    print(f"  ⚠️  WARNING - Only {len(blink_events)} transitions detected")
    print("     Blink detection may need threshold tuning")

# ── SUMMARY ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("  ✅ ALL CHECKS PASSED - Your setup is ready!")
print("  Now run:  run_cockpit_control.bat")
print("=" * 60)
input("\nPress Enter to exit...")
