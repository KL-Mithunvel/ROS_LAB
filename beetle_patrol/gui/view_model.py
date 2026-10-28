"""All GUI logic, pure Python: no tkinter, no rclpy, no numpy. Unit-tested in tests/test_gui_model.py.

Everything takes plain dicts as produced by patrol.protocol (status / decision / warning) and returns
plain values (strings, tuples, floats) that beetle_gui.py only has to draw. Missing keys are tolerated
(`.get`) so a slightly older or newer node never crashes the GUI.
"""
import math
from collections import deque

TERMS = ("age", "risk", "distance", "alert")          # same order as patrol.priority.TERMS
TERM_COLOURS = {"age": "#d9822b", "risk": "#c0392b", "distance": "#2e86c1", "alert": "#8e44ad"}

LIN_CAP, ANG_CAP = 0.15, 0.5       # hard drive caps, m/s and rad/s
STALE_WARN_S = 2.0                 # status older than this: amber
STALE_LOST_S = 4.0                 # ... red "no /patrol/status for N s"
FLASH_S = 3.0                      # warning banner flashes this long after a new warning
FLASH_PERIOD_S = 0.5
NEW_ZONE_HIGHLIGHT_S = 3.0         # a newly created zone gets a thick outline this long
HISTORY_LEN = 20
WARNING_LEN = 50
WEIGHT_DEBOUNCE_S = 0.4
KEY_RELEASE_GRACE_S = 0.08         # X11 key auto-repeat sends release+press pairs; ignore those
RISKY_DOMAIN = "155"               # shared with another BeetleBot on the lab Wi-Fi
OWN_DOMAIN = "154"


# --- colours ------------------------------------------------------------------------------------
_GREEN, _YELLOW, _RED = (46, 160, 67), (235, 200, 40), (214, 48, 49)


def age_colour(age_norm):
    """Heatmap colour for a zone: age_norm 0 (just visited) = green, 0.5 = yellow, 1 (stale) = red.

    Piecewise-linear green -> yellow -> red in RGB; values outside 0..1 (or None) are clamped.
    Returns '#rrggbb'.
    """
    a = 0.0 if age_norm is None else min(1.0, max(0.0, float(age_norm)))
    if a <= 0.5:
        lo, hi, f = _GREEN, _YELLOW, a / 0.5
    else:
        lo, hi, f = _YELLOW, _RED, (a - 0.5) / 0.5
    return "#%02x%02x%02x" % tuple(round(l + (h - l) * f) for l, h in zip(lo, hi))


def bar_fraction(value):
    return 0.0 if value is None else min(1.0, max(0.0, float(value)))


def format_age(age_s):
    age_s = max(0, int(age_s or 0))
    return f"{age_s}s" if age_s < 100 else f"{age_s // 60}m{age_s % 60:02d}"


# --- top bar ------------------------------------------------------------------------------------
def domain_label(domain_id):
    """(text, is_warning). Domain 155 is shared with another robot -> warn."""
    d = (domain_id or "").strip() or "0 (unset)"
    if d == RISKY_DOMAIN:
        return f"ROS domain {d}  SHARED WITH ANOTHER ROBOT - use {OWN_DOMAIN}", True
    return f"ROS domain {d}", False


def staleness(last_rx, now):
    """(text, level) for the status line; level 'ok' | 'warn' | 'lost'. last_rx None = never received."""
    if last_rx is None:
        return "waiting for /patrol/status ...", "lost"
    age = max(0.0, now - last_rx)
    if age >= STALE_LOST_S:
        return f"no /patrol/status for {age:.0f} s", "lost"
    if age >= STALE_WARN_S:
        return f"/patrol/status slow ({age:.1f} s)", "warn"
    return "status ok", "ok"


def flags_text(status):
    """Top-bar cells as [(label, value_text, state)] where state is True/False/None(unknown)."""
    s = status or {}
    return [("mode", str(s.get("mode", "?")), None),
            ("armed", {True: "yes", False: "no"}.get(s.get("armed"), "?"), s.get("armed")),
            ("nav_ready", "yes" if s.get("nav_ready") else "no", bool(s.get("nav_ready"))),
            ("explore", "on" if s.get("explore_active") else "off", bool(s.get("explore_active"))),
            ("recording", "REC" if s.get("recording") else "off", bool(s.get("recording")))]


class EstopLatch:
    """GUI-side E-STOP latch. trigger() always latches; release() only works when `confirmed`."""

    def __init__(self):
        self.latched = False

    def trigger(self):
        self.latched = True

    def release(self, confirmed):
        if confirmed:
            self.latched = False
        return not self.latched


