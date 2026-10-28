"""Zone grid and visit heatmap.

The warehouse is cut into a grid of rectangular zones (zones.yaml). Each zone remembers when the
robot last visited it and when motion was last detected in it. `ZoneMap.snapshot()` is what the GUI
paints as the heatmap: green = visited recently, red = long overdue.

A zone counts as visited when the robot is within `visit_radius_m` of the zone centre. (Line of
sight is not checked - the radius is kept small so a robot in the next aisle does not count.)

Two ways to get zones:
  static  - the fixed grid from zones.yaml (`build_zones`), numbered 1..N in build order.
  dynamic - `zones.yaml: dynamic.enabled`. The map starts EMPTY; zone 1 is the cell whose centre is the
            robot's start point (the "anchor") and `patrol.discovery` adds cells as SLAM reveals free
            space. Cell ids stay "R<row>C<col>" but row/col may be NEGATIVE relative to the anchor cell
            R0C0. Zones are never removed; only `reset()` clears them. `Zone.n` is the discovery number.
"""
import math
from dataclasses import dataclass

from .schema import from_mapping


@dataclass(frozen=True)
class Zone:
    id: str
    n: int         # discovery number, 1 = first zone (the start cell in dynamic mode)
    row: int
    col: int
    cx: float      # centre, map frame (m)
    cy: float
    w: float       # size (m)
    h: float
    risk: float    # 0..1


@dataclass
class DynamicConfig:
    """zones.yaml `dynamic:` section - growing zones. See patrol/discovery.py for the rules."""
    enabled: bool = True
    cell_size_m: float = 1.0                  # zone edge length
    min_free_fraction: float = 0.40           # a cell appears when this share of it is known-free
    blocked_occupied_fraction: float = 0.50   # a cell this occupied is a wall / furniture: never a zone
    max_zones: int = 50
    map_update_s: float = 2.0                 # /map is processed at most this often

    def __post_init__(self):
        if not isinstance(self.enabled, bool):
            raise ValueError(f"zones.yaml [dynamic]: enabled must be true or false, got {self.enabled!r}")
        if not self.cell_size_m > 0:
            raise ValueError("zones.yaml [dynamic]: cell_size_m must be > 0")
        for name in ("min_free_fraction", "blocked_occupied_fraction"):
            if not 0.0 < getattr(self, name) <= 1.0:
                raise ValueError(f"zones.yaml [dynamic]: {name} must be within (0, 1]")
        if isinstance(self.max_zones, bool) or not isinstance(self.max_zones, int) or self.max_zones < 1:
            raise ValueError("zones.yaml [dynamic]: max_zones must be an integer >= 1")
        if not self.map_update_s >= 0:
            raise ValueError("zones.yaml [dynamic]: map_update_s must be >= 0")


def dynamic_config(zones_cfg):
    """DynamicConfig from the parsed zones.yaml. A file WITHOUT a `dynamic:` section is static
    (enabled False); inside the section `enabled` defaults to true."""
    section = zones_cfg.get("dynamic")
    if section is None:
        return DynamicConfig(enabled=False)
    if not isinstance(section, dict):
        raise ValueError("zones.yaml [dynamic]: must be a mapping")
    return from_mapping(DynamicConfig, section, "dynamic", source="zones.yaml")


@dataclass
class HeatmapConfig:
    visit_radius_m: float = 1.2
    max_age_s: float = 300.0
    alert_memory_s: float = 120.0

    def __post_init__(self):
        if self.visit_radius_m <= 0 or self.max_age_s <= 0 or self.alert_memory_s <= 0:
            raise ValueError("heatmap: visit_radius_m, max_age_s and alert_memory_s must be > 0")


def zone_id(row, col):
    return f"R{row}C{col}"


def _cell_key(key):
    """'1,2' -> (1, 2); a bad key raises a ValueError that names the offending text."""
    try:
        row, col = (int(part) for part in str(key).split(","))
    except ValueError:
        raise ValueError(f"zones.yaml: cell key {key!r} must look like 'row,col'") from None
    return row, col


