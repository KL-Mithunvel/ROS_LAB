"""MENGJIE Coin-D6 TOF lidar: serial frame parser, reader thread and raw-byte sniffer.

The Coin-D6 packet format is NOT confirmed yet (no public datasheet found). The parser is
therefore driven by a `Profile` describing the frame layout. The built-in `ld06` profile is
the LDROBOT LD06 layout, a *guess* that similar 230400-baud units follow; replace it with a
`--profile-file` YAML once the real format is known (see `profile_example.yaml`).
"""
from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import serial
import yaml
from serial.tools import list_ports

DEFAULT_BAUD = 230400
BAUD_CANDIDATES = (230400, 115200, 460800, 921600, 128000, 153600)


# --------------------------------------------------------------------------- checksums
def crc8(data: bytes, poly: int = 0x4D) -> int:
    """MSB-first CRC-8, init 0, no final xor (the LD06 variant: crc8(b'\\x01') == 0x4D)."""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def sum8(data: bytes) -> int:
    return sum(data) & 0xFF


def xor8(data: bytes) -> int:
    out = 0
    for byte in data:
        out ^= byte
    return out


CHECKSUMS = {"crc8": crc8, "sum8": sum8, "xor8": xor8}


# --------------------------------------------------------------------------- profile
@dataclass(frozen=True)
class Profile:
    """Byte layout of one lidar packet. Offsets are from the first header byte."""

    name: str
    header: bytes
    frame_len: int
    n_points: int
    points_offset: int
    point_stride: int
    dist_offset: int          # within one point record
    intensity_offset: int     # within one point record; -1 = no intensity
    start_angle_offset: int
    end_angle_offset: int
    angle_scale: float = 0.01      # degrees per count
    dist_scale: float = 0.001      # metres per count
    checksum: str = "none"         # none | crc8 | sum8 | xor8 (over every byte before the last)
    verified: bool = False

    def validate(self) -> None:
        if not self.header:
            raise ValueError("profile header must not be empty")
        if self.checksum != "none" and self.checksum not in CHECKSUMS:
            raise ValueError(f"unknown checksum {self.checksum!r}; use none/{'/'.join(CHECKSUMS)}")
        last = self.points_offset + self.n_points * self.point_stride
        if last > self.frame_len:
            raise ValueError(f"{self.n_points} points end at byte {last} but frame_len is {self.frame_len}")
        for label, off in (("start_angle_offset", self.start_angle_offset),
                           ("end_angle_offset", self.end_angle_offset)):
            if not 0 <= off <= self.frame_len - 2:
                raise ValueError(f"{label} {off} outside the {self.frame_len}-byte frame")


LD06 = Profile(
    name="ld06", header=b"\x54\x2c", frame_len=47, n_points=12,
    points_offset=6, point_stride=3, dist_offset=0, intensity_offset=2,
    start_angle_offset=4, end_angle_offset=42, checksum="crc8", verified=False,
)
PROFILES = {"ld06": LD06}


