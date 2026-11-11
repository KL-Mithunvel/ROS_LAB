"""PC control panel for the tunnel rig (ESP32 + Cytron MDD3A, Classic Bluetooth).

Run:  .venv\\Scripts\\python control_panel.py
Pair "TunnelRig" in Windows first; use its *outgoing* COM port (default in panel_config.yaml).

Hold a key (WASD / arrows) or a pad button to drive; release to stop. The held command is resent
every `repeat_ms` so the firmware's 500 ms failsafe never trips while you are driving.
"""
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk

import serial
import serial.tools.list_ports
import yaml

from panel_logic import STOP, clamp_speed, command_for, direction_for_key

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "panel_config.yaml")
DEFAULTS = {"port": "COM6", "repeat_ms": 150, "default_speed": 6}
BAUD = 115200
KEY_RELEASE_DEBOUNCE_MS = 40   # Windows key auto-repeat sends release+press pairs

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
    cfg["repeat_ms"] = max(50, min(400, int(cfg["repeat_ms"])))   # must stay < 500 ms failsafe
    cfg["default_speed"] = clamp_speed(cfg["default_speed"])
    return cfg


def save_port(port):
    """Remember the last working port in panel_config.yaml."""
    cfg = load_config()
    cfg["port"] = port
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            yaml.safe_dump(cfg, fh, sort_keys=False)
    except OSError as exc:
        print(f"[config] could not save port: {exc}")


class Panel:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.ser = None
        self.connecting = False
        self.held = {}              # source token -> direction (e.g. "key:w" -> "up")
        self.release_jobs = {}      # key token -> after-id (debounce)
        self.last_sent = STOP
        self.results = queue.Queue()   # connect-thread results
        self.pad_buttons = []

        root.title("Tunnel Rig Control")
        root.configure(padx=12, pady=12)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.minsize(380, 460)
        self._build_ui()
        self.refresh_ports()
        self._set_drive_enabled(False)

        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        root.bind("<FocusOut>", lambda e: self.release_all() if e.widget is root else None)
        root.after(self.cfg["repeat_ms"], self.tick)

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x")
        ttk.Label(top, text="Port").pack(side="left")
        self.port_var = tk.StringVar(value=self.cfg["port"])
        self.port_box = ttk.Combobox(top, textvariable=self.port_var, width=34, state="readonly")
        self.port_box.pack(side="left", padx=6)
        ttk.Button(top, text="↻", width=3, command=self.refresh_ports).pack(side="left")

        row = ttk.Frame(self.root)
        row.pack(fill="x", pady=(8, 0))
        self.connect_btn = ttk.Button(row, text="Connect", command=self.toggle_connection)
        self.connect_btn.pack(side="left")
        self.status_var = tk.StringVar(value="Disconnected")
        self.status_lbl = tk.Label(row, textvariable=self.status_var, fg="#a33", anchor="w")
        self.status_lbl.pack(side="left", padx=10)

        pad = ttk.Frame(self.root)
        pad.pack(pady=18)
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
                       "Release = stop.").pack(pady=(10, 0))
        self.cmd_var = tk.StringVar(value="cmd: -")
        ttk.Label(self.root, textvariable=self.cmd_var, foreground="#666").pack(anchor="w", pady=(6, 0))
        self.reply_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.reply_var, foreground="#666").pack(anchor="w")

    def _set_drive_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for b in self.pad_buttons + [self.stop_btn, self.speed_scale]:
            b.config(state=state)

    def set_status(self, text, ok):
        self.status_var.set(text)
        self.status_lbl.config(fg="#1b7a3a" if ok else "#a33")

    # ---------------- ports ----------------
    def refresh_ports(self):
        ports = sorted(serial.tools.list_ports.comports(), key=lambda p: p.device)
        self._port_map = {f"{p.device} - {p.description}": p.device for p in ports}
        labels = list(self._port_map)
        self.port_box["values"] = labels
        wanted = self.port_var.get().split(" - ")[0]
        for label, dev in self._port_map.items():
            if dev == wanted:
                self.port_var.set(label)
                break
        else:
            if labels:
                self.port_var.set(labels[0])

    def selected_port(self):
        return self.port_var.get().split(" - ")[0].strip()

    # ---------------- connection ----------------
    def toggle_connection(self):
        if self.ser:
            self.disconnect("Disconnected")
        elif not self.connecting:
            self.connect()

    def connect(self):
        port = self.selected_port()
        if not port:
            self.set_status("No port selected", False)
            return
        self.connecting = True
        self.connect_btn.config(state="disabled")
        self.set_status(f"Connecting to {port}... (can take a few seconds)", False)
        threading.Thread(target=self._open_port, args=(port,), daemon=True).start()
        self.root.after(100, self._poll_connect)

    def _open_port(self, port):
        try:
            ser = serial.Serial(port, BAUD, timeout=0, write_timeout=0.3)
            self.results.put((port, ser, None))
        except (serial.SerialException, OSError, ValueError) as exc:
            self.results.put((port, None, exc))

    def _poll_connect(self):
        try:
            port, ser, err = self.results.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_connect)
            return
        self.connecting = False
        self.connect_btn.config(state="normal")
        if err is not None:
            self.set_status(f"Failed: {err}", False)
            return
        self.ser = ser
        self.last_sent = STOP
        self.connect_btn.config(text="Disconnect")
        self.set_status(f"Connected: {port}", True)
        self._set_drive_enabled(True)
        save_port(port)
        self.send(STOP)
        self.send(str(self.speed_var.get()))
        self.root.focus_set()

    def disconnect(self, message):
        if self.ser:
            try:
                self.ser.write(STOP.encode())
            except (serial.SerialException, OSError):
                pass
            try:
                self.ser.close()
            except (serial.SerialException, OSError):
                pass
        self.ser = None
        self.held.clear()
        self.connect_btn.config(text="Connect")
        self._set_drive_enabled(False)
        self.set_status(message, False)

    def send(self, char):
        """Write one command char. On a serial error, drop the link and report it."""
        if not self.ser:
            return False
        try:
            self.ser.write(char.encode())
            self.cmd_var.set(f"cmd: {char}")
            return True
        except (serial.SerialException, OSError) as exc:
            self.disconnect(f"Link lost: {exc}")
            return False

    # ---------------- input ----------------
    def press(self, token, dirs):
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
        if not direction:
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
        if self.ser:
            self.send(STOP)
            self.last_sent = STOP

    def on_speed(self, value):
        level = clamp_speed(value)
        if self.ser:
            self.send(str(level))

    # ---------------- periodic ----------------
    def tick(self):
        if self.ser:
            cmd = command_for(set(self.held.values()))
            if cmd != STOP:
                self.send(cmd)                   # keepalive: resend while held
            elif self.last_sent != STOP:
                self.send(STOP)
            self.last_sent = cmd
            self._read_replies()
        self.root.after(self.cfg["repeat_ms"], self.tick)

    def _read_replies(self):
        if not self.ser:
            return
        try:
            waiting = self.ser.in_waiting
            if waiting:
                text = self.ser.read(waiting).decode(errors="replace").strip()
                if text:
                    self.reply_var.set(f"rig: {text.splitlines()[-1]}")
        except (serial.SerialException, OSError) as exc:
            self.disconnect(f"Link lost: {exc}")

    def on_close(self):
        self.disconnect("Disconnected")
        self.root.destroy()


def main():
    root = tk.Tk()
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
