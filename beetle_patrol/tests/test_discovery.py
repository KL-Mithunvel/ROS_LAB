"""Dynamic zones: ZoneMap growth, map-driven discovery on maps that grow in steps, config validation."""
import numpy as np
import pytest

from patrol.discovery import OccupancyInfo, cell_fractions, discover_zones
from patrol.heatmap import DynamicConfig, ZoneMap, dynamic_config

RES = 0.1          # map resolution (m); 10 map cells per 1 m zone edge
ANCHOR = (0.0, 0.0)
SIDE = 60          # 6 m x 6 m map, origin (-3, -3)


def cfg(**kw):
    return DynamicConfig(**kw)


def blank():
    return np.full((SIDE, SIDE), -1, dtype=np.int8)


def paint(grid, x0, y0, x1, y1, value):
    """Fill the world rectangle [x0,x1) x [y0,y1) (metres) of a map with origin (-3,-3)."""
    i0, i1 = round((x0 + 3) / RES), round((x1 + 3) / RES)
    j0, j1 = round((y0 + 3) / RES), round((y1 + 3) / RES)
    grid[j0:j1, i0:i1] = value


def info(grid):
    return OccupancyInfo(SIDE, SIDE, RES, -3.0, -3.0, grid.ravel())


def fresh_map(**kw):
    zm = ZoneMap([], 0.0, dynamic=cfg(**kw))
    zm.reset(ANCHOR, 0.0)
    return zm


def ids(zm):
    return {z.id: z.n for z in zm.zones}


# --- ZoneMap -----------------------------------------------------------------------------
def test_reset_makes_zone_one_centred_on_the_anchor():
    zm = ZoneMap([], 5.0, dynamic=cfg())
    zm.reset((2.3, -1.1), 5.0)
    (z,) = zm.zones
    assert (z.id, z.n, z.cx, z.cy, z.w, z.h) == ("R0C0", 1, 2.3, -1.1, 1.0, 1.0)
    assert zm.cell_of(2.3 + 0.49, -1.1 - 0.49) == (0, 0)
    assert zm.cell_of(2.3 + 0.51, -1.1) == (0, 1)


def test_negative_indices_and_sequential_numbers():
    zm = fresh_map()
    a = zm.add_zone(-1, 0, 3.0)
    b = zm.add_zone(0, -2, 4.0)
    assert (a.id, a.n, a.cy) == ("R-1C0", 2, -1.0)
    assert (b.id, b.n, b.cx) == ("R0C-2", 3, -2.0)
    assert zm.age_s("R-1C0", 10.0) == 7.0           # a new zone starts fresh at its creation time
    with pytest.raises(ValueError):
        zm.add_zone(0, 0, 5.0)


def test_add_zone_needs_an_anchor_and_dynamic_mode():
    with pytest.raises(RuntimeError, match="anchor"):
        ZoneMap([], 0.0, dynamic=cfg()).add_zone(0, 0, 0.0)
    with pytest.raises(RuntimeError, match="not enabled"):
        ZoneMap([], 0.0).reset((0, 0), 0.0)


def test_ensure_zone_at_creates_the_cell_once_unless_blocked_or_capped():
    zm = fresh_map(max_zones=3)
    z = zm.ensure_zone_at(1.2, 0.1, 1.0)
    assert z.id == "R0C1" and z.n == 2
    assert zm.ensure_zone_at(1.4, -0.2, 2.0) is z and len(zm.zones) == 2
    zm.blocked.add((5, 5))
    assert zm.ensure_zone_at(5.0, 5.0, 3.0) is None
    assert zm.ensure_zone_at(0.0, 2.0, 3.0).id == "R2C0"
    assert zm.ensure_zone_at(0.0, -2.0, 3.0) is None        # cap of 3 reached
    assert len(zm.zones) == 3


def test_ensure_zone_at_before_anchor_is_none():
    assert ZoneMap([], 0.0, dynamic=cfg()).ensure_zone_at(0, 0, 0.0) is None


