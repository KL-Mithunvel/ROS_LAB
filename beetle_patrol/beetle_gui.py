#!/usr/bin/python3
"""BeetleBot patrol control panel (Tkinter). Thin frontend: all logic is in gui/view_model.py.

    ./beetle_gui.py              # re-execs on /usr/bin/python3 with ROS Humble sourced if needed
    ./beetle_gui.py --selftest   # build the window, feed canned data, exit 0 (skips without DISPLAY)

Domain: uses ROS_DOMAIN_ID if set, otherwise 154 (155 is shared with another robot and is flagged red).
Robot-stack control over SSH (start/stop base stack, patrol launch) is out of scope: placeholder only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SELFTEST = "--selftest" in sys.argv

if not SELFTEST:
    try:
        import rclpy  # noqa: F401
    except ImportError:     # started from a venv / shell without ROS: re-exec on the system python
        if os.environ.get("_BEETLE_GUI_REEXEC"):
            sys.exit("rclpy not importable: source /opt/ros/humble/setup.bash && /usr/bin/python3 beetle_gui.py")
        os.environ["_BEETLE_GUI_REEXEC"] = "1"
        os.execvp("bash", ["bash", "-c", 'source /opt/ros/humble/setup.bash && exec /usr/bin/python3 "$@"',
                           "_", os.path.abspath(__file__), *sys.argv[1:]])

sys.path.insert(0, HERE)
os.environ.setdefault("ROS_DOMAIN_ID", "154")

import json
import math
import queue
import threading
import time
import tkinter as tk
from array import array
from tkinter import messagebox, simpledialog, ttk

from gui import view_model as vm

try:
    from PIL import Image, ImageTk
except ImportError:     # camera / map image degrade to "unavailable"
    Image = ImageTk = None

BG, FG, PANEL = "#1e2227", "#e6e6e6", "#2a2f36"
RED, AMBER, GREEN = "#d63031", "#e0a800", "#2ea043"
STATUS_COLOUR = {"ok": GREEN, "warn": AMBER, "lost": RED}
DEFAULT_TOPICS = {"scan": "/scan", "camera": "/pi_camera/image_raw/compressed", "nav_cmd_vel": "/cmd_vel_nav",
                  "disarm_service": "/lyra/disarm"}
# Laser yaw relative to base_link (not in /patrol/status; the sim uses 180). Override: BEETLE_LASER_YAW_DEG.
LASER_YAW = math.radians(float(os.environ.get("BEETLE_LASER_YAW_DEG", "0")))


def load_topics():
    try:
        import yaml
        with open(os.environ.get("BEETLE_PATROL_YAML") or os.path.join(HERE, "patrol.yaml")) as f:
            return {**DEFAULT_TOPICS, **(yaml.safe_load(f).get("topics") or {})}
    except Exception:
        return dict(DEFAULT_TOPICS)


CAMERA_TOPIC = load_topics().get("camera", "/patrol/camera/compressed")   # patrol.yaml topics.camera


# --------------------------------------------------------------------------- ROS plumbing
class Bridge:
    """rclpy node on a background thread. Incoming data goes to `events` as (kind, payload)."""

    def __init__(self, topics):
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
        from geometry_msgs.msg import Twist
        from nav_msgs.msg import OccupancyGrid
        from sensor_msgs.msg import CompressedImage, LaserScan
        from std_msgs.msg import String
        from std_srvs.srv import Trigger
        self._Twist, self._String, self._Trigger = Twist, String, Trigger
        self.events = queue.Queue(maxsize=500)
        self._last_cam = 0.0
        self.ctx = rclpy.Context()
        rclpy.init(context=self.ctx)
        self.node = rclpy.create_node("beetle_gui", context=self.ctx)
        n = self.node
        for kind, topic in (("status", "/patrol/status"), ("decision", "/patrol/decision"),
                            ("warning", "/patrol/warning")):
            n.create_subscription(String, topic, lambda m, k=kind: self._json(k, m), 10)
        n.create_subscription(OccupancyGrid, "/map", self._on_map, QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        n.create_subscription(LaserScan, topics["scan"], self._on_scan, qos_profile_sensor_data)
        n.create_subscription(CompressedImage, CAMERA_TOPIC, self._on_camera, qos_profile_sensor_data)
        self.pub_cmd = n.create_publisher(String, "/patrol/command", 10)
        self.pub_twist = n.create_publisher(Twist, topics["nav_cmd_vel"], 10)
        self.disarm_cli = n.create_client(Trigger, topics["disarm_service"])
        self.ex = SingleThreadedExecutor(context=self.ctx)
        self.ex.add_node(n)
        self._run = True
        threading.Thread(target=self._spin, daemon=True).start()

    def _spin(self):
        while self._run:
            try:
                self.ex.spin_once(timeout_sec=0.05)
            except Exception as exc:
                self._put("log", f"ros: {type(exc).__name__}: {exc}")
                time.sleep(0.2)

    def _put(self, kind, payload):
        try:
            self.events.put_nowait((kind, payload))
        except queue.Full:
            pass

    def _json(self, kind, msg):
        try:
            self._put(kind, json.loads(msg.data))
        except ValueError:
            self._put("log", f"bad JSON on {kind}")

    def _on_map(self, m):
        lut = bytes(150 if v == 255 else (30 if 50 <= v <= 100 else 250) for v in range(256))
        pix = array("b", m.data).tobytes().translate(lut)
        self._put("map", {"info": {"origin": (m.info.origin.position.x, m.info.origin.position.y),
                                   "width": m.info.width, "height": m.info.height,
                                   "resolution": m.info.resolution}, "pixels": pix})

    def _on_scan(self, m):
        self._put("scan", {"angle_min": m.angle_min, "inc": m.angle_increment,
                           "ranges": list(m.ranges), "range_max": m.range_max or 12.0})

    def _on_camera(self, m):
        now = time.monotonic()
        if now - self._last_cam >= 0.5:         # ~2 fps is plenty for a status view
            self._last_cam = now
            self._put("camera", bytes(m.data))

    # -- outgoing
    def command(self, cmd, **fields):
        from patrol import protocol
        self.pub_cmd.publish(self._String(data=json.dumps(protocol.build_command(cmd, **fields))))

    def twist(self, lin, ang):
        t = self._Twist()
        t.linear.x, t.angular.z = float(lin), float(ang)
        self.pub_twist.publish(t)

    def estop(self):
        """Command + direct disarm service + zero velocity: works even if patrol_node is dead."""
        self.command("estop")
        for _ in range(3):
            self.twist(0.0, 0.0)
        if self.disarm_cli.service_is_ready():
            self.disarm_cli.call_async(self._Trigger.Request())
        else:
            self._put("log", "disarm service not available (command + zero cmd_vel were sent)")

    def stop(self):
        self._run = False
        try:
            self.ex.shutdown()
            self.node.destroy_node()
            self.ctx.try_shutdown()
        except Exception:
            pass


# --------------------------------------------------------------------------- GUI
class App:
    def __init__(self, root, bridge, domain):
        self.root, self.bridge, self.domain = root, bridge, domain
        self.status = None
        self.last_rx = None
        self.history, self.warnings = vm.History(), vm.WarningLog()
        self.estop = vm.EstopLatch()
        self.keys, self.sender = vm.HeldKeys(), vm.DriveSender()
        self.new_zones = vm.NewZoneTracker()
        self.debounce = vm.Debouncer()
        self.map = None             # {"info":..., "image": PIL image}
        self.scan = None
        self.cam_data = None
        self.photos = {}            # keep PhotoImage refs alive
        self.logs = []
        root.title("BeetleBot patrol")
        root.configure(bg=BG)
        root.minsize(1100, 720)
        self._style()
        self._build_top()
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=6)
        left, right = tk.Frame(body, bg=BG), tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        right.pack(side="right", fill="y", padx=(6, 0))
        self.map_canvas = tk.Canvas(left, bg="#101317", highlightthickness=0, width=560, height=420)
        self.map_canvas.pack(fill="both", expand=True)
        self._build_sensors(left)
        self._build_decision(right)
        self._build_warnings(right)
        self._build_controls()
        self.status_line = tk.Label(root, text="", anchor="w", bg=BG, fg=FG, font=("TkDefaultFont", 10, "bold"))
        self.status_line.pack(fill="x", padx=8)
        for key, d in (("w", "forward"), ("s", "back"), ("a", "left"), ("d", "right")):
            root.bind(f"<KeyPress-{key}>", lambda e, d=d: self.keys.press(d))
            root.bind(f"<KeyRelease-{key}>", lambda e, d=d: self.keys.release(d, time.monotonic()))
        root.bind("<space>", lambda e: self.do_estop())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.dirty = True
        self.root.after(50, self.tick_drive)
        self.root.after(100, self.tick_ui)

    # -- layout
    def _style(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=20)
        s.configure("Treeview.Heading", background="#3a414a", foreground=FG)

    def _label(self, parent, text, **kw):
        return tk.Label(parent, text=text, bg=kw.pop("bg", BG), fg=kw.pop("fg", FG), **kw)

    def _build_top(self):
        top = tk.Frame(self.root, bg=PANEL)
        top.pack(fill="x", padx=6, pady=6)
        self.estop_btn = tk.Button(top, text="E-STOP  (Space)", bg=RED, fg="white", activebackground="#ff5a4f",
                                   font=("TkDefaultFont", 14, "bold"), padx=20, pady=6, command=self.do_estop)
        self.estop_btn.pack(side="left", padx=8, pady=6)
        text, warn = vm.domain_label(self.domain)
        self._label(top, text, bg=RED if warn else PANEL, fg="white" if warn else FG,
                    font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=8)
        self.flag_labels = {}
        for name in ("mode", "armed", "nav_ready", "explore", "recording"):
            f = tk.Frame(top, bg=PANEL)
            f.pack(side="left", padx=8)
            self._label(f, name, bg=PANEL, fg="#9aa4af", font=("TkDefaultFont", 8)).pack()
            lab = self._label(f, "?", bg=PANEL, font=("TkDefaultFont", 11, "bold"))
            lab.pack()
            self.flag_labels[name] = lab

    def _build_sensors(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)
        self.cam_label = tk.Label(row, text="camera: waiting", bg="#101317", fg="#778", width=34, height=10)
        self.cam_label.pack(side="left")
        m = tk.Frame(row, bg=BG)
        m.pack(side="left", fill="x", expand=True, padx=8)
        self._label(m, "Motion confidence", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.motion_bars = {}
        for name in ("lidar", "camera", "fused"):
            r = tk.Frame(m, bg=BG)
            r.pack(fill="x", pady=1)
            self._label(r, name, width=7, anchor="w").pack(side="left")
            c = tk.Canvas(r, width=200, height=14, bg=PANEL, highlightthickness=0)
            c.pack(side="left")
            v = self._label(r, "-", width=5)
            v.pack(side="left")
            self.motion_bars[name] = (c, v)
        self.ego_label = self._label(m, "ego: -")
        self.ego_label.pack(anchor="w")

    def _build_decision(self, parent):
        self._label(parent, "Decision (why this zone next)", font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        self.dec_canvas = tk.Canvas(parent, width=520, height=170, bg=PANEL, highlightthickness=0)
        self.dec_canvas.pack()
        self.explain = self._label(parent, "No decision yet.", wraplength=510, justify="left", anchor="w")
        self.explain.pack(fill="x")
        self.skip_label = self._label(parent, "", fg=AMBER, wraplength=510, justify="left", anchor="w")
        self.skip_label.pack(fill="x")
        self.hist = tk.Listbox(parent, height=5, bg=PANEL, fg=FG, highlightthickness=0, width=70)
        self.hist.pack(fill="x", pady=2)
        wf = tk.LabelFrame(parent, text="Weights (sent on release)", bg=BG, fg=FG)
        wf.pack(fill="x", pady=2)
        self.sliders = {}
        for t in vm.TERMS:
            s = tk.Scale(wf, from_=0, to=100, orient="horizontal", label=t, bg=BG, fg=FG,
                         highlightthickness=0, length=120, command=lambda _v: self.on_slider())
            s.pack(side="left", padx=2)
            s.bind("<ButtonRelease-1>", lambda e: self.on_slider(force=True))
            self.sliders[t] = s
        self.weights_label = self._label(parent, "", anchor="w")
        self.weights_label.pack(fill="x")

    def _build_warnings(self, parent):
        self.banner = tk.Label(parent, text="no warnings", bg=PANEL, fg="#9aa4af",
                               font=("TkDefaultFont", 11, "bold"))
        self.banner.pack(fill="x", pady=(6, 2))
        cols = ("time", "zone", "x,y", "fused", "lidar", "camera")
        self.warn_tree = ttk.Treeview(parent, columns=cols, show="headings", height=5)
        for c in cols:
            self.warn_tree.heading(c, text=c)
            self.warn_tree.column(c, width=80 if c != "x,y" else 90, anchor="center")
        self.warn_tree.pack(fill="x")

    def _build_controls(self):
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=6, pady=4)
        self.cmd_buttons = []
        self.set_start_btn = None
        for text, fn in (("Start", lambda: self.cmd("start")), ("Pause", lambda: self.cmd("pause")),
                         ("Explore start", lambda: self.cmd("explore_start")),
                         ("Explore stop", lambda: self.cmd("explore_stop")),
                         ("Save map", self.save_map), ("Set start here", self.set_start), ("Record", lambda: self.cmd("record")),
                         ("Stop rec", lambda: self.cmd("stop_record")), ("Arm", self.arm),
                         ("Disarm", lambda: self.cmd("disarm")), ("Release E-STOP", self.release)):
            b = tk.Button(bar, text=text, command=fn)
            b.pack(side="left", padx=2)
            self.cmd_buttons.append(b)
            if text == "Set start here":
                self.set_start_btn = b
        pad = tk.LabelFrame(bar, text=f"Drive (WASD, hold; max {vm.LIN_CAP} m/s, {vm.ANG_CAP} rad/s)", bg=BG, fg=FG)
        pad.pack(side="left", padx=12)
        self.pad_buttons = []
        for text, d, r, c in (("W", "forward", 0, 1), ("A", "left", 1, 0), ("S", "back", 1, 1), ("D", "right", 1, 2)):
            b = tk.Button(pad, text=text, width=3)
            b.grid(row=r, column=c)
            b.bind("<ButtonPress-1>", lambda e, d=d: self.keys.press(d))
            b.bind("<ButtonRelease-1>", lambda e, d=d: self.keys.release(d, 0.0))   # no grace for clicks
            self.pad_buttons.append(b)
        self.drive_hint = self._label(pad, "", fg=AMBER)
        self.drive_hint.grid(row=0, column=3, padx=6)
        stack = tk.LabelFrame(bar, text="Robot stack (SSH) - placeholder", bg=BG, fg="#778")
        stack.pack(side="right")
        for text in ("Start base", "Stop base", "Launch patrol"):
            b = tk.Button(stack, text=text, state="disabled")
            b.pack(side="left", padx=2)
            Tooltip(b, "needs robot/ deploy (gated)")

    # -- events
    def handle(self, kind, payload):
        now = time.monotonic()
        if kind == "status":
            self.status, self.last_rx = payload, now
            self.new_zones.update(payload, now)
            if payload.get("decision"):
                if self.history.add(payload["decision"]):
                    self.refresh_history()
            if payload.get("last_warning"):
                self.add_warning(payload["last_warning"])
            self.sync_sliders(payload.get("weights"))
        elif kind == "decision":
            if self.history.add(payload):
                self.refresh_history()
            if self.status is not None:
                self.status["decision"] = payload
        elif kind == "warning":
            self.add_warning(payload)
        elif kind == "map" and Image is not None:
            info = payload["info"]
            img = Image.frombytes("L", (info["width"], info["height"]), payload["pixels"])
            self.map = {"info": info, "image": img.transpose(Image.FLIP_TOP_BOTTOM)}
        elif kind == "scan":
            self.scan = payload
        elif kind == "camera":
            self.cam_data = payload
        elif kind == "log":
            self.logs.append(payload)
        self.dirty = True

    def add_warning(self, w):
        if self.warnings.add(w, time.monotonic()):
            self.warn_tree.delete(*self.warn_tree.get_children())
            for item in list(self.warnings.items)[:12]:
                self.warn_tree.insert("", "end", values=vm.warning_row(item))

    def refresh_history(self):
        self.hist.delete(0, "end")
        for h in self.history.newest_first():
            self.hist.insert("end", f"{time.strftime('%H:%M:%S', time.localtime(h['t']))}  {h['explanation']}")

    # -- commands
    def cmd(self, name, **kw):
        if self.bridge:
            self.bridge.command(name, **kw)

    def save_map(self):
        name = simpledialog.askstring("Save map", "Map name:", parent=self.root)
        if name and name.strip():
            self.cmd("save_map", name=name.strip())

    def set_start(self):
        if messagebox.askyesno("Set start here", "Forget all zones and make the robot's current cell zone 1?",
                               parent=self.root):
            self.cmd("set_start")

    def arm(self):
        if messagebox.askyesno("Arm", "Arm the robot? It may move.", parent=self.root):
            self.cmd("arm")

    def do_estop(self):
        self.keys.clear()
        self.estop.trigger()
        if self.bridge:
            self.bridge.estop()
        self.dirty = True

    def release(self):
        if not vm.estop_active(self.estop, self.status):
            return
        if messagebox.askyesno("Release E-STOP", "Area clear? Release the E-STOP (robot stays disarmed)?",
                               parent=self.root):
            self.estop.release(True)
            self.cmd("release")

    def sync_sliders(self, weights):
        """Follow the node's weights unless the user is dragging (a send is pending)."""
        if weights and self.debounce._due is None:
            n = vm.normalise_weights(weights)
            for t, s in self.sliders.items():
                s.set(round(n[t] * 100))
        self.weights_label.config(text="node weights: " + vm.weights_text(weights or {}))

    def on_slider(self, force=False):
        vals = {t: s.get() for t, s in self.sliders.items()}
        if sum(vals.values()) > 0 and force:
            self.debounce.change(vals, time.monotonic())

    # -- timers
    def tick_drive(self):
        now = time.monotonic()
        active = vm.estop_active(self.estop, self.status)
        enabled = vm.drive_enabled(self.status, active)
        if not enabled:
            self.keys.clear()
        cmd = vm.drive_command(self.keys.held(now), enabled)
        for lin, ang in self.sender.step(cmd):
            if self.bridge:
                self.bridge.twist(lin, ang)
        if active and self.bridge:
            self.bridge.twist(0.0, 0.0)             # keep streaming zero while latched
        for b in self.pad_buttons:
            b.config(state="normal" if enabled else "disabled")
        if self.set_start_btn is not None:
            self.set_start_btn.config(state="normal" if vm.set_start_enabled(self.status, active) else "disabled")
        self.drive_hint.config(text="" if enabled else "drive disabled (needs armed + idle)")
        self.root.after(50, self.tick_drive)

    def tick_ui(self):
        now = time.monotonic()
        if self.bridge:
            try:
                for _ in range(200):
                    self.handle(*self.bridge.events.get_nowait())
            except queue.Empty:
                pass
        w = self.debounce.poll(now)
        if w:
            self.cmd("set_weights", weights=w)
        self.refresh(now)
        self.root.after(150, self.tick_ui)

    def refresh(self, now=None):
        now = time.monotonic() if now is None else now
        st = self.status or {}
        text, level = vm.staleness(self.last_rx, now)
        self.status_line.config(text=text + (f"   |   {self.logs[-1]}" if self.logs else ""), fg=STATUS_COLOUR[level])
        for (name, value, state), key in zip(vm.flags_text(st), self.flag_labels):
            colour = FG if state is None else (GREEN if state else "#9aa4af")
            if name == "armed" and state is None:
                colour = AMBER
            if name == "mode" and value == "estop":
                colour = RED
            self.flag_labels[key].config(text=value, fg=colour)
        active = vm.estop_active(self.estop, self.status)
        self.estop_btn.config(text="E-STOP ACTIVE - latched" if active else "E-STOP  (Space)",
                              bg="#7a0f10" if active else RED)
        on = self.warnings.banner_on(now)
        if self.warnings.items:
            w = self.warnings.items[0]
            self.banner.config(text="MOTION WARNING  " + " ".join(vm.warning_row(w)[:2]) + f"  {w['message']}",
                               bg=RED if on else PANEL, fg="white" if on else AMBER)
        self.draw_motion(st.get("motion"))
        self.draw_decision(st)
        self.draw_map(st, now)
        self.draw_camera()

    # -- drawing
    def draw_motion(self, m):
        for name, (c, lab) in self.motion_bars.items():
            c.delete("all")
            v = vm.bar_fraction((m or {}).get(name))
            c.create_rectangle(0, 0, 200 * v, 14, fill=vm.age_colour(v), width=0)
            lab.config(text="-" if not m else f"{v:.2f}")
        self.ego_label.config(text="ego: " + ("-" if not m else
                              f"moving={'yes' if m['ego_moving'] else 'no'}  turning={'yes' if m['ego_turning'] else 'no'}"))

    def draw_decision(self, st):
        c = self.dec_canvas
        c.delete("all")
        dec = st.get("decision")
        rows = vm.score_rows(dec)
        heads = ("zone", "total", "age", "risk", "dist", "alert")
        xs = (6, 62, 108, 166, 226, 286)
        for h, x in zip(heads, xs):
            c.create_text(x, 8, text=h, anchor="w", fill="#9aa4af", font=("TkDefaultFont", 8, "bold"))
        c.create_text(345, 8, text="weighted contribution", anchor="w", fill="#9aa4af", font=("TkDefaultFont", 8))
        numbers = vm.zone_numbers(st)
        mx = rows[0]["total"] if rows else 1.0
        for i, r in enumerate(rows[:9]):
            y = 24 + i * 16
            if r["chosen"]:
                c.create_rectangle(0, y - 8, 520, y + 8, fill="#3b4a2e", width=0)
            cells = [vm.zone_display(r["zone"], numbers) + (" *" if r["chosen"] else ""), f"{r['total']:.2f}"]
            cells += [f"{r['raw'][t]:.2f} ({r['contrib'][t]:+.2f})" if t != "distance" else
                      f"{r['distance_m']:.1f}m ({r['contrib'][t]:+.2f})" for t in vm.TERMS]
            for txt, x in zip(cells, xs):
                c.create_text(x, y, text=txt, anchor="w", fill=FG, font=("TkFixedFont", 8))
            for term, x0, x1 in vm.segments(r, mx, 170):
                if x1 > x0:
                    c.create_rectangle(345 + x0, y - 5, 345 + x1, y + 5, fill=vm.TERM_COLOURS[term], width=0)
        lx = 6
        for t in vm.TERMS:
            c.create_rectangle(lx, 160, lx + 8, 168, fill=vm.TERM_COLOURS[t], width=0)
            c.create_text(lx + 11, 164, text=t, anchor="w", fill=FG, font=("TkDefaultFont", 8))
            lx += 70
        self.explain.config(text=vm.explanation_text(dec))
        self.skip_label.config(text="\n".join(vm.skipped_lines(st)))

    def draw_map(self, st, now=None):
        now = time.monotonic() if now is None else now
        c = self.map_canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 200), max(c.winfo_height(), 200)
        info = self.map["info"] if self.map else None
        vp = vm.Viewport(vm.fit_bounds(vm.world_bounds(st.get("zones"), info), st.get("zones")), w, h)
        if self.map:
            ox, oy = info["origin"]
            top_left = vp.to_canvas(ox, oy + info["height"] * info["resolution"])
            size = max(1, int(info["width"] * info["resolution"] * vp.scale)), \
                   max(1, int(info["height"] * info["resolution"] * vp.scale))
            self.photos["map"] = ImageTk.PhotoImage(self.map["image"].resize(size))
            c.create_image(*top_left, anchor="nw", image=self.photos["map"])
        else:       # plain grid
            for gx in range(-20, 21):
                a, b = vp.to_canvas(gx, -20), vp.to_canvas(gx, 20)
                c.create_line(*a, *b, fill="#1d232a")
                a, b = vp.to_canvas(-20, gx), vp.to_canvas(20, gx)
                c.create_line(*a, *b, fill="#1d232a")
        for z, fill, alert, label, goal in vm.zone_styles(st):
            new = self.new_zones.is_new(z["id"], now)
            c.create_rectangle(*vm.zone_rect(vp, z), fill=fill, stipple="gray50",
                               outline="#ff3860" if alert else ("#ffffff" if goal else ("#ffd60a" if new else "#3c444d")),
                               width=4 if new else (3 if (alert or goal) else 1))
            cx, cy = vp.to_canvas(z["cx"], z["cy"])
            big = max(12, min(48, int(vp.length(z["h"]) * 0.4)))
            c.create_text(cx, cy - big * 0.3, text=vm.zone_title(z), fill="white", font=("TkDefaultFont", big, "bold"))
            c.create_text(cx, cy + big * 0.7, text=label, fill="white",
                          font=("TkDefaultFont", 8, "bold" if goal else "normal"))
        robot = st.get("robot")
        if self.scan and robot:
            for px, py in vm.scan_points(robot, self.scan["angle_min"], self.scan["inc"], self.scan["ranges"],
                                         self.scan["range_max"], LASER_YAW):
                x, y = vp.to_canvas(px, py)
                c.create_rectangle(x, y, x + 1.5, y + 1.5, fill="#4cc9f0", width=0)
        if robot:
            x, y = vp.to_canvas(robot["x"], robot["y"])
            hx, hy = vp.to_canvas(robot["x"] + 0.3 * math.cos(robot["yaw"]), robot["y"] + 0.3 * math.sin(robot["yaw"]))
            c.create_oval(x - 6, y - 6, x + 6, y + 6, fill="#f5f5f5", outline="#000")
            c.create_line(x, y, hx, hy, fill="#d63031", width=3)
        else:
            c.create_text(10, 10, text="no robot pose", anchor="nw", fill=AMBER)
        if not self.map:
            c.create_text(w - 8, 10, text="no /map - zones on plain grid", anchor="ne", fill="#778")

    def draw_camera(self):
        if not self.cam_data:
            return
        data, self.cam_data = self.cam_data, None
        photo = decode_frame(data, 300, 170)
        if photo is None:
            self.cam_label.config(text="camera: no decoder (needs Pillow or cv2)", image="")
        else:
            self.photos["cam"] = photo
            self.cam_label.config(image=photo, text="", width=300, height=170)

    def close(self):
        if self.bridge:
            self.bridge.stop()
        self.root.destroy()


