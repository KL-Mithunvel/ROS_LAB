"""
mission.py — the "brain" of the Acrux waypoint mission. Pure Python, no ROS.

The robot visits up to MAX waypoints one at a time. At each waypoint it STOPS and waits
until the operator says "yes" (next). After the last waypoint it drives home.

This file only decides *what should happen next*. It never talks to ROS: it
receives events (operator commands, navigation results) and returns a list of
*actions* (navigate here, cancel, print this). `mission_node.py` carries the
actions out against Nav2. Keeping the logic ROS-free is what lets `pytest` test
every path on a plain Windows PC.

States
------
    IDLE            waiting for the first "yes"
    NAVIGATING      driving to a waypoint
    AT_WAYPOINT     arrived, waiting for "yes" (task done) before moving on
    PAUSED          operator paused; goal cancelled, will resume to same target
    BLOCKED         navigation failed (after auto-retries); waiting for operator
    RETURNING_HOME  driving home after the last waypoint (or after "home")
    DONE            back home, mission complete
    ABORTED         operator quit
"""

import math
from collections import deque
from dataclasses import dataclass
from enum import Enum

# --- operator commands (canonical names) -------------------------------------
CMD_NEXT = "next"
CMD_SKIP = "skip"
CMD_RETRY = "retry"
CMD_HOME = "home"
CMD_PAUSE = "pause"
CMD_QUIT = "quit"
CMD_STATUS = "status"

# What the operator may type -> canonical command. Empty string = just Enter.
_COMMAND_ALIASES = {
    "": CMD_NEXT, "y": CMD_NEXT, "yes": CMD_NEXT, "next": CMD_NEXT, "go": CMD_NEXT,
    "s": CMD_SKIP, "skip": CMD_SKIP,
    "r": CMD_RETRY, "retry": CMD_RETRY,
    "h": CMD_HOME, "home": CMD_HOME,
    "p": CMD_PAUSE, "pause": CMD_PAUSE, "resume": CMD_PAUSE,
    "q": CMD_QUIT, "quit": CMD_QUIT,
    "?": CMD_STATUS, "status": CMD_STATUS, "help": CMD_STATUS,
}

HELP_TEXT = (
    "Commands:  y/Enter = next waypoint   s = skip   r = retry   "
    "p = pause/resume   h = go home   q = quit   ? = status"
)


def parse_command(text):
    """Map what the operator typed to a canonical command, or None if unknown."""
    return _COMMAND_ALIASES.get(text.strip().lower())


# --- data types --------------------------------------------------------------
@dataclass(frozen=True)
class Pose:
    """A 2D pose in the map frame: metres and radians (yaw 0 = facing +x)."""
    x: float
    y: float
    yaw: float
    label: str = ""


class State(Enum):
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    AT_WAYPOINT = "AT_WAYPOINT"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    RETURNING_HOME = "RETURNING_HOME"
    DONE = "DONE"
    ABORTED = "ABORTED"