def test_reset_clears_everything():
    zm = fresh_map()
    zm.add_zone(0, 1, 1.0)
    zm.record_alert(1.0, 0.0, 2.0)
    zm.blocked.add((3, 3))
    zm.reset((10.0, 10.0), 9.0)
    assert ids(zm) == {"R0C0": 1} and zm.blocked == set() and zm.alert_level("R0C0", 9.0) == 0.0
    assert zm.zones[0].cx == 10.0


# --- fractions ---------------------------------------------------------------------------
def test_cell_fractions_count_unknown_as_not_free():
    g = blank()
    paint(g, -0.5, -0.5, 0.5, 0.0, 0)          # lower half of zone 1 free
    paint(g, 0.3, 0.0, 0.5, 0.5, 100)          # a strip occupied
    free, occ = cell_fractions(info(g), 0.0, 0.0, 1.0)
    assert free == pytest.approx(0.5) and occ == pytest.approx(0.1)


def test_cell_partly_outside_the_map_counts_the_outside_as_unknown():
    g = blank()
    paint(g, 2.0, -0.5, 3.0, 0.5, 0)           # free up to the map edge (x = 3)
    free, _ = cell_fractions(info(g), 3.0, 0.0, 1.0)     # cell centred on the edge: half outside
    assert free == pytest.approx(0.5)


def test_occupancy_info_validates_size():
    with pytest.raises(ValueError, match="data has"):
        OccupancyInfo(2, 2, 0.1, 0, 0, [0, 0, 0])


# --- discovery on growing maps ------------------------------------------------------------
def test_first_frame_with_only_the_start_patch_gives_exactly_zone_one():
    g = blank()
    paint(g, -0.5, -0.5, 0.5, 0.5, 0)
    zm = fresh_map()
    assert discover_zones(info(g), zm, cfg(), 1.0) == []
    assert ids(zm) == {"R0C0": 1}


def test_corridor_east_adds_zone_two_with_the_right_cell_and_number():
    g = blank()
    paint(g, -0.5, -0.5, 0.5, 0.5, 0)
    zm = fresh_map()
    discover_zones(info(g), zm, cfg(), 1.0)
    paint(g, 0.5, -0.5, 1.5, 0.5, 0)                       # corridor east, free
    new = discover_zones(info(g), zm, cfg(), 2.0)
    assert [(z.id, z.n, z.cx, z.cy) for z in new] == [("R0C1", 2, 1.0, 0.0)]
    assert zm.age_s("R0C1", 2.0) == 0.0
    paint(g, 1.5, -0.5, 2.5, 0.5, 0)                       # extends further: next ring
    new = discover_zones(info(g), zm, cfg(), 3.0)
    assert [(z.id, z.n) for z in new] == [("R0C2", 3)]


def test_one_pass_adds_one_ring_only():
    g = blank()
    paint(g, -0.5, -0.5, 2.5, 0.5, 0)                      # three cells free in a row
    zm = fresh_map()
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 1.0)] == ["R0C1"]
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 2.0)] == ["R0C2"]


def test_threshold_is_inclusive_and_just_below_does_not_create():
    g = blank()
    paint(g, -0.5, -0.5, 0.5, 0.5, 0)
    paint(g, 0.5, -0.5, 0.9, 0.5, 0)                       # exactly 40 % of the east cell
    zm = fresh_map()
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 1.0)] == ["R0C1"]
    g2 = blank()
    paint(g2, -0.5, -0.5, 0.5, 0.5, 0)
    paint(g2, 0.5, -0.5, 0.8, 0.5, 0)                      # 30 %
    assert discover_zones(info(g2), fresh_map(), cfg(), 1.0) == []


def test_wall_heavy_cells_are_blocked_and_never_created():
    g = blank()
    paint(g, -0.5, -0.5, 1.5, 0.5, 0)
    paint(g, 0.5, -0.5, 1.5, 0.0, 100)                     # east cell: half wall, half free
    zm = fresh_map()
    assert discover_zones(info(g), zm, cfg(), 1.0) == []
    assert zm.blocked == {(0, 1)}
    assert zm.ensure_zone_at(1.0, 0.0, 2.0) is None        # the robot standing there does not override it
    paint(g, 0.5, -0.5, 1.5, 0.0, 0)                       # the map changes its mind
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 3.0)] == ["R0C1"]
    assert zm.blocked == set()


