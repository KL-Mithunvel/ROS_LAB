"""Live plot of the MENGJIE Coin-D6 TOF lidar over a USB2LDS (CP210x) adapter.

    python plot_live.py                       # auto-detect port, 230400 baud, ld06 profile
    python plot_live.py --port COM3 --max-range 6
    python plot_live.py --sniff               # no plotting: dump raw bytes + guess the header
"""
from __future__ import annotations

import argparse
import sys
import time

import coin_d6 as cd


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="serial port, e.g. COM3 (default: auto-detect CP210x)")
    ap.add_argument("--baud", type=int, default=cd.DEFAULT_BAUD)
    ap.add_argument("--profile", default="ld06", choices=sorted(cd.PROFILES), help="built-in frame layout")
    ap.add_argument("--profile-file", help="YAML frame layout; overrides --profile")
    ap.add_argument("--max-range", type=float, default=8.0, help="plot radius in metres")
    ap.add_argument("--dtr", type=int, choices=(0, 1), help="force DTR line (some adapters gate the motor)")
    ap.add_argument("--rts", type=int, choices=(0, 1), help="force RTS line")
    ap.add_argument("--sniff", action="store_true", help="dump raw bytes and guess the header, then exit")
    ap.add_argument("--sniff-all-bauds", action="store_true", help="with --sniff: try common baud rates")
    ap.add_argument("--sniff-seconds", type=float, default=2.0)
    return ap.parse_args(argv)


def _line(value: int | None) -> bool | None:
    return None if value is None else bool(value)


def run_plot(args: argparse.Namespace, profile: cd.Profile, port: str) -> int:
    import matplotlib.pyplot as plt
    import numpy as np

    try:
        ser = cd.open_port(port, args.baud, _line(args.dtr), _line(args.rts))
    except Exception as exc:
        print(f"Cannot open {port}: {exc}", file=sys.stderr)
        return 1
    reader = cd.LidarReader(ser, profile)
    reader.start()

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(projection="polar")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)       # clockwise, 0 deg = straight ahead
    ax.set_rmax(args.max_range)
    sc = ax.scatter([], [], s=6, c=[], cmap="viridis", vmin=0, vmax=255)
    title = ax.set_title("waiting for data...")
    fig.colorbar(sc, ax=ax, label="intensity", shrink=0.7, pad=0.1)

    last_scans, t0 = 0, time.monotonic()
    try:
        while plt.fignum_exists(fig.number):
            if reader.error:
                print(f"Serial error: {reader.error}", file=sys.stderr)
                return 1
            pts = [p for p in reader.latest() if 0 < p.dist_m <= args.max_range]
            if pts:
                sc.set_offsets(np.c_[np.radians([p.angle_deg for p in pts]), [p.dist_m for p in pts]])
                sc.set_array(np.array([p.intensity for p in pts]))
            elapsed = time.monotonic() - t0
            if elapsed > 4 and reader.parser.frames_ok == 0:
                title.set_text(f"no valid frames from {port} @ {args.baud} "
                               f"({reader.parser.frames_bad} bad) - try --sniff")
            else:
                hz = (reader.scans - last_scans) / elapsed if elapsed > 0 else 0.0
                title.set_text(f"{profile.name}{'' if profile.verified else ' (unverified)'}  "
                               f"scans {reader.scans}  frames ok/bad "
                               f"{reader.parser.frames_ok}/{reader.parser.frames_bad}  ~{hz:.1f} Hz")
            plt.pause(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        ser.close()
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        profile = cd.load_profile(args.profile_file) if args.profile_file else cd.PROFILES[args.profile]
    except (OSError, ValueError) as exc:
        print(f"Profile error: {exc}", file=sys.stderr)
        return 2
    port = args.port or cd.find_port()
    print(f"Using {port} @ {args.baud} baud, profile {profile.name}")
    if args.sniff:
        bauds = cd.BAUD_CANDIDATES if args.sniff_all_bauds else (args.baud,)
        cd.sniff(port, bauds, args.sniff_seconds, _line(args.dtr), _line(args.rts))
        return 0
    return run_plot(args, profile, port)


if __name__ == "__main__":
    sys.exit(main())
