"""
====================================================================
TOBII EYE SPARK PRO — COCKPIT GAZE & DOUBLE-BLINK CONTROLLER
====================================================================
Based on TU Darmstadt ADP Eye Tracking Architecture

What this script does:
1. Connects to Tobii Pro Spark via Tobii Pro SDK (tobiiresearch)
2. Normalizes gaze coordinates to your screen resolution (1920x1080)
3. Smooths gaze using rolling average (from record_Data.py)
4. Detects eye blinks (using validity/NaN from calibration_image.py)
5. Detects intentional DOUBLE-BLINKS to trigger cockpit selections
6. Broadcasts real-time events over WebSocket to cockpit.html
====================================================================
"""

import os
import sys
import time
import math
import json
import asyncio
import datetime
import collections
import numpy as np

# WebSocket library for real-time browser communication
try:
    import websockets
except ImportError:
    print("[ERROR] 'websockets' package missing. Install via: pip install websockets")
    sys.exit(1)

# Tobii Research SDK
try:
    import tobii_research as tr
except ImportError:
    print("[WARNING] 'tobiiresearch' package not found!")
    print("If you are testing without the physical hardware, simulated mode will be enabled.")
    tr = None

# Screen resolution (matches previous ADP constants.py)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

# Output data directory for saved sessions
DATA_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recorded_sessions")
os.makedirs(DATA_OUTPUT_DIR, exist_ok=True)

# ------------------------------------------------------------------
# 1. DOUBLE-BLINK DETECTION STATE MACHINE
# ------------------------------------------------------------------
class DoubleBlinkDetector:
    """
    Detects voluntary double-blinks while ignoring natural micro-blinks
    and prolonged eye closures.
    
    A natural voluntary double-blink pattern:
    - Blink 1: closed for 80 - 350 ms
    - Gap between blinks: eyes open for 80 - 400 ms
    - Blink 2: closed for 80 - 350 ms
    - Complete: reopen within timeout -> TRIGGER!
    """
    def __init__(self):
        self.state = "OPEN"
        self.last_change_time = time.time()
        self.blink_count = 0
        self.last_blink_end_time = 0

    def update(self, both_eyes_closed: bool) -> bool:
        now = time.time()
        elapsed_ms = (now - self.last_change_time) * 1000

        # Reset if too much time passed since the first blink
        if self.blink_count == 1 and self.state == "OPEN":
            if (now - self.last_blink_end_time) * 1000 > 450:
                self.blink_count = 0

        if self.state == "OPEN":
            if both_eyes_closed:
                # Started closing eyes
                self.state = "CLOSED"
                self.last_change_time = now

        elif self.state == "CLOSED":
            if not both_eyes_closed:
                # Eyes reopened
                self.state = "OPEN"
                self.last_change_time = now
                
                # Check if this was a clean blink duration (80ms - 350ms)
                if 80 <= elapsed_ms <= 380:
                    self.blink_count += 1
                    self.last_blink_end_time = now
                    
                    if self.blink_count == 2:
                        # Double blink detected!
                        self.blink_count = 0
                        return True
                else:
                    # Too short (flicker) or too long (looking down/sleeping)
                    self.blink_count = 0

        return False

