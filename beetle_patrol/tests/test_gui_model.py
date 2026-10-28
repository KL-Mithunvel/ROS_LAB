import math

from gui import view_model as vm
from patrol import protocol as P

W = {"age": 0.5, "risk": 0.2, "distance": 0.2, "alert": 0.1}


def make_decision(t=1.0, chosen="z2"):
    def sc(zone, total, a):
        raw = {"age": a, "risk": 0.5, "distance": 0.5, "alert": 0.0}
        contrib = {"age": a * 0.5, "risk": 0.1, "distance": 0.1, "alert": 0.0}
        contrib["age"] = total - 0.2
        return {"zone": zone, "total": total, "distance_m": 1.0, "raw": raw, "contrib": contrib}
    scores = [sc("z1", 0.4, 0.2), sc("z2", 0.9, 0.9), sc("z3", 0.6, 0.5)]
    return P.build_decision(t, chosen, "Chose z2: stalest", W, scores)


def make_status(**kw):
    zones = [{"id": f"z{i}", "n": i + 1, "row": 0, "col": i, "cx": i - 1.0, "cy": 0.0, "w": 1.0, "h": 1.0, "risk": 0.5}
             for i in range(3)]
    heat = {z["id"]: {"age_s": 30 * i, "age_norm": i / 2, "alert": 0.0} for i, z in enumerate(zones)}
    args = dict(t=5.0, mode="idle", armed=True, nav_ready=True, explore_active=False,
                robot={"x": 0.0, "y": 0.0, "yaw": 0.0}, goal_zone="z1", goal_state="active",
                weights=W, zones=zones, heatmap=heat, skipped={"z0": "recent"},
                motion={"lidar": 0.1, "camera": 0.0, "fused": 0.07, "ego_moving": False, "ego_turning": False},
                decision=make_decision(), last_warning=None, recording=False, bag_dir=None)
    args.update(kw)
    return P.build_status(**args)


# --- colour
def test_colour_endpoints_and_clamp():
    assert vm.age_colour(0) == "#2ea043"
    assert vm.age_colour(1) == "#d63031"
    assert vm.age_colour(-5) == vm.age_colour(0)
    assert vm.age_colour(9) == vm.age_colour(1)
    assert vm.age_colour(None) == vm.age_colour(0)


def test_colour_monotonic_green_to_red():
    cols = [vm.age_colour(i / 20) for i in range(21)]
    reds = [int(c[1:3], 16) for c in cols]
    greens = [int(c[3:5], 16) for c in cols]
    assert reds[:11] == sorted(reds[:11])          # red rises green->yellow
    assert greens[10:] == sorted(greens[10:], reverse=True)   # green falls yellow->red
    assert len(set(cols)) > 15


# --- decision
def test_score_rows_sorted_and_chosen():
    rows = vm.score_rows(make_decision())
    assert [r["zone"] for r in rows] == ["z2", "z3", "z1"]
    assert [r["chosen"] for r in rows] == [True, False, False]


def test_segments_sum_to_scaled_total():
    rows = vm.score_rows(make_decision())
    mx = rows[0]["total"]
    for r in rows:
        segs = vm.segments(r, mx, 200)
        assert abs(segs[-1][2] - r["total"] / mx * 200) < 1e-6
        assert all(segs[i][2] == segs[i + 1][1] for i in range(3))   # contiguous


def test_score_rows_tolerates_bad_entries():
    d = make_decision()
    d["scores"].append({"zone": "bad"})
    assert len(vm.score_rows(d)) == 3
    assert vm.score_rows(None) == []


def test_skip_text():
    assert "cooldown" in vm.skip_text("z4", "cooldown")
    assert "recently" in vm.skip_text("z4", "recent")
    assert "weird" in vm.skip_text("z4", "weird")
    assert len(vm.skipped_lines(make_status())) == 1


def test_history_cap_and_dedupe():
    h = vm.History()
    assert h.add(make_decision(t=1.0))
    assert not h.add(make_decision(t=1.0))
    for i in range(2, 40):
        h.add(make_decision(t=float(i)))
    assert len(h.items) == vm.HISTORY_LEN
    assert h.newest_first()[0]["t"] == 39.0


# --- warnings / staleness
def test_warning_flash_timing_and_dedupe():
    log = vm.WarningLog()
    w = P.build_warning(10.0, 9.0, 1.0, 2.0, "z1", 0.8, 0.9, 0.3, "m")
    assert not log.flashing(0)
    assert log.add(w, now=100.0)
    assert not log.add(dict(w), now=100.5)
    assert log.flashing(100.0 + vm.FLASH_S - 0.01)
    assert not log.flashing(100.0 + vm.FLASH_S)
    assert not log.banner_on(200.0)
    states = {log.banner_on(100.0 + i * 0.1) for i in range(25)}
    assert states == {True, False}
    log.add(P.build_warning(11.0, 10.0, 0, 0, None, .6, .6, .6, "n"), now=101.0)
    assert log.items[0]["t"] == 11.0
    assert vm.warning_row(log.items[0])[1] == "-"


