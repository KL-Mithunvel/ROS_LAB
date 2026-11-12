"""Tunnel rig on a Raspberry Pi 5: UDP -> MDD3A tank drive. Same protocol as tunnel_rig.ino.

Run:  python3 rig_server.py [rig_config.yaml]      (Ctrl+C or SIGTERM stops the motors)
"""
import os
import select
import signal
import socket
import sys
import time

import yaml

from rig_logic import DUTY_MAX, RigState, parse_packet

PIN_NAMES = ("left_a", "left_b", "right_a", "right_b")


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    for key in ("udp_port", "pins", "pwm_hz", "default_level", "cmd_timeout_ms",
                "ramp_per_step", "ramp_ms", "rssi_report", "invert_left", "invert_right"):
        if key not in cfg:
            raise ValueError("%s: missing '%s'" % (path, key))
    for name in PIN_NAMES:
        if name not in cfg["pins"]:
            raise ValueError("%s: missing pins.%s" % (path, name))
    return cfg


def make_outputs(cfg):
    from gpiozero import Device, PWMOutputDevice          # imported late: tests need no GPIO
    from gpiozero.pins.lgpio import LGPIOFactory          # lgpio is required on the Pi 5
    Device.pin_factory = LGPIOFactory()
    return {name: PWMOutputDevice(cfg["pins"][name], frequency=cfg["pwm_hz"], initial_value=0)
            for name in PIN_NAMES}


def drive(out_a, out_b, duty, invert):
    if invert:
        duty = -duty
    if duty >= 0:
        out_b.value = 0
        out_a.value = duty / DUTY_MAX
    else:
        out_a.value = 0
        out_b.value = -duty / DUTY_MAX


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = load_config(argv[1] if len(argv) > 1 else os.path.join(here, "rig_config.yaml"))
    out = make_outputs(cfg)
    state = RigState(cfg["default_level"], cfg["cmd_timeout_ms"] / 1000.0,
                     cfg["ramp_per_step"], cfg["ramp_ms"] / 1000.0)

    def stop_all(*_):
        sys.exit(0)                                       # finally-block below zeroes the outputs

    signal.signal(signal.SIGTERM, stop_all)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", cfg["udp_port"]))
    print("[rig] listening on udp/%d" % cfg["udp_port"], flush=True)

    try:
        while True:
            ready, _, _ = select.select([sock], [], [], cfg["ramp_ms"] / 1000.0)
            now = time.monotonic()
            if ready:
                data, addr = sock.recvfrom(64)
                seq, cmd = parse_packet(data)
                state.handle(cmd, now)
                sock.sendto(state.reply(seq, cfg["rssi_report"]).encode("ascii"), addr)
            left, right = state.tick(now)
            drive(out["left_a"], out["left_b"], left, cfg["invert_left"])
            drive(out["right_a"], out["right_b"], right, cfg["invert_right"])
    except KeyboardInterrupt:
        pass
    finally:
        for dev in out.values():
            dev.value = 0
            dev.close()


if __name__ == "__main__":
    main(sys.argv)
