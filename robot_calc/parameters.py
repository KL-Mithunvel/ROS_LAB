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
    """Read the YAML parameter file and return the full nested dict.

    Raises FileNotFoundError if the file is missing, ValueError if it is not
    valid YAML or not shaped like a parameter file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            params = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise ValueError(f"{path} is not valid YAML: {exc}") from exc

    if not isinstance(params, dict) or not params:
        raise ValueError(f"{path} did not contain any parameters")
    for key, spec in params.items():
        if not isinstance(spec, dict) or "value" not in spec:
            raise ValueError(f"parameter '{key}' must be a mapping with a 'value' key")
    return params


def save(params, path=DEFAULT_PARAMS_FILE):
    """Write the parameter dict back to YAML, keeping the key order.

    This rewrites the file with a YAML dumper, so hand-written comments in
    params.yaml are lost - ask before overwriting.
    """
    answer = input(f"Rewrite {os.path.basename(path)}? "
                   f"(comments in the file will be dropped) [y/N]: ").strip().lower()
    if answer != "y":
        print("Not saved.")
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(params, f, sort_keys=False, default_flow_style=False)
    except OSError as exc:
        print(f"Could not save to {path}: {exc}")
        return
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
        spec = params.get(key)
        if not isinstance(spec, dict):
            print(f"  (no parameter '{key}' in params.yaml - skipped)")
            continue
        flag = "  (estimate - confirm)" if spec.get("confirm") else ""
        prompt = (f"  {key} [{spec['value']}] {spec.get('unit', '')} - "
                  f"{spec.get('desc', '')}{flag}\n    new value: ")
        raw = input(prompt).strip()
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
    """Edit only the parameters a single set uses."""
    print("\nEditing the parameters this set uses (blank = keep current):")
    return _edit_keys(params, keys)


def print_all(params):
    """Print every parameter as a table."""
    print("\nCurrent robot parameters:")
    width = max(len(k) for k in params)
    for key, spec in params.items():
        flag = "  <- confirm" if spec.get("confirm") else ""
        print(f"  {key:<{width}} = {str(spec['value']):>10}  "
              f"{spec.get('unit', ''):<7} {spec.get('desc', '')}{flag}")
