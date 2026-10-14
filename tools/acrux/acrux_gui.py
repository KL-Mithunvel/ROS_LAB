#!/usr/bin/python3
"""Acrux control panel: one window for the whole gift-greeter project, run on the laptop.

    ./acrux_gui.py

What it gives you
  * E-STOP (button or Space): latches, streams zero /cmd_vel, cancels Nav2 goals, and also sends
    a zero over SSH on a second path. Release is a deliberate, confirmed click.
  * Live camera, LiDAR, map (with robot pose + scan overlay; click-drag to set initial pose / goal).
  * Drive pad (buttons or WASD, hold to move, same speed caps as ./acrux teleop).
  * Mission: start/stop mission_node.py and send y / s / r / p / h / q to it.
  * Demo <-> Development switch: change mode, reboot the robot, wait for it, reconnect ROS.
  * Development-mode helpers: start/stop the motor bridge, LiDAR and camera drivers.

Everything robot-side goes through the existing scripts in this folder (acrux, dev-mode.sh,
sensor-test.sh), so SSH key/IP settings stay in acrux.env. The robot's sudo password is asked for
when needed, kept in memory only, and never written to disk.
"""
import os
import sys

try:
    import rclpy  # noqa: F401
    import numpy  # noqa: F401
    import PIL.ImageTk  # noqa: F401
except ImportError:   # started from a venv / shell without ROS: re-exec on the system python
    if os.environ.get("_ACRUX_GUI_REEXEC"):
        sys.exit("rclpy not importable. Install ROS 2 Humble and run: "
                 "source /opt/ros/humble/setup.bash && /usr/bin/python3 acrux_gui.py")
    os.environ["_ACRUX_GUI_REEXEC"] = "1"
    os.execvp("bash", ["bash", "-c", 'source /opt/ros/humble/setup.bash && exec /usr/bin/python3 "$@"',
                       "_", os.path.abspath(__file__), *sys.argv[1:]])

import math
import queue
import re
import shlex
import signal
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np
from PIL import Image, ImageTk

import rclpy
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist
from nav_msgs.msg import OccupancyGrid
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image as RosImage, LaserScan
from std_msgs.msg import Float32, Int32, String
from tf2_ros import Buffer, TransformListener

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
GREETER = REPO / "practice" / "acrux_greeter"
ACRUX = str(HERE / "acrux")

LIN_MAX, ANG_MAX = 0.20, 0.60          # same hard caps as `./acrux drive` / wasd_teleop.py
CMD_RATE_HZ = 20.0
NAV_CANCEL_SERVICES = ["/navigate_to_pose/_action/cancel_goal",
                       "/navigate_through_poses/_action/cancel_goal",
                       "/follow_waypoints/_action/cancel_goal"]
BASE_FRAMES = ("base_link", "base_footprint")
# The X2 LiDAR is mounted rotated 180 deg (its valid arc is the robot's FRONT but shows up at +-180 deg in
# the scan). Display-only correction; editable in the LiDAR panel. Nav2/SLAM still see the raw scan.
LIDAR_ROT_DEG = 180.0

OWNER, OWS = "rigbetel-labs", "/home/rigbetel-labs/ros2_ws"   # same as sensor-test.sh
JOBDIR = "/tmp/acrux_jobs"                                   # pid + log per job, on the robot
GREETER_REMOTE = "/tmp/acrux_greeter"                        # where the greeter launch files are pushed
# Background ROS jobs run on the robot as OWNER (via sudo), detached, with pid + log files.
# name, label, command (editable in the window), needs greeter files pushed first, is a "stack"
JOBS = [
    ("slam", "SLAM mapping stack",
     "ros2 launch acrux_bringup autobringup.launch.py exploration:=True realsense:=False joy:=False", False, True),
    ("nav", "Navigation on saved map",
     "ros2 launch acrux_bringup autobringup.launch.py exploration:=False "
     "map_file:=/home/rigbetel-labs/maps/lab.yaml realsense:=False joy:=False", False, True),
    ("mapsave", "Save current map (one-shot)",
     "mkdir -p /home/rigbetel-labs/maps && ros2 run nav2_map_server map_saver_cli -f /home/rigbetel-labs/maps/lab",
     False, False),
    ("amcl", "Localization (AMCL + map_server)",
     f"ros2 launch {GREETER_REMOTE}/launch/localization.launch.py map:=/home/rigbetel-labs/maps/lab.yaml", True, False),
    ("safety", "Safety: collision monitor",
     f"ros2 launch {GREETER_REMOTE}/launch/safety.launch.py cmd_vel_in:=cmd_vel_nav cmd_vel_out:=cmd_vel", True, False),
    ("camthrottle", "Camera relay for GUI (5 Hz)",
     "python3 /tmp/acrux_tools/image_throttle.py /camera/camera/color/image_raw/compressed "
     "/gui/camera/compressed 5", "tools", False),
    ("custom", "Custom ROS command", "ros2 topic list", False, False),
]
JOB_NAMES = [j[0] for j in JOBS]

BG, FG, PANEL = "#1e2127", "#e6e6e6", "#2a2f38"
RED, GREEN, AMBER, GREY = "#d9342b", "#3fb950", "#e3a008", "#7d8590"