def load_profile(path: str | Path) -> Profile:
    """Load a Profile from YAML. `header` is a hex string such as "54 2C"."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    raw = dict(raw)
    try:
        raw["header"] = bytes.fromhex(str(raw["header"]))
        prof = Profile(**raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path}: bad profile ({exc})") from exc
    prof.validate()
    return prof


# --------------------------------------------------------------------------- parsing
@dataclass(frozen=True)
class Point:
    angle_deg: float
    dist_m: float
    intensity: int


class FrameParser:
    """Resynchronising stream parser: feed raw bytes, get lists of Points per valid frame."""

    def __init__(self, profile: Profile):
        profile.validate()
        self.p = profile
        self._buf = bytearray()
        self.frames_ok = 0
        self.frames_bad = 0

    def feed(self, data: bytes) -> Iterator[list[Point]]:
        p = self.p
        self._buf += data
        while True:
            idx = self._buf.find(p.header)
            if idx < 0:
                # keep a possible partial header at the tail
                del self._buf[: max(0, len(self._buf) - len(p.header) + 1)]
                return
            del self._buf[:idx]
            if len(self._buf) < p.frame_len:
                return
            frame = bytes(self._buf[: p.frame_len])
            if self._checksum_ok(frame):
                del self._buf[: p.frame_len]
                self.frames_ok += 1
                yield self._decode(frame)
            else:
                del self._buf[:1]       # false header: slide one byte and re-sync
                self.frames_bad += 1

    def _checksum_ok(self, frame: bytes) -> bool:
        if self.p.checksum == "none":
            return True
        return CHECKSUMS[self.p.checksum](frame[:-1]) == frame[-1]

    def _decode(self, frame: bytes) -> list[Point]:
        p = self.p
        start = int.from_bytes(frame[p.start_angle_offset:p.start_angle_offset + 2], "little") * p.angle_scale
        end = int.from_bytes(frame[p.end_angle_offset:p.end_angle_offset + 2], "little") * p.angle_scale
        span = (end - start) % 360.0
        step = span / (p.n_points - 1) if p.n_points > 1 else 0.0
        points = []
        for i in range(p.n_points):
            base = p.points_offset + i * p.point_stride
            dist = int.from_bytes(frame[base + p.dist_offset:base + p.dist_offset + 2], "little")
            inten = frame[base + p.intensity_offset] if p.intensity_offset >= 0 else 0
            points.append(Point((start + step * i) % 360.0, dist * p.dist_scale, inten))
        return points


class ScanAssembler:
    """Collects Points and releases one list per revolution (when the angle wraps past 360)."""

    def __init__(self):
        self._pts: list[Point] = []
        self._last = None

    def add(self, points: list[Point]) -> list[Point] | None:
        done = None
        for pt in points:
            if self._last is not None and pt.angle_deg < self._last - 180.0 and self._pts:
                done, self._pts = self._pts, []
            self._pts.append(pt)
            self._last = pt.angle_deg
        return done


# --------------------------------------------------------------------------- serial
def find_port() -> str:
    """Pick the USB-serial adapter, preferring CP210x (the USB2LDS bridge)."""
    ports = list(list_ports.comports())
    for port in ports:
        if "CP210" in (port.description or "") or port.vid == 0x10C4:
            return port.device
    usb = [p for p in ports if p.vid is not None]
    if len(usb) == 1:
        return usb[0].device
    names = ", ".join(f"{p.device} ({p.description})" for p in ports) or "none found"
    raise SystemExit(f"Could not pick a port automatically; pass --port. Ports: {names}")


def open_port(port: str, baud: int, dtr: bool | None = None, rts: bool | None = None) -> serial.Serial:
    ser = serial.Serial(None, baud, timeout=0.2)
    ser.port = port
    if dtr is not None:
        ser.dtr = dtr
    if rts is not None:
        ser.rts = rts
    ser.open()
    return ser


class LidarReader(threading.Thread):
    """Background thread: serial -> FrameParser -> ScanAssembler; keeps the latest full scan."""

    def __init__(self, ser: serial.Serial, profile: Profile):
        super().__init__(daemon=True)
        self.ser = ser
        self.parser = FrameParser(profile)
        self.assembler = ScanAssembler()
        self._lock = threading.Lock()
        self._scan: list[Point] = []
        self.scans = 0
        self.error: Exception | None = None
        self._stop = threading.Event()

    def run(self) -> None:
        try:
            while not self._stop.is_set():
                data = self.ser.read(self.ser.in_waiting or 1)
                for pts in self.parser.feed(data):
                    scan = self.assembler.add(pts)
                    if scan:
                        with self._lock:
                            self._scan, self.scans = scan, self.scans + 1
        except (serial.SerialException, OSError) as exc:
            self.error = exc

    def latest(self) -> list[Point]:
        with self._lock:
            return list(self._scan)

    def stop(self) -> None:
        self._stop.set()


# --------------------------------------------------------------------------- sniffing
def analyze(data: bytes, top: int = 5) -> list[tuple[bytes, int, int]]:
    """Guess frame headers: 2-byte patterns that recur at one dominant spacing.

    Returns (pattern, count, modal_spacing) sorted by how often the modal spacing repeats.
    """
    positions: dict[bytes, list[int]] = collections.defaultdict(list)
    for i in range(len(data) - 1):
        positions[data[i:i + 2]].append(i)
    ranked = []
    for pat, pos in positions.items():
        if len(pos) < 4:
            continue
        gaps = collections.Counter(b - a for a, b in zip(pos, pos[1:]))
        gap, hits = gaps.most_common(1)[0]
        if gap >= 4 and hits >= 3:
            ranked.append((pat, hits, gap))
    ranked.sort(key=lambda r: r[1], reverse=True)
    return ranked[:top]


def sniff(port: str, bauds: tuple[int, ...], seconds: float, dtr: bool | None, rts: bool | None) -> None:
    """Print raw bytes at each baud rate and a header/frame-length guess."""
    for baud in bauds:
        try:
            ser = open_port(port, baud, dtr, rts)
        except serial.SerialException as exc:
            print(f"{port} @ {baud}: cannot open ({exc})")
            return
        with ser:
            time.sleep(0.3)
            ser.reset_input_buffer()
            data = bytearray()
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                data += ser.read(ser.in_waiting or 1)
        print(f"\n== {port} @ {baud}: {len(data)} bytes in {seconds:.1f}s")
        if not data:
            continue
        print("first 96 bytes:", bytes(data[:96]).hex(" "))
        print("top bytes     :", [(f"0x{b:02X}", n) for b, n in collections.Counter(data).most_common(5)])
        for pat, hits, gap in analyze(bytes(data)):
            print(f"header guess  : {pat.hex(' ')}  repeats every {gap} bytes ({hits}x)")
