"""
parameters.py — load, edit, print and save the robot parameter set.

The parameter file (params.yaml) maps each key to a small dict:
    {value: <number>, unit: <str>, desc: <str>, confirm: <bool>}

`resolve()` flattens that to {key: float(value)} for the calculation functions.
"""

import os

import yaml

DEFAULT_PARAMS_FILE = os.path.join(os.path.dirname(__file__), "params.yaml")


def load(path=DEFAULT_PARAMS_FILE):
    """Read the YAML parameter file and return the full nested dict."""
    with open(path, "r", encoding="utf-8") as f:
        params = yaml.safe_load(f)
    if not isinstance(params, dict) or not params:
        raise ValueError(f"{path} did not contain any parameters")
    return params


def save(params, path=DEFAULT_PARAMS_FILE):
    """Write the parameter dict back to YAML, keeping the key order."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(params, f, sort_keys=False, default_flow_style=False)
    print(f"Saved to {path}")


def resolve(params):
    """Flatten to {key: float(value)} for use in the calculations."""
    flat = {}
    for key, spec in params.items():
        try:
            flat[key] = float(spec["value"])
        except (TypeError, ValueError):
            raise ValueError(f"parameter '{key}' has a non-numeric value: {spec['value']!r}")
    return flat


def _edit_keys(params, keys):
    """Prompt for each key in `keys`. Blank input keeps the current value."""
    changed = False
    for key in keys:
        spec = params[key]
        flag = "  (estimate - confirm)" if spec.get("confirm") else ""
        raw = input(f"  {key} [{spec['value']}] {spec['unit']} - {spec['desc']}{flag}\n    new value: ").strip()
        if not raw:
            continue
        try:
            spec["value"] = float(raw)
            changed = True
            print("    set.")
        except ValueError:
            print("    not a number - keeping the old value.")
    if not changed:
        print("  (nothing changed)")
    return changed


def edit_all(params):
    """Edit every parameter."""
    print("\nEditing all robot parameters (blank = keep current):")
    return _edit_keys(params, list(params))


def edit_subset(params, keys):
    """Edit only the parameters a single calculation uses."""
    print("\nEditing the parameters this calculation uses (blank = keep current):")
    return _edit_keys(params, keys)


def print_all(params):
    """Print every parameter as a table."""
    print("\nCurrent robot parameters:")
    width = max(len(k) for k in params)
    for key, spec in params.items():
        flag = "  <- confirm" if spec.get("confirm") else ""
        print(f"  {key:<{width}} = {spec['value']:>10}  {spec['unit']:<7} {spec['desc']}{flag}")