class NavResult(Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


@dataclass(frozen=True)
class NavigateTo:
    """Action: send a Nav2 goal to this pose."""
    pose: Pose


@dataclass(frozen=True)
class CancelNavigation:
    """Action: cancel the Nav2 goal currently in flight."""


@dataclass(frozen=True)
class Message:
    """Action: show this text to the operator."""
    text: str


@dataclass(frozen=True)
class Shutdown:
    """Action: stop the node."""


def yaw_to_quaternion(yaw):
    """Return (z, w) of the quaternion for a rotation of `yaw` radians about Z."""
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


# --- the state machine -------------------------------------------------------
class Mission:
    """Decides what the robot does next. See the module docstring."""

    def __init__(self, home, waypoints, waypoint_count, max_auto_retries=1):
        if isinstance(waypoint_count, bool) or not isinstance(waypoint_count, int):
            raise ValueError(f"waypoint_count must be a whole number, got {waypoint_count!r}")
        if not 1 <= waypoint_count <= len(waypoints):
            raise ValueError(
                f"waypoint_count must be between 1 and {len(waypoints)}, got {waypoint_count}")
        if max_auto_retries < 0:
            raise ValueError("max_auto_retries cannot be negative")

        self.home = home
        self.waypoint_count = waypoint_count
        self.state = State.IDLE
        self.visited = []     # waypoints whose waypoint was reached
        self.skipped = []     # waypoints dropped by the operator

        self._max_auto_retries = max_auto_retries
        self._queue = deque(waypoints[:waypoint_count])   # waypoints not yet driven to
        self._target = None            # pose being driven to / waited at
        self._driving_state = None     # NAVIGATING or RETURNING_HOME (for resume/retry)
        self._retries_left = 0

    # -- queries --------------------------------------------------------------
    @property
    def is_finished(self):
        return self.state in (State.DONE, State.ABORTED)

    def status_text(self):
        target = self._target.label if self._target else "-"
        waiting = ", ".join(p.label for p in self._queue) or "-"
        visited = ", ".join(p.label for p in self.visited) or "-"
        skipped = ", ".join(p.label for p in self.skipped) or "-"
        return (f"state={self.state.value}  target={target}  "
                f"still to visit: {waiting}  visited: {visited}  skipped: {skipped}")

    # -- events ---------------------------------------------------------------
    def on_command(self, command):
        """Handle one canonical operator command. Returns a list of actions."""
        if command == CMD_STATUS:
            return [Message(self.status_text()), Message(HELP_TEXT)]
        if self.is_finished:
            return [Message(f"The mission is over ({self.state.value}).")]

        handler = {
            CMD_NEXT: self._cmd_next,
            CMD_SKIP: self._cmd_skip,
            CMD_RETRY: self._cmd_retry,
            CMD_HOME: self._cmd_home,
            CMD_PAUSE: self._cmd_pause,
            CMD_QUIT: self._cmd_quit,
        }.get(command)
        if handler is None:
            raise ValueError(f"unknown command {command!r}")
        return handler()

    def on_nav_result(self, result):
        """Handle the end of a Nav2 goal. Returns a list of actions.

        Results that arrive when no drive is expected (stale) are ignored.
        """
        if self.state not in (State.NAVIGATING, State.RETURNING_HOME):
            return []

        if result is NavResult.SUCCEEDED:
            if self.state is State.RETURNING_HOME:
                self.state = State.DONE
                return [Message("Home. Mission complete. " + self.status_text())]
            self.visited.append(self._target)
            self.state = State.AT_WAYPOINT
            return [Message(f"Arrived at {self._target.label}. "
                            "Waiting - press y/Enter once the waypoint task is done.")]

        # FAILED or CANCELED that we did not ask for -> treat as a failure.
        if self._retries_left > 0:
            self._retries_left -= 1
            return [Message(f"Navigation to {self._target.label} failed - retrying "
                            f"({self._retries_left} auto-retries left)."),
                    NavigateTo(self._target)]
        self.state = State.BLOCKED
        return [Message(f"BLOCKED on the way to {self._target.label}. "
                        "r = retry, s = skip this waypoint, h = go home.")]

    # -- command handlers -----------------------------------------------------
    def _cmd_next(self):
        if self.state in (State.IDLE, State.AT_WAYPOINT):
            return self._go_to_next_waypoint()
        if self.state is State.PAUSED:
            return [Message("Paused - press p to resume.")]
        if self.state is State.BLOCKED:
            return [Message("Blocked - r = retry, s = skip, h = home.")]
        return [Message("Still driving - it will stop and wait when it arrives.")]

    def _cmd_skip(self):
        if self.state is State.NAVIGATING:
            return self._skip_current_target(cancel=True)
        if self.state is State.BLOCKED:
            if self._driving_state is State.RETURNING_HOME:
                return [Message("Cannot skip going home - r = retry, q = quit.")]
            return self._skip_current_target(cancel=False)
        if self.state is State.PAUSED:
            if self._driving_state is State.RETURNING_HOME:
                return [Message("Cannot skip going home - p = resume.")]
            return self._skip_current_target(cancel=False)
        if self.state is State.RETURNING_HOME:
            return [Message("Already heading home.")]
        # IDLE or AT_WAYPOINT: drop the next waypoint in the queue without visiting.
        if not self._queue:
            return [Message("Nobody left to skip - press y/Enter to go home.")]
        dropped = self._queue.popleft()
        self.skipped.append(dropped)
        return [Message(f"Skipped {dropped.label}. Press y/Enter to continue.")]

    def _cmd_retry(self):
        if self.state in (State.BLOCKED, State.PAUSED):
            return self._drive_to(self._target, self._driving_state,
                                  f"Retrying {self._target.label}.")
        return [Message("Nothing to retry.")]

    def _cmd_pause(self):
        if self.state in (State.NAVIGATING, State.RETURNING_HOME):
            self.state = State.PAUSED
            return [CancelNavigation(), Message("Paused. Press p to resume.")]
        if self.state is State.PAUSED:
            return self._drive_to(self._target, self._driving_state,
                                  f"Resuming to {self._target.label}.")
        return [Message("Nothing to pause - the robot is not driving.")]

    def _cmd_home(self):
        if self.state is State.RETURNING_HOME:
            return [Message("Already heading home.")]
        actions = []
        if self.state is State.NAVIGATING:
            actions.append(CancelNavigation())
            self.skipped.append(self._target)
        self.skipped.extend(self._queue)
        self._queue.clear()
        return actions + self._go_home("Going home; remaining waypoints dropped.")

    def _cmd_quit(self):
        actions = []
        if self.state in (State.NAVIGATING, State.RETURNING_HOME):
            actions.append(CancelNavigation())
        self.state = State.ABORTED
        return actions + [Message("Quit - robot stopped where it is."), Shutdown()]

    # -- helpers --------------------------------------------------------------
    def _drive_to(self, target, driving_state, text):
        self._target = target
        self._driving_state = driving_state
        self.state = driving_state
        self._retries_left = self._max_auto_retries
        return [Message(text), NavigateTo(target)]

    def _go_to_next_waypoint(self):
        if not self._queue:
            return self._go_home("All waypoints served. Heading home.")
        target = self._queue.popleft()
        return self._drive_to(target, State.NAVIGATING, f"Heading to {target.label}.")

    def _go_home(self, text):
        return self._drive_to(self.home, State.RETURNING_HOME, text)

    def _skip_current_target(self, cancel):
        self.skipped.append(self._target)
        actions = [CancelNavigation()] if cancel else []
        return actions + [Message(f"Skipped {self._target.label}.")] + \
            self._go_to_next_waypoint()
