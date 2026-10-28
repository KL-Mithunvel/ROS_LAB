"""Rosbag recording of a patrol run (`ros2 bag record` in a subprocess)."""
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class RecordingConfig:
    auto_start: bool = True            # record whenever a patrol starts
    folder: str = "runs"               # relative to beetle_patrol/
    storage: str = "sqlite3"           # "mcap" is smaller/faster but needs ros-<distro>-rosbag2-storage-mcap
    compression: str = "zstd"          # "" to disable
    topics: list = field(default_factory=lambda: [
        "/scan", "/odometry/filtered", "/wheel/odom", "/imu/data", "/tf", "/tf_static", "/map",
        "/patrol/camera/compressed",    # throttled copy; the robot's own camera runs at ~56 Hz
        "/lyra/armed", "/cmd_vel_nav", "/cmd_vel", "/explore/status",
        "/patrol/status", "/patrol/warning", "/patrol/decision", "/patrol/command"])


def bag_command(config, out_dir):
    """The `ros2 bag record` argument list for this config."""
    cmd = ["ros2", "bag", "record", "-o", str(out_dir), "-s", config.storage]
    if config.compression:
        cmd += ["--compression-mode", "file", "--compression-format", config.compression]
    return cmd + list(config.topics)


LOG_TAIL_CHARS = 400     # how much of ros2bag.log to quote in a failure message


class BagRecorder:
    """Runs `ros2 bag record`; its stderr goes to `<bag dir>.ros2bag.log` (next to the bag folder,
    because ros2 bag refuses to write into an existing folder), so a failed recording is visible."""

    def __init__(self, config, base_dir, command_fn=bag_command):
        self.config = config
        self._command_fn = command_fn
        self._stopping = False
        self._failure_reported = False
        self.log_path = None
        self.base_dir = Path(base_dir) / config.folder
        self._proc = None
        self.out_dir = None

    @property
    def recording(self):
        return self._proc is not None and self._proc.poll() is None

    def start(self, label="patrol"):
        if self.recording:
            return self.out_dir
        if shutil.which("ros2") is None:
            raise RuntimeError("ros2 not found on PATH - source the ROS setup file first")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir = self.base_dir / f"{label}_{datetime.now():%Y%m%d_%H%M%S}"
        self.log_path = self.out_dir.with_name(self.out_dir.name + ".ros2bag.log")
        self._stopping = self._failure_reported = False
        with open(self.log_path, "w") as log:   # the child keeps its own copy of the descriptor
            self._proc = subprocess.Popen(self._command_fn(self.config, self.out_dir),
                                          stdout=log, stderr=subprocess.STDOUT)
        return self.out_dir

    def failure(self):
        """Once, a message if the recorder died by itself (not via stop()); otherwise None.

        Call this periodically: it is how a bad topic / storage plugin / full disk becomes visible.
        """
        if self._proc is None or self._stopping or self._failure_reported:
            return None
        code = self._proc.poll()
        if code is None:
            return None
        self._failure_reported = True
        try:
            tail = self.log_path.read_text()[-LOG_TAIL_CHARS:].strip()
        except OSError:
            tail = "(log unreadable)"
        return f"ros2 bag record exited with code {code}; see {self.log_path}: {tail}"

    def stop(self, timeout_s=15):
        """SIGINT lets ros2 bag finish and write its metadata; kill only if it hangs."""
        if self._proc is None:
            return
        self._stopping = True
        if self._proc.poll() is None:
            self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout_s)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