# --------------------------------------------------------------------------- ROS side
class Ros:
    """rclpy node in its own context + thread; the GUI reads the latest values under a lock."""

    def __init__(self, log):
        self.log = log
        self.lock = threading.Lock()
        self.ctx = rclpy.Context()
        rclpy.init(context=self.ctx)
        self.node = rclpy.create_node("acrux_gui", context=self.ctx)
        self.cmd_pub = self.node.create_publisher(Twist, "/cmd_vel", 10)
        self.greeter_pub = self.node.create_publisher(String, "/greeter/command", 10)
        self.initpose_pub = self.node.create_publisher(PoseWithCovarianceStamped, "/initialpose", 10)
        self.goal_pub = self.node.create_publisher(PoseStamped, "/goal_pose", 10)

        self.scan = None            # (angle_min, angle_inc, ranges, range_max)
        self.scan_times = []
        self.map = None             # dict(seq,w,h,res,ox,oy,img)
        self.map_seq = 0
        self.pose = None            # (x, y, yaw) in map frame
        self.image = None           # PIL image
        self.image_time = 0.0
        self.battery_pct = None
        self.battery_v = None
        self.image_topics = {}      # name -> type string
        self.estopped = False
        self._img_sub = None
        self.img_topic = None
        self._last_decode = 0.0
        self._cancel_clients = {}

        self.node.create_subscription(LaserScan, "/scan", self._on_scan, qos_profile_sensor_data)
        self.node.create_subscription(
            OccupancyGrid, "/map", self._on_map,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.node.create_subscription(Int32, "/battery/percentage", self._on_batt, 10)
        self.node.create_subscription(Float32, "/battery/voltage", self._on_batt_v, 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.node, spin_thread=False)
        self.node.create_timer(0.1, self._update_pose)
        self.node.create_timer(2.0, self._discover_images)
        self.node.create_timer(1.0 / CMD_RATE_HZ, self._estop_stream)

        self.executor = SingleThreadedExecutor(context=self.ctx)
        self.executor.add_node(self.node)
        self._run = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    # -- lifecycle
    def _spin(self):
        while self._run:
            try:
                self.executor.spin_once(timeout_sec=0.05)
            except Exception as exc:   # keep the link alive; surface the problem
                self.log(f"[ros] {type(exc).__name__}: {exc}")
                time.sleep(0.2)

    def stop(self):
        self._run = False
        self.thread.join(timeout=1.5)
        try:
            self.executor.shutdown()
            self.node.destroy_node()
            self.ctx.try_shutdown()
        except Exception:
            pass

    # -- callbacks (ROS thread)
    def _on_scan(self, m):
        now = time.monotonic()
        with self.lock:
            self.scan = (m.angle_min, m.angle_increment, list(m.ranges), m.range_max or 12.0)
            self.scan_times = [t for t in self.scan_times if now - t < 3.0] + [now]

    def _on_map(self, m):
        a = np.array(m.data, dtype=np.int8).reshape(m.info.height, m.info.width)
        rgb = np.full(a.shape + (3,), 205, np.uint8)             # unknown
        rgb[a == 0] = 250                                        # free
        rgb[a >= 50] = 20                                        # occupied
        mid = (a > 0) & (a < 50)
        rgb[mid] = 225
        img = Image.fromarray(np.flipud(rgb), "RGB")
        with self.lock:
            self.map_seq += 1
            self.map = dict(seq=self.map_seq, w=m.info.width, h=m.info.height, res=m.info.resolution,
                            ox=m.info.origin.position.x, oy=m.info.origin.position.y, img=img)

    def _on_batt(self, m):
        self.battery_pct = m.data

    def _on_batt_v(self, m):
        self.battery_v = m.data

    def _update_pose(self):
        for frame in BASE_FRAMES:
            try:
                t = self.tf_buffer.lookup_transform("map", frame, rclpy.time.Time())
            except Exception:
                continue
            q = t.transform.rotation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            with self.lock:
                self.pose = (t.transform.translation.x, t.transform.translation.y, yaw)
            return
        with self.lock:
            self.pose = None

    def _discover_images(self):
        found = {n: t[0] for n, t in self.node.get_topic_names_and_types()
                 if t and t[0] in ("sensor_msgs/msg/Image", "sensor_msgs/msg/CompressedImage")}
        with self.lock:
            self.image_topics = found

    def set_image_topic(self, name):
        with self.lock:
            types = dict(self.image_topics)
        if self._img_sub is not None:
            self.node.destroy_subscription(self._img_sub)
            self._img_sub = None
        self.img_topic = None
        with self.lock:
            self.image = None
        if not name or name not in types:
            return
        compressed = types[name].endswith("CompressedImage")
        cls = CompressedImage if compressed else RosImage
        cb = self._on_compressed if compressed else self._on_raw
        self._img_sub = self.node.create_subscription(cls, name, cb, qos_profile_sensor_data)
        self.img_topic = name

    def _store_image(self, img):
        img.thumbnail((640, 480))
        with self.lock:
            self.image, self.image_time = img, time.monotonic()

    def _on_compressed(self, m):
        if time.monotonic() - self._last_decode < 0.08:
            return
        self._last_decode = time.monotonic()
        try:
            import io
            self._store_image(Image.open(io.BytesIO(bytes(m.data))).convert("RGB"))
        except Exception as exc:
            self.log(f"[camera] decode failed: {exc}")

    def _on_raw(self, m):
        if time.monotonic() - self._last_decode < 0.08:
            return
        self._last_decode = time.monotonic()
        try:
            buf = np.frombuffer(bytes(m.data), np.uint8)
            h, w, enc = m.height, m.width, m.encoding
            if enc in ("rgb8", "bgr8"):
                a = buf.reshape(h, m.step)[:, :w * 3].reshape(h, w, 3)
                if enc == "bgr8":
                    a = a[:, :, ::-1]
            elif enc in ("mono8", "8UC1"):
                a = buf.reshape(h, m.step)[:, :w]
            elif enc in ("16UC1", "mono16"):      # depth in mm: 0..4 m -> 0..255
                a16 = np.frombuffer(bytes(m.data), np.uint16).reshape(h, m.step // 2)[:, :w]
                a = np.clip(a16 / 4000.0 * 255, 0, 255).astype(np.uint8)
            else:
                return
            self._store_image(Image.fromarray(np.ascontiguousarray(a)).convert("RGB"))
        except Exception as exc:
            self.log(f"[camera] decode failed: {exc}")

    # -- commands (any thread)
    def snapshot(self):
        with self.lock:
            sc = self.scan
            rate = (len(self.scan_times) - 1) / (self.scan_times[-1] - self.scan_times[0]) \
                if len(self.scan_times) > 1 and self.scan_times[-1] > self.scan_times[0] else 0.0
            age = time.monotonic() - self.scan_times[-1] if self.scan_times else None
            return dict(scan=sc, scan_hz=rate, scan_age=age, pose=self.pose, map=self.map,
                        image=self.image, image_age=time.monotonic() - self.image_time
                        if self.image_time else None, image_topics=dict(self.image_topics))

    def send_cmd(self, lin, ang):
        if self.estopped:
            return
        m = Twist()
        m.linear.x, m.angular.z = float(lin), float(ang)
        self.cmd_pub.publish(m)

    def greeter(self, text):
        self.greeter_pub.publish(String(data=text))

    def publish_pose(self, x, y, yaw, as_goal):
        q_z, q_w = math.sin(yaw / 2), math.cos(yaw / 2)
        stamp = self.node.get_clock().now().to_msg()
        if as_goal:
            m = PoseStamped()
            m.header.frame_id, m.header.stamp = "map", stamp
            p = m.pose
            self.goal_pub.publish(m)
        else:
            m = PoseWithCovarianceStamped()
            m.header.frame_id, m.header.stamp = "map", stamp
            m.pose.covariance[0] = m.pose.covariance[7] = 0.25
            m.pose.covariance[35] = 0.07
            p = m.pose.pose
        p.position.x, p.position.y = x, y
        p.orientation.z, p.orientation.w = q_z, q_w
        (self.goal_pub if as_goal else self.initpose_pub).publish(m)

    def _estop_stream(self):
        if self.estopped:
            self.cmd_pub.publish(Twist())

    def cancel_navigation(self):
        """Cancel every active Nav2 goal (zero goal-id + zero stamp means 'all')."""
        sent = []
        for name in NAV_CANCEL_SERVICES:
            cli = self._cancel_clients.get(name)
            if cli is None:
                cli = self._cancel_clients[name] = self.node.create_client(CancelGoal, name)
            if cli.service_is_ready():
                cli.call_async(CancelGoal.Request())
                sent.append(name.split("/")[1])
        return sent

    def estop(self):
        self.estopped = True
        for _ in range(3):
            self.cmd_pub.publish(Twist())
        return self.cancel_navigation()


# --------------------------------------------------------------------------- app
class App:
    def __init__(self, root):
        self.root = root
        root.title("Acrux control")
        root.configure(bg=BG)
        root.minsize(1180, 700)
        self.logq = queue.Queue()
        self.uiq = queue.Queue()
        self.sudo_pw = None
        self.busy = False                  # a mode switch / driver operation is running
        self.status = dict(ssh=None, linger=None, agent=0, lidar=0, cam=0, nav=0, jobs=set())
        self.job_cmd = {j[0]: tk.StringVar(value=j[2]) for j in JOBS}
        self.job_win = None
        self.job_labels = {}
        self.rviz = None
        self.keys = set()
        self.pad = (0, 0)                  # direction from on-screen buttons
        self.pad_active = False
        self.was_moving = False
        self.mission = None                # subprocess
        self.map_mode = tk.StringVar(value="view")
        self.drag = None
        self.map_xform = None
        self._map_photo = None
        self._map_key = None
        self._cam_photo = None
        self.cam_choice = tk.StringVar(value="(auto)")
        self.cam_user_set = False
        self.lin = tk.DoubleVar(value=0.10)
        self.ang = tk.DoubleVar(value=0.40)
        self.lidar_range = tk.DoubleVar(value=4.0)
        self.lidar_rot = tk.DoubleVar(value=LIDAR_ROT_DEG)

        self.style()
        self.build()
        self.ros = Ros(self.log)
        self.log("ROS link up; waiting for robot topics...")
        self.bind_keys()
        self.root.after(100, self.tick_ui)
        self.root.after(int(1000 / CMD_RATE_HZ), self.tick_cmd)
        self.root.after(500, self.tick_slow)
        threading.Thread(target=self.poll_robot, daemon=True).start()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---- layout
    def style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL)
        s.configure("TLabelframe", background=BG, foreground=FG)
        s.configure("TLabelframe.Label", background=BG, foreground=FG, font=("TkDefaultFont", 10, "bold"))
        s.configure("TButton", padding=4)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("TRadiobutton", background=BG, foreground=FG)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)],
              selectbackground=[("readonly", PANEL)], selectforeground=[("readonly", FG)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)

    def build(self):
        r = self.root
        r.columnconfigure(1, weight=1)
        r.rowconfigure(1, weight=1)

        # top bar
        top = tk.Frame(r, bg=PANEL)
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.top = top
        self.estop_btn = tk.Button(top, text="E-STOP  (Space)", bg=RED, fg="white", activebackground="#ff5a4f",
                                   font=("TkDefaultFont", 18, "bold"), relief="raised", bd=4,
                                   command=self.do_estop, padx=24, pady=6)
        self.estop_btn.pack(side="left", padx=8, pady=6)
        self.ind = {}
        for key in ("ssh", "ros", "mode", "stack", "batt", "scan"):
            lab = tk.Label(top, text=f"{key}: ?", bg=PANEL, fg=GREY, font=("TkDefaultFont", 10, "bold"), padx=8)
            lab.pack(side="left")
            self.ind[key] = lab
        ttk.Button(top, text="Reconnect ROS", command=self.reconnect_ros).pack(side="right", padx=6)
        ttk.Button(top, text="Forget sudo password", command=self.forget_pw).pack(side="right", padx=6)

        # left: camera + lidar
        left = ttk.Frame(r)
        left.grid(row=1, column=0, sticky="ns", padx=6, pady=6)
        cam = ttk.LabelFrame(left, text="Camera")
        cam.pack(fill="x")
        self.cam_box = ttk.Combobox(cam, textvariable=self.cam_choice, state="readonly", width=44)
        self.cam_box.pack(fill="x", padx=4, pady=4)
        self.cam_box.bind("<<ComboboxSelected>>", self.on_cam_select)
        self.cam_label = tk.Label(cam, bg="black", fg=GREY, text="no camera stream\n"
                                  "(start the camera driver, or pick a topic)", width=48, height=10)
        self.cam_label.pack(padx=4, pady=4)
        lid = ttk.LabelFrame(left, text="LiDAR (robot-centred, forward = up)")
        lid.pack(fill="both", expand=True, pady=(6, 0))
        row = ttk.Frame(lid)
        row.pack(fill="x")
        ttk.Label(row, text="range m").pack(side="left", padx=4)
        ttk.Spinbox(row, from_=1, to=12, increment=1, width=4, textvariable=self.lidar_range).pack(side="left")
        ttk.Label(row, text="  rotate °").pack(side="left")
        ttk.Spinbox(row, from_=-180, to=180, increment=90, width=5, textvariable=self.lidar_rot).pack(side="left")
        self.lidar_info = ttk.Label(row, text="")
        self.lidar_info.pack(side="left", padx=10)
        self.lidar = tk.Canvas(lid, width=380, height=260, bg="#0d1117", highlightthickness=0)
        self.lidar.pack(padx=4, pady=4, fill="both", expand=True)

        # centre: map
        mid = ttk.LabelFrame(r, text="Map")
        mid.grid(row=1, column=1, sticky="nsew", pady=6)
        bar = ttk.Frame(mid)
        bar.pack(fill="x")
        for text, val in (("view", "view"), ("set initial pose", "initpose"), ("send goal", "goal")):
            ttk.Radiobutton(bar, text=text, value=val, variable=self.map_mode).pack(side="left", padx=6)
        ttk.Label(bar, text="(click-drag = position + heading)").pack(side="left", padx=6)
        self.pose_label = ttk.Label(bar, text="")
        self.pose_label.pack(side="right", padx=6)
        self.map_canvas = tk.Canvas(mid, bg="#0d1117", highlightthickness=0)
        self.map_canvas.pack(fill="both", expand=True, padx=4, pady=4)
        self.map_canvas.bind("<ButtonPress-1>", self.map_press)
        self.map_canvas.bind("<B1-Motion>", self.map_motion)
        self.map_canvas.bind("<ButtonRelease-1>", self.map_release)

        # right: drive, mission, mode, drivers
        right = ttk.Frame(r)
        right.grid(row=1, column=2, sticky="ns", padx=6, pady=6)

        drive = ttk.LabelFrame(right, text="Drive (hold button or W A S D, +/- speed, X stop)")
        drive.pack(fill="x")
        pad = ttk.Frame(drive)
        pad.pack(pady=4)
        for txt, (rr, cc), d in (("▲", (0, 1), (1, 0)), ("◀", (1, 0), (0, 1)), ("▶", (1, 2), (0, -1)),
                                 ("▼", (2, 1), (-1, 0))):
            b = ttk.Button(pad, text=txt, width=4)
            b.grid(row=rr, column=cc, padx=2, pady=1)
            b.bind("<ButtonPress-1>", lambda e, d=d: self.pad_press(d))
            b.bind("<ButtonRelease-1>", lambda e: self.pad_release())
        ttk.Button(pad, text="■", width=4, command=self.stop_motion).grid(row=1, column=1, padx=2, pady=2)
        self.speed_txt = {}
        for key, label, var, mx, unit in (("lin", "linear", self.lin, LIN_MAX, "m/s"),
                                          ("ang", "angular", self.ang, ANG_MAX, "rad/s")):
            f = ttk.Frame(drive)
            f.pack(fill="x", padx=4)
            ttk.Label(f, text=label, width=8).pack(side="left")
            ttk.Scale(f, from_=0.02, to=mx, variable=var, orient="horizontal").pack(side="left", fill="x", expand=True)
            txt = tk.StringVar()
            self.speed_txt[key] = (txt, var, unit, mx)
            ttk.Label(f, textvariable=txt, width=16).pack(side="left")
            var.trace_add("write", lambda *_a, k=key: self.show_speed(k))
            self.show_speed(key)
        self.cmd_txt = tk.StringVar(value="sending: -")
        ttk.Label(drive, textvariable=self.cmd_txt).pack(anchor="w", padx=4)

        mis = ttk.LabelFrame(right, text="Gift mission")
        mis.pack(fill="x", pady=(6, 0))
        r1 = ttk.Frame(mis)
        r1.pack(fill="x", padx=4, pady=2)
        ttk.Label(r1, text="guests").pack(side="left")
        self.count = tk.IntVar(value=3)
        ttk.Spinbox(r1, from_=1, to=4, width=3, textvariable=self.count).pack(side="left", padx=4)
        self.opt_pose = tk.BooleanVar(value=False)
        self.opt_unsurveyed = tk.BooleanVar(value=False)
        ttk.Checkbutton(r1, text="set initial pose = home", variable=self.opt_pose).pack(side="left", padx=4)
        r2 = ttk.Frame(mis)
        r2.pack(fill="x", padx=4)
        default = GREETER / ("guests_surveyed.yaml" if (GREETER / "guests_surveyed.yaml").exists() else "guests.yaml")
        self.guests_file = tk.StringVar(value=str(default))
        ttk.Entry(r2, textvariable=self.guests_file, width=30).pack(side="left", fill="x", expand=True)
        ttk.Checkbutton(mis, text="allow unsurveyed (simulation only)", variable=self.opt_unsurveyed).pack(anchor="w", padx=4)
        r3 = ttk.Frame(mis)
        r3.pack(fill="x", padx=4, pady=2)
        self.mission_btn = ttk.Button(r3, text="Start mission program", command=self.toggle_mission)
        self.mission_btn.pack(side="left")
        self.mission_state = ttk.Label(r3, text="not running")
        self.mission_state.pack(side="left", padx=8)
        r4 = ttk.Frame(mis)
        r4.pack(fill="x", padx=4, pady=2)
        for text, cmd in (("Next (y)", "y"), ("Skip", "s"), ("Retry", "r"), ("Pause/Resume", "p"), ("Home", "h"),
                          ("Quit", "q")):
            ttk.Button(r4, text=text, width=11 if len(text) > 5 else 8,
                       command=lambda c=cmd: self.mission_cmd(c)).pack(side="left", padx=1)
        self.mission_status = tk.Label(mis, text="", bg=BG, fg=FG, justify="left", wraplength=360, anchor="w")
        self.mission_status.pack(fill="x", padx=4, pady=2)

        mode = ttk.LabelFrame(right, text="Robot mode (switch + reboot + reconnect)")
        mode.pack(fill="x", pady=(6, 0))
        self.mode_label = ttk.Label(mode, text="mode: ?")
        self.mode_label.pack(anchor="w", padx=4)
        rb = ttk.Frame(mode)
        rb.pack(fill="x", padx=4, pady=2)
        self.btn_demo = ttk.Button(rb, text="Switch to DEMO", command=lambda: self.switch_mode("off"))
        self.btn_demo.pack(side="left", expand=True, fill="x", padx=1)
        self.btn_dev = ttk.Button(rb, text="Switch to DEVELOPMENT", command=lambda: self.switch_mode("on"))
        self.btn_dev.pack(side="left", expand=True, fill="x", padx=1)

        drv = ttk.LabelFrame(right, text="Drivers (development mode)")
        drv.pack(fill="x", pady=(6, 0))
        self.drv_labels = {}
        for i, (name, key) in enumerate((("Motor bridge", "base"), ("LiDAR", "lidar"), ("Camera", "camera"))):
            ttk.Label(drv, text=name, width=12).grid(row=i, column=0, padx=4, pady=1)
            lab = ttk.Label(drv, text="?", width=8)
            lab.grid(row=i, column=1)
            self.drv_labels[key] = lab
            ttk.Button(drv, text="Start", width=6, command=lambda k=key: self.driver("start", k)).grid(row=i, column=2)
            ttk.Button(drv, text="Stop", width=6, command=lambda k=key: self.driver("stop", k)).grid(row=i, column=3)

        ttk.Button(drv, text="Robot jobs (ROS stacks)...", command=self.open_jobs).grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=4, pady=3)
        ttk.Button(drv, text="RViz2", width=6, command=self.toggle_rviz).grid(row=3, column=3, padx=2)

        # bottom: log
        self.logbox = ScrolledText(r, height=3, bg="#0d1117", fg="#c9d1d9", font=("monospace", 9), state="disabled")
        self.logbox.grid(row=2, column=0, columnspan=3, sticky="ew", padx=6, pady=(0, 6))

    # ---- logging / thread plumbing
    def log(self, text):
        self.logq.put(time.strftime("%H:%M:%S ") + text)

    def log_once(self, text):
        if text != getattr(self, "_last_err", None):
            self._last_err = text
            self.log(text)

    def post(self, fn):
        self.uiq.put(fn)

    def drain(self):
        try:
            while True:
                self.uiq.get_nowait()()
        except queue.Empty:
            pass
        lines = []
        try:
            while True:
                lines.append(self.logq.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.logbox.configure(state="normal")
            self.logbox.insert("end", "\n".join(lines) + "\n")
            self.logbox.see("end")
            self.logbox.configure(state="disabled")

    # ---- E-stop
    def do_estop(self):
        if self.ros.estopped:
            self.release_estop()
            return
        sent = self.ros.estop()
        self.keys.clear()
        self.pad_active = False
        self.log("E-STOP engaged: zero /cmd_vel streaming; cancelled Nav2 goals: " + (", ".join(sent) or "none reachable"))
        self.render_estop()
        threading.Thread(target=self.ssh_zero, daemon=True).start()

    def ssh_zero(self):
        """Second path: publish zero from the robot itself, in case DDS discovery from here is broken."""
        try:
            out = subprocess.run([ACRUX, "ros", "timeout 3 ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist '{}' "
                                  ">/dev/null 2>&1; echo ssh-zero-sent"], capture_output=True, text=True, timeout=15)
            self.log("E-STOP ssh path: " + (out.stdout.strip() or out.stderr.strip() or "no output"))
        except Exception as exc:
            self.log(f"E-STOP ssh path failed: {exc}")

    def release_estop(self):
        if not messagebox.askyesno("Release E-STOP", "Is the area around the robot clear?\n\n"
                                   "Releasing only stops the zero-stream. A cancelled mission stays BLOCKED/paused "
                                   "until you choose Retry/Next."):
            return
        self.ros.estopped = False
        self.log("E-STOP released.")
        self.render_estop()

    def render_estop(self):
        on = self.ros.estopped
        self.estop_btn.configure(text="RELEASE E-STOP" if on else "E-STOP  (Space)",
                                 bg=AMBER if on else RED, fg="black" if on else "white")
        self.top.configure(bg=RED if on else PANEL)
        for lab in self.ind.values():
            lab.configure(bg=RED if on else PANEL)

    # ---- teleop
    KEYMAP = {"w": (1, 0), "s": (-1, 0), "a": (0, 1), "d": (0, -1)}

    def bind_keys(self):
        r = self.root
        r.bind_all("<KeyPress>", self.key_press)
        r.bind_all("<KeyRelease>", self.key_release)
        r.bind_all("<Button-1>", lambda e: e.widget.focus_set() if e.widget.winfo_class() not in
                   ("Entry", "TEntry", "TSpinbox", "Spinbox", "TCombobox") else None, add="+")
        r.bind("<FocusOut>", lambda e: (self.keys.clear(), setattr(self, "pad_active", False)))
        self._release_jobs = {}

    def show_speed(self, key):
        txt, var, unit, mx = self.speed_txt[key]
        try:
            txt.set(f"{var.get():.2f} {unit} (max {mx:.2f})")
        except tk.TclError:
            pass

    def bump_speed(self, sign):
        for var, mx in ((self.lin, LIN_MAX), (self.ang, ANG_MAX)):
            var.set(round(min(mx, max(0.02, var.get() + sign * mx / 10)), 3))

    def key_press(self, e):
        if isinstance(e.widget, (tk.Entry, ttk.Entry, ttk.Spinbox)):
            return
        k = e.keysym.lower()
        if k == "space":
            self.do_estop()
        elif k == "x":
            self.stop_motion()
        elif k in ("plus", "equal", "kp_add"):
            self.bump_speed(+1)
        elif k in ("minus", "underscore", "kp_subtract"):
            self.bump_speed(-1)
        elif k in self.KEYMAP:
            job = self._release_jobs.pop(k, None)
            if job:
                self.root.after_cancel(job)
            self.keys.add(k)

    def key_release(self, e):
        k = e.keysym.lower()
        if k in self.KEYMAP:        # debounce X11 auto-repeat (release+press pairs)
            self._release_jobs[k] = self.root.after(60, lambda: self.keys.discard(k))

    def pad_press(self, d):
        self.pad, self.pad_active = d, True

    def pad_release(self):
        self.pad_active = False

    def stop_motion(self):
        self.keys.clear()
        self.pad_active = False
        self.ros.send_cmd(0, 0)

    def tick_cmd(self):
        try:
            self._tick_cmd()
        except Exception as exc:
            self.log_once(f"drive loop error: {type(exc).__name__}: {exc}")
        finally:
            self.root.after(int(1000 / CMD_RATE_HZ), self.tick_cmd)

    def _tick_cmd(self):
        lin_s = ang_s = 0
        if self.pad_active:
            lin_s, ang_s = self.pad
        for k in self.keys:
            l, a = self.KEYMAP[k]
            lin_s += l
            ang_s += a
        lin_s, ang_s = max(-1, min(1, lin_s)), max(-1, min(1, ang_s))
        moving = (lin_s or ang_s) and not self.ros.estopped
        if moving:
            lin_v = lin_s * min(self.lin.get(), LIN_MAX)
            ang_v = ang_s * min(self.ang.get(), ANG_MAX)
            self.ros.send_cmd(lin_v, ang_v)
            self.cmd_txt.set(f"sending: {lin_v:+.2f} m/s  {ang_v:+.2f} rad/s")
            self.was_moving = True
        elif self.was_moving:                    # one zero on release, then stay silent (don't fight Nav2)
            self.ros.send_cmd(0, 0)
            self.cmd_txt.set("sending: stopped")
            self.was_moving = False

    # ---- periodic UI refresh
    def tick_ui(self):
        try:
            self.drain()
            snap = self.ros.snapshot()
            for draw in (self.draw_lidar, self.draw_map, self.draw_camera):
                try:
                    draw(snap)
                except Exception as exc:
                    self.log_once(f"{draw.__name__} error: {type(exc).__name__}: {exc}")
        except Exception as exc:
            self.log_once(f"UI refresh error: {type(exc).__name__}: {exc}")
        finally:
            self.root.after(120, self.tick_ui)

    def tick_slow(self):
        try:
            self._tick_slow()
        except Exception as exc:
            self.log_once(f"status refresh error: {type(exc).__name__}: {exc}")
        finally:
            self.root.after(1500, self.tick_slow)

    def _tick_slow(self):
        snap = self.ros.snapshot()
        age = snap["scan_age"]
        ros_ok = age is not None and age < 2.0
        self.set_ind("ros", "ROS: linked" if ros_ok else "ROS: no data", GREEN if ros_ok else RED)
        self.set_ind("scan", f"scan {snap['scan_hz']:.1f} Hz" if ros_ok else "scan: -", GREEN if ros_ok else GREY)
        b = self.ros.battery_pct
        if b is not None:
            v = self.ros.battery_v
            self.set_ind("batt", f"battery {b}%" + (f" {v:.1f} V" if v else ""), GREEN if b > 25 else AMBER if b > 12 else RED)
        else:
            self.set_ind("batt", "battery: -", GREY)
        st = self.status
        ssh = st["ssh"]
        self.set_ind("ssh", "SSH: up" if ssh else "SSH: down" if ssh is False else "SSH: ?", GREEN if ssh else RED if ssh is False else GREY)
        if ssh:
            mode = "DEMO (autostart)" if st["linger"] == "yes" else "DEVELOPMENT"
            self.mode_label.configure(text=f"mode: {mode}")
            self.set_ind("mode", "mode: " + ("DEMO" if st["linger"] == "yes" else "DEV"), AMBER if st["linger"] != "yes" else GREEN)
            self.set_ind("stack", f"nav stack: {'up' if st['nav'] else 'down'}", GREEN if st["nav"] else GREY)
        else:
            self.mode_label.configure(text="mode: unknown (robot unreachable)")
            self.set_ind("mode", "mode: ?", GREY)
            self.set_ind("stack", "nav stack: ?", GREY)
        esp_up = self.ros.node.count_publishers("/wheel/ticks") > 0
        for key, n in (("base", st["agent"]), ("lidar", st["lidar"]), ("camera", st["cam"])):
            if key == "base" and n:
                text = "running" if esp_up else "no ESP!"
            else:
                text = "running" if n else "stopped" if ssh else "?"
            self.drv_labels[key].configure(text=text)
        for name, lab in self.job_labels.items():
            try:
                lab.configure(text="running" if name in st["jobs"] else "stopped" if ssh else "?")
            except tk.TclError:
                pass
        state = "disabled" if self.busy else "normal"
        for b in (self.btn_demo, self.btn_dev):
            b.configure(state=state)
        # camera topics
        names = sorted(snap["image_topics"])
        self.cam_box.configure(values=["(none)"] + names)
        if not self.cam_user_set and self.ros.img_topic is None and names:
            pick = self.pick_camera(names)
            if pick:
                self.cam_choice.set(pick)
                self.ros.set_image_topic(pick)
                self.log(f"camera: using {pick}")
        # mission
        if self.mission is not None and self.mission.poll() is not None:
            self.log(f"mission program exited ({self.mission.returncode})")
            self.mission = None
            self.mission_btn.configure(text="Start mission program")
            self.mission_state.configure(text="not running")
        elif self.mission is not None:
            self.ros.greeter("?")

    @staticmethod
    def pick_camera(names):
        names = [n for n in names if not n.endswith(("compressedDepth", "theora"))]
        for pred in (lambda n: n == "/gui/camera/compressed", lambda n: "color" in n and "compressed" in n, lambda n: "color" in n and "image_raw" in n,
                     lambda n: "compressed" in n and "depth" not in n, lambda n: "depth" not in n):
            for n in names:
                if pred(n):
                    return n
        return None

    def set_ind(self, key, text, color):
        self.ind[key].configure(text=text, fg=color)

    def on_cam_select(self, _e=None):
        self.cam_user_set = True
        v = self.cam_choice.get()
        self.ros.set_image_topic(None if v in ("(none)", "(auto)") else v)

    # ---- drawing
    def draw_camera(self, snap):
        img, age = snap["image"], snap["image_age"]
        if img is None or age is None or age > 3.0:
            self.cam_label.configure(image="", width=48, height=10,
                                     text="no camera stream\n(start the camera driver, or pick a topic)"
                                     if img is None else f"stream stalled ({age:.0f} s)")
            self._cam_photo = None
            return
        if img.width > 400:
            img = img.resize((400, int(img.height * 400 / img.width)))
        self._cam_photo = ImageTk.PhotoImage(img)
        self.cam_label.configure(image=self._cam_photo, text="", width=0, height=0)

    def rot_rad(self):
        try:
            return math.radians(float(self.lidar_rot.get()))
        except (tk.TclError, ValueError):
            return 0.0

    def range_value(self):
        try:
            return min(12.0, max(1.0, float(self.lidar_range.get())))
        except (tk.TclError, ValueError):
            return 4.0

    def draw_lidar(self, snap):
        c = self.lidar
        w, h = max(c.winfo_width(), 100), max(c.winfo_height(), 100)
        c.delete("all")
        cx, cy = w / 2, h / 2
        rng = self.range_value()
        scale = (min(w, h) / 2 - 12) / rng
        for m in range(1, int(rng) + 1):
            c.create_oval(cx - m * scale, cy - m * scale, cx + m * scale, cy + m * scale, outline="#30363d")
            c.create_text(cx + 3, cy - m * scale - 2, text=f"{m} m", fill="#6e7681", anchor="sw", font=("TkDefaultFont", 7))
        c.create_line(cx, cy, cx, cy - 20, fill="#58a6ff", width=2)
        c.create_polygon(cx, cy - 9, cx - 6, cy + 6, cx + 6, cy + 6, fill="#58a6ff")
        sc = snap["scan"]
        if sc is None or snap["scan_age"] is None or snap["scan_age"] > 2.0:
            c.create_text(cx, cy + 40, text="no /scan data", fill=GREY)
            self.lidar_info.configure(text="")
            return
        a0, inc, ranges, rmax = sc
        near = (9e9, 0.0)
        rot = self.rot_rad()
        for i, r in enumerate(ranges):
            if not (0.05 < r < rmax) or r != r:
                continue
            th = math.atan2(math.sin(a0 + i * inc + rot), math.cos(a0 + i * inc + rot))
            if r < near[0]:
                near = (r, th)
            if r > rng:
                continue
            x, y = cx - r * math.sin(th) * scale, cy - r * math.cos(th) * scale
            col = "#f85149" if r < 0.6 else "#e3a008" if r < 1.2 else "#3fb950"
            c.create_rectangle(x - 1, y - 1, x + 1, y + 1, fill=col, outline=col)
        if near[0] < 9e8:
            self.lidar_info.configure(text=f"nearest {near[0]:.2f} m at {math.degrees(near[1]):+.0f}°   "
                                           f"{sum(1 for r in ranges if 0.05 < r < rmax)}/{len(ranges)} beams")

    def draw_map(self, snap):
        c = self.map_canvas
        c.delete("pose", "scan", "drag")
        w, h = max(c.winfo_width(), 50), max(c.winfo_height(), 50)
        m = snap["map"]
        if m is None:
            c.delete("map")
            c.create_text(w / 2, h / 2, text="no /map yet\n(demo mode: SLAM publishes it; or run localization)",
                          fill=GREY, tags="pose", justify="center")
            self.map_xform = None
            return
        s = min(w / m["w"], h / m["h"])
        ox_px, oy_px = (w - m["w"] * s) / 2, (h - m["h"] * s) / 2
        key = (m["seq"], w, h)
        if key != self._map_key:
            img = m["img"].resize((max(1, int(m["w"] * s)), max(1, int(m["h"] * s))), Image.NEAREST)
            self._map_photo = ImageTk.PhotoImage(img)
            self._map_key = key
            c.delete("map")
            c.create_image(ox_px, oy_px, image=self._map_photo, anchor="nw", tags="map")
            c.tag_lower("map")
        self.map_xform = (m, s, ox_px, oy_px)

        def to_px(x, y):
            return ox_px + (x - m["ox"]) / m["res"] * s, oy_px + (m["h"] - (y - m["oy"]) / m["res"]) * s

        pose = snap["pose"]
        if pose is None:
            self.pose_label.configure(text="robot pose: no map→base TF")
            return
        x, y, yaw = pose
        self.pose_label.configure(text=f"x {x:+.2f}  y {y:+.2f}  yaw {math.degrees(yaw):+.0f}°")
        sc = snap["scan"]
        if sc is not None and snap["scan_age"] is not None and snap["scan_age"] < 2.0:
            a0, inc, ranges, rmax = sc
            rot = self.rot_rad()
            for i, r in enumerate(ranges):
                if 0.05 < r < rmax:
                    th = yaw + a0 + i * inc + rot
                    px, py = to_px(x + r * math.cos(th), y + r * math.sin(th))
                    c.create_rectangle(px - 1, py - 1, px + 1, py + 1, fill="#f85149", outline="", tags="scan")
        px, py = to_px(x, y)
        L = 11
        tip = (px + L * math.cos(yaw), py - L * math.sin(yaw))
        l_ = (px + L * 0.7 * math.cos(yaw + 2.5), py - L * 0.7 * math.sin(yaw + 2.5))
        r_ = (px + L * 0.7 * math.cos(yaw - 2.5), py - L * 0.7 * math.sin(yaw - 2.5))
        c.create_polygon(*tip, *l_, *r_, fill="#58a6ff", outline="white", tags="pose")

    # ---- map interaction
    def map_to_world(self, ex, ey):
        if not self.map_xform:
            return None
        m, s, ox_px, oy_px = self.map_xform
        return m["ox"] + (ex - ox_px) / s * m["res"], m["oy"] + (m["h"] - (ey - oy_px) / s) * m["res"]

    def map_press(self, e):
        if self.map_mode.get() != "view" and self.map_xform:
            self.drag = (e.x, e.y, e.x, e.y)

    def map_motion(self, e):
        if self.drag:
            self.drag = (self.drag[0], self.drag[1], e.x, e.y)
            self.map_canvas.delete("drag")
            self.map_canvas.create_line(self.drag, fill=AMBER, width=3, arrow="last", tags="drag")

    def map_release(self, e):
        if not self.drag:
            return
        x0, y0, _, _ = self.drag
        self.drag = None
        self.map_canvas.delete("drag")
        w0 = self.map_to_world(x0, y0)
        if w0 is None:
            return
        yaw = 0.0
        if math.hypot(e.x - x0, e.y - y0) > 8:
            yaw = math.atan2(-(e.y - y0), e.x - x0)
        goal = self.map_mode.get() == "goal"
        if goal:
            if self.ros.estopped:
                self.log("goal not sent: E-STOP is engaged")
                return
            if not messagebox.askyesno("Send goal", f"Drive to x={w0[0]:.2f} y={w0[1]:.2f} "
                                       f"yaw={math.degrees(yaw):.0f}° ?"):
                return
        self.ros.publish_pose(w0[0], w0[1], yaw, as_goal=goal)
        self.log(f"{'goal' if goal else 'initial pose'} sent: x={w0[0]:.2f} y={w0[1]:.2f} yaw={math.degrees(yaw):.0f}°")

    # ---- mission
    def toggle_mission(self):
        if self.mission is not None:
            if messagebox.askyesno("Stop mission", "Stop mission_node.py? (Ctrl-C: it cancels the active goal)"):
                self.mission.send_signal(signal.SIGINT)
            return
        cmd = [sys.executable, str(GREETER / "mission_node.py"), "--count", str(self.count.get()),
               "--guests", self.guests_file.get()]
        if self.opt_pose.get():
            cmd.append("--set-initial-pose")
        if self.opt_unsurveyed.get():
            cmd.append("--allow-unsurveyed")
        try:
            self.mission = subprocess.Popen(cmd, cwd=GREETER, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True, bufsize=1)
        except OSError as exc:
            self.log(f"cannot start mission: {exc}")
            return
        self.mission_btn.configure(text="Stop mission program")
        self.mission_state.configure(text=f"running ({self.count.get()} guests)")
        threading.Thread(target=self.read_mission, args=(self.mission,), daemon=True).start()
        self.log("mission program started: " + " ".join(cmd[1:]))

    def read_mission(self, proc):
        seen_help = False
        for line in proc.stdout:
            line = line.rstrip()
            if "state=" in line:
                txt = line.split("]", 1)[-1].strip()
                self.post(lambda t=txt: self.mission_status.configure(text=t))
                continue
            if "Commands:" in line:
                if seen_help:
                    continue
                seen_help = True
            self.log("[mission] " + line)

    def mission_cmd(self, c):
        if self.ros.estopped and c in ("y", "r", "p"):
            self.log("mission command blocked: E-STOP is engaged (release it first)")
            return
        if c == "q" and not messagebox.askyesno("Quit mission", "End the mission program?"):
            return
        self.ros.greeter(c)
        self.log(f"mission command: {c}")
        if self.mission is None:
            self.log("(mission program is not running; start it first)")

    # ---- SSH helpers / robot state
    def run_script(self, args, env_pw=False, timeout=240):
        env = dict(os.environ)
        if env_pw:
            env["ACRUX_SUDO_PW"] = self.sudo_pw
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env, cwd=HERE)
        return p.returncode, (p.stdout + p.stderr).strip()

    def poll_robot(self):
        probe = ("echo LINGER=$(loginctl show-user rigbetel-labs -p Linger --value 2>/dev/null);"
                 "echo AGENT=$(pgrep -fc '[l]ib/micro_ros_agent/micro_ros_agent');echo LIDAR=$(pgrep -fc '[y]dlidar_ros2_driver_node');"
                 "echo CAM=$(pgrep -fc '[r]ealsense2_camera_node');"
                 "echo NAV=$(pgrep -fc '[n]av2_|[b]t_navigator|[s]lam_toolbox|[c]artographer_node');"
                 f"for n in {' '.join(JOB_NAMES)}; do kill -0 $(cat {JOBDIR}/$n.pid 2>/dev/null) 2>/dev/null "
                 "&& echo JOB_$n=1; done; true")
        while True:
            try:
                p = subprocess.run([ACRUX, "run", probe], capture_output=True, text=True, timeout=12, cwd=HERE)
                vals = dict(re.findall(r"^(\w+)=(.*)$", p.stdout, re.M))
                if p.returncode == 0 and vals:
                    self.status = dict(ssh=True, linger=vals.get("LINGER", "").strip(),
                                       agent=int(vals.get("AGENT", "0") or 0), lidar=int(vals.get("LIDAR", "0") or 0),
                                       cam=int(vals.get("CAM", "0") or 0), nav=int(vals.get("NAV", "0") or 0),
                                       jobs={k[4:] for k, v in vals.items() if k.startswith("JOB_") and v.strip() == "1"})
                else:
                    self.status = dict(ssh=False, linger=None, agent=0, lidar=0, cam=0, nav=0, jobs=set())
            except Exception:
                self.status = dict(ssh=False, linger=None, agent=0, lidar=0, cam=0, nav=0, jobs=set())
            time.sleep(4)

    def need_pw(self):
        if self.sudo_pw is None:
            pw = simpledialog.askstring("Robot sudo password", "Password for the robot's sudo (kept in memory only):",
                                        show="*", parent=self.root)
            if not pw:
                return False
            self.sudo_pw = pw
        return True

    def forget_pw(self):
        self.sudo_pw = None
        self.log("sudo password forgotten.")

    # ---- drivers
    def driver(self, action, which):
        if self.busy:
            return
        if not self.need_pw():
            return
        self.busy = True
        self.log(f"driver {action} {which} ...")

        def work():
            try:
                rc, out = self.run_script([str(HERE / "sensor-test.sh"), action, which], env_pw=True, timeout=90)
                self.log(out or f"(rc={rc})")
                if rc != 0 and "sudo" in out.lower() and "password" in out.lower():
                    self.sudo_pw = None
            except Exception as exc:
                self.log(f"driver {action} {which} failed: {exc}")
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()

    # ---- background ROS jobs on the robot
    def root_run(self, script, timeout=60):
        """Run a bash snippet as root on the robot (password on stdin, no TTY)."""
        p = subprocess.run([ACRUX, "run", f"sudo -S -p '' bash -c {shlex.quote(script)}"],
                           input=self.sudo_pw + "\n", capture_output=True, text=True, timeout=timeout, cwd=HERE)
        out = (p.stdout + p.stderr).strip()
        if "incorrect password" in out.lower() or "sorry" in out.lower():
            self.sudo_pw = None
        return p.returncode, out

    def open_jobs(self):
        if self.job_win is not None and self.job_win.winfo_exists():
            self.job_win.lift()
            return
        w = self.job_win = tk.Toplevel(self.root)
        w.title("Acrux robot jobs")
        w.configure(bg=BG)
        w.columnconfigure(2, weight=1)
        ttk.Label(w, text="Run on the robot as rigbetel-labs, detached; logs in /tmp/acrux_jobs/. "
                          "Commands are editable. Presets are UNVERIFIED on the robot: read the guide §7-8.",
                  wraplength=900).grid(row=0, column=0, columnspan=6, padx=6, pady=6, sticky="w")
        for i, (name, label, _cmd, push, stack) in enumerate(JOBS, start=1):
            ttk.Label(w, text=label, width=30).grid(row=i, column=0, padx=6, pady=2, sticky="w")
            lab = ttk.Label(w, text="?", width=9)
            lab.grid(row=i, column=1)
            self.job_labels[name] = lab
            ttk.Entry(w, textvariable=self.job_cmd[name], width=90).grid(row=i, column=2, sticky="ew", padx=4)
            ttk.Button(w, text="Start", width=6, command=lambda n=name: self.job_start(n)).grid(row=i, column=3)
            ttk.Button(w, text="Stop", width=6, command=lambda n=name: self.job_stop(n)).grid(row=i, column=4)
            ttk.Button(w, text="Log", width=6, command=lambda n=name: self.job_log(n)).grid(row=i, column=5, padx=4)

    def job_start(self, name):
        job = next(j for j in JOBS if j[0] == name)
        cmd = self.job_cmd[name].get().strip()
        if not cmd or self.busy:
            return
        if job[4] and self.status.get("linger") == "yes" and not messagebox.askyesno(
                "Demo mode", "The robot is in DEMO mode: its autostart stack is already running.\n"
                             "Starting another stack on top will conflict. Start anyway?"):
            return
        if self.ros.estopped and job[4]:
            self.log("stack not started: E-STOP is engaged")
            return
        if not self.need_pw():
            return
        self.busy = True
        self.log(f"job {name}: starting ...")

        def work():
            try:
                if job[3] == "tools":
                    rc = subprocess.run([ACRUX, "push", str(HERE / "image_throttle.py"), "/tmp/acrux_tools/image_throttle.py"],
                                        capture_output=True, text=True, timeout=60, cwd=HERE)
                    if rc.returncode:   # directory may not exist yet
                        subprocess.run([ACRUX, "run", "mkdir -p /tmp/acrux_tools"], timeout=20, cwd=HERE)
                        rc = subprocess.run([ACRUX, "push", str(HERE / "image_throttle.py"),
                                             "/tmp/acrux_tools/image_throttle.py"], capture_output=True, text=True,
                                            timeout=60, cwd=HERE)
                    self.log(f"job {name}: pushed image_throttle.py (rc={rc.returncode})")
                elif job[3]:
                    rc = subprocess.run([ACRUX, "push", f"{GREETER}/", f"{GREETER_REMOTE}/"],
                                        capture_output=True, text=True, timeout=60, cwd=HERE)
                    self.log(f"job {name}: pushed greeter files (rc={rc.returncode})")
                inner = (f"echo $$ > {JOBDIR}/{name}.pid; source /opt/ros/humble/setup.bash; "
                         f"source {OWS}/install/setup.bash 2>/dev/null; exec bash -c {shlex.quote(cmd)}")
                f = f"{JOBDIR}/{name}"
                script = (f"mkdir -p {JOBDIR}; chmod 777 {JOBDIR}; "
                          f"if [ -f {f}.pid ] && kill -0 $(cat {f}.pid) 2>/dev/null; then echo 'already running'; exit 0; fi; "
                          f"rm -f {f}.pid; : > {f}.log; chmod 666 {f}.log; "
                          f"setsid -f runuser -u {OWNER} -- bash -lc {shlex.quote(inner)} > {f}.log 2>&1; sleep 3; "
                          f"if kill -0 $(cat {f}.pid 2>/dev/null) 2>/dev/null; then echo started; "
                          f"else echo 'exited already (one-shot or failed):'; tail -n 15 {f}.log; fi")
                rc, out = self.root_run(script, timeout=60)
                self.log(f"job {name}: {out or 'rc=' + str(rc)}")
            except Exception as exc:
                self.log(f"job {name} failed: {exc}")
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()

    def job_stop(self, name):
        if self.busy or not self.need_pw():
            return
        self.busy = True
        self.log(f"job {name}: stopping ...")

        def work():
            try:
                f = f"{JOBDIR}/{name}"
                script = (f"[ -f {f}.pid ] || {{ echo 'not running'; exit 0; }}; p=$(cat {f}.pid); "
                          f"s=$(ps -o sid= -p $p 2>/dev/null | tr -d ' '); "
                          f"if [ -n \"$s\" ] && [ \"$s\" != 1 ]; then pkill -INT -s $s; sleep 3; pkill -KILL -s $s; fi; "
                          f"rm -f {f}.pid; echo stopped")
                rc, out = self.root_run(script, timeout=40)
                self.log(f"job {name}: {out or 'rc=' + str(rc)}")
            except Exception as exc:
                self.log(f"job {name} stop failed: {exc}")
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()

    def job_log(self, name):
        def work():
            p = subprocess.run([ACRUX, "run", f"tail -n 40 {JOBDIR}/{name}.log 2>&1"], capture_output=True,
                               text=True, timeout=20, cwd=HERE)
            self.log(f"--- job {name} log ---\n{p.stdout.strip() or p.stderr.strip() or '(empty)'}")
        threading.Thread(target=work, daemon=True).start()

    def toggle_rviz(self):
        if self.rviz is not None and self.rviz.poll() is None:
            self.rviz.terminate()
            return
        try:
            self.rviz = subprocess.Popen(["rviz2"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log("rviz2 started on the laptop")
        except OSError as exc:
            self.log(f"cannot start rviz2: {exc}")

    # ---- mode switch + reboot + reconnect
    def switch_mode(self, which):
        target = "DEVELOPMENT" if which == "on" else "DEMO"
        if self.busy:
            return
        if not messagebox.askyesno(
                f"Switch to {target}",
                f"Switch the robot to {target} mode, then REBOOT it and reconnect?\n\n"
                "The robot will stop moving and be unreachable for 1-3 minutes.\n"
                "The E-STOP latch will be engaged during the switch."):
            return
        if not self.need_pw():
            return
        self.busy = True
        if not self.ros.estopped:
            self.do_estop()
        threading.Thread(target=self.switch_worker, args=(which, target), daemon=True).start()

    def switch_worker(self, which, target):
        try:
            self.log(f"== switching to {target} ==")
            rc, out = self.run_script([str(HERE / "dev-mode.sh"), which], env_pw=True, timeout=120)
            self.log(out)
            if rc != 0:
                self.log("mode switch FAILED; not rebooting. (Wrong sudo password? it was forgotten.)")
                self.sudo_pw = None
                return
            self.log("rebooting robot ...")
            pw = self.sudo_pw
            subprocess.run(
                [ACRUX, "run", "sudo -S -p '' bash -c 'reboot || systemctl reboot || shutdown -r now'"],
                input=pw + "\n", capture_output=True, text=True, timeout=30, cwd=HERE)
            went_down = self.wait_ssh(False, 90)
            if not went_down:
                self.log("robot never went offline - the reboot command probably did not run. "
                         "Reboot it by hand, then press Reconnect ROS.")
                return
            self.log("robot is down; waiting for it to come back (up to 4 min) ...")
            if not self.wait_ssh(True, 240):
                self.log("robot did not come back within 4 minutes.")
                return
            self.log("robot SSH is back; letting services settle (20 s) ...")
            time.sleep(20)
            self.post(self.reconnect_ros)
            self.log(f"== now in {target} mode. E-STOP is still latched; release it when the area is clear. ==")
            if which == "on":
                self.log("development mode: nothing autostarts. Start the motor bridge / LiDAR / camera under "
                         "'Drivers' and bring up what you need.")
        except Exception as exc:
            self.log(f"mode switch error: {exc}")
        finally:
            self.busy = False

    def wait_ssh(self, want_up, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                p = subprocess.run([ACRUX, "run", "true"], capture_output=True, timeout=10, cwd=HERE)
                up = p.returncode == 0
            except Exception:
                up = False
            if up == want_up:
                return True
            time.sleep(3)
        return False

    def reconnect_ros(self):
        self.log("reconnecting ROS ...")
        estopped = self.ros.estopped
        topic = self.ros.img_topic
        self.ros.stop()
        self.ros = Ros(self.log)
        self.ros.estopped = estopped
        self.cam_user_set = topic is not None and self.cam_user_set
        self.map_xform, self._map_key = None, None

    # ---- shutdown
    def on_close(self):
        if self.mission is not None and not messagebox.askyesno("Quit", "Mission program is running. Stop it and quit?"):
            return
        try:
            for _ in range(3):
                self.ros.cmd_pub.publish(Twist())
            if self.mission is not None:
                self.mission.send_signal(signal.SIGINT)
            self.ros.stop()
        finally:
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
