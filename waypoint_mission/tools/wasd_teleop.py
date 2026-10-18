#!/usr/bin/env python3
"""WASD keyboard teleop for the Acrux. Runs on the robot (via `./acrux teleop`), publishes /cmd_vel.

Hold a key to move; the command expires HOLD_S after the last key event (deadman), then a single zero
is sent. Space/x stops at once. Any exit path (q, Ctrl-C, SSH drop) sends zero.
"""
import atexit
import select
import signal
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist

LIN_MAX, ANG_MAX = 0.20, 0.60        # same hard caps as `acrux drive`
LIN_STEP, ANG_STEP = 0.02, 0.10
HOLD_S = 0.6                          # covers keyboard auto-repeat start delay
RATE_HZ = 20.0

# key -> (linear sign, angular sign)
MOVES = {
    'w': (1, 0), 's': (-1, 0), 'a': (0, 1), 'd': (0, -1),
    'q': (1, 1), 'e': (1, -1), 'z': (-1, -1), 'c': (-1, 1),   # arcs (back arcs keep turn direction of travel)
}
HELP = """\r
Acrux WASD teleop  (hold a key to move)\r
   q  w  e        w/s  forward / back\r
   a  s  d        s    back, a/d turn left / right (in place)\r
   z  x  c        q e z c  arcs, x stop\r
 space or x = stop      + / - = speed up / down\r
 ctrl-c or p = quit\r
"""


def main():
    if not sys.stdin.isatty():
        sys.exit("needs a terminal (run via ./acrux teleop)")
    rclpy.init()
    node = rclpy.create_node('wasd_teleop')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    lin, ang = 0.10, 0.40           # current speed setting
    cmd = (0.0, 0.0)
    last_key = 0.0
    moving = False

    def send(l, a):
        m = Twist()
        m.linear.x, m.angular.z = float(l), float(a)
        pub.publish(m)

    def shutdown(*_):
        try:
            for _i in range(3):
                send(0.0, 0.0)
                time.sleep(0.03)
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        finally:
            rclpy.try_shutdown()
        print('\r\nstopped.', flush=True)
        sys.exit(0)

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, shutdown)
    atexit.register(lambda: termios.tcsetattr(fd, termios.TCSADRAIN, old))

    tty.setcbreak(fd)
    print(HELP + f"\rspeed: lin {lin:.2f} m/s  ang {ang:.2f} rad/s", end='', flush=True)

    period = 1.0 / RATE_HZ
    while rclpy.ok():
        r, _, _ = select.select([sys.stdin], [], [], period)
        now = time.monotonic()
        if r:
            k = sys.stdin.read(1).lower()
            if k in MOVES:
                ls, as_ = MOVES[k]
                cmd = (ls * lin, as_ * ang)
                last_key, moving = now, True
            elif k in (' ', 'x'):
                cmd, moving = (0.0, 0.0), False
                send(0.0, 0.0)
            elif k in ('+', '='):
                lin, ang = min(LIN_MAX, lin + LIN_STEP), min(ANG_MAX, ang + ANG_STEP)
            elif k in ('-', '_'):
                lin, ang = max(LIN_STEP, lin - LIN_STEP), max(ANG_STEP, ang - ANG_STEP)
            elif k in ('p', '\x03'):
                break
            print(f"\rspeed: lin {lin:.2f} m/s  ang {ang:.2f} rad/s   cmd: {cmd[0]:+.2f} {cmd[1]:+.2f}   ", end='', flush=True)
        if moving:
            if now - last_key > HOLD_S:
                moving, cmd = False, (0.0, 0.0)
                send(0.0, 0.0)           # one zero on release; then stay silent (don't fight other publishers)
            else:
                send(*cmd)
    shutdown()


if __name__ == '__main__':
    main()