def estop_active(latch, status):
    return latch.latched or (status or {}).get("mode") == "estop"


# --- decision panel -----------------------------------------------------------------------------
def score_rows(decision):
    """Rows for the decision table, best (highest total) first; ties broken by zone id.

    Each row: dict(zone, total, distance_m, chosen, raw={term: x}, contrib={term: x}). A malformed
    score entry is skipped rather than raising.
    """
    if not decision:
        return []
    chosen = decision.get("chosen")
    rows = []
    for s in decision.get("scores") or []:
        try:
            rows.append({"zone": s["zone"], "total": float(s["total"]),
                         "distance_m": float(s.get("distance_m", 0.0)), "chosen": s["zone"] == chosen,
                         "raw": {t: float(s["raw"][t]) for t in TERMS},
                         "contrib": {t: float(s["contrib"][t]) for t in TERMS}})
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda r: (-r["total"], r["zone"]))
    return rows


def segments(row, max_total, width_px):
    """Stacked-bar pieces [(term, x0, x1)] for one row; the whole bar is total/max_total * width_px,
    each piece proportional to that term's weighted contribution."""
    scale = width_px / max_total if max_total > 0 else 0.0
    out, x = [], 0.0
    for t in TERMS:
        w = max(0.0, row["contrib"][t]) * scale
        out.append((t, x, x + w))
        x += w
    return out


def skip_text(zone, reason):
    return {"cooldown": f"{zone}: skipped - Nav2 failed to reach it recently (cooldown)",
            "recent": f"{zone}: skipped - visited too recently (min revisit time)"
            }.get(reason, f"{zone}: skipped ({reason})")


def skipped_lines(status):
    return [skip_text(z, r) for z, r in sorted(((status or {}).get("skipped") or {}).items())]


def explanation_text(decision):
    if not decision:
        return "No decision yet."
    return decision.get("explanation") or f"Chose {decision.get('chosen')}."


class History:
    """Ring buffer of the last N distinct decisions (a decision repeated in every status message
    is recorded once, keyed by its timestamp)."""

    def __init__(self, maxlen=HISTORY_LEN):
        self.items = deque(maxlen=maxlen)       # oldest first
        self._last_t = None

    def add(self, decision):
        """Returns True if it was new."""
        if not decision or decision.get("t") == self._last_t:
            return False
        self._last_t = decision.get("t")
        self.items.append({"t": decision.get("t"), "chosen": decision.get("chosen"),
                           "explanation": explanation_text(decision)})
        return True

    def newest_first(self):
        return list(reversed(self.items))


# --- weights ------------------------------------------------------------------------------------
def normalise_weights(w):
    """Weights scaled to sum to 1 (as the node does). All-zero / bad input -> equal weights."""
    vals = {t: max(0.0, float((w or {}).get(t, 0.0))) for t in TERMS}
    total = sum(vals.values())
    if total <= 0:
        return {t: 1.0 / len(TERMS) for t in TERMS}
    return {t: v / total for t, v in vals.items()}


def weights_text(w):
    n = normalise_weights(w)
    return "  ".join(f"{t} {n[t] * 100:.0f}%" for t in TERMS)


class Debouncer:
    """Send the slider values once, `delay` s after the last change. Feed it fake times in tests.

    change(values, now) records a pending value; poll(now) returns the values to send (once) when the
    delay has passed without a newer change, else None.
    """

    def __init__(self, delay=WEIGHT_DEBOUNCE_S):
        self.delay, self._value, self._due = delay, None, None

    def change(self, value, now):
        self._value, self._due = dict(value), now + self.delay

    def poll(self, now):
        if self._due is not None and now >= self._due:
            value, self._value, self._due = self._value, None, None
            return value
        return None


# --- warnings -----------------------------------------------------------------------------------
class WarningLog:
    """Newest-first warning list plus banner flash timing."""

    def __init__(self, maxlen=WARNING_LEN):
        self.items = deque(maxlen=maxlen)       # newest first (appendleft)
        self._seen = set()
        self.flash_until = 0.0

    def add(self, w, now):
        """Add a warning dict (duplicates by (t, t_robot) ignored). Returns True if new."""
        if not w:
            return False
        key = (w.get("t"), w.get("t_robot"), w.get("x"), w.get("y"))
        if key in self._seen:
            return False
        self._seen.add(key)
        if len(self.items) == self.items.maxlen:
            old = self.items[-1]
            self._seen.discard((old.get("t"), old.get("t_robot"), old.get("x"), old.get("y")))
        self.items.appendleft(w)
        self.flash_until = now + FLASH_S
        return True

    def flashing(self, now):
        return now < self.flash_until

    def banner_on(self, now):
        """True on the 'bright' half of the flash period while flashing."""
        if not self.flashing(now):
            return False
        return int((self.flash_until - now) / FLASH_PERIOD_S) % 2 == 0


