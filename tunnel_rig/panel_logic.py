"""Pure logic for the tunnel-rig control panel: held directions -> firmware command char.

No GUI and no serial here so it can be unit-tested. Commands match tunnel_rig.ino.
"""
import re

STOP = "S"

_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

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


_FLIP_FB = str.maketrans("FBGHIJ", "BFHGJI")   # forward <-> back (F/B, G/H, I/J)
_FLIP_LR = str.maketrans("LRGIHJ", "RLIGJH")   # left <-> right (L/R, G/I, H/J)


def flip_command(cmd, flip_fb=False, flip_lr=False):
    """Reverse forward/back and/or left/right on a drive command (S, digits, '?' pass through)."""
    if flip_fb:
        cmd = cmd.translate(_FLIP_FB)
    if flip_lr:
        cmd = cmd.translate(_FLIP_LR)
    return cmd


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


# ---------------------------------------------------------------------------
# Wi-Fi link: packets, replies and comm-health scoring
# ---------------------------------------------------------------------------
from collections import deque, namedtuple  # noqa: E402

PING = "?"                      # ping only: the firmware replies but does not feed its failsafe
HEALTH_WINDOW = 20              # number of recent packets the loss / RTT figures cover

Reply = namedtuple("Reply", "seq rssi speed state")
Health = namedtuple("Health", "score level rssi rtt_ms loss_pct lost ever_replied")


def build_packet(seq, cmd):
    """Encode '<seq>:<cmd>' for the firmware."""
    return f"{int(seq)}:{cmd}".encode()


def parse_reply(data):
    """Parse '<seq>,<rssi>,<speed>,<state>' from the firmware; None if it is malformed."""
    try:
        parts = data.decode().strip().split(",")
    except (UnicodeDecodeError, AttributeError):
        return None
    if len(parts) != 4 or len(parts[3]) != 1:
        return None
    try:
        return Reply(int(parts[0]), int(parts[1]), int(parts[2]), parts[3])
    except ValueError:
        return None


def _scale(value, bad, good):
    """0..100: 0 at `bad`, 100 at `good` (works whichever is larger), clamped."""
    return max(0.0, min(1.0, (value - bad) / (good - bad))) * 100.0


def health_score(loss_pct, rtt_ms, rssi):
    """Blend loss (50 %), round-trip time (25 %) and Wi-Fi signal (25 %) into 0..100."""
    loss_s = max(0.0, 100.0 - 2.0 * loss_pct)       # 50 % loss -> 0
    rtt_s = _scale(rtt_ms, bad=300.0, good=30.0)
    rssi_s = _scale(rssi, bad=-85.0, good=-50.0)
    return int(round(0.5 * loss_s + 0.25 * rtt_s + 0.25 * rssi_s))


def health_level(score):
    return "GOOD" if score >= 70 else "FAIR" if score >= 40 else "POOR"


class HealthTracker:
    """Tracks sent packets and replies and summarises link quality. Times are passed in
    (seconds, any monotonic clock) so it can be tested without sleeping."""

    def __init__(self, window=HEALTH_WINDOW, lost_after_s=0.5):
        self.lost_after = lost_after_s
        self._log = deque(maxlen=window)            # [seq, sent_time, rtt_or_None]
        self._rssi = None
        self._last_reply = None

    def reset(self):
        self._log.clear()
        self._rssi = None
        self._last_reply = None

    def sent(self, seq, now):
        self._log.append([seq, now, None])

    def on_reply(self, reply, now):
        for entry in reversed(self._log):
            if entry[0] == reply.seq and entry[2] is None:
                entry[2] = now - entry[1]
                break
        self._rssi = reply.rssi
        self._last_reply = now

    def snapshot(self, now):
        resolved = [e for e in self._log if e[2] is not None or now - e[1] > self.lost_after]
        missed = sum(1 for e in resolved if e[2] is None)
        loss_pct = 100.0 * missed / len(resolved) if resolved else 0.0
        rtts = [e[2] for e in self._log if e[2] is not None]
        rtt_ms = 1000.0 * sum(rtts) / len(rtts) if rtts else None
        ever = self._last_reply is not None
        lost = (not ever) or (now - self._last_reply > self.lost_after)
        if lost or rtt_ms is None or self._rssi is None:
            return Health(0, "LOST", self._rssi, rtt_ms, loss_pct, True, ever)
        score = health_score(loss_pct, rtt_ms, self._rssi)
        return Health(score, health_level(score), self._rssi, rtt_ms, loss_pct, False, ever)


def ssh_server_command(action, user, host, server_dir):
    """argv that starts or stops rig_server.py on the Pi over SSH (key login, no password prompt).

    The stop pattern is written '[r]ig_server' so the remote shell's own command line does not
    match it (otherwise pkill would kill the very shell running it).
    """
    for label, value in (("user", user), ("host", host), ("server_dir", server_dir)):
        if not _SAFE_NAME.match(str(value)):
            raise ValueError(f"unsafe {label}: {value!r}")
    if action == "start":
        remote = (f"cd ~/{server_dir} && "
                  "(setsid nohup python3 rig_server.py > rig.log 2>&1 < /dev/null &); sleep 1")
    elif action == "stop":
        remote = "pkill -f '[r]ig_server'; sleep 0.5; true"
    else:
        raise ValueError(f"unknown action: {action!r}")
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=6", f"{user}@{host}", remote]
