"""PC control panel for the tunnel rig (ESP32 + Cytron MDD3A over Wi-Fi / UDP).

Run:  .venv\\Scripts\\python control_panel.py
Network: laptop (Ethernet) -> router <- ESP32 (2.4 GHz Wi-Fi, fixed IP). See WIFI-PLAN.md.

Hold a key (WASD / arrows) or a pad button to drive; release to stop. A packet is sent every
`repeat_ms` (the held command, or STOP when idle). Every packet is answered by the ESP32 with its
Wi-Fi signal strength, which feeds the comm-health bar (RSSI, round-trip time, packet loss).
No reply for `lost_after_ms` -> LINK LOST: drive is disabled, and the rig stops by itself.
"""
import os
import socket
import time
import tkinter as tk
import webbrowser
from tkinter import ttk

import yaml

from panel_logic import (STOP, HealthTracker, build_packet, clamp_speed, command_for,
                         direction_for_key, parse_reply)

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "panel_config.yaml")
DEFAULTS = {
    "host": "192.168.1.60", "udp_port": 4210,
    "camera_url": "https://192.168.1.250/#/index/Preview/",
    "repeat_ms": 150, "lost_after_ms": 500, "default_speed": 6,
}
KEY_RELEASE_DEBOUNCE_MS = 40     # Windows key auto-repeat sends release+press pairs
POLL_MS = 20                     # how often the socket is read (keeps RTT readings accurate)
SPEED_RESYNC_S = 0.3             # min gap between speed re-sends
BAR_W, BAR_H = 320, 20
LEVEL_COLOUR = {"GOOD": "#2e9e5b", "FAIR": "#d9a21b", "POOR": "#d9534f", "LOST": "#777777"}

# Pad layout: (label, row, col, directions held while pressed)
PAD = [
    ("↖", 0, 0, ("up", "left")), ("▲", 0, 1, ("up",)), ("↗", 0, 2, ("up", "right")),
    ("◀", 1, 0, ("left",)), None, ("▶", 1, 2, ("right",)),
    ("↙", 2, 0, ("down", "left")), ("▼", 2, 1, ("down",)), ("↘", 2, 2, ("down", "right")),
]


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as fh:
            cfg.update(yaml.safe_load(fh) or {})
    except FileNotFoundError:
        pass
    except yaml.YAMLError as exc:
        print(f"[config] ignoring bad {CONFIG_PATH}: {exc}")
    cfg["udp_port"] = int(cfg["udp_port"])
    cfg["repeat_ms"] = max(50, min(400, int(cfg["repeat_ms"])))          # must stay < 500 ms failsafe
    cfg["lost_after_ms"] = max(200, min(2000, int(cfg["lost_after_ms"])))
    cfg["default_speed"] = clamp_speed(cfg["default_speed"])
    return cfg


