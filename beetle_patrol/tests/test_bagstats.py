import pytest
import yaml

from patrol.bagstats import (BagInfo, check_bag, format_event, format_table, load_expected, rate_hz,
                             read_metadata)


def write_meta(folder, counts, duration_s=10.0, version=4, compression="zstd"):
    topics = [{"topic_metadata": {"name": n, "type": "x/msg/Y", "serialization_format": "cdr"},
               "message_count": c} for n, c in counts.items()]
    info = {"version": version, "storage_identifier": "sqlite3", "duration": {"nanoseconds": int(duration_s * 1e9)},
            "starting_time": {"nanoseconds_since_epoch": 1_700_000_000_000_000_000},
            "message_count": sum(counts.values()), "topics_with_message_count": topics,
            "compression_format": compression, "compression_mode": "FILE" if compression else ""}
    folder.mkdir(exist_ok=True)
    (folder / "metadata.yaml").write_text(yaml.safe_dump({"rosbag2_bagfile_information": info}))
    return folder


EXPECTED = [(("/scan",), 5.0), (("/pi_camera/image_raw/compressed", "/patrol/camera/compressed"), 2.0),
            (("/tf_static",), None)]


def test_read_metadata(tmp_path):
    info = read_metadata(write_meta(tmp_path / "bag", {"/scan": 100, "/tf": 5}))
    assert info.duration_s == 10.0 and info.counts == {"/scan": 100, "/tf": 5}
    assert info.compression == "zstd" and info.storage == "sqlite3"
    assert info.start_ns == 1_700_000_000_000_000_000
    assert read_metadata(tmp_path / "bag" / "metadata.yaml").counts == info.counts   # file path works too
    assert read_metadata(write_meta(tmp_path / "plain", {}, compression="")).compression == ""


def test_pass_fail_logic():
    info = BagInfo(10.0, 0, {"/scan": 50, "/patrol/camera/compressed": 19, "/tf_static": 1}, "", "")
    scan, cam, static = check_bag(info, EXPECTED)
    assert scan.ok and scan.hz == 5.0                       # exactly at the limit passes
    assert not cam.ok and cam.best == "/patrol/camera/compressed" and cam.hz == pytest.approx(1.9)
    assert static.ok and static.note == "present"
    assert "FAIL" in format_table([scan, cam, static]) and "need >= 2 Hz" in format_table([cam])


def test_alternative_topic_picks_busiest():
    info = BagInfo(10.0, 0, {"/pi_camera/image_raw/compressed": 30, "/patrol/camera/compressed": 5}, "", "")
    cam = check_bag(info, [EXPECTED[1]])[0]
    assert cam.ok and cam.best == "/pi_camera/image_raw/compressed" and cam.hz == 3.0


def test_missing_topic_and_zero_count():
    info = BagInfo(10.0, 0, {"/scan": 0}, "", "")
    scan, cam, static = check_bag(info, EXPECTED)
    assert not scan.ok and not cam.ok and not static.ok and "missing" in scan.note
    assert scan.hz is None and "/scan" in format_table([scan])


def test_zero_duration():
    assert rate_hz(10, 0.0) is None
    info = BagInfo(0.0, 0, {"/scan": 3, "/tf_static": 1}, "", "")
    scan, _, static = check_bag(info, EXPECTED)
    assert not scan.ok and "zero duration" in scan.note
    assert static.ok                                         # presence-only needs no duration


def test_unknown_format_version_and_bad_files(tmp_path):
    with pytest.raises(ValueError, match="unsupported metadata version 99"):
        read_metadata(write_meta(tmp_path / "v", {"/scan": 1}, version=99))
    with pytest.raises(FileNotFoundError, match="bag metadata not found"):
        read_metadata(tmp_path / "empty")
    (tmp_path / "w").mkdir()
    (tmp_path / "w" / "metadata.yaml").write_text("foo: 1\n")
    with pytest.raises(ValueError, match="rosbag2_bagfile_information"):
        read_metadata(tmp_path / "w")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "metadata.yaml").write_text("rosbag2_bagfile_information: {version: 4}\n")
    with pytest.raises(ValueError, match="bad or missing field"):
        read_metadata(tmp_path / "b")
    (tmp_path / "j").mkdir()
    (tmp_path / "j" / "metadata.yaml").write_text("[1, 2")
    with pytest.raises(ValueError, match="not valid YAML"):
        read_metadata(tmp_path / "j")


def test_load_expected(tmp_path):
    path = tmp_path / "e.yaml"
    path.write_text("checks:\n  - {topics: [/scan], min_hz: 5}\n  - {topics: [/map]}\n")
    assert load_expected(path) == [(("/scan",), 5.0), (("/map",), None)]
    for text, msg in [("checks: []\n", "non-empty"), ("checks: [{min_hz: 1}]\n", "topics"),
                      ("checks: [{topics: [/a], min_hz: fast}]\n", "not a number"),
                      ("checks: [{topics: [/a], min_hz: 0}]\n", "> 0")]:
        path.write_text(text)
        with pytest.raises(ValueError, match=msg):
            load_expected(path)
    with pytest.raises(FileNotFoundError):
        load_expected(tmp_path / "none.yaml")


def test_format_event():
    line = format_event(12_340_000_000, 0, "/patrol/warning", '{"b": 2, "a": "x"}')
    assert line == '+   12.34s  WARNING   {"a":"x","b":2}'
    assert "DECISION" in format_event(0, 0, "/patrol/decision", "not json")
    assert format_event(0, 0, "/patrol/decision", "not json").endswith("not json")
