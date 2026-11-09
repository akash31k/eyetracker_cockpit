# Tobii Eye Spark Pro — Cockpit Gaze & Interaction System

Real-time gaze tracking and double-blink cockpit HUD controller developed for the ADP Eye Tracking project.

---

## 🚀 How to Set Up & Run on a New Computer

### Step 1: Install Prerequisites (One-time setup)
1. **Tobii Pro Eye Tracker Manager**:
   - Download & install from Tobii's official site: https://www.tobii.com/products/software/applications/eye-tracker-manager
   - Plug in your **Tobii Pro Spark** via USB and complete the calibration.
2. **Miniconda / Python 3.10**:
   - Install Miniconda for Windows: https://docs.conda.io/en/latest/miniconda.html
   - Open **Anaconda Prompt** and run:
     ```bash
     conda create -n tobii-env python=3.10 -y
     conda activate tobii-env
     pip install tobii_research websockets numpy
     ```
   *(Note: Python 3.10 is required because `tobii_research` has prebuilt wheels for Python 3.10 on Windows).*

---

### Step 2: Test the Connection
- Double-click **`test_tobii_connection.bat`**
- It will verify that your Tobii Pro Spark is detected and streaming gaze data.

---

### Step 3: Run the Cockpit System
- Double-click **`run_cockpit_control.bat`**
- This will:
  1. Activate the `tobii-env` environment.
  2. Launch **`cockpit.html`** in your default web browser.
  3. Start the Python bridge (`tobii_cockpit_controller.py`) which streams gaze & double-blink signals at 60 Hz.
  4. Automatically record session gaze data into `recorded_sessions/`.

---

### Step 4: Run the Filter & Target Tests
- Double-click **`run_tests.bat`**
- Runs the 8 automated tests measuring noise reduction, added delay, and border hysteresis.

---

## 📁 Key Project Files

| File | Description |
|---|---|
| `cockpit.html` | Interactive browser-based cockpit HUD |
| `tobii_cockpit_controller.py` | Python SDK bridge, 60 Hz WebSocket server, session logger |
| `filter.py` | Eye fusion and causal smoothing filter with known delay |
| `targets.py` | Cockpit AOI definition with hysteresis to prevent border flickering |
| `test_filter_targets.py` | 8-test validation suite for filter and targets |
| `run_cockpit_control.bat` | 1-click launcher for the entire cockpit system |
| `run_tests.bat` | 1-click test runner |
| `test_tobii_connection.bat` | Fast hardware connection diagnostic |
| `recorded_sessions/` | Folder where recorded gaze sessions (`data.txt`) are stored |
