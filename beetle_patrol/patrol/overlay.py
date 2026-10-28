"""Check zones.yaml against a saved ROS map (offline, no ROS needed).

Answers three questions the day before a patrol:
  * how much of each zone rectangle is really free floor (vs wall / unknown)?
  * where is the free area, and which grid `origin` would centre the grid on it?
  * what does it look like? (`draw_overlay` -> PNG, written with numpy + zlib only.)

Map format: nav2 map_server (map.yaml + .pgm, P2 or P5), trinary interpretation. Map rotation
(origin yaw) is not supported and is rejected rather than silently ignored.
"""
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from .heatmap import build_zones

FREE, OCCUPIED, UNKNOWN = 0, 1, 2   # cell classes in OccupancyMap.cells

# 5x7 bitmap font, one string per row ('#' = pixel). Only what the overlay prints.
_FONT = {
    "0": ["#####", "#...#", "#..##", "#.#.#", "##..#", "#...#", "#####"],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "....#", "...#.", "..##.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
}
_GLYPHS = {ch: np.array([[c == "#" for c in row] for row in rows]) for ch, rows in _FONT.items()}

# Grey levels / colours of the overlay.
_GREY = {FREE: 255, OCCUPIED: 30, UNKNOWN: 150}
_ZONE_COLOUR = (220, 30, 30)
_TEXT_COLOUR = (0, 70, 220)


@dataclass
class OccupancyMap:
    cells: np.ndarray        # (H, W) of FREE / OCCUPIED / UNKNOWN; row 0 is the TOP of the picture
    resolution: float        # metres per cell
    origin: tuple            # (x, y) world position of the bottom-left corner of the picture

    @property
    def shape(self):
        return self.cells.shape

    def cell_centres(self):
        """(xs, ys): world x of every column centre, world y of every row centre (top row first)."""
        h, w = self.cells.shape
        xs = self.origin[0] + (np.arange(w) + 0.5) * self.resolution
        ys = self.origin[1] + (h - np.arange(h) - 0.5) * self.resolution
        return xs, ys

    def world_to_pixel(self, x, y):
        """World metres -> (column, row) in picture pixels (float, may lie outside the picture)."""
        return ((x - self.origin[0]) / self.resolution,
                self.cells.shape[0] - (y - self.origin[1]) / self.resolution)


