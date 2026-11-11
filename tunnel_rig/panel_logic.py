"""Pure logic for the tunnel-rig control panel: held directions -> firmware command char.

No GUI and no serial here so it can be unit-tested. Commands match tunnel_rig.ino.
"""

STOP = "S"

# (up, down, left, right) booleans -> command character
_COMMANDS = {
    (True, False, False, False): "F",
    (False, True, False, False): "B",
    (False, False, True, False): "L",   # spin left
    (False, False, False, True): "R",   # spin right
    (True, False, True, False): "G",    # forward-left
    (True, False, False, True): "I",    # forward-right
    (False, True, True, False): "H",    # back-left
    (False, True, False, True): "J",    # back-right
}

# Tk keysym (lower-case) -> logical direction
KEY_TO_DIRECTION = {
    "w": "up", "up": "up",
    "s": "down", "down": "down",
    "a": "left", "left": "left",
    "d": "right", "right": "right",
}

MIN_SPEED, MAX_SPEED = 0, 9


def command_for(directions):
    """Return the command char for a set of held directions ('up','down','left','right').

    Opposite directions cancel each other; anything unmapped (or nothing held) is STOP.
    """
    up = "up" in directions
    down = "down" in directions
    left = "left" in directions
    right = "right" in directions
    if up and down:
        up = down = False
    if left and right:
        left = right = False
    return _COMMANDS.get((up, down, left, right), STOP)


def direction_for_key(keysym):
    """Map a Tk keysym to a logical direction, or None if the key is not a drive key."""
    return KEY_TO_DIRECTION.get(str(keysym).lower())


def clamp_speed(level):
    """Clamp a speed level to 0..9 (non-numeric input -> MIN_SPEED)."""
    try:
        value = int(round(float(level)))
    except (TypeError, ValueError):
        return MIN_SPEED
    return max(MIN_SPEED, min(MAX_SPEED, value))
