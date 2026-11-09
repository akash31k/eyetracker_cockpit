"""
====================================================================
FILTER MODULE — Eye Fusion + Causal Smoothing
====================================================================
Specification:
  - Both eyes valid  → average their positions
  - Only one valid   → use that one
  - Neither valid    → return None (invalid sample / blink)
  - Causal smoothing → rolling weighted average; delay is KNOWN
                       and measured in filter_test.py

Tuning parameter:
  SMOOTH_WINDOW_N  (default 5 samples at 60 Hz ≈ 83 ms delay)

What "causal" means here:
  We only use PAST samples (never future ones), so the filter
  can run in real-time. The price is a lag: the larger the window,
  the smoother but slower the output.

After a blink:
  The buffer is CLEARED when both eyes are invalid, so when the
  eyes reopen the filter starts fresh — no ghost position from
  before the blink leaks into the new estimate.
====================================================================
"""

import math
import collections
import numpy as np


# ──────────────────────────────────────────────────────────────────
# TUNING PARAMETER  ← change this to trade latency for smoothness
# At 60 Hz: N=1 → 0 ms lag (raw), N=5 → ~67 ms, N=9 → ~133 ms
# Measure the actual delay with filter_test.py and write it here:
#   Measured delay = _______ ms   (fill in after running the test)
SMOOTH_WINDOW_N = 5
# ──────────────────────────────────────────────────────────────────


class GazeFilter:
    """
    Fuses both eyes and applies a causal rolling-average smoother.

    Usage (at 60 Hz, inside the Tobii callback):
        gf = GazeFilter()
        ...
        result = gf.update(left_pt, left_valid, right_pt, right_valid)
        if result is not None:
            x, y = result   # smoothed screen-space pixel coords
    """

    def __init__(self, screen_w: int = 1920, screen_h: int = 1080,
                 window: int = SMOOTH_WINDOW_N):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.window   = window

        # Circular buffer — holds (norm_x, norm_y) for valid samples
        self._buf: collections.deque = collections.deque(maxlen=window)

        # Public state (pixels) — None when no valid gaze exists yet
        self.x: float | None = None
        self.y: float | None = None
        self.is_valid: bool  = False          # True iff last update returned a point
        self.both_invalid: bool = False       # True iff both eyes were missing this sample

    # ------------------------------------------------------------------
    def update(self,
               left_pt,  left_valid:  bool,
               right_pt, right_valid: bool
               ) -> tuple[float, float] | None:
        """
        Call once per Tobii sample (60 Hz).

        Parameters
        ----------
        left_pt, right_pt : (norm_x, norm_y) in [0, 1] — from Tobii SDK
        left_valid, right_valid : bool — from Tobii validity flags

        Returns
        -------
        (x_px, y_px)  if a smoothed gaze point is available
        None          if both eyes are invalid this sample (blink / loss)
        """
        # ── 1. EYE FUSION ──────────────────────────────────────────
        raw = self._fuse(left_pt, left_valid, right_pt, right_valid)

        # ── 2. BLINK / LOSS HANDLING ───────────────────────────────
        if raw is None:
            self.both_invalid = True
            self.is_valid     = False
            # Clear the buffer so old positions don't bleed through
            self._buf.clear()
            self.x = None
            self.y = None
            return None

        self.both_invalid = False

        # ── 3. CAUSAL SMOOTHING (rolling average) ──────────────────
        self._buf.append(raw)                 # add newest sample
        arr = np.array(self._buf)
        sx  = float(np.mean(arr[:, 0]))       # mean of past ≤ N norm-x values
        sy  = float(np.mean(arr[:, 1]))       # mean of past ≤ N norm-y values

        # ── 4. CONVERT TO PIXELS ───────────────────────────────────
        self.x = sx * self.screen_w
        self.y = sy * self.screen_h
        self.is_valid = True

        return (self.x, self.y)

    # ------------------------------------------------------------------
    @staticmethod
    def _fuse(left_pt, left_valid: bool,
              right_pt, right_valid: bool
              ) -> tuple[float, float] | None:
        """
        Fuse two (possibly invalid) eye positions into one point.

        Rules (matches specification exactly):
          both valid  → average
          left only   → left
          right only  → right
          neither     → None
        """
        def _ok(pt, valid):
            if not valid:
                return False
            try:
                return not (math.isnan(pt[0]) or math.isnan(pt[1]))
            except (TypeError, IndexError):
                return False

        l_ok = _ok(left_pt,  left_valid)
        r_ok = _ok(right_pt, right_valid)

        if l_ok and r_ok:
            return ((left_pt[0] + right_pt[0]) / 2.0,
                    (left_pt[1] + right_pt[1]) / 2.0)
        elif l_ok:
            return (left_pt[0],  left_pt[1])
        elif r_ok:
            return (right_pt[0], right_pt[1])
        else:
            return None

    # ------------------------------------------------------------------
    @property
    def theoretical_delay_ms(self) -> float:
        """
        Maximum smoothing delay in milliseconds (at 60 Hz).
        This is the CAUSAL delay added by the N-sample rolling average.
        Formula: delay = (N-1) / 2 / sample_rate * 1000
        """
        SAMPLE_RATE_HZ = 60.0
        return (self.window - 1) / 2.0 / SAMPLE_RATE_HZ * 1000.0
