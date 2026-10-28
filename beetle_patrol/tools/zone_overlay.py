#!/usr/bin/env python3
"""Check zones.yaml against a saved map and draw an overlay PNG.

    python tools/zone_overlay.py --map maps/lab.yaml [--zones zones.yaml] [--out overlay.png]

Prints the free-space percentage of every zone, the map's free/occupied extent and a suggested
`grid.origin`. Exit code 1 (message on stderr) if a file is missing or malformed.
"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from patrol.config import HERE  # noqa: E402
from patrol.heatmap import build_zones  # noqa: E402
from patrol.overlay import (OCCUPIED, bounding_box, load_map, render_overlay,  # noqa: E402
                            suggest_origin, write_png, zone_coverage)


def _fmt_box(box):
    return "none" if box is None else "x %.2f..%.2f  y %.2f..%.2f" % (box[0], box[2], box[1], box[3])


def run(map_yaml, zones_yaml, out_png):
    try:
        zones_cfg = yaml.safe_load(Path(zones_yaml).read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"zones file not found: {zones_yaml}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"{Path(zones_yaml).name} is not valid YAML: {exc}") from None
    if not isinstance(zones_cfg, dict):
        raise ValueError(f"{Path(zones_yaml).name} must contain a mapping at the top level")

    omap = load_map(map_yaml)
    zones = build_zones(zones_cfg)
    coverage = zone_coverage(omap, zones)
    suggestion = suggest_origin(omap, zones_cfg)

    h, w = omap.shape
    print(f"map: {w}x{h} cells, {omap.resolution:g} m/cell, origin {omap.origin}")
    print(f"free box:     {_fmt_box(suggestion.free_box)}")
    print(f"occupied box: {_fmt_box(bounding_box(omap, OCCUPIED))}")
    print(f"\n{'zone':<8}{'free%':>8}{'occupied%':>11}{'unknown%':>10}")
    for c in coverage:
        print(f"{c.id:<8}{c.free_pct:>8.1f}{c.occupied_pct:>11.1f}{c.unknown_pct:>10.1f}")
    current = zones_cfg["grid"]["origin"]
    print(f"\ngrid.origin now:       {current}")
    print(f"suggested grid.origin: [{suggestion.origin[0]:.2f}, {suggestion.origin[1]:.2f}]")
    for warning in suggestion.warnings:
        print(f"WARNING: {warning}")

    write_png(out_png, render_overlay(omap, zones, coverage))
    print(f"overlay written to {out_png}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--map", required=True, help="map.yaml saved by map_saver")
    parser.add_argument("--zones", default=str(HERE / "zones.yaml"), help="zones.yaml (default: the project's)")
    parser.add_argument("--out", default="overlay.png", help="output PNG (default overlay.png)")
    args = parser.parse_args(argv)
    try:
        run(args.map, args.zones, args.out)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