def read_pgm(path):
    """Read a P2 (ascii) or P5 (binary) PGM into a (H, W) array of 0..maxval, plus maxval."""
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise FileNotFoundError(f"cannot read map image {path}: {exc.strerror}") from None
    magic = raw[:2]
    if magic not in (b"P2", b"P5"):
        raise ValueError(f"{path.name}: not a PGM file (expected P2 or P5, got {magic!r})")

    pos, header = 2, []
    while len(header) < 3:                       # width, height, maxval; '#' starts a comment
        while pos < len(raw) and raw[pos:pos + 1].isspace():
            pos += 1
        if pos >= len(raw):
            break
        if raw[pos:pos + 1] == b"#":
            pos = raw.find(b"\n", pos)
            if pos < 0:
                break
            continue
        end = pos
        while end < len(raw) and not raw[end:end + 1].isspace() and raw[end:end + 1] != b"#":
            end += 1
        try:
            header.append(int(raw[pos:end]))
        except ValueError:
            raise ValueError(f"{path.name}: bad PGM header") from None
        pos = end
    if len(header) < 3:
        raise ValueError(f"{path.name}: truncated PGM header")
    width, height, maxval = header
    if width < 1 or height < 1 or not 0 < maxval < 65536:
        raise ValueError(f"{path.name}: bad PGM size {width}x{height}, maxval {maxval}")

    count = width * height
    if magic == b"P2":
        try:
            values = np.array(raw[pos:].split()[:count], dtype=np.int64)
        except ValueError:
            raise ValueError(f"{path.name}: non-numeric pixel in P2 data") from None
    else:
        pos += 1                                  # exactly one whitespace byte after maxval
        dtype = ">u2" if maxval > 255 else "u1"
        values = np.frombuffer(raw[pos:], dtype=dtype, count=min(count, len(raw[pos:]) // np.dtype(dtype).itemsize))
    if values.size != count:
        raise ValueError(f"{path.name}: expected {count} pixels, found {values.size}")
    if values.max() > maxval:
        raise ValueError(f"{path.name}: pixel value above maxval {maxval}")
    return values.reshape(height, width).astype(np.int64), maxval


def load_map(yaml_path):
    """Load a nav2 map.yaml and the image it names into an OccupancyMap."""
    yaml_path = Path(yaml_path)
    try:
        meta = yaml.safe_load(yaml_path.read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"map yaml not found: {yaml_path}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"{yaml_path.name} is not valid YAML: {exc}") from None
    if not isinstance(meta, dict):
        raise ValueError(f"{yaml_path.name} must contain a mapping at the top level")
    try:
        image = Path(str(meta["image"]))
        resolution = float(meta["resolution"])
        ox, oy, yaw = (float(v) for v in meta["origin"])
        negate = int(meta.get("negate", 0))
        occ_thresh = float(meta.get("occupied_thresh", 0.65))
        free_thresh = float(meta.get("free_thresh", 0.25))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{yaml_path.name}: bad or missing key ({exc!r}); need image, resolution, "
                         "origin [x, y, yaw]") from None
    if resolution <= 0:
        raise ValueError(f"{yaml_path.name}: resolution must be > 0")
    if not 0.0 <= free_thresh < occ_thresh <= 1.0:
        raise ValueError(f"{yaml_path.name}: need 0 <= free_thresh < occupied_thresh <= 1")
    if abs(yaw) > 1e-6:
        raise ValueError(f"{yaml_path.name}: origin yaw {yaw} != 0 is not supported")

    pixels, maxval = read_pgm(image if image.is_absolute() else yaml_path.parent / image)
    shade = pixels / maxval
    occupancy = shade if negate else 1.0 - shade   # map_server: probability that the cell is occupied
    cells = np.full(pixels.shape, UNKNOWN, dtype=np.int8)
    cells[occupancy > occ_thresh] = OCCUPIED
    cells[occupancy < free_thresh] = FREE
    return OccupancyMap(cells, resolution, (ox, oy))


@dataclass(frozen=True)
class ZoneCoverage:
    id: str
    cells: int            # map cells whose centre lies inside the zone rectangle
    free_pct: float
    occupied_pct: float
    unknown_pct: float    # includes the part of the zone lying outside the picture


def _rect_mask(omap, cx, cy, w, h):
    xs, ys = omap.cell_centres()
    in_x = np.abs(xs - cx) <= w / 2
    in_y = np.abs(ys - cy) <= h / 2
    return in_y[:, None] & in_x[None, :]


def zone_coverage(omap, zones):
    """Free / occupied / unknown percentage of every zone (list of ZoneCoverage, zone order)."""
    result = []
    for z in zones:
        inside = omap.cells[_rect_mask(omap, z.cx, z.cy, z.w, z.h)]
        if inside.size == 0:
            result.append(ZoneCoverage(z.id, 0, 0.0, 0.0, 100.0))
            continue
        pct = {c: 100.0 * np.count_nonzero(inside == c) / inside.size for c in (FREE, OCCUPIED, UNKNOWN)}
        result.append(ZoneCoverage(z.id, int(inside.size), pct[FREE], pct[OCCUPIED], pct[UNKNOWN]))
    return result


def bounding_box(omap, cell_class):
    """(xmin, ymin, xmax, ymax) of all cells of that class (cell edges), or None if there are none."""
    rows, cols = np.nonzero(omap.cells == cell_class)
    if rows.size == 0:
        return None
    xs, ys = omap.cell_centres()
    half = omap.resolution / 2
    return (xs[cols.min()] - half, ys[rows.max()] - half, xs[cols.max()] + half, ys[rows.min()] + half)


@dataclass
class GridSuggestion:
    origin: tuple            # suggested grid.origin
    grid_size: tuple         # (width, height) of the whole grid, m
    free_box: tuple          # (xmin, ymin, xmax, ymax) or None
    warnings: list


def suggest_origin(omap, zones_cfg):
    """Grid origin that centres the configured grid on the free-space bounding box."""
    build_zones(zones_cfg)                       # validates the grid section with the usual messages
    grid = zones_cfg["grid"]
    width = int(grid["cols"]) * float(grid["cell_w"])
    height = int(grid["rows"]) * float(grid["cell_h"])
    box = bounding_box(omap, FREE)
    if box is None:
        raise ValueError("the map has no free cells - nothing to centre the grid on")
    origin = ((box[0] + box[2]) / 2 - width / 2, (box[1] + box[3]) / 2 - height / 2)
    warnings = []
    free_w, free_h = box[2] - box[0], box[3] - box[1]
    if width > free_w + 1e-9 or height > free_h + 1e-9:
        warnings.append(f"grid is {width:g} x {height:g} m but the free area is only "
                        f"{free_w:.2f} x {free_h:.2f} m - it does not fit; shrink cell_w/cell_h or rows/cols")
    return GridSuggestion(origin, (width, height), box, warnings)


# ---------------------------------------------------------------- picture

def _draw_text(img, text, x, y, colour, scale=1):
    """Stamp `text` (glyphs of _FONT) with its top-left at pixel (x, y); clipped to the image."""
    for i, ch in enumerate(text):
        glyph = _GLYPHS.get(ch)
        if glyph is None:
            continue
        big = np.kron(glyph, np.ones((scale, scale), dtype=bool))
        x0, y0 = x + i * 6 * scale, y
        h, w = big.shape
        ys0, xs0 = max(y0, 0), max(x0, 0)
        ys1, xs1 = min(y0 + h, img.shape[0]), min(x0 + w, img.shape[1])
        if ys1 > ys0 and xs1 > xs0:
            sub = big[ys0 - y0:ys1 - y0, xs0 - x0:xs1 - x0]
            img[ys0:ys1, xs0:xs1][sub] = colour


def render_overlay(omap, zones, coverage, scale=None):
    """RGB uint8 picture: the map in grey, each zone outlined with its id and free %."""
    if scale is None:
        scale = max(1, 600 // max(omap.shape))
    grey = np.array([_GREY[FREE], _GREY[OCCUPIED], _GREY[UNKNOWN]], dtype=np.uint8)[omap.cells]
    grey = np.kron(grey, np.ones((scale, scale), dtype=np.uint8))
    img = np.repeat(grey[:, :, None], 3, axis=2)
    height, width = img.shape[:2]
    for z, cov in zip(zones, coverage):
        left, top = omap.world_to_pixel(z.cx - z.w / 2, z.cy + z.h / 2)
        right, bottom = omap.world_to_pixel(z.cx + z.w / 2, z.cy - z.h / 2)
        l, t, r, b = (int(round(v * scale)) for v in (left, top, right, bottom))
        for xx in (l, r - 1):
            if 0 <= xx < width:
                img[max(t, 0):max(min(b, height), 0), xx] = _ZONE_COLOUR
        for yy in (t, b - 1):
            if 0 <= yy < height:
                img[yy, max(l, 0):max(min(r, width), 0)] = _ZONE_COLOUR
        text_scale = 2 if (r - l) >= 90 and (b - t) >= 40 else 1
        _draw_text(img, z.id, l + 3, t + 3, _TEXT_COLOUR, text_scale)
        _draw_text(img, f"{cov.free_pct:.0f}%", l + 3, t + 5 + 7 * text_scale, _TEXT_COLOUR, text_scale)
    return img


def write_png(path, rgb):
    """Write an (H, W, 3) uint8 array as a PNG (no Pillow needed)."""
    rgb = np.asarray(rgb, dtype=np.uint8)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("write_png needs an (H, W, 3) array")
    height, width = rgb.shape[:2]

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    scanlines = np.concatenate([np.zeros((height, 1), dtype=np.uint8), rgb.reshape(height, -1)], axis=1)
    data = (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines.tobytes(), 9))
            + chunk(b"IEND", b""))
    Path(path).write_bytes(data)
