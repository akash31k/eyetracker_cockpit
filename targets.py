"""
====================================================================
TARGETS MODULE — Which Cockpit Target Is Being Looked At?
====================================================================
Specification:
  - List of targets: id, shape (rectangle), action type
  - "Point in shape" test with a margin (hysteresis ring)
  - Avoids spurious changes between neighbouring targets
  - Action types: 'reversible' (look away = undo) or
                  'consequential' (confirmed before acting)

Hysteresis rule (prevents flickering between adjacent targets):
  - To ENTER a target:  gaze must be INSIDE its core boundary
  - To EXIT a target:   gaze must move OUTSIDE its expanded boundary
                        (core + MARGIN_PX pixels on every side)
  → You can be "between" a core zone and an expanded zone;
    the last confirmed target stays active.

Tuning parameters at the bottom of this file (COCKPIT_TARGETS).
====================================================================
"""

import math
from dataclasses import dataclass, field
from typing import Optional


# ──────────────────────────────────────────────────────────────────
# TUNING PARAMETER  ← set this after measuring gaze error at gate A
# Rule: margin must be SMALLER than the gaze error so neighbours
#       cannot be confused (see Critical Review in spec).
HYSTERESIS_MARGIN_PX = 90   # pixels added around each target's core box
#                             to build the "stay-inside" zone
# ──────────────────────────────────────────────────────────────────


@dataclass
class Target:
    """
    One cockpit area of interest (AOI / target).

    id          : unique string label used in the WebSocket message
    x1, y1      : top-left corner of the core bounding box (pixels)
    x2, y2      : bottom-right corner of the core bounding box (pixels)
    action_type : 'reversible'    → toggled just by looking / looking away
                  'consequential' → requires double-blink confirmation
    """
    id:          str
    x1:          float
    y1:          float
    x2:          float
    y2:          float
    action_type: str = 'reversible'   # 'reversible' | 'consequential'

    # ── helpers ────────────────────────────────────────────────────
    def contains(self, x: float, y: float) -> bool:
        """Is (x, y) strictly inside the CORE bounding box?"""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def contains_expanded(self, x: float, y: float,
                          margin: float = HYSTERESIS_MARGIN_PX) -> bool:
        """Is (x, y) inside the EXPANDED box (core + margin on each side)?"""
        return (self.x1 - margin <= x <= self.x2 + margin and
                self.y1 - margin <= y <= self.y2 + margin)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


class TargetTracker:
    """
    Given a list of Targets and a smoothed gaze point (from GazeFilter),
    returns the currently active target — or None if gaze is on background.

    Hysteresis prevents jumping between two neighbouring targets when
    the gaze sits near the boundary.

    Usage:
        tracker = TargetTracker(COCKPIT_TARGETS)
        ...
        active = tracker.update(x, y)
        if active:
            print(active.id, active.action_type)
    """

    def __init__(self, targets: list[Target],
                 margin: float = HYSTERESIS_MARGIN_PX):
        self.targets       = targets
        self.margin        = margin
        self._current: Optional[Target] = None   # last confirmed target

    # ------------------------------------------------------------------
    def update(self, x: float | None, y: float | None
               ) -> Optional[Target]:
        """
        Call once per smoothed gaze sample.

        Parameters
        ----------
        x, y : smoothed pixel coordinates (from GazeFilter)
               Pass None / None when gaze is invalid (blink).

        Returns
        -------
        Target   currently active target  (may be same as before)
        None     if gaze is on background or invalid
        """
        if x is None or y is None:
            # Gaze lost (blink) → release current target
            self._current = None
            return None

        # ── HYSTERESIS LOGIC ───────────────────────────────────────
        # Case A: We already have an active target
        if self._current is not None:
            # Stay in current target as long as gaze is inside EXPANDED box
            if self._current.contains_expanded(x, y, self.margin):
                return self._current
            else:
                # Gaze has clearly left the current target
                self._current = None

        # Case B: No active target — look for a new one
        # Gaze must be inside the CORE box to register (stricter entry)
        for t in self.targets:
            if t.contains(x, y):
                self._current = t
                return self._current

        return None   # background / between targets

    # ------------------------------------------------------------------
    def reset(self):
        """Force-clear the active target (call at session start)."""
        self._current = None

    @property
    def current(self) -> Optional[Target]:
        return self._current


# ══════════════════════════════════════════════════════════════════
# YOUR COCKPIT TARGETS — edit these to match your cockpit.html layout
# Coordinates are in screen pixels (1920 × 1080)
# ══════════════════════════════════════════════════════════════════
COCKPIT_TARGETS = [
    # ── Flight instruments (left cluster) ─────────────────────────
    Target(id="PFD",
           x1=200,  y1=60,  x2=580,  y2=500,
           action_type="reversible"),

    Target(id="NAV_DISPLAY",
           x1=600,  y1=60,  x2=980,  y2=500,
           action_type="reversible"),

    Target(id="EICAS",
           x1=1000, y1=60,  x2=1380, y2=500,
           action_type="reversible"),

    # ── MCP Speed-brake bar (bottom) ──────────────────────────────
    Target(id="MCP_SPEED",
           x1=100,  y1=900, x2=300,  y2=980,
           action_type="reversible"),

    Target(id="MCP_HEADING",
           x1=310,  y1=900, x2=510,  y2=980,
           action_type="reversible"),

    Target(id="MCP_ALTITUDE",
           x1=520,  y1=900, x2=720,  y2=980,
           action_type="reversible"),

    # ── Autopilot master (consequential — double-blink needed) ────
    Target(id="AUTOPILOT",
           x1=200,  y1=510, x2=580,  y2=620,
           action_type="consequential"),

    # ── Communications panel ──────────────────────────────────────
    Target(id="COMMS",
           x1=1400, y1=60,  x2=1700, y2=400,
           action_type="reversible"),
]
