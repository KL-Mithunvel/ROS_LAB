"""Pure heartbeat watchdog decision logic (no ROS imports)."""

CANCEL = 'cancel_goals'
PAUSE = 'pause_explore'
DISARM = 'disarm'


class WatchdogLogic:
    """Fire the safety actions ONCE per outage.

    feed(now): a heartbeat arrived; clears the outage and re-arms the watchdog.
    check(now, armed): returns [cancel_goals, pause_explore, disarm] once when the
    robot is armed and no heartbeat has been seen for MORE than timeout_s
    (exactly timeout_s does not fire). Returns [] otherwise.

    Before the first heartbeat, the timer starts at the first check() call, so a
    laptop that never connects still triggers the safe stop. A backwards clock
    never fires.
    """

    def __init__(self, timeout_s: float = 2.0):
        self.timeout_s = timeout_s
        self._last = None
        self._fired = False

    def feed(self, now: float) -> None:
        self._last = now
        self._fired = False

    def check(self, now: float, armed: bool):
        if not armed:
            return []
        if self._last is None:
            self._last = now  # grace baseline
            return []
        if self._fired:
            return []
        if now - self._last > self.timeout_s:
            self._fired = True
            return [CANCEL, PAUSE, DISARM]
        return []