def test_warning_cap():
    log = vm.WarningLog(maxlen=3)
    for i in range(6):
        log.add(P.build_warning(float(i), float(i), 0, 0, None, .6, .6, .6, "n"), now=0)
    assert len(log.items) == 3 and log.items[0]["t"] == 5.0


def test_staleness_thresholds():
    assert vm.staleness(None, 10)[1] == "lost"
    assert vm.staleness(9.5, 10)[1] == "ok"
    assert vm.staleness(10 - vm.STALE_WARN_S, 10)[1] == "warn"
    text, level = vm.staleness(10 - vm.STALE_LOST_S - 1, 10)
    assert level == "lost" and "no /patrol/status for 5 s" == text


def test_domain_label():
    assert vm.domain_label("155")[1] is True
    assert vm.domain_label("154") == ("ROS domain 154", False)
    assert vm.domain_label(None)[1] is False


# --- weights
def test_normalise_and_debounce():
    n = vm.normalise_weights({"age": 2, "risk": 1, "distance": 1, "alert": 0})
    assert abs(sum(n.values()) - 1) < 1e-9 and n["age"] == 0.5
    assert vm.normalise_weights({"age": 0, "risk": 0, "distance": 0, "alert": 0})["age"] == 0.25
    assert "age 50%" in vm.weights_text(W)
    d = vm.Debouncer(delay=0.4)
    assert d.poll(0) is None
    d.change({"age": 1}, 1.0)
    assert d.poll(1.2) is None
    d.change({"age": 2}, 1.3)             # newer change restarts the timer
    assert d.poll(1.6) is None
    assert d.poll(1.75) == {"age": 2}
    assert d.poll(5.0) is None            # sent once only


# --- drive
def test_drive_caps_and_disabled():
    assert vm.drive_command({"forward"}, True, 5.0, 9.0) == (vm.LIN_CAP, 0.0)
    assert vm.drive_command({"left", "back"}, True, 5.0, 9.0) == (-vm.LIN_CAP, vm.ANG_CAP)
    assert vm.drive_command({"forward", "back"}, True) == (0.0, 0.0)
    assert vm.drive_command({"forward"}, False) == (0.0, 0.0)
    assert vm.drive_command(set(), True) == (0.0, 0.0)


def test_drive_enabled_rules():
    idle = make_status()
    assert vm.drive_enabled(idle, False)
    assert not vm.drive_enabled(idle, True)
    assert not vm.drive_enabled(make_status(armed=False), False)
    assert not vm.drive_enabled(make_status(armed=None), False)
    assert not vm.drive_enabled(make_status(mode="patrol"), False)
    assert not vm.drive_enabled(make_status(mode="mapping"), False)
    assert not vm.drive_enabled(None, False)


def test_held_keys_grace_and_sender():
    k = vm.HeldKeys(grace=0.08)
    k.press("forward")
    assert k.held(0) == {"forward"}
    k.release("forward", 1.0)
    k.press("forward")                    # auto-repeat pair
    assert k.held(1.5) == {"forward"}
    k.release("forward", 2.0)
    assert k.held(2.05) == {"forward"}
    assert k.held(2.1) == set()
    s = vm.DriveSender()
    assert s.step((0.0, 0.0)) == []
    assert s.step((0.1, 0.0)) == [(0.1, 0.0)]
    assert s.step((0.0, 0.0)) == [(0.0, 0.0)] * 3
    assert s.step((0.0, 0.0)) == []


def test_estop_latch():
    e = vm.EstopLatch()
    e.trigger()
    assert e.latched and vm.estop_active(e, None)
    e.release(False)
    assert e.latched
    e.release(True)
    assert not e.latched
    assert vm.estop_active(e, {"mode": "estop"})


# --- geometry
def test_viewport_round_trip():
    vp = vm.Viewport((-1.5, -1.5, 1.5, 1.5), 400, 300)
    for x, y in [(0, 0), (-1.5, -1.5), (1.2, 0.7)]:
        wx, wy = vp.to_world(*vp.to_canvas(x, y))
        assert abs(wx - x) < 1e-9 and abs(wy - y) < 1e-9
    assert vp.to_canvas(0, 1)[1] < vp.to_canvas(0, -1)[1]     # +y is up the screen


def test_zone_rect_and_bounds():
    st = make_status()
    b = vm.world_bounds(st["zones"])
    vp = vm.Viewport(b, 500, 300)
    x0, y0, x1, y1 = vm.zone_rect(vp, st["zones"][1])
    assert x1 > x0 and y1 > y0 and abs((x1 - x0) - vp.length(1.0)) < 1e-9
    mi = {"origin": (-5.0, -4.0), "width": 100, "height": 80, "resolution": 0.1}
    assert vm.world_bounds([], mi) == (-5.0, -4.0, 5.0, 4.0)
    assert vm.world_bounds([]) == (-2.0, -2.0, 2.0, 2.0)