class Panel:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.sock = None
        self.target = None
        self.seq = 0
        self.tracker = HealthTracker(lost_after_s=self.cfg["lost_after_ms"] / 1000.0)
        self.held = {}              # source token -> direction (e.g. "key:w" -> "up")
        self.release_jobs = {}      # key -> after-id (debounce)
        self.pad_buttons = []
        self.drive_enabled = None   # unknown until first health refresh
        self.link_ok = False
        self.last_speed_sync = 0.0

        root.title("Tunnel Rig Control (Wi-Fi)")
        root.configure(padx=12, pady=12)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.minsize(400, 560)
        self._build_ui()
        self._set_drive_enabled(False)
        self._set_stop_enabled(False)
        self._draw_health(None)

        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        root.bind("<FocusOut>", lambda e: self.release_all() if e.widget is root else None)
        root.after(self.cfg["repeat_ms"], self.tick)
        root.after(POLL_MS, self.poll)

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x")
        ttk.Label(top, text="Rig IP").pack(side="left")
        self.host_var = tk.StringVar(value=self.cfg["host"])
        ttk.Entry(top, textvariable=self.host_var, width=16).pack(side="left", padx=6)
        self.connect_btn = ttk.Button(top, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side="left")
        ttk.Button(top, text="Open camera", command=self.open_camera).pack(side="right")

        self.status_var = tk.StringVar(value="Not connected")
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var, fg="#a33", anchor="w")
        self.status_lbl.pack(fill="x", pady=(8, 0))

        health = ttk.LabelFrame(self.root, text="Comm health", padding=8)
        health.pack(fill="x", pady=(8, 0))
        self.health_title = tk.StringVar(value="--")
        tk.Label(health, textvariable=self.health_title, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        self.bar = tk.Canvas(health, width=BAR_W, height=BAR_H, highlightthickness=1,
                             highlightbackground="#999", bg="#eeeeee")
        self.bar.pack(anchor="w", pady=4)
        self.health_detail = tk.StringVar(value="RSSI --   RTT --   loss --")
        ttk.Label(health, textvariable=self.health_detail, foreground="#555").pack(anchor="w")

        pad = ttk.Frame(self.root)
        pad.pack(pady=16)
        for item in PAD:
            if item is None:
                continue
            label, r, c, dirs = item
            btn = tk.Button(pad, text=label, width=4, height=2, font=("Segoe UI", 18))
            btn.grid(row=r, column=c, padx=3, pady=3)
            token = f"btn:{r}{c}"
            btn.bind("<ButtonPress-1>", lambda e, t=token, d=dirs: self.press(t, d))
            btn.bind("<ButtonRelease-1>", lambda e, t=token, d=dirs: self.release(t, d))
            self.pad_buttons.append(btn)
        self.stop_btn = tk.Button(pad, text="STOP", width=6, height=2, bg="#c62828", fg="white",
                                  font=("Segoe UI", 12, "bold"), command=self.emergency_stop)
        self.stop_btn.grid(row=1, column=1, padx=3, pady=3)

        speed = ttk.Frame(self.root)
        speed.pack(fill="x")
        ttk.Label(speed, text="Speed").pack(side="left")
        self.speed_var = tk.IntVar(value=self.cfg["default_speed"])
        self.speed_scale = tk.Scale(speed, from_=0, to=9, orient="horizontal", variable=self.speed_var,
                                    command=self.on_speed, showvalue=True, length=260)
        self.speed_scale.pack(side="left", padx=8, fill="x", expand=True)

        ttk.Label(self.root, foreground="#666",
                  text="Hold W/A/S/D or arrows (or the pad) to drive. Space = STOP. "
                       "Release = stop.").pack(pady=(8, 0))
        self.cmd_var = tk.StringVar(value="cmd: -")
        ttk.Label(self.root, textvariable=self.cmd_var, foreground="#666").pack(anchor="w", pady=(6, 0))

    def _set_drive_enabled(self, enabled):
        if enabled == self.drive_enabled:
            return
        self.drive_enabled = enabled
        state = "normal" if enabled else "disabled"
        for b in self.pad_buttons + [self.speed_scale]:
            b.config(state=state)
        if not enabled:
            self.release_all()

    def _set_stop_enabled(self, enabled):
        self.stop_btn.config(state="normal" if enabled else "disabled")

    def set_status(self, text, ok):
        self.status_var.set(text)
        self.status_lbl.config(fg="#1b7a3a" if ok else "#a33")

    def _draw_health(self, h):
        self.bar.delete("all")
        if h is None:
            self.health_title.set("Not connected")
            self.health_detail.set("RSSI --   RTT --   loss --")
            return
        colour = LEVEL_COLOUR[h.level]
        self.bar.create_rectangle(0, 0, int(BAR_W * h.score / 100), BAR_H, fill=colour, width=0)
        if h.level == "LOST":
            self.health_title.set("LINKING..." if not h.ever_replied else "LINK LOST - rig will stop")
        else:
            self.health_title.set(f"{h.level}  ({h.score}/100)")
        rssi = f"{h.rssi} dBm" if h.rssi is not None else "--"
        rtt = f"{h.rtt_ms:.0f} ms" if h.rtt_ms is not None else "--"
        self.health_detail.set(f"RSSI {rssi}   RTT {rtt}   loss {h.loss_pct:.0f} %")

    # ---------------- connection ----------------
    def toggle_connection(self):
        if self.sock:
            self.disconnect("Not connected")
        else:
            self.connect()

    def connect(self):
        host = self.host_var.get().strip()
        try:
            ip = socket.gethostbyname(host)
        except (socket.gaierror, UnicodeError) as exc:
            self.set_status(f"Bad address '{host}': {exc}", False)
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("", 0))
            sock.setblocking(False)
            if hasattr(socket, "SIO_UDP_CONNRESET"):      # Windows: don't raise on ICMP "port unreachable"
                sock.ioctl(socket.SIO_UDP_CONNRESET, False)
        except OSError as exc:
            self.set_status(f"Socket error: {exc}", False)
            return
        self.sock = sock
        self.target = (ip, self.cfg["udp_port"])
        self.tracker.reset()
        self.connect_btn.config(text="Disconnect")
        self._set_stop_enabled(True)
        self.set_status(f"Linking to {ip}:{self.cfg['udp_port']} ...", False)
        self.root.focus_set()

    def disconnect(self, message):
        if self.sock:
            for _ in range(2):                            # UDP: send stop twice, fire-and-forget
                self._send_raw(STOP)
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None
        self.target = None
        self.held.clear()
        self.link_ok = False
        self.connect_btn.config(text="Connect")
        self._set_drive_enabled(False)
        self._set_stop_enabled(False)
        self._draw_health(None)
        self.set_status(message, False)

    def _send_raw(self, cmd):
        if not self.sock:
            return False
        self.seq += 1
        try:
            self.sock.sendto(build_packet(self.seq, cmd), self.target)
        except OSError as exc:
            self.set_status(f"Send failed: {exc}", False)
            return False
        self.tracker.sent(self.seq, time.monotonic())
        return True

    def send(self, cmd):
        if self._send_raw(cmd):
            self.cmd_var.set(f"cmd: {cmd}")

    def open_camera(self):
        webbrowser.open(self.cfg["camera_url"])

    # ---------------- input ----------------
    def press(self, token, dirs):
        if not self.link_ok:
            return
        for d in dirs:
            self.held[f"{token}:{d}"] = d

    def release(self, token, dirs):
        for d in dirs:
            self.held.pop(f"{token}:{d}", None)

    def release_all(self):
        for job in self.release_jobs.values():
            self.root.after_cancel(job)
        self.release_jobs.clear()
        self.held.clear()

    def on_key_press(self, event):
        key = event.keysym.lower()
        if key == "space":
            self.emergency_stop()
            return
        direction = direction_for_key(key)
        if not direction or not self.link_ok:
            return
        job = self.release_jobs.pop(key, None)
        if job:
            self.root.after_cancel(job)          # auto-repeat: cancel the pending release
        self.held[f"key:{key}"] = direction

    def on_key_release(self, event):
        key = event.keysym.lower()
        if not direction_for_key(key):
            return
        if key in self.release_jobs:
            self.root.after_cancel(self.release_jobs[key])
        self.release_jobs[key] = self.root.after(KEY_RELEASE_DEBOUNCE_MS, self._finish_key_release, key)

    def _finish_key_release(self, key):
        self.release_jobs.pop(key, None)
        self.held.pop(f"key:{key}", None)

    def emergency_stop(self):
        self.release_all()
        if self.sock:
            self.send(STOP)
            self.send(STOP)                      # twice: UDP can drop one

    def on_speed(self, value):
        if self.sock and self.link_ok:
            self.send(str(clamp_speed(value)))
            self.last_speed_sync = time.monotonic()

    # ---------------- periodic ----------------
    def tick(self):
        if self.sock:
            dirs = set(self.held.values()) if self.link_ok else set()
            self.send(command_for(dirs))         # held command, or STOP when idle (also the ping)
            self.refresh_health()
        self.root.after(self.cfg["repeat_ms"], self.tick)

    def poll(self):
        if self.sock:
            while True:
                try:
                    data, addr = self.sock.recvfrom(256)
                except BlockingIOError:
                    break
                except ConnectionResetError:     # ICMP unreachable on Windows: ignore, keep reading
                    continue
                except OSError as exc:
                    self.set_status(f"Receive error: {exc}", False)
                    break
                if addr[0] != self.target[0]:
                    continue
                reply = parse_reply(data)
                if reply:
                    self.tracker.on_reply(reply, time.monotonic())
                    self._sync_speed(reply)
        self.root.after(POLL_MS, self.poll)

    def _sync_speed(self, reply):
        """If the rig's speed differs from the slider (lost packet, reboot), send it again."""
        now = time.monotonic()
        if reply.speed != self.speed_var.get() and now - self.last_speed_sync > SPEED_RESYNC_S:
            self.last_speed_sync = now
            self.send(str(self.speed_var.get()))

    def refresh_health(self):
        h = self.tracker.snapshot(time.monotonic())
        self._draw_health(h)
        self.link_ok = not h.lost
        self._set_drive_enabled(self.link_ok)
        if self.link_ok:
            self.set_status(f"Connected: {self.target[0]}", True)
        elif h.ever_replied:
            self.set_status("LINK LOST - drive disabled (rig stops by itself)", False)

    def on_close(self):
        self.disconnect("Not connected")
        self.root.destroy()


def main():
    root = tk.Tk()
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
