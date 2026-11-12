# tunnel_rig on a Raspberry Pi 5 (`klmpi`)

Replaces the ESP32: the Pi drives the same Cytron MDD3A and speaks the **same UDP protocol**
(`"<seq>:<cmd>"` -> `"<seq>,<rssi>,<speed>,<last>"`, port 4210), so `control_panel.py` works unchanged.
The Pi is wired to the router by Ethernet (no Wi-Fi hop). Status: **written + unit-tested on the PC;
not yet run on the Pi** (the Pi was unreachable when this was written).

## Wiring (Pi 5 40-pin header -> MDD3A signal header)

| Pi pin | GPIO (BCM) | MDD3A | Role |
|---|---|---|---|
| 32 | GPIO12 | M1A | Left forward PWM |
| 33 | GPIO13 | M1B | Left reverse PWM |
| 34 | GND | GND | Common ground (required) |
| 35 | GPIO19 | M2A | Right forward PWM |
| 36 | GPIO16 | M2B | Right reverse PWM |

Battery -> MDD3A POWER (+ via fuse, - direct), 470-1000 uF across the battery terminals. Left motors in
parallel on M1A/M1B, right on M2A/M2B. The MDD3A has no 5 V output: power the Pi from its own supply.
Boot-time pulls on these GPIOs are low, so the motors stay off while the Pi starts.

## Deploy (from the PC, with the Pi reachable; the Tile notes list `192.168.1.11` on the D-Link LAN)

```
ssh klm@192.168.1.11 "mkdir -p ~/tunnel_rig_pi"
scp pi/rig_logic.py pi/rig_server.py pi/rig_config.yaml pi/requirements.txt pi/tunnel-rig.service klm@192.168.1.11:tunnel_rig_pi/
ssh klm@192.168.1.11
  sudo apt install -y python3-gpiozero python3-lgpio python3-yaml
  cd ~/tunnel_rig_pi && python3 rig_server.py        # try by hand first, wheels off the ground
```

Then in `panel_config.yaml` set `host: 192.168.1.11` and run the panel. Once happy, enable on boot:

```
sudo cp ~/tunnel_rig_pi/tunnel-rig.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now tunnel-rig
```

## Notes

- `gpiozero` + `lgpio` is required on the Pi 5 (`RPi.GPIO` does not work). PWM is software (1 kHz).
- Direction: flip `invert_left` / `invert_right` in `rig_config.yaml` if a side runs backwards.
- Failsafe: no drive command for 500 ms stops the motors; SIGTERM / Ctrl+C also zero all outputs.
- `rssi_report` is a fixed value because the link is wired.
- Tests (PC): `cd tunnel_rig && .venv\Scripts\python -m pytest`.
