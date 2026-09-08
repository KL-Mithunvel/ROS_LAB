# BeetleBot — network config examples

Netplan configs for giving a robot a fixed WiFi IP. These are the same two files
as `docs/wolf/net/` — copied from
[`VEEROBOT/ros-scripts`](https://github.com/VEEROBOT/ros-scripts) →
`ros2_network_yaml/` (commit `9529dd9`, retrieved 2026-09-08) — kept here as a
generic netplan reference.

**The BeetleBot handouts do networking a different way:** the robot ships with
`~/lyra_setup/install_wifi.sh "SSID" "PASSWORD" "192.168.29.101"` (see
`docs/beetlebot/04-system-setup-guide.md`). That script writes a netplan file for
you. These YAMLs are the **manual equivalent** — useful if `install_wifi.sh`
isn't present, or to see what it actually produces.

| File | netplan syntax | wlan0 address |
|------|----------------|---------------|
| `60-wolf-net.yaml` | older — `gateway4:` | `192.168.1.137/24` |
| `70-wolf-net.yaml` | newer — `routes:` (`gateway4` is deprecated) | `192.168.1.138/24` |

For the BeetleBot lab, set the SSID/password/address to your lab's values
(`BEETLEBOT_5G` on the lab network) and your assigned robot number — confirm
these with the instructor (the handouts disagree; see
`../../../learn/lab/01-lab-day-runbook.md`).

### Changes from upstream

Password redacted to `<your-wifi-password>`; `nameservers` de-duplicated;
a stray TAB in `70-wolf-net.yaml` replaced with spaces. Full notes in
`docs/wolf/net/README.md`.

### Usage

```bash
# on the robot (over SSH)
sudo cp 70-wolf-net.yaml /etc/netplan/
sudo chmod 600 /etc/netplan/70-wolf-net.yaml
sudoedit /etc/netplan/70-wolf-net.yaml     # set SSID, password, address, gateway
sudo netplan generate
sudo netplan apply
ip addr show wlan0
```
