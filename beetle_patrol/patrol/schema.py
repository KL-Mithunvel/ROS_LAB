"""Build a settings dataclass from a YAML mapping, rejecting typos and unknown keys."""
from dataclasses import fields


def from_mapping(cls, mapping, section, source="patrol.yaml"):
    """Create `cls(**mapping)`; unknown keys raise ValueError naming the YAML file and section."""
    mapping = mapping or {}
    allowed = {f.name for f in fields(cls)}
    unknown = set(mapping) - allowed
    if unknown:
        raise ValueError(f"{source} [{section}]: unknown key(s) {sorted(unknown)}; "
                         f"allowed: {sorted(allowed)}")
    return cls(**mapping)