def warning_row(w):
    """(time_text, zone, 'x,y', fused, lidar, camera) strings for the warning table."""
    import time as _time
    t = w.get("t")
    when = _time.strftime("%H:%M:%S", _time.localtime(t)) if isinstance(t, (int, float)) else "--"
    return (when, w.get("zone") or "-", f"{w.get('x', 0):.1f},{w.get('y', 0):.1f}",
            f"{w.get('fused', 0):.2f}", f"{w.get('lidar', 0):.2f}", f"{w.get('camera', 0):.2f}")


# --- drive pad ----------------------------------------------------------------------------------
_DIRS = {"forward": (1, 0), "back": (-1, 0), "left": (0, 1), "right": (0, -1)}


def drive_enabled(status, estop):
    """Drive only when armed, not E-STOPPED and the node is idle (not mapping / patrolling)."""
    s = status or {}
    return (not estop) and s.get("armed") is True and s.get("mode") == "idle"


def drive_command(held, enabled, lin_speed=LIN_CAP, ang_speed=ANG_CAP):
    """(linear m/s, angular rad/s) for the held directions, clipped to the hard caps. (0,0) if disabled."""
    if not enabled:
        return 0.0, 0.0
    lx = sum(_DIRS[d][0] for d in held if d in _DIRS)
    az = sum(_DIRS[d][1] for d in held if d in _DIRS)
    lin = max(-LIN_CAP, min(LIN_CAP, lx * abs(lin_speed)))
    ang = max(-ANG_CAP, min(ANG_CAP, az * abs(ang_speed)))
    return (lin if lx else 0.0), (ang if az else 0.0)


class HeldKeys:
    """Which drive directions are held, tolerant of key auto-repeat release/press pairs."""

    def __init__(self, grace=KEY_RELEASE_GRACE_S):
        self.grace, self._down = grace, {}      # direction -> None (held) or release time

    def press(self, d):
        self._down[d] = None

    def release(self, d, now):
        if d in self._down:
            self._down[d] = now

    def clear(self):
        self._down.clear()

    def held(self, now):
        for d, rel in list(self._down.items()):
            if rel is not None and now - rel >= self.grace:
                del self._down[d]
        return set(self._down)


class DriveSender:
    """Turns successive (lin, ang) commands into Twists to publish: stream while moving, and a burst
    of zero Twists when motion stops."""

    def __init__(self, burst=3):
        self.burst, self._moving = burst, False

    def step(self, cmd):
        if cmd != (0.0, 0.0):
            self._moving = True
            return [cmd]
        if self._moving:
            self._moving = False
            return [(0.0, 0.0)] * self.burst
        return []


# --- geometry -----------------------------------------------------------------------------------
class Viewport:
    """World (metres, y up) <-> canvas (pixels, y down), uniform scale, bounds centred in the canvas."""

    def __init__(self, bounds, width, height, margin=12):
        x0, y0, x1, y1 = bounds
        self.x0, self.y0 = x0, y0
        span_x, span_y = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        self.scale = max(1e-6, min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y))
        self.off_x = (width - self.scale * span_x) / 2
        self.off_y = (height - self.scale * span_y) / 2
        self.height_m = span_y

    def to_canvas(self, x, y):
        return (self.off_x + (x - self.x0) * self.scale,
                self.off_y + (self.height_m - (y - self.y0)) * self.scale)

    def to_world(self, px, py):
        return (self.x0 + (px - self.off_x) / self.scale,
                self.y0 + self.height_m - (py - self.off_y) / self.scale)

    def length(self, metres):
        return metres * self.scale


def world_bounds(zones, map_info=None, pad=0.5):
    """(x0, y0, x1, y1): the map extent if there is one, else the zone extent + pad, else a 4 m box."""
    if map_info:
        ox, oy = map_info["origin"]
        return (ox, oy, ox + map_info["width"] * map_info["resolution"],
                oy + map_info["height"] * map_info["resolution"])
    if zones:
        return (min(z["cx"] - z["w"] / 2 for z in zones) - pad, min(z["cy"] - z["h"] / 2 for z in zones) - pad,
                max(z["cx"] + z["w"] / 2 for z in zones) + pad, max(z["cy"] + z["h"] / 2 for z in zones) + pad)
    return (-2.0, -2.0, 2.0, 2.0)


