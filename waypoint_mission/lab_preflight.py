"""
lab_preflight.py — answer the "open items" of guide section 14 from the live robot.

    source /opt/ros/<distro>/setup.bash
    export ROS_DOMAIN_ID=<n>
    python3 lab_preflight.py            # run on the robot, or on the laptop
    python3 lab_preflight.py --quick    # skip the slow rate/TF probes

It only READS: it shells out to the `ros2` CLI, never publishes or moves anything.
Each line is PASS / WARN / FAIL / INFO. Paste the output into the Result column
of guide section 14. Parsers are pure functions covered by tests/test_preflight.py.
"""

import argparse
import os
import re
import subprocess
import sys

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"


# ---------------------------------------------------------------- pure parsers

def parse_lines(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def parse_hz(text):
    """Average rate (Hz) from `ros2 topic hz` output, or None if no sample yet."""
    rates = re.findall(r"average rate:\s*([0-9.]+)", text)
    return float(rates[-1]) if rates else None


def parse_topic_info_verbose(text):
    """Return (publisher_node_names, subscriber_node_names) from `ros2 topic info -v`."""
    publishers, subscribers = [], []
    name = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Node name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Endpoint type:") and name is not None:
            kind = line.split(":", 1)[1].strip().upper()
            (publishers if kind == "PUBLISHER" else subscribers).append(name)
            name = None
    return publishers, subscribers


def has_transform(tf2_echo_text):
    """True if `tf2_echo` printed at least one transform."""
    return bool(re.search(r"At time|Translation:", tf2_echo_text))


def find_matches(names, *needles):
    return sorted({n for n in names if any(s in n.lower() for s in needles)})


def classify_cmd_vel(publishers, subscribers):
    """Interpret who talks on /cmd_vel. Returns (status, message)."""
    pubs = [p for p in publishers if "collision_monitor" not in p]
    if "collision_monitor" in " ".join(publishers):
        return PASS, ("collision_monitor already publishes /cmd_vel "
                      f"(other publishers: {pubs or 'none'})")
    if not publishers:
        return WARN, "nobody publishes /cmd_vel right now (Nav2 not up, or it uses another name)"
    if len(set(publishers)) > 1:
        return WARN, (f"several nodes publish /cmd_vel: {sorted(set(publishers))} "
                      "- they will fight over the wheels")
    return INFO, (f"{publishers[0]} publishes /cmd_vel directly; the collision monitor must "
                  "take its output and publish /cmd_vel instead (guide section 7)")


# -------------------------------------------------------------------- probes

def run(cmd, timeout=10):
    """Run a command, return (ok, stdout+stderr). A timeout still returns its output."""
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return done.returncode == 0, done.stdout + done.stderr
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        return True, out.decode(errors="replace") if isinstance(out, bytes) else out
    except FileNotFoundError:
        return False, f"{cmd[0]}: command not found (source /opt/ros/<distro>/setup.bash?)"


def check_environment(report):
    distro = os.environ.get("ROS_DISTRO")
    report(PASS if distro else FAIL, "ROS distro (item 1)",
           distro or "ROS_DISTRO not set - source your ROS setup.bash")
    report(INFO, "ROS_DOMAIN_ID", os.environ.get("ROS_DOMAIN_ID", "(unset = 0)"))
    ok, _ = run(["python3", "-c", "import nav2_simple_commander"])
    report(PASS if ok else FAIL, "nav2_simple_commander importable (item 6)",
           "yes" if ok else "no - sudo apt install ros-<distro>-nav2-simple-commander")
    for pkg, why in (("nav2_collision_monitor", "item 4"), ("nav2_amcl", "item 2")):
        ok, out = run(["ros2", "pkg", "prefix", pkg])
        report(PASS if ok else FAIL, f"package {pkg} ({why})",
               out.strip() if ok else f"not installed - sudo apt install ros-{distro or '<distro>'}-"
               + pkg.replace("_", "-"))


def check_nodes(report):
    ok, out = run(["ros2", "node", "list"])
    if not ok:
        report(FAIL, "ros2 node list", out.strip() or "failed")
        return
    nodes = parse_lines(out)
    report(INFO, "nodes visible", f"{len(nodes)}" + ("  <-- none: wrong ROS_DOMAIN_ID / WSL2 NAT?"
                                                      if not nodes else ""))
    for label, needles, want in (
            ("AMCL running (item 2)", ("amcl",), True),
            ("map_server running", ("map_server",), True),
            ("Cartographer running (competes with AMCL for map->odom)", ("cartographer",), False),
            ("collision_monitor running (item 4)", ("collision_monitor",), True)):
        found = find_matches(nodes, *needles)
        if want:
            report(PASS if found else WARN, label, ", ".join(found) or "not running")
        else:
            report(WARN if found else PASS, label, ", ".join(found) or "not running")


def check_topics(report, quick):
    ok, out = run(["ros2", "topic", "list"])
    topics = parse_lines(out) if ok else []
    cmd_topics = [t for t in topics if "cmd_vel" in t]
    report(INFO, "cmd_vel topics (item 3)", ", ".join(cmd_topics) or "none found")
    camera = [t for t in topics if t.startswith("/camera")]
    report(PASS if "/camera/points" in topics else WARN, "RealSense /camera/points (item 5)",
           "present" if "/camera/points" in topics else
           f"missing (camera topics: {camera[:4] or 'none'}) - realsense:=True? USB 3?")
    report(PASS if "/scan" in topics else FAIL, "/scan present",
           "present" if "/scan" in topics else
           ("only /lidar/scan - merge_scan:=True not running?" if "/lidar/scan" in topics
            else "missing - LiDAR driver not up"))

    ok, out = run(["ros2", "topic", "info", "/cmd_vel", "-v"])
    if ok:
        status, msg = classify_cmd_vel(*parse_topic_info_verbose(out))
        report(status, "/cmd_vel chain (item 3)", msg)
    else:
        report(WARN, "/cmd_vel chain (item 3)", "topic does not exist yet - bring up the base/Nav2")

    if quick:
        return
    for topic in ("/scan", "/camera/points"):
        if topic not in topics:
            continue
        ok, out = run(["ros2", "topic", "hz", topic, "--window", "10"], timeout=6)
        hz = parse_hz(out)
        report(PASS if hz else WARN, f"{topic} rate",
               f"{hz:.1f} Hz" if hz else "no messages in 6 s")


def check_tf(report):
    for parent, child, note in (("map", "odom", "item 2: who owns map->odom"),
                                ("odom", "base_link", "wheel/scan odometry frame")):
        ok, out = run(["ros2", "run", "tf2_ros", "tf2_echo", parent, child], timeout=5)
        found = has_transform(out)
        report(PASS if found else WARN, f"TF {parent} -> {child} ({note})",
               "available" if found else "not available")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Acrux waypoint-mission pre-flight (read-only)")
    parser.add_argument("--quick", action="store_true", help="skip rate and TF probes (~20 s)")
    args = parser.parse_args(argv)

    results = []

    def report(status, name, detail):
        results.append(status)
        print(f"{status:<5} {name}: {detail}", flush=True)

    print("Acrux waypoint-mission pre-flight - read-only, nothing is published.\n")
    check_environment(report)
    check_nodes(report)
    check_topics(report, args.quick)
    if not args.quick:
        check_tf(report)
    print(f"\n{results.count(PASS)} pass, {results.count(WARN)} warn, "
          f"{results.count(FAIL)} fail.  Copy the lines into guide section 14.")
    return 1 if FAIL in results else 0


if __name__ == "__main__":
    sys.exit(main())
