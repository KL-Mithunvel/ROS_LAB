"""Grow the zone grid from the SLAM occupancy map (dynamic zones). Pure functions, no ROS imports.

`discover_zones(occupancy, zonemap, cfg, now, robot_xy)` looks at the cells next to the zones that
already exist and adds a zone for each one that SLAM has shown to be free floor.

For one candidate cell (a `cell_size_m` square, cell (0, 0) centred on the anchor):
  free fraction     = map cells known-free   / all map cells in the square (unknown counts as NOT free)
  occupied fraction = map cells occupied     / all map cells in the square
  * occupied fraction >= blocked_occupied_fraction -> the cell is a wall / furniture: it is remembered
    in `zonemap.blocked` and never becomes a zone.
  * else free fraction >= min_free_fraction -> a new zone is created.

Growth rule (so zones spread outward contiguously and never appear in disconnected pockets): only cells
in the 8-neighbourhood of an EXISTING zone, or the cell containing the robot, are candidates. One call
adds one "ring"; a cell that becomes a neighbour only because of a zone created in this call waits for
the next call (the engine calls again on the next map update while the grid is still growing).
New zones are numbered in order of distance from the anchor (ties: row, then column) and stop at
`max_zones`.
"""
import math
from dataclasses import dataclass

import numpy as np

UNKNOWN = -1
FREE_MAX, OCCUPIED_MIN = 25, 65     # occupancy % : 0..25 counts as free, 65..100 as occupied (map_saver defaults)
NEIGHBOURS = tuple((dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))
SNAP_DECIMALS = 6                   # rounding that keeps float noise out of the cell-index maths


@dataclass
class OccupancyInfo:
    """A nav_msgs/OccupancyGrid without ROS: row-major `data`, index = j * width + i, int8 occupancy
    (-1 unknown, 0 free, 100 occupied); cell (i, j) spans x from origin_x + i*resolution, y likewise."""
    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    data: object

    def __post_init__(self):
        if self.width < 1 or self.height < 1 or not self.resolution > 0:
            raise ValueError("OccupancyInfo: width/height must be >= 1 and resolution > 0")
        self.data = np.asarray(self.data, dtype=np.int16)
        if self.data.size != self.width * self.height:
            raise ValueError(f"OccupancyInfo: data has {self.data.size} values, expected "
                             f"{self.width}x{self.height}")
        self.data = self.data.reshape(self.height, self.width)


def _index_range(low, high, origin, resolution):
    """Map-cell indices whose centre lies in [low, high) (world metres along one axis)."""
    first = math.ceil(round((low - origin) / resolution - 0.5, SNAP_DECIMALS))
    last = math.ceil(round((high - origin) / resolution - 0.5, SNAP_DECIMALS))
    return first, last


def cell_fractions(occupancy, cx, cy, size):
    """(free fraction, occupied fraction) of the `size` square centred on (cx, cy).
    Map cells outside the map count as unknown (in the denominator, not free)."""
    half = size / 2
    i0, i1 = _index_range(cx - half, cx + half, occupancy.origin_x, occupancy.resolution)
    j0, j1 = _index_range(cy - half, cy + half, occupancy.origin_y, occupancy.resolution)
    total = (i1 - i0) * (j1 - j0)
    if total <= 0:
        return 0.0, 0.0
    patch = occupancy.data[max(j0, 0):max(j1, 0), max(i0, 0):max(i1, 0)]
    free = np.count_nonzero((patch >= 0) & (patch <= FREE_MAX))
    occupied = np.count_nonzero(patch >= OCCUPIED_MIN)
    return free / total, occupied / total


def discover_zones(occupancy, zonemap, cfg, now, robot_xy=None):
    """Add the newly revealed zones to `zonemap`; returns them (list of Zone, creation order).

    `cfg` is a DynamicConfig, `robot_xy` the robot's map-frame position (its cell is also a candidate).
    A zonemap without an anchor (no first pose yet) gets nothing.
    """
    if zonemap.anchor is None:
        return []
    candidates = set()
    for zone in zonemap.zones:
        candidates.update((zone.row + dr, zone.col + dc) for dr, dc in NEIGHBOURS)
    if robot_xy is not None:
        candidates.add(zonemap.cell_of(*robot_xy))
    candidates = [c for c in candidates if not zonemap.has_cell(*c)]
    candidates.sort(key=lambda c: (math.hypot(*c), c))   # nearest the anchor first

    created = []
    for row, col in candidates:
        cx, cy = zonemap.cell_centre(row, col)
        free, occupied = cell_fractions(occupancy, cx, cy, cfg.cell_size_m)
        if occupied >= cfg.blocked_occupied_fraction:
            zonemap.blocked.add((row, col))
            continue
        zonemap.blocked.discard((row, col))        # the map changed its mind: it is not a wall any more
        if free >= cfg.min_free_fraction and zonemap.can_add(row, col):
            created.append(zonemap.add_zone(row, col, now))
    return created
