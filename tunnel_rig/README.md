# tunnel_rig — ESP32 + Cytron MDD3A 4-motor tank drive over Bluetooth

ESP32 DevKit V1 drives a **Cytron MDD3A** dual-channel motor driver. Left two motors share
channel 1, right two share channel 2 (skid-steer / tank drive). Control is **Android Classic
Bluetooth** (SPP): pair with `TunnelRig`, then send single characters from a serial-Bluetooth app.
(History: this was a servo pan/tilt rig with a Wi-Fi GUI until 2026-11-11.)

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
- A side runs backwards? Flip `INVERT_LEFT` / `INVERT_RIGHT` in the sketch (or swap that side's motor wires).

## Flash (Windows, arduino-cli)

```powershell
arduino-cli core install esp32:esp32
arduino-cli compile --fqbn esp32:esp32:esp32 tunnel_rig
arduino-cli upload  --fqbn esp32:esp32:esp32 -p COM3 tunnel_rig
arduino-cli monitor -p COM3 -c baudrate=115200
```

No extra library: `BluetoothSerial` ships with the ESP32 core (3.x; uses `ledcAttach`/`ledcWrite`).
If upload hangs at "Connecting...", hold the BOOT button until it starts.

## Use

1. Android: Settings → Bluetooth → pair **TunnelRig** (no PIN, or 1234/0000 if asked).
2. Install a serial-Bluetooth app (e.g. *Serial Bluetooth Terminal*, or a joystick/RC-car app that
   sends the characters below) and connect to `TunnelRig`.
3. Send commands (case-insensitive):

| Char | Action | Char | Action |
|---|---|---|---|
| `F` | forward | `G` | forward-left |
| `B` | backward | `I` | forward-right |
| `L` | spin left | `H` | back-left |
| `R` | spin right | `J` | back-right |
| `S` | stop (immediate) | `0`–`9` | speed level (default 6; 9 = 100 %) |

4. Bench test without Bluetooth: the same characters typed into the USB serial monitor work too.

## PC control panel (Windows)

`control_panel.py` is a Tkinter window that drives the rig over the paired Bluetooth COM port.

```powershell
cd tunnel_rig
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python control_panel.py
pytest                     # logic tests (panel_logic.py)
```

1. Pair `TunnelRig` in Windows Bluetooth settings once. Windows creates an *outgoing* COM port
   for it (find it in Device Manager → Ports, or the panel's dropdown). Put it in `panel_config.yaml`
   (`port:`); the panel also remembers the last port that connected.
2. Press **Connect** (opening the port can take a few seconds).
3. Hold **W/A/S/D** or the arrow keys (or the on-screen pad) to drive, release to stop. **Space** or the
   red **STOP** button stops immediately. The slider sets speed 0–9.
4. The held command is resent every `repeat_ms` (150 ms) to keep the 500 ms firmware failsafe happy.
   Disconnecting, closing the window or losing focus sends stop.

Files: `control_panel.py` (GUI + serial), `panel_logic.py` (held keys → command char, tested in
`tests/test_panel_logic.py`), `panel_config.yaml`, `requirements.txt`.

## Safety / notes

- Motor pins are driven low before PWM starts, so the motors are off at boot.
- **Failsafe:** no drive command for `CMD_TIMEOUT_MS` (500 ms) → motors stop. Joystick apps resend
  while a button is held, so hold = drive, release = stop. A terminal app sending one `F` per tap
  will drive for only 0.5 s; set `CMD_TIMEOUT_MS` to 0 to disable (then drive until you send `S`).
- Acceleration is ramped (`RAMP_PER_STEP`); `S` and the failsafe stop instantly (MDD3A brakes with both inputs 0).
- Classic Bluetooth is **Android only** — iPhones can't connect (would need BLE).
- First test with the wheels off the ground.
- Compiled and flashed to COM3; boots and advertises `TunnelRig`. Not yet tested with the MDD3A / motors wired (see `TODO.md`).
