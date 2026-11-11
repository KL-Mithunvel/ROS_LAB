# Tunnel rig — Wi-Fi control plan

Status (2026-11-11): **built, not yet tested on the real network.** Firmware compiles, the PC panel
is tested against a fake rig on localhost. This file is the plan + test procedure; results go in the
table at the end.

## Why

Classic Bluetooth (the first version) dropped as soon as the rig entered the tunnel (~10 m class,
and the tunnel walls absorb it). Instead, put a **router inside the tunnel** so the only wireless
hop is short (ESP32 ↔ router), and bring everything else back to the laptop over **Ethernet**.

## Topology

```
 TUNNEL                                                        OUTSIDE / BENCH
 ┌────────────────────────────────────────────┐
 │  rig: ESP32 + MDD3A + 4 motors             │
 │    │  2.4 GHz Wi-Fi (short hop)            │
 │    ▼                                       │
 │  router (D-Link DIR-825, 192.168.1.1) ─────┼── Ethernet ──► laptop (192.168.1.x)
 │    ▲ Ethernet                              │                 control panel + camera in browser
 │  PoE switch ◄── Ethernet cable ── PoE camera (192.168.1.250)
 └────────────────────────────────────────────┘
```

- The **PoE switch** powers the camera and passes its data. The switch's uplink goes to a **LAN port of
  the router** (the router itself is not a PoE source).
- The laptop connects to another LAN port of the router (or the router→laptop run is the long cable).
- Everything is on one subnet, `192.168.1.0/24`, so no routing is needed.
- Only the **router model and settings** were taken from the old tile-sorting project
  (`Tile_Sorting/documents/electrical/network_plan.md`); none of its nodes (Pi, gantry, ...) are used.

## Router (from the tile project's notes — verify on the day)

| Item | Value |
|---|---|
| Model | D-Link DIR-825 AC1200, stock firmware (H/W J2, FW 1.0.5a) |
| LAN | `192.168.1.1` / `255.255.255.0` |
| DHCP pool | `192.168.1.100`–`.199` (lease 1440 min) |
| Wi-Fi | planned SSID `TileLine`, WPA2-PSK — **not verified as configured**; ESP32 needs the **2.4 GHz** radio on |
| Uplink | none (isolated LAN) — fine, nothing here needs the internet |

## Addresses

| Device | Address | How |
|---|---|---|
| Router | `192.168.1.1` | fixed |
| Laptop (Ethernet) | `192.168.1.x` | DHCP from the router, or the old static `192.168.1.33/24` (no gateway needed) |
| Rig ESP32 | **`192.168.1.60`** | fixed in the firmware (outside the DHCP pool, free) |
| Camera | `192.168.1.250` | existing; web UI `https://192.168.1.250/#/index/Preview/` |

## Control protocol (UDP, port 4210)

- Panel → rig: `"<seq>:<cmd>"`, every `repeat_ms` (150 ms). `<cmd>` is the held command
  (F/B/L/R/G/I/H/J) or `S` when idle, so every packet doubles as a ping. Speed digits `0`–`9` as before.
- Rig → panel: `"<seq>,<rssi>,<speedLevel>,<lastCmd>"` — the signal strength the rig sees, plus an echo of
  the sequence number so the panel can time the round trip.
- UDP on purpose: a late packet is useless for hold-to-drive; the next one replaces it.
- If the rig's reported speed differs from the slider (lost packet / reboot), the panel re-sends it.

## Safety

- Rig stops if no drive command arrives for 500 ms **or** Wi-Fi drops (`stopNow()` on link loss).
- Panel disables the drive pad when no reply for `lost_after_ms` (500 ms) and sends STOP;
  STOP button / Space send two stop packets.
- `repeat_ms` is clamped to ≤ 400 ms so it can never exceed the failsafe.
- Credentials stay out of git (`secrets.h` is gitignored).

## Comm-health bar

Score 0–100 from the last 20 packets: **50 % packet loss** (0 at 50 % loss), **25 % round-trip time**
(100 at ≤30 ms, 0 at ≥300 ms), **25 % RSSI** (100 at ≥−50 dBm, 0 at ≤−85 dBm).
GOOD ≥ 70, FAIR ≥ 40, POOR below, **LOST** when nothing has come back for `lost_after_ms`.
Shown as a coloured bar with `RSSI / RTT / loss` underneath. Logic: `panel_logic.py` (`HealthTracker`, tested).

## Test procedure

1. Router: 2.4 GHz Wi-Fi on; note the SSID/password. Copy `secrets.h.example` → `secrets.h`, fill in.
2. Flash (README). Serial monitor should print `[WiFi] up, RSSI ... dBm, listening on udp/4210`.
3. Laptop: `ping 192.168.1.60`. Camera page opens from the panel's **Open camera** button.
4. Run the panel → **Connect** → bar goes green. Wheels off the ground: check F/B/L/R, STOP, speed.
5. Failsafe: unplug the router (or switch off the rig's Wi-Fi) → panel shows LINK LOST, wheels stop.
6. Tunnel: place the router, then record RSSI / RTT / loss at increasing distances (table below).

| Distance from router (m) | RSSI (dBm) | RTT (ms) | Loss (%) | Health | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Open items

- [ ] Confirm the router broadcasts 2.4 GHz and the SSID/password
- [ ] Is `192.168.1.60` really free on that LAN?
- [ ] Range inside the tunnel: tunnel length, router placement/height, metal/pipes near the antenna
- [ ] Router and PoE switch power in the tunnel
- [ ] If range is still short: external-antenna ESP32 board, second router as a bridge, or a tethered Ethernet-to-serial link
