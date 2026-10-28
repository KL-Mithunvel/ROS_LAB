"""Summarise a rosbag2 run from its metadata.yaml (offline, no ROS needed).

Message counts and the duration are stored in metadata.yaml, also for zstd-compressed bags, so a
health check does not have to open the database. `check_bag` compares the average rate of each
topic against an expected table (tools/bag_expected.yaml).
"""
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

SUPPORTED_VERSIONS = range(1, 10)   # rosbag2 metadata "version" (Humble writes 4)


@dataclass(frozen=True)
class BagInfo:
    duration_s: float
    start_ns: int
    counts: dict            # topic -> message count
    compression: str        # "" if not compressed
    storage: str


@dataclass(frozen=True)
class TopicResult:
    topics: tuple           # alternatives of the expectation
    best: str               # alternative that was judged ("" if none was recorded)
    count: int
    hz: float               # None if the duration is zero
    min_hz: float           # None = presence only
    ok: bool
    note: str

    @property
    def status(self):
        return "PASS" if self.ok else "FAIL"


def _read_yaml(path, what):
    try:
        data = yaml.safe_load(Path(path).read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"{what} not found: {path}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"{what} {path} is not valid YAML: {exc}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{what} {path} must contain a mapping at the top level")
    return data


def find_metadata(bag_dir):
    """Path of metadata.yaml for a bag folder (or the metadata file itself)."""
    path = Path(bag_dir)
    return path / "metadata.yaml" if path.is_dir() else path


def read_metadata(bag_dir):
    """Parse a rosbag2 metadata.yaml into a BagInfo."""
    path = find_metadata(bag_dir)
    info = _read_yaml(path, "bag metadata").get("rosbag2_bagfile_information")
    if not isinstance(info, dict):
        raise ValueError(f"{path}: no 'rosbag2_bagfile_information' section - not a rosbag2 metadata file")
    version = info.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"{path}: unsupported metadata version {version!r} "
                         f"(supported: {SUPPORTED_VERSIONS.start}..{SUPPORTED_VERSIONS.stop - 1})")
    try:
        duration_s = float(info["duration"]["nanoseconds"]) / 1e9
        start_ns = int(info["starting_time"]["nanoseconds_since_epoch"])
        counts = {}
        for entry in info["topics_with_message_count"]:
            counts[str(entry["topic_metadata"]["name"])] = int(entry["message_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path}: bad or missing field ({exc!r})") from None
    if duration_s < 0:
        raise ValueError(f"{path}: negative duration")
    return BagInfo(duration_s, start_ns, counts, str(info.get("compression_format") or ""),
                   str(info.get("storage_identifier") or ""))


def load_expected(path):
    """Parse bag_expected.yaml into a list of (topics tuple, min_hz or None)."""
    checks = _read_yaml(path, "expected-topics file").get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError(f"{path}: needs a non-empty 'checks' list")
    expected = []
    for i, item in enumerate(checks):
        topics = item.get("topics") if isinstance(item, dict) else None
        if not isinstance(topics, list) or not topics:
            raise ValueError(f"{path}: checks[{i}] needs a non-empty 'topics' list")
        min_hz = item.get("min_hz")
        if min_hz is not None:
            try:
                min_hz = float(min_hz)
            except (TypeError, ValueError):
                raise ValueError(f"{path}: checks[{i}] min_hz {min_hz!r} is not a number") from None
            if min_hz <= 0:
                raise ValueError(f"{path}: checks[{i}] min_hz must be > 0")
        expected.append((tuple(str(t) for t in topics), min_hz))
    return expected


def rate_hz(count, duration_s):
    """Average rate, or None for a zero-length bag."""
    return count / duration_s if duration_s > 0 else None


def check_bag(info, expected):
    """One TopicResult per expectation. An entry passes if any alternative meets it."""
    results = []
    for topics, min_hz in expected:
        recorded = [t for t in topics if info.counts.get(t, 0) > 0]
        if not recorded:
            results.append(TopicResult(topics, "", 0, None, min_hz, False, "missing (no messages)"))
            continue
        best = max(recorded, key=lambda t: info.counts[t])
        count = info.counts[best]
        hz = rate_hz(count, info.duration_s)
        if min_hz is None:
            ok, note = True, "present"
        elif hz is None:
            ok, note = False, "zero duration - rate unknown"
        else:
            ok = hz >= min_hz
            note = f"need >= {min_hz:g} Hz" if not ok else ""
        results.append(TopicResult(topics, best, count, hz, min_hz, ok, note))
    return results


def format_table(results):
    """Text table of check_bag results."""
    lines = [f"{'topic':<40}{'msgs':>8}{'Hz':>9}{'min Hz':>8}  status"]
    for r in results:
        name = r.best or " | ".join(r.topics)
        hz = "-" if r.hz is None else f"{r.hz:.1f}"
        want = "-" if r.min_hz is None else f"{r.min_hz:g}"
        lines.append(f"{name:<40}{r.count:>8}{hz:>9}{want:>8}  {r.status}" + (f"  ({r.note})" if r.note else ""))
    return "\n".join(lines)


def format_event(t_ns, start_ns, topic, payload):
    """One timeline line: '+12.34s WARNING  <details>' from a /patrol/warning|decision String payload."""
    kind = "WARNING" if topic.endswith("warning") else "DECISION" if topic.endswith("decision") else topic
    try:
        data = json.loads(payload)
        text = json.dumps(data, sort_keys=True, separators=(",", ":")) if isinstance(data, dict) else str(data)
    except ValueError:
        text = payload
    return f"+{(t_ns - start_ns) / 1e9:8.2f}s  {kind:<8}  {text}"