def decode_frame(data, w, h):
    """JPEG bytes -> Tk PhotoImage using Pillow, else cv2 (via PPM); None if neither works."""
    try:
        if Image is not None:
            import io
            img = Image.open(io.BytesIO(data))
            img.thumbnail((w, h))
            return ImageTk.PhotoImage(img)
        import cv2
        import numpy as np
        frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        frame = cv2.resize(frame, (w, h))
        ppm = b"P6 %d %d 255\n" % (w, h) + cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes()
        return tk.PhotoImage(data=ppm)
    except Exception:
        return None


class Tooltip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _e):
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f"+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty() + 28}")
        tk.Label(self.tip, text=self.text, bg="#ffffe0", fg="black", padx=4).pack()

    def hide(self, _e):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# --------------------------------------------------------------------------- self-test / main
def selftest():
    if not os.environ.get("DISPLAY"):
        print("no display, skipped")
        return 0
    from patrol import protocol as P
    root = tk.Tk()
    app = App(root, None, os.environ.get("ROS_DOMAIN_ID"))
    w = {"age": 0.5, "risk": 0.2, "distance": 0.2, "alert": 0.1}
    zones = [{"id": f"z{r}{c}", "n": 3 * r + c + 1, "row": r, "col": c, "cx": c - 1.0, "cy": 1.0 - r, "w": 1.0, "h": 1.0, "risk": 0.5}
             for r in range(3) for c in range(3)]
    heat = {z["id"]: {"age_s": 13 * i, "age_norm": i / 8, "alert": 1.0 if i == 4 else 0.0} for i, z in enumerate(zones)}
    scores = [{"zone": z["id"], "total": 0.9 - 0.1 * i, "distance_m": 1.0 + i,
               "raw": {t: 0.5 for t in vm.TERMS}, "contrib": {"age": 0.4 - 0.05 * i, "risk": 0.1, "distance": 0.1,
                                                              "alert": 0.1 * (i == 0)}}
              for i, z in enumerate(zones[:5])]
    dec = P.build_decision(time.time(), "z00", "Chose z00: oldest", w, scores)
    warn = P.build_warning(time.time(), 1.0, 0.5, 0.5, "z01", 0.8, 0.9, 0.3, "Movement near z01")
    st = P.build_status(time.time(), "idle", True, True, False, {"x": 0.2, "y": 0.1, "yaw": 0.5}, "z00", "active", w,
                        zones, heat, {"z22": "recent", "z21": "cooldown"},
                        {"lidar": 0.9, "camera": 0.3, "fused": 0.8, "ego_moving": False, "ego_turning": True},
                        dec, warn, False, None)
    P.validate_status(st)
    app.handle("status", st)
    app.handle("decision", dec)
    app.handle("warning", warn)
    app.handle("scan", {"angle_min": 0.0, "inc": 0.1, "ranges": [1.0] * 60, "range_max": 5.0})
    root.update()
    app.refresh()
    root.update()
    grown = dict(st, zones=zones + [dict(zones[0], id="R-1C0", n=10, row=-1, cy=2.0)])   # a zone appears
    app.handle("status", grown)
    app.refresh()
    root.update()
    app.handle("status", st)                                                           # ... and goes (reset)
    app.refresh()
    root.update()
    root.destroy()
    print("selftest ok")
    return 0


def main():
    if SELFTEST:
        sys.exit(selftest())
    domain = os.environ.get("ROS_DOMAIN_ID")
    root = tk.Tk()
    bridge = Bridge(load_topics())
    App(root, bridge, domain)
    root.mainloop()


if __name__ == "__main__":
    main()
