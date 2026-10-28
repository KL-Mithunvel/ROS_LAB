#!/usr/bin/env python3
"""Health check of a recorded patrol bag.

    python tools/bag_check.py runs/patrol_20260101_120000 [--expected tools/bag_expected.yaml] [--timeline]

Reads metadata.yaml only (no ROS needed), prints per-topic message count and average rate, and
exits 1 if any expected topic is missing or too slow. `--timeline` additionally lists the
/patrol/warning and /patrol/decision events in time order; that needs rosbag2_py
(source /opt/ros/humble/setup.bash) and is skipped with a message otherwise.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from patrol.bagstats import (check_bag, find_metadata, format_event, format_table,  # noqa: E402
                             load_expected, read_metadata)

EVENT_TOPICS = ("/patrol/warning", "/patrol/decision")
DEFAULT_EXPECTED = Path(__file__).resolve().parent / "bag_expected.yaml"


def read_events(bag_dir, info):
    """[(time_ns, topic, text)] for the event topics, sorted by time. Needs rosbag2_py."""
    from rclpy.serialization import deserialize_message   # lazy: only with --timeline
    import rosbag2_py
    from std_msgs.msg import String

    reader_class = rosbag2_py.SequentialCompressionReader if info.compression else rosbag2_py.SequentialReader
    reader = reader_class()
    reader.open(rosbag2_py.StorageOptions(uri=str(bag_dir), storage_id=info.storage or "sqlite3"),
                rosbag2_py.ConverterOptions("", ""))
    reader.set_filter(rosbag2_py.StorageFilter(topics=list(EVENT_TOPICS)))
    events = []
    while reader.has_next():
        topic, data, t_ns = reader.read_next()
        events.append((t_ns, topic, deserialize_message(data, String).data))
    return sorted(events)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bag", help="rosbag2 folder (containing metadata.yaml)")
    parser.add_argument("--expected", default=str(DEFAULT_EXPECTED), help="expected-topics YAML")
    parser.add_argument("--timeline", action="store_true", help="list warning/decision events (needs rosbag2_py)")
    args = parser.parse_args(argv)
    try:
        info = read_metadata(args.bag)
        results = check_bag(info, load_expected(args.expected))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    comp = f", {info.compression}-compressed" if info.compression else ""
    print(f"{find_metadata(args.bag)}: {info.duration_s:.1f} s, {sum(info.counts.values())} messages{comp}\n")
    print(format_table(results))
    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)} PASS, {len(failed)} FAIL")

    if args.timeline:
        try:
            events = read_events(args.bag, info)
        except ImportError as exc:
            print(f"\n--timeline skipped: {exc} (source /opt/ros/humble/setup.bash)", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 - rosbag2_py raises plain RuntimeError for storage problems
            print(f"\n--timeline failed: {exc}", file=sys.stderr)
        else:
            print(f"\ntimeline ({len(events)} events):")
            for t_ns, topic, text in events:
                print(format_event(t_ns, info.start_ns, topic, text))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
