"""Pure command -> motor-duty logic for the Pi tunnel rig (no GPIO, fully testable).

Mirrors tunnel_rig.ino so the PC control panel works unchanged:
  packet  "<seq>:<cmd>"            (a bare "F" also works)
  reply   "<seq>,<rssi>,<speed>,<last>"
"""

DUTY_MAX = 255
LEVEL_MAX = 9

# command -> (left %, right %) of the current speed level; negative = reverse
MOVES = {
    "F": (100, 100), "B": (-100, -100),
    "L": (-100, 100), "R": (100, -100),   # spin on the spot
    "G": (40, 100), "I": (100, 40),       # forward + left / right
    "H": (-40, -100), "J": (-100, -40),   # back + left / right
}


def parse_packet(data):
    """Return (seq, cmd) from b'<seq>:<cmd>' or b'<cmd>'; (0, '') if empty/garbage."""
    text = data.decode("ascii", errors="ignore").strip()
    if not text:
        return 0, ""
    if ":" in text:
        head, _, tail = text.partition(":")
        try:
            seq = int(head)
        except ValueError:
            seq = 0
        return seq, tail[:1]
    return 0, text[:1]


def level_to_duty(level):
    return (level * DUTY_MAX) // LEVEL_MAX


def _step_toward(cur, tgt, step):
    if cur < tgt:
        return min(cur + step, tgt)
    if cur > tgt:
        return max(cur - step, tgt)
    return cur


def _pct(duty, pct):
    """duty * pct / 100, truncating toward zero for negative percentages."""
    return duty * pct // 100 if pct >= 0 else -(duty * -pct // 100)


class RigState:
    """Speed level, ramped left/right duty (-255..255) and the no-command failsafe."""

    def __init__(self, default_level=6, cmd_timeout_s=0.5, ramp_per_step=12, ramp_s=0.01):
        self.level = default_level
        self.cmd_timeout_s = cmd_timeout_s
        self.ramp_per_step = ramp_per_step
        self.ramp_s = ramp_s
        self.tgt_l = self.tgt_r = 0
        self.cur_l = self.cur_r = 0
        self.last_char = "S"
        self.last_cmd_t = 0.0
        self.last_ramp_t = 0.0

    def stop_now(self):
        self.tgt_l = self.tgt_r = self.cur_l = self.cur_r = 0
        self.last_char = "S"

    def handle(self, cmd, now):
        """Apply one command character. Returns True if it counts as a drive command."""
        if not cmd:
            return False
        c = cmd.upper()
        if c in MOVES:
            duty = level_to_duty(self.level)
            l_pct, r_pct = MOVES[c]
            self.tgt_l, self.tgt_r = _pct(duty, l_pct), _pct(duty, r_pct)
            self.last_cmd_t, self.last_char = now, c
            return True
        if c == "S":
            self.stop_now()
        elif c == "Q" or c.isdigit():
            self.level = LEVEL_MAX if c == "Q" else int(c)
            base = max(abs(self.tgt_l), abs(self.tgt_r))
            if base > 0:                       # re-scale a move already in progress
                new_base = level_to_duty(self.level)
                self.tgt_l = int(self.tgt_l * new_base / base)
                self.tgt_r = int(self.tgt_r * new_base / base)
        return False                           # '?', unknown bytes: no motion, no failsafe feed

    def tick(self, now):
        """Run failsafe + ramp. Returns (left, right) signed duty -255..255."""
        moving = self.tgt_l or self.tgt_r or self.cur_l or self.cur_r
        if self.cmd_timeout_s and moving and now - self.last_cmd_t > self.cmd_timeout_s:
            self.stop_now()
        steps = int((now - self.last_ramp_t) / self.ramp_s)
        if steps > 0:
            self.last_ramp_t = now
            for _ in range(min(steps, 100)):
                self.cur_l = _step_toward(self.cur_l, self.tgt_l, self.ramp_per_step)
                self.cur_r = _step_toward(self.cur_r, self.tgt_r, self.ramp_per_step)
        return self.cur_l, self.cur_r

    def reply(self, seq, rssi):
        return "%d,%d,%d,%s" % (seq, rssi, self.level, self.last_char)