def test_disconnected_free_pocket_waits_for_its_neighbour():
    g = blank()
    paint(g, -0.5, -0.5, 0.5, 0.5, 0)
    paint(g, 1.5, -0.5, 2.5, 0.5, 0)                       # pocket two cells east, gap unknown
    zm = fresh_map()
    assert discover_zones(info(g), zm, cfg(), 1.0) == []
    paint(g, 0.5, -0.5, 1.5, 0.5, 0)                       # the gap is revealed
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 2.0)] == ["R0C1"]
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 3.0)] == ["R0C2"]


def test_diagonal_neighbours_count_and_negative_indices_appear():
    g = blank()
    paint(g, -1.5, -1.5, 0.5, 0.5, 0)
    zm = fresh_map()
    new = discover_zones(info(g), zm, cfg(), 1.0)
    assert {z.id for z in new} == {"R-1C-1", "R-1C0", "R0C-1"}
    assert [z.n for z in new] == [2, 3, 4]
    assert new[-1].id == "R-1C-1"                          # numbering: nearest to the anchor first


def test_max_zones_caps_growth():
    g = np.zeros((SIDE, SIDE), dtype=np.int8)              # everything free
    zm = fresh_map(max_zones=4)
    discover_zones(info(g), zm, cfg(max_zones=4), 1.0)
    assert len(zm.zones) == 4 and [z.n for z in zm.zones] == [1, 2, 3, 4]
    assert discover_zones(info(g), zm, cfg(max_zones=4), 2.0) == []


def test_robot_cell_is_a_candidate_even_when_not_adjacent():
    g = blank()
    paint(g, -0.5, -0.5, 0.5, 0.5, 0)
    paint(g, 1.5, -0.5, 2.5, 0.5, 0)
    zm = fresh_map()
    assert [z.id for z in discover_zones(info(g), zm, cfg(), 1.0, robot_xy=(2.0, 0.0))] == ["R0C2"]


def test_discovery_without_an_anchor_does_nothing():
    zm = ZoneMap([], 0.0, dynamic=cfg())
    assert discover_zones(info(np.zeros((SIDE, SIDE), dtype=np.int8)), zm, cfg(), 1.0) == []


def test_non_default_anchor_shifts_the_cells():
    g = np.zeros((SIDE, SIDE), dtype=np.int8)
    zm = ZoneMap([], 0.0, dynamic=cfg())
    zm.reset((0.5, 0.5), 0.0)                              # anchor not at a map-cell corner
    z = discover_zones(info(g), zm, cfg(), 1.0)[0]
    assert (z.cx - 0.5) % 1.0 == pytest.approx(0.0) and (z.cy - 0.5) % 1.0 == pytest.approx(0.0)


# --- config ------------------------------------------------------------------------------
def test_shipped_zones_yaml_keeps_dynamic_zones_off_but_valid():
    """Reduced scope: the shipped config patrols the fixed 3x3 grid; the dynamic section stays valid."""
    from patrol.config import load_settings
    c = dynamic_config(load_settings().zones)
    assert not c.enabled and (c.cell_size_m, c.min_free_fraction, c.blocked_occupied_fraction,
                              c.max_zones, c.map_update_s) == (1.0, 0.40, 0.50, 50, 2.0)


def test_no_dynamic_section_means_static():
    assert dynamic_config({"grid": {}}).enabled is False


@pytest.mark.parametrize("bad", [
    {"enabled": "yes"}, {"cell_size_m": 0}, {"min_free_fraction": 0}, {"min_free_fraction": 1.5},
    {"blocked_occupied_fraction": 0}, {"max_zones": 0}, {"max_zones": 2.5}, {"map_update_s": -1}])
def test_bad_dynamic_values_are_rejected(bad):
    with pytest.raises(ValueError, match="dynamic"):
        dynamic_config({"dynamic": bad})


def test_unknown_dynamic_key_is_rejected_naming_zones_yaml():
    with pytest.raises(ValueError, match=r"zones.yaml \[dynamic\].*cell_size"):
        dynamic_config({"dynamic": {"cell_size": 1.0}})
    with pytest.raises(ValueError, match="mapping"):
        dynamic_config({"dynamic": 3})
