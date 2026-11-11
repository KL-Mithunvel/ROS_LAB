# tunnel_rig — ESP32 + Cytron MDD3A 4-motor tank drive over Wi-Fi

ESP32 DevKit V1 drives a **Cytron MDD3A** dual-channel motor driver. Left two motors share
channel 1, right two share channel 2 (skid-steer / tank drive). Control is **Wi-Fi (UDP)** through a
router placed in the tunnel; a **Windows control panel** drives it and shows a comm-health bar.
The full network plan and test procedure are in **`WIFI-PLAN.md`**.
(History: servo pan/tilt + Wi-Fi web GUI → Bluetooth (dropped out in the tunnel) → this, 2026-11-11.)

## Wiring

MDD3A signal header (5 pins: M1A, M1B, GND, M2A, M2B):

| ESP32 | MDD3A header | Role |
|---|---|---|
| GPIO25 | M1A | Left side, forward PWM |
| GPIO26 | M1B | Left side, reverse PWM |
| GPIO32 | M2A | Right side, forward PWM |
| GPIO33 | M2B | Right side, reverse PWM |
| GND | GND | Common ground (required) |

MDD3A screw terminals:

| From | To |
|---|---|
| Battery + (via fuse) | POWER + |
| Battery − | POWER − |
| Left motors 1+2 in parallel | M1A / M1B |
| Right motors 3+4 in parallel | M2A / M2B |

- MDD3A: 4–16 V, ~3 A continuous / 5 A peak **per channel**. Two motors in parallel add their
  currents — check the pair's combined stall current fits.
- The MDD3A has no 5 V output. Power the ESP32 from USB (bench) or a buck converter
  (battery → 5 V → ESP32 VIN, grounds joined).
- Add a 470–1000 µF capacitor across the battery terminals near the MDD3A, and a fuse on battery +.
- Logic is 3.3 V compatible — no level shifter.
- GPIO32/33 are used on the right side instead of GPIO14/12, which glitch at boot.
- Direction: `INVERT_LEFT` / `INVERT_RIGHT` in the sketch are both `true` (the motors ran backwards with `false`).

## Wi-Fi setup + flash (Windows, arduino-cli)

1. Copy `secrets.h.example` to `secrets.h` (gitignored) and set `WIFI_SSID` / `WIFI_PASS`.
   The ESP32 is **2.4 GHz only** — the router's 2.4 GHz radio must be on.
2. The rig's address is fixed in the sketch: `192.168.1.60` (gateway `192.168.1.1`, UDP port `4210`).

```powershell
arduino-cli core install esp32:esp32
arduino-cli compile --fqbn esp32:esp32:esp32 tunnel_rig
arduino-cli upload  --fqbn esp32:esp32:esp32 -p COM3 tunnel_rig
arduino-cli monitor -p COM3 -c baudrate=115200
```

No extra library (WiFi/WiFiUdp ship with the ESP32 core 3.x). If upload hangs at "Connecting...",
hold the BOOT button. The monitor should print `[WiFi] up, RSSI ... dBm, listening on udp/4210`.
The same command characters also work typed into the USB serial monitor (bench test).

## Protocol

Panel → rig, UDP: `"<seq>:<cmd>"` (e.g. `1042:F`). Rig → panel: `"<seq>,<rssi>,<speed>,<lastCmd>"`.

| Char | Action | Char | Action |
|---|---|---|---|
| `F` | forward | `G` | forward-left |
| `B` | backward | `I` | forward-right |
| `L` | spin left | `H` | back-left |
| `R` | spin right | `J` | back-right |
| `S` | stop (immediate) | `?` | ping only (no motion) |
| `0`–`9` | speed level (default 6; 9 = 100 %) | `Q` | speed 9 |

## PC control panel (Windows)

```powershell
cd tunnel_rig
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python control_panel.py
pytest                     # logic tests (panel_logic.py)
```

1. Laptop on the router's network (Ethernet), rig powered and joined to the router.
2. **Connect** (rig IP from `panel_config.yaml`, default `192.168.1.60`). The health bar fills as replies arrive.
3. Hold **W/A/S/D** or the arrow keys (or the on-screen pad) to drive, release to stop. **Space** or the
   red **STOP** button stops immediately. The slider sets speed 0–9.
4. **Comm health** bar: score 0–100 from packet loss, round-trip time and the rig's Wi-Fi RSSI, with
   `RSSI / RTT / loss` underneath. GOOD ≥ 70, FAIR ≥ 40, POOR below, **LINK LOST** when nothing comes
   back for `lost_after_ms` — the drive pad is then disabled and the rig stops by itself.
5. **Open camera** opens `camera_url` (the PoE camera's web page) in the browser.

Files: `control_panel.py` (GUI + UDP), `panel_logic.py` (key → command, packets, health scoring),
`panel_config.yaml`, `requirements.txt`, `tests/test_panel_logic.py`.

## Safety / notes

- Motor pins are driven low before PWM starts, so the motors are off at boot.
- **Failsafe:** no drive command for `CMD_TIMEOUT_MS` (500 ms) **or** Wi-Fi lost → motors stop.
  The panel sends a packet every 150 ms (the held command, or STOP), so hold = drive, release = stop.
- Acceleration is ramped (`RAMP_PER_STEP`); `S` and the failsafe stop instantly (MDD3A brakes with both inputs 0).
- UDP is unauthenticated: anyone on the router's Wi-Fi who sends to `192.168.1.60:4210` can drive the rig.
  Use WPA2 and keep the network isolated.
- First test with the wheels off the ground.
- Status: firmware compiles; panel tested against a fake rig on localhost. **Not yet tested on the real
  router / with the motors wired** (see `TODO.md`).