def zone_rect(vp, z):
    """Canvas (x0, y0, x1, y1) of a zone (top-left, bottom-right)."""
    ax, ay = vp.to_canvas(z["cx"] - z["w"] / 2, z["cy"] + z["h"] / 2)
    bx, by = vp.to_canvas(z["cx"] + z["w"] / 2, z["cy"] - z["h"] / 2)
    return ax, ay, bx, by


def zone_styles(status):
    """Per-zone drawing info [(zone, fill, alert_outline, label, is_goal)] from a status dict."""
    s = status or {}
    heat, goal = s.get("heatmap") or {}, s.get("goal_zone")
    out = []
    for z in s.get("zones") or []:
        h = heat.get(z["id"], {})
        label = z["id"] + (f"\n{format_age(h['age_s'])}" if "age_s" in h else "")
        out.append((z, age_colour(h.get("age_norm")), float(h.get("alert", 0.0)) > 0.05, label,
                    z["id"] == goal))
    return out


def fit_bounds(bounds, zones):
    """`bounds` (x0, y0, x1, y1) grown just enough to contain every zone rectangle; unchanged if they
    already fit. Keeps zones that appear beyond the map / current view on screen."""
    x0, y0, x1, y1 = bounds
    for z in zones or []:
        x0, y0 = min(x0, z["cx"] - z["w"] / 2), min(y0, z["cy"] - z["h"] / 2)
        x1, y1 = max(x1, z["cx"] + z["w"] / 2), max(y1, z["cy"] + z["h"] / 2)
    return (x0, y0, x1, y1)


def zone_title(zone):
    """The big number drawn in a zone box (its discovery number n)."""
    return str(zone.get("n", "?"))


def zone_numbers(status):
    """{zone id: n} from a status dict, for labelling the decision table."""
    return {z["id"]: z.get("n") for z in (status or {}).get("zones") or [] if "id" in z}


def zone_display(zone_id, numbers):
    """'#3 R0C2' when the number is known, else just the id."""
    n = (numbers or {}).get(zone_id)
    return f"#{n} {zone_id}" if n is not None else zone_id


class NewZoneTracker:
    """Remembers when each zone id first appeared so the GUI can outline new zones for a moment.

    The first status seen is the baseline (a GUI joining a running node does not flash everything).
    An id that disappears (zones were reset by 'Set start here') is forgotten, so it flashes again
    when it is re-created.
    """

    def __init__(self, duration=NEW_ZONE_HIGHLIGHT_S):
        self.duration = duration
        self._first_seen = {}       # zone id -> time first seen (None = baseline, never highlighted)
        self._started = False

    def update(self, status, now):
        ids = {z["id"] for z in (status or {}).get("zones") or [] if "id" in z}
        for zid in list(self._first_seen):
            if zid not in ids:
                del self._first_seen[zid]
        for zid in ids:
            if zid not in self._first_seen:
                self._first_seen[zid] = now if self._started else None
        self._started = True

    def is_new(self, zone_id, now):
        t = self._first_seen.get(zone_id)
        return t is not None and now - t < self.duration


def set_start_enabled(status, estop):
    """'Set start here' only while the node is idle (it refuses otherwise) and no E-STOP is latched."""
    return (not estop) and (status or {}).get("mode") == "idle"


def scan_points(robot, angle_min, angle_inc, ranges, range_max=12.0, mount_yaw=0.0, max_points=360):
    """World (x, y) of valid scan returns, drawn from the robot pose {x,y,yaw}.

    `mount_yaw` is the laser's yaw relative to base_link (0 if unknown). Invalid (inf/nan/<=0 or
    > range_max) beams are dropped; at most `max_points` evenly-spaced beams are used.
    """
    if not robot or not ranges:
        return []
    step = max(1, math.ceil(len(ranges) / max_points))
    base = robot["yaw"] + mount_yaw
    pts = []
    for i in range(0, len(ranges), step):
        r = ranges[i]
        if not math.isfinite(r) or r <= 0.05 or r > range_max:
            continue
        a = base + angle_min + i * angle_inc
        pts.append((robot["x"] + r * math.cos(a), robot["y"] + r * math.sin(a)))
    return pts
