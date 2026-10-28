import numpy as np
import pytest

from patrol.heatmap import build_zones
from patrol.overlay import (FREE, OCCUPIED, UNKNOWN, load_map, read_pgm, render_overlay, suggest_origin,
                            write_png, zone_coverage)

# 60x60 cells of 0.05 m = 3 m, origin (-1.5, -1.5). Picture rows/cols 0-based, row 0 = top:
#   wall ring 5 cells thick; free = rows/cols 5..44 in x, rows 5..54 in y (x: -1.25..0.75);
#   unknown = cols 45..54; wall = cols 55..59.
ZONES = {"grid": {"origin": [-1.5, -1.5], "rows": 3, "cols": 3, "cell_w": 1.0, "cell_h": 1.0}}


def synthetic_pixels():
    px = np.zeros((60, 60), dtype=np.uint8)         # 0 = black = occupied
    px[5:55, 5:45] = 254                            # free
    px[5:55, 45:55] = 205                           # unknown
    return px


def write_map(tmp_path, binary=True, negate=0, image="m.pgm"):
    px = synthetic_pixels()
    if negate:
        px = 255 - px
    if binary:
        (tmp_path / "m.pgm").write_bytes(b"P5\n# comment\n60 60\n255\n" + px.tobytes())
    else:
        rows = "\n".join(" ".join(str(v) for v in r) for r in px)
        (tmp_path / "m.pgm").write_text(f"P2\n60 60\n255\n{rows}\n")
    yml = tmp_path / "map.yaml"
    yml.write_text(f"image: {image}\nresolution: 0.05\norigin: [-1.5, -1.5, 0.0]\nnegate: {negate}\n"
                   "occupied_thresh: 0.65\nfree_thresh: 0.196\n")   # 0.196 is what map_saver writes
    return yml


@pytest.mark.parametrize("binary,negate", [(True, 0), (False, 0), (True, 1)])
def test_load_map_classes(tmp_path, binary, negate):
    omap = load_map(write_map(tmp_path, binary, negate))
    assert omap.shape == (60, 60) and omap.resolution == 0.05 and omap.origin == (-1.5, -1.5)
    assert omap.cells[30, 20] == FREE and omap.cells[30, 50] == UNKNOWN and omap.cells[0, 0] == OCCUPIED
    assert np.count_nonzero(omap.cells == FREE) == 50 * 40


def test_zone_free_percentages(tmp_path):
    omap = load_map(write_map(tmp_path))
    cov = {c.id: c for c in zone_coverage(omap, build_zones(ZONES))}
    assert cov["R0C0"].free_pct == pytest.approx(56.25)       # bottom-left: 15x15 free of 20x20
    assert cov["R0C0"].occupied_pct == pytest.approx(43.75)
    assert cov["R0C0"].unknown_pct == 0.0
    assert cov["R1C1"].free_pct == pytest.approx(100.0)
    assert (cov["R1C2"].free_pct, cov["R1C2"].unknown_pct, cov["R1C2"].occupied_pct) == pytest.approx((25, 50, 25))
    assert cov["R0C0"].cells == 400


def test_zone_outside_map_is_unknown(tmp_path):
    omap = load_map(write_map(tmp_path))
    far = {"grid": {**ZONES["grid"], "origin": [10.0, 10.0]}}
    cov = zone_coverage(omap, build_zones(far))
    assert all(c.cells == 0 and c.unknown_pct == 100.0 and c.free_pct == 0.0 for c in cov)


def test_suggested_origin_and_fit_warning(tmp_path):
    omap = load_map(write_map(tmp_path))
    big = suggest_origin(omap, ZONES)       # free box x -1.25..0.75, y -1.25..1.25
    assert big.origin == pytest.approx((-1.75, -1.5))
    assert big.free_box == pytest.approx((-1.25, -1.25, 0.75, 1.25))
    assert len(big.warnings) == 1 and "does not fit" in big.warnings[0]

    small = suggest_origin(omap, {"grid": {**ZONES["grid"], "rows": 2, "cols": 2}})
    assert small.origin == pytest.approx((-1.25, -1.0)) and small.warnings == []


def test_suggest_origin_no_free_cells(tmp_path):
    (tmp_path / "m.pgm").write_bytes(b"P5\n2 2\n255\n" + bytes(4))
    (tmp_path / "map.yaml").write_text("image: m.pgm\nresolution: 1\norigin: [0, 0, 0]\n")
    with pytest.raises(ValueError, match="no free cells"):
        suggest_origin(load_map(tmp_path / "map.yaml"), ZONES)


def test_bad_inputs(tmp_path):
    with pytest.raises(FileNotFoundError, match="map yaml not found"):
        load_map(tmp_path / "nope.yaml")
    write_map(tmp_path)
    (tmp_path / "bad.yaml").write_text("image: m.pgm\n")
    with pytest.raises(ValueError, match="bad or missing key"):
        load_map(tmp_path / "bad.yaml")
    (tmp_path / "yaw.yaml").write_text("image: m.pgm\nresolution: 0.05\norigin: [0, 0, 1.0]\n")
    with pytest.raises(ValueError, match="yaw"):
        load_map(tmp_path / "yaw.yaml")
    (tmp_path / "res.yaml").write_text("image: m.pgm\nresolution: 0\norigin: [0, 0, 0]\n")
    with pytest.raises(ValueError, match="resolution"):
        load_map(tmp_path / "res.yaml")
    (tmp_path / "gone.yaml").write_text("image: gone.pgm\nresolution: 0.05\norigin: [0, 0, 0]\n")
    with pytest.raises(FileNotFoundError, match="map image"):
        load_map(tmp_path / "gone.yaml")
    (tmp_path / "junk.yaml").write_text("[1, 2")
    with pytest.raises(ValueError, match="not valid YAML"):
        load_map(tmp_path / "junk.yaml")


@pytest.mark.parametrize("content,msg", [
    (b"P6\n1 1\n255\n\x00", "not a PGM"),
    (b"P5\n4 4\n255\n\x00\x00", "expected 16 pixels"),
    (b"P5\n4 x\n255\n", "bad PGM header"),
    (b"P5\n4 4\n", "truncated"),
    (b"P2\n2 1\n255\n1 999\n", "above maxval"),
    (b"P2\n2 1\n255\n1 a\n", "non-numeric"),
])
def test_bad_pgm(tmp_path, content, msg):
    path = tmp_path / "x.pgm"
    path.write_bytes(content)
    with pytest.raises(ValueError, match=msg):
        read_pgm(path)


def test_png_and_overlay(tmp_path):
    omap = load_map(write_map(tmp_path))
    zones = build_zones(ZONES)
    img = render_overlay(omap, zones, zone_coverage(omap, zones))
    assert img.shape == (600, 600, 3) and img.dtype == np.uint8
    out = tmp_path / "o.png"
    write_png(out, img)
    data = out.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and b"IHDR" in data and data.endswith(b"IEND\xaeB`\x82")
    with pytest.raises(ValueError):
        write_png(out, np.zeros((3, 3)))