# ------------------------------------------------------------------
# 2. TOBII CONTROLLER CLASS
# ------------------------------------------------------------------
class TobiiCockpitController:
    def __init__(self):
        self.tracker = None
        self.double_blink_detector = DoubleBlinkDetector()
        
        # 5-sample smoothing buffer (from ADP record_Data.py)
        self.gaze_buffer = collections.deque(maxlen=5)
        
        # Current state
        self.current_x = SCREEN_WIDTH // 2
        self.current_y = SCREEN_HEIGHT // 2
        self.both_eyes_closed = False
        self.last_double_blink = False
        
        # Connected web clients (the cockpit browser tabs)
        self.connected_clients = set()

        # Session Recording for comparison (exact ADP format: X, Y, Timestamp, PupilSize)
        self.start_time = time.time()
        self.recorded_data = []
        self.session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_folder = os.path.join(DATA_OUTPUT_DIR, f"session_{self.session_timestamp}")
        os.makedirs(self.session_folder, exist_ok=True)
        print(f"[RECORDER] Session logs will be saved to:\n  -> {self.session_folder}")

    def connect_device(self):
        if tr is None:
            print("[INFO] Running in SIMULATION mode (Mouse simulation).")
            return False

        print("[INFO] Searching for Tobii eye trackers...")
        found = tr.find_all_eyetrackers()
        if not found:
            print("[WARNING] No Tobii eye tracker found! Plug in your Tobii Spark Pro.")
            print("[INFO] Falling back to simulation mode.")
            return False

        self.tracker = found[0]
        print(f"[SUCCESS] Connected to: {self.tracker.device_name} (Model: {self.tracker.model})")
        print(f"[SUCCESS] Serial: {self.tracker.serial_number}")

        # Subscribe to real-time gaze stream
        self.tracker.subscribe_to(tr.EYETRACKER_GAZE_DATA, self._on_gaze_data, as_dictionary=True)
        return True

    def _on_gaze_data(self, gaze_sample):
        """Callback executed by Tobii SDK at 60 Hz"""
        left_validity = gaze_sample['left_gaze_point_validity']
        right_validity = gaze_sample['right_gaze_point_validity']

        left_pt = gaze_sample['left_gaze_point_on_display_area']
        right_pt = gaze_sample['right_gaze_point_on_display_area']

        # Eye closure check (as in ADP calibration_image.py)
        left_closed = (left_validity == 0) or math.isnan(left_pt[0]) or math.isnan(left_pt[1])
        right_closed = (right_validity == 0) or math.isnan(right_pt[0]) or math.isnan(right_pt[1])
        
        self.both_eyes_closed = left_closed and right_closed

        # Check for double blink
        if self.double_blink_detector.update(self.both_eyes_closed):
            self.last_double_blink = True
            print("[ACTION] *** DOUBLE BLINK DETECTED! ***")

        # Average gaze point of valid eyes
        points = []
        if not left_closed:
            points.append(left_pt)
        if not right_closed:
            points.append(right_pt)

        if points:
            norm_x = np.mean([p[0] for p in points])
            norm_y = np.mean([p[1] for p in points])
            
            # Convert normalized [0..1] to screen pixels [1920x1080]
            pixel_x = int(norm_x * SCREEN_WIDTH)
            pixel_y = int(norm_y * SCREEN_HEIGHT)

            self.gaze_buffer.append((pixel_x, pixel_y))

            # Apply 5-sample smoothing (ADP evaluate_video.py logic)
            self.current_x = int(np.mean([p[0] for p in self.gaze_buffer]))
            self.current_y = int(np.mean([p[1] for p in self.gaze_buffer]))

            # Extract pupil diameter
            pupil_samples = []
            if gaze_sample.get('left_pupil_validity') and not math.isnan(gaze_sample.get('left_pupil_diameter', float('nan'))):
                pupil_samples.append(gaze_sample['left_pupil_diameter'])
            if gaze_sample.get('right_pupil_validity') and not math.isnan(gaze_sample.get('right_pupil_diameter', float('nan'))):
                pupil_samples.append(gaze_sample['right_pupil_diameter'])
            avg_pupil = float(np.mean(pupil_samples)) if pupil_samples else 3.0

            # Record sample in exact ADP data.txt format: [X, Y, Timestamp, PupilSize]
            rel_time = time.time() - self.start_time
            self.recorded_data.append([float(self.current_x), float(self.current_y), round(rel_time, 4), round(avg_pupil, 2)])

    async def broadcast_loop(self):
        """Pushes gaze state to all connected browser clients 60 times/sec"""
        while True:
            if self.connected_clients:
                payload = json.dumps({
                    "x": self.current_x,
                    "y": self.current_y,
                    "eyes_closed": self.both_eyes_closed,
                    "double_blink": self.last_double_blink,
                    "hardware_connected": self.tracker is not None
                })
                # Reset double-blink trigger flag after sending
                if self.last_double_blink:
                    self.last_double_blink = False

                # Broadcast to web browser
                disconnected = set()
                for client in self.connected_clients:
                    try:
                        await client.send(payload)
                    except:
                        disconnected.add(client)
                self.connected_clients -= disconnected

            await asyncio.sleep(1 / 60.0) # 60 Hz matching Tobii Spark

    async def ws_handler(self, websocket):
        print(f"[WS] Cockpit HUD connected! ({websocket.remote_address})")
        self.connected_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.connected_clients.remove(websocket)
            print(f"[WS] Cockpit HUD disconnected.")

    def close(self):
        if self.tracker:
            try:
                self.tracker.unsubscribe_from(tr.EYETRACKER_GAZE_DATA)
                print("[INFO] Eye tracker stream closed.")
            except Exception as e:
                print(f"[WARNING] Error closing stream: {e}")

        # Save session data.txt
        if self.recorded_data:
            out_file = os.path.join(self.session_folder, "data.txt")
            np.savetxt(out_file, np.array(self.recorded_data), fmt="%.1f %.1f %.4f %.2f")
            print("\n" + "=" * 60)
            print(f"[SUCCESS] Recorded {len(self.recorded_data)} gaze points!")
            print(f"[SAVED] data.txt created at:")
            print(f"  -> {out_file}")
            
            # Also save as latest_session for easy access
            latest_dir = os.path.join(DATA_OUTPUT_DIR, "latest_session")
            os.makedirs(latest_dir, exist_ok=True)
            np.savetxt(os.path.join(latest_dir, "data.txt"), np.array(self.recorded_data), fmt="%.1f %.1f %.4f %.2f")
            print(f"  -> Also copied to: {os.path.join(latest_dir, 'data.txt')}")
            print("=" * 60 + "\n")
        else:
            print("[INFO] No gaze data recorded during this session.")

# ------------------------------------------------------------------
# 3. MAIN RUNNER
# ------------------------------------------------------------------
async def main():
    print("=" * 60)
    print(" TOBII EYE SPARK PRO — COCKPIT INTERACTION BRIDGE")
    print("=" * 60)
    
    controller = TobiiCockpitController()
    controller.connect_device()

    # Start WebSocket server on localhost:8765
    server = await websockets.serve(controller.ws_handler, "localhost", 8765)
    print("[SUCCESS] Local Bridge Server active at: ws://localhost:8765")
    print("[READY] Open 'cockpit.html' in your browser to begin.")
    print("=" * 60)

    try:
        await controller.broadcast_loop()
    except asyncio.CancelledError:
        pass
    finally:
        controller.close()
        server.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOP] Controller stopped by user.")
