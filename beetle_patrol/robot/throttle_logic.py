"""Pure rate-limit decision for the camera throttle (no ROS imports)."""


class ThrottleLogic:
    """should_publish(now) -> True at most max_hz times per second.

    `now` is any monotonic seconds value. The first call always passes.
    If the clock goes backwards the reference is reset and the frame passes,
    so a clock jump can never freeze the stream.
    """

    def __init__(self, max_hz: float = 5.0):
        if max_hz <= 0:
            raise ValueError("max_hz must be > 0")
        self.period = 1.0 / max_hz
        self._last = None

    def should_publish(self, now: float) -> bool:
        if self._last is None or now < self._last:
            self._last = now
            return True
        # tiny epsilon so exactly-on-period frames pass despite float rounding
        if now - self._last >= self.period - 1e-9:
            self._last = now
            return True
        return False