def build_zones(cfg):
    """Turn the parsed zones.yaml mapping into a list of Zone (blocked cells left out)."""
    try:
        grid = cfg["grid"]
        rows, cols = int(grid["rows"]), int(grid["cols"])
        cell_w, cell_h = float(grid["cell_w"]), float(grid["cell_h"])
        ox, oy = (float(v) for v in grid["origin"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"zones.yaml: bad or missing 'grid' section ({exc!r})") from None
    if rows < 1 or cols < 1 or cell_w <= 0 or cell_h <= 0:
        raise ValueError("zones.yaml: rows/cols must be >= 1 and cell_w/cell_h > 0")

    default_risk = float(cfg.get("default_risk", 0.3))
    risks = {_cell_key(k): float(v) for k, v in (cfg.get("risk") or {}).items()}
    blocked = {_cell_key(k) for k in (cfg.get("blocked") or [])}
    for cell, risk in [(c, r) for c, r in risks.items()] + [(None, default_risk)]:
        if not 0.0 <= risk <= 1.0:
            raise ValueError(f"zones.yaml: risk {risk} (cell {cell}) must be within 0..1")
    for cell in list(risks) + list(blocked):
        if not (0 <= cell[0] < rows and 0 <= cell[1] < cols):
            raise ValueError(f"zones.yaml: cell {cell[0]},{cell[1]} is outside the {rows}x{cols} grid")

    zones = []
    for row in range(rows):
        for col in range(cols):
            if (row, col) in blocked:
                continue
            zones.append(Zone(
                id=zone_id(row, col), n=len(zones) + 1, row=row, col=col,
                cx=ox + (col + 0.5) * cell_w, cy=oy + (row + 0.5) * cell_h,
                w=cell_w, h=cell_h, risk=risks.get((row, col), default_risk)))
    if not zones:
        raise ValueError("zones.yaml: every cell is blocked - nothing to patrol")
    return zones


class ZoneMap:
    """Visit and alert times for every zone; in dynamic mode also the growing grid itself."""

    def __init__(self, zones, start_time, config=None, dynamic=None, default_risk=0.3):
        self.zones = list(zones)
        self.config = config or HeatmapConfig()
        self.dynamic = dynamic if dynamic is not None and dynamic.enabled else None
        self.default_risk = default_risk
        self.anchor = None                  # (x, y) centre of cell R0C0 (dynamic mode only)
        self.blocked = set()                # (row, col) cells seen as wall / furniture (dynamic mode)
        self._by_id = {z.id: z for z in self.zones}
        # A never-visited zone is as old as the patrol itself.
        self._last_visit = {z.id: float(start_time) for z in self.zones}
        self._last_alert = {}

    @classmethod
    def from_mapping(cls, zones_cfg, heatmap_cfg, start_time):
        return cls(build_zones(zones_cfg), start_time, from_mapping(HeatmapConfig, heatmap_cfg, "heatmap"))

    # --- dynamic growth -----------------------------------------------------------------
    def reset(self, anchor, now):
        """Forget every zone, alert and blocked cell; zone 1 is the cell centred on `anchor` (x, y)."""
        self._require_dynamic()
        self.zones, self._by_id = [], {}
        self._last_visit, self._last_alert = {}, {}
        self.blocked = set()
        self.anchor = (float(anchor[0]), float(anchor[1]))
        self.add_zone(0, 0, now)

    def cell_of(self, x, y):
        """(row, col) of the dynamic cell containing (x, y); cell (0, 0) is centred on the anchor."""
        size = self.dynamic.cell_size_m
        return (math.floor((y - self.anchor[1]) / size + 0.5), math.floor((x - self.anchor[0]) / size + 0.5))

    def cell_centre(self, row, col):
        size = self.dynamic.cell_size_m
        return self.anchor[0] + col * size, self.anchor[1] + row * size

    def has_cell(self, row, col):
        return zone_id(row, col) in self._by_id

    def can_add(self, row, col):
        """True if a new zone may be created at this cell (anchored, new, not blocked, under the cap)."""
        return (self.dynamic is not None and self.anchor is not None and not self.has_cell(row, col)
                and (row, col) not in self.blocked and len(self.zones) < self.dynamic.max_zones)

    def add_zone(self, row, col, now):
        """Create the zone for cell (row, col), numbered next in sequence; its age starts at 0."""
        self._require_dynamic()
        if self.anchor is None:
            raise RuntimeError("ZoneMap.add_zone: no anchor yet - call reset(anchor, now) first")
        if self.has_cell(row, col):
            raise ValueError(f"zone {zone_id(row, col)} already exists")
        cx, cy = self.cell_centre(row, col)
        size = self.dynamic.cell_size_m
        zone = Zone(id=zone_id(row, col), n=len(self.zones) + 1, row=row, col=col, cx=cx, cy=cy,
                    w=size, h=size, risk=self.default_risk)
        self.zones.append(zone)
        self._by_id[zone.id] = zone
        self._last_visit[zone.id] = float(now)
        return zone

    def ensure_zone_at(self, x, y, now):
        """The zone containing (x, y); created if that cell is new, not blocked and under max_zones.
        None when there is no zone and none may be made (not anchored, blocked, cap reached)."""
        if self.dynamic is None or self.anchor is None:
            return None
        row, col = self.cell_of(x, y)
        if self.has_cell(row, col):
            return self._by_id[zone_id(row, col)]
        return self.add_zone(row, col, now) if self.can_add(row, col) else None

    def _require_dynamic(self):
        if self.dynamic is None:
            raise RuntimeError("ZoneMap: dynamic zones are not enabled (zones.yaml dynamic.enabled)")

    def zone(self, zid):
        return self._by_id[zid]

    def zone_at(self, x, y):
        """The zone whose rectangle contains (x, y), or None (outside the grid / blocked)."""
        for z in self.zones:
            if abs(x - z.cx) <= z.w / 2 and abs(y - z.cy) <= z.h / 2:
                return z
        return None

    def mark_visited(self, x, y, t):
        """Reset the age (= turn the box green) of every zone the robot has entered. Returns the ids reset.

        A zone counts as entered when the point is inside its rectangle, or within the visit radius of
        its centre (the radius also covers a zone larger than the cell, e.g. a big warehouse aisle).
        """
        hit = [z.id for z in self.zones
               if (abs(x - z.cx) <= z.w / 2 and abs(y - z.cy) <= z.h / 2)
               or math.hypot(x - z.cx, y - z.cy) <= self.config.visit_radius_m]
        for zid in hit:
            self._last_visit[zid] = max(self._last_visit[zid], float(t))
        return hit

    def record_alert(self, x, y, t):
        """Note a motion alert at (x, y). Returns the zone id, or None if outside every zone."""
        z = self.zone_at(x, y)
        if z is not None:
            self._last_alert[z.id] = float(t)
            return z.id
        return None

    def age_s(self, zid, now):
        return max(0.0, now - self._last_visit[zid])

    def age_norm(self, zid, now):
        return min(1.0, self.age_s(zid, now) / self.config.max_age_s)

    def alert_level(self, zid, now):
        """1.0 right after an alert, fading linearly to 0 over alert_memory_s."""
        if zid not in self._last_alert:
            return 0.0
        return max(0.0, 1.0 - (now - self._last_alert[zid]) / self.config.alert_memory_s)

    def snapshot(self, now):
        """{zone id: {age_s, age_norm, alert}} - everything the heatmap view needs."""
        return {z.id: {"age_s": self.age_s(z.id, now),
                       "age_norm": self.age_norm(z.id, now),
                       "alert": self.alert_level(z.id, now)}
                for z in self.zones}