def test_scan_points():
    robot = {"x": 1.0, "y": 1.0, "yaw": math.pi / 2}
    ranges = [1.0, float("inf"), float("nan"), 0.0, 99.0]
    pts = vm.scan_points(robot, 0.0, 0.1, ranges)
    assert len(pts) == 1
    assert abs(pts[0][0] - 1.0) < 1e-9 and abs(pts[0][1] - 2.0) < 1e-9
    assert vm.scan_points(None, 0, 0.1, ranges) == []
    big = vm.scan_points(robot, 0, 0.001, [2.0] * 3000, max_points=300)
    assert len(big) <= 300


# --- protocol samples flow through
def test_protocol_samples_through_view_model():
    st = make_status()
    P.validate_status(st)
    assert vm.score_rows(st["decision"])
    styles = vm.zone_styles(st)
    assert len(styles) == 3 and sum(1 for s in styles if s[4]) == 1
    assert styles[2][1] == vm.age_colour(1.0)
    assert [c[0] for c in vm.flags_text(st)][0] == "mode"
    assert vm.explanation_text(st["decision"]).startswith("Chose")
    vm.warning_row(P.build_warning(1.0, 1.0, 0.0, 0.0, None, .6, .6, .6, "m"))
    assert P.build_command("set_weights", weights=W)["cmd"] == "set_weights"
    assert vm.zone_styles(None) == [] and vm.flags_text(None)


# --- dynamic zones
def zone(zid, n, cx, cy, size=1.0):
    return {"id": zid, "n": n, "row": 0, "col": 0, "cx": cx, "cy": cy, "w": size, "h": size, "risk": 0.3}


def test_fit_bounds_unchanged_when_zones_fit_and_grows_when_not():
    bounds = (-2.0, -2.0, 2.0, 2.0)
    assert vm.fit_bounds(bounds, [zone("a", 1, 0, 0), zone("b", 2, 1.5, 1.5)]) == bounds
    assert vm.fit_bounds(bounds, [zone("c", 3, 3.0, -1.0)]) == (-2.0, -2.0, 3.5, 2.0)
    assert vm.fit_bounds(bounds, [zone("d", 4, -2.0, -4.0)]) == (-2.5, -4.5, 2.0, 2.0)
    assert vm.fit_bounds(bounds, None) == bounds


def test_fit_bounds_keeps_every_zone_inside_the_viewport():
    zones = [zone("a", 1, 0, 0), zone("b", 2, 6.0, 5.0), zone("c", 3, -4.0, -3.0)]
    vp = vm.Viewport(vm.fit_bounds(vm.world_bounds(zones[:1]), zones), 400, 300)
    for z in zones:
        x0, y0, x1, y1 = vm.zone_rect(vp, z)
        assert 0 <= x0 < x1 <= 400 and 0 <= y0 < y1 <= 300


def test_zone_title_numbers_and_display():
    st = make_status()
    assert [vm.zone_title(z) for z in st["zones"]] == ["1", "2", "3"]
    assert vm.zone_title({"id": "x"}) == "?"
    nums = vm.zone_numbers(st)
    assert nums == {"z0": 1, "z1": 2, "z2": 3}
    assert vm.zone_display("z1", nums) == "#2 z1" and vm.zone_display("q", nums) == "q"
    assert vm.zone_numbers(None) == {}


def test_new_zone_tracker_highlights_for_three_seconds_after_the_baseline():
    t = vm.NewZoneTracker()
    first = {"zones": [zone("a", 1, 0, 0)]}
    t.update(first, 10.0)
    assert not t.is_new("a", 10.0)                                   # baseline: no flash on connect
    grown = {"zones": [zone("a", 1, 0, 0), zone("b", 2, 1, 0)]}
    t.update(grown, 11.0)
    assert t.is_new("b", 11.0) and t.is_new("b", 13.9) and not t.is_new("b", 14.0)
    t.update(grown, 12.0)
    assert t.is_new("b", 12.0) and t.is_new("b", 12.5)               # not re-stamped by later statuses
    assert not t.is_new("a", 11.0)


def test_new_zone_tracker_flashes_again_after_a_reset():
    t = vm.NewZoneTracker()
    t.update({"zones": [zone("a", 1, 0, 0), zone("b", 2, 1, 0)]}, 1.0)
    t.update({"zones": []}, 20.0)                                    # node reset the zones
    t.update({"zones": [zone("a", 1, 5, 5)]}, 21.0)
    assert t.is_new("a", 21.5) and not t.is_new("b", 21.5)
    t.update(None, 22.0)
    assert not t.is_new("a", 22.0)


def test_set_start_enabled_only_when_idle_and_not_estopped():
    assert vm.set_start_enabled({"mode": "idle"}, False)
    assert not vm.set_start_enabled({"mode": "idle"}, True)
    for mode in ("patrol", "mapping", "estop"):
        assert not vm.set_start_enabled({"mode": mode}, False)
    assert not vm.set_start_enabled(None, False)
