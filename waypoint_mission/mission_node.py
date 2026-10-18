"""
mission_node.py — run the Acrux waypoint mission from the LAPTOP.

    python3 mission_node.py --count 3

It sends Nav2 goals to the robot over Wi-Fi (same ROS_DOMAIN_ID on both ends),
and reads your live commands from this terminal (y/Enter, s, r, p, h, q, ?) or
from the ROS topic /waypoint/command (std_msgs/String).

Do NOT start this through `ros2 launch`: launch does not forward the keyboard.

All decisions live in mission.py (tested without ROS). This file only:
  1. loads waypoints.yaml,
  2. turns Mission actions into Nav2 calls (nav2_simple_commander),
  3. feeds operator commands and Nav2 results back into Mission.

Safety note: the emergency stop (collision monitor) runs ON THE ROBOT, see
launch/safety.launch.py. If this laptop or the Wi-Fi dies, the robot's own
safety layer keeps working and Ctrl+C here cancels the active goal.
"""

import argparse
import queue
import sys
import threading
import time

import waypoint_config
import mission

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.parameter import Parameter
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String

COMMAND_TOPIC = "/waypoint/command"
CANCEL_WAIT_S = 5.0      # how long to wait for Nav2 to confirm a cancel

_RESULT_MAP = {
    TaskResult.SUCCEEDED: mission.NavResult.SUCCEEDED,
    TaskResult.CANCELED: mission.NavResult.CANCELED,
    TaskResult.FAILED: mission.NavResult.FAILED,
}


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Acrux waypoint mission (laptop side)")
    parser.add_argument("--count", type=int, required=True,
                        help="number of waypoints today (1-4); there is deliberately no default")
    parser.add_argument("--waypoints", default=waypoint_config.DEFAULT_CONFIG_FILE,
                        help="path to waypoints.yaml (default: next to this script)")
    parser.add_argument("--sim", action="store_true",
                        help="Gazebo run: set use_sim_time=true on this node")
    parser.add_argument("--set-initial-pose", action="store_true",
                        help="publish 'home' as the AMCL initial pose before starting "
                             "(only if the robot really starts parked at home)")
    parser.add_argument("--no-wait", action="store_true",
                        help="do not wait for Nav2/AMCL lifecycle nodes to be active")
    parser.add_argument("--allow-unsurveyed", action="store_true",
                        help="drive even though waypoints.yaml says surveyed: false (sim only!)")
    return parser.parse_args(remove_ros_args(argv)[1:])


def to_pose_stamped(pose, frame_id, stamp):
    z, w = mission.yaw_to_quaternion(pose.yaw)
    msg = PoseStamped()
    msg.header.frame_id = frame_id
    msg.header.stamp = stamp
    msg.pose.position.x = pose.x
    msg.pose.position.y = pose.y
    msg.pose.orientation.z = z
    msg.pose.orientation.w = w
    return msg


def start_stdin_reader(commands):
    """Push every line typed in this terminal onto the command queue."""
    def _read():
        for line in sys.stdin:
            commands.put(line)
    threading.Thread(target=_read, daemon=True).start()


class Driver:
    """Carries out Mission actions against Nav2 and tracks the goal in flight."""

    def __init__(self, navigator, frame_id, goal_timeout_s):
        self._nav = navigator
        self._frame_id = frame_id
        self._goal_timeout_s = goal_timeout_s
        self.active = False
        self.shutdown = False
        self._started_at = 0.0

    def execute(self, actions):
        for action in actions:
            if isinstance(action, mission.Message):
                print(f"[waypoint] {action.text}", flush=True)
            elif isinstance(action, mission.CancelNavigation):
                self.cancel()
            elif isinstance(action, mission.NavigateTo):
                stamp = self._nav.get_clock().now().to_msg()
                self._nav.goToPose(to_pose_stamped(action.pose, self._frame_id, stamp))
                self.active = True
                self._started_at = time.monotonic()
            elif isinstance(action, mission.Shutdown):
                self.shutdown = True

    def poll(self):
        """Return a NavResult if the goal in flight just ended (or timed out)."""
        if not self.active:
            return None
        if self._nav.isTaskComplete():
            self.active = False
            return _RESULT_MAP.get(self._nav.getResult(), mission.NavResult.FAILED)
        if time.monotonic() - self._started_at > self._goal_timeout_s:
            print(f"[waypoint] goal timed out after {self._goal_timeout_s:.0f}s", flush=True)
            self.cancel()
            return mission.NavResult.FAILED
        return None

    def cancel(self):
        if not self.active:
            return
        self._nav.cancelTask()
        deadline = time.monotonic() + CANCEL_WAIT_S
        while not self._nav.isTaskComplete() and time.monotonic() < deadline:
            pass   # isTaskComplete() itself spins for 0.1 s per call
        self.active = False


def main():
    args = parse_args(sys.argv)

    try:
        config = waypoint_config.load_config(args.waypoints)
        plan = mission.Mission(config.home, config.waypoints, args.count,
                               config.max_auto_retries)
    except (OSError, ValueError) as exc:
        print(f"[waypoint] cannot start: {exc}", file=sys.stderr)
        return 2

    if not config.surveyed and not args.allow_unsurveyed:
        print("[waypoint] waypoints.yaml says surveyed: false - these are placeholder "
              "coordinates. Survey the real spots (see README) or pass "
              "--allow-unsurveyed for simulation.", file=sys.stderr)
        return 2

    rclpy.init(args=sys.argv)
    navigator = BasicNavigator()
    if args.sim:
        navigator.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, True)])

    commands = queue.Queue()
    navigator.create_subscription(
        String, COMMAND_TOPIC, lambda msg: commands.put(msg.data), 10)
    start_stdin_reader(commands)
    driver = Driver(navigator, config.frame_id, config.goal_timeout_s)

    try:
        if args.set_initial_pose:
            stamp = navigator.get_clock().now().to_msg()
            navigator.setInitialPose(to_pose_stamped(config.home, config.frame_id, stamp))
        if not args.no_wait:
            print("[waypoint] waiting for Nav2 to become active...", flush=True)
            navigator.waitUntilNav2Active()

        print(f"[waypoint] ready: {args.count} waypoint(s). {mission.HELP_TEXT}", flush=True)
        print("[waypoint] Press y/Enter to send the robot to the first waypoint.", flush=True)

        while rclpy.ok() and not plan.is_finished and not driver.shutdown:
            result = driver.poll()
            if result is not None:
                driver.execute(plan.on_nav_result(result))
                continue

            if not driver.active:
                rclpy.spin_once(navigator, timeout_sec=0.1)
            try:
                text = commands.get_nowait()
            except queue.Empty:
                continue
            command = mission.parse_command(text)
            if command is None:
                print(f"[waypoint] unknown command {text.strip()!r}. {mission.HELP_TEXT}",
                      flush=True)
                continue
            driver.execute(plan.on_command(command))
    except KeyboardInterrupt:
        print("\n[waypoint] Ctrl+C - cancelling the active goal.", flush=True)
    finally:
        driver.cancel()
        navigator.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    print("[waypoint] " + plan.status_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
