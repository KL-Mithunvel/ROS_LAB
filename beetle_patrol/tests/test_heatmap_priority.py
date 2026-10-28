import pytest

from patrol.config import load_settings
from patrol.heatmap import HeatmapConfig, ZoneMap, build_zones
from patrol.priority import Weights, choose_next, explain, score_zones

GRID = {"grid": {"origin": [0, 0], "rows": 2, "cols": 3, "cell_w": 2.0, "cell_h": 2.0}}


def make_map(extra=None, start=0.0, **hm):
    return ZoneMap(build_zones({**GRID, **(extra or {})}), start, HeatmapConfig(**hm))


def test_build_zones_layout_and_overrides():
    zones = build_zones({**GRID, "default_risk": 0.3, "risk": {"1,2": 0.9}, "blocked": ["0,1"]})
    ids = {z.id: z for z in zones}
    assert len(zones) == 5 and "R0C1" not in ids
    assert (ids["R0C0"].cx, ids["R0C0"].cy) == (1.0, 1.0)
    assert (ids["R1C2"].cx, ids["R1C2"].cy) == (5.0, 3.0)
    assert ids["R1C2"].risk == 0.9 and ids["R0C0"].risk == 0.3


@pytest.mark.parametrize("bad", [
    {"grid": {"origin": [0, 0], "rows": 0, "cols": 1, "cell_w": 1, "cell_h": 1}},
    {"grid": {"rows": 1}},
    {**GRID, "risk": {"0,0": 1.5}},
    {**GRID, "risk": {"zero-zero": 0.5}},
    {**GRID, "risk": {"2,0": 0.5}},          # row 2 does not exist on a 2-row grid
    {**GRID, "blocked": ["0,3"]},            # col 3 does not exist on a 3-col grid
    {**GRID, "blocked": [f"{r},{c}" for r in range(2) for c in range(3)]},
])
def test_build_zones_rejects_bad_config(bad):
    with pytest.raises(ValueError):
        build_zones(bad)


def test_visit_resets_age_only_for_nearby_zones():
    zm = make_map(visit_radius_m=1.2, max_age_s=100)
    assert zm.mark_visited(1.0, 1.0, t=50) == ["R0C0"]
    assert zm.age_s("R0C0", 60) == 10 and zm.age_s("R0C1", 60) == 60
    assert zm.age_norm("R0C1", 500) == 1.0          # capped


def test_older_visit_never_overwrites_newer():
    zm = make_map()
    zm.mark_visited(1, 1, t=50)
    zm.mark_visited(1, 1, t=10)
    assert zm.age_s("R0C0", 60) == 10


def test_alert_fades_and_lands_in_right_zone():
    zm = make_map(alert_memory_s=100)
    assert zm.record_alert(5.0, 3.0, t=0) == "R1C2"
    assert zm.alert_level("R1C2", 0) == 1.0
    assert zm.alert_level("R1C2", 50) == pytest.approx(0.5)
    assert zm.alert_level("R1C2", 500) == 0.0
    assert zm.record_alert(99, 99, t=0) is None


def test_priority_prefers_stalest_when_only_age_counts():
    zm = make_map(max_age_s=100)
    zm.mark_visited(1, 1, 90)    # R0C0 fresh
    scores = score_zones(zm, (1, 1), now=100, weights=Weights(1, 0, 0, 0))
    assert scores[0].zone_id != "R0C0" and scores[-1].zone_id == "R0C0"


def test_distance_breaks_a_tie_between_equally_stale_zones():
    zm = make_map()
    scores = score_zones(zm, (1, 1), now=100, weights=Weights(0.5, 0, 0.5, 0))
    assert scores[0].zone_id == "R0C0"   # the zone the robot stands in is closest


def test_risk_and_alert_raise_a_zone():
    zm = make_map({"risk": {"1,1": 1.0}}, alert_memory_s=100)
    zm.record_alert(5.0, 1.0, t=100)     # R0C2
    by_risk = score_zones(zm, (3, 2), 100, Weights(0, 1, 0, 0))
    by_alert = score_zones(zm, (3, 2), 100, Weights(0, 0, 0, 1))
    assert by_risk[0].zone_id == "R1C1" and by_alert[0].zone_id == "R0C2"


def test_contributions_sum_to_total_and_weights_are_normalised():
    zm = make_map()
    for s in score_zones(zm, (0, 0), 100, Weights(5, 2, 2, 1)):
        assert sum(s.contrib.values()) == pytest.approx(s.total)
        assert 0 <= s.total <= 1


def test_choose_next_skips_excluded_zones_and_handles_none_left():
    zm = make_map()
    scores = score_zones(zm, (0, 0), 100, Weights())
    first = choose_next(scores)
    assert choose_next(scores, exclude={first.zone_id}).zone_id != first.zone_id
    assert choose_next(scores, exclude={s.zone_id for s in scores}) is None


def test_explain_names_chosen_and_runner_up():
    scores = score_zones(make_map(), (0, 0), 100, Weights())
    text = explain(scores[0], scores)
    assert scores[0].zone_id in text and scores[1].zone_id in text and "mainly on" in text


@pytest.mark.parametrize("w", [(-1, 1, 1, 1), (0, 0, 0, 0)])
def test_bad_weights_rejected(w):
    with pytest.raises(ValueError):
        Weights(*w)


def test_shipped_yaml_files_load():
    s = load_settings()
    zm = ZoneMap.from_mapping(s.zones, {}, 0.0)
    assert len(zm.zones) == 9 and s.priority.weight_obj().age == 0.5
    assert zm.zone_at(-1.0, -1.0).id == "R0C0" and zm.zone_at(1.0, 1.0).id == "R2C2"
