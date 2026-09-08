# Wolf — network config examples

Netplan configs for giving the robot a fixed WiFi IP, copied from
[`VEEROBOT/ros-scripts`](https://github.com/VEEROBOT/ros-scripts) →
`ros2_network_yaml/` (commit `9529dd9`, retrieved 2026-09-08).

| File | netplan syntax | wlan0 address |
|------|----------------|---------------|
| `60-wolf-net.yaml` | older — `gateway4:` | `192.168.1.137/24` |
| `70-wolf-net.yaml` | newer — `routes:` (`gateway4` is deprecated) | `192.168.1.138/24` |

Use **one** of them, not both — the number prefix is netplan's apply order, a
higher number wins. `70-` is the form to prefer on Ubuntu 22.04+.

### Changes from upstream

- `password:` redacted to `<your-wifi-password>` (this repo keeps no credentials
  in tracked files — put the real value in only on the robot).
- `nameservers.addresses` de-duplicated (`8.8.8.8` was listed with `192.168.1.1`
  twice).
- `70-wolf-net.yaml`: a literal TAB on the `via:` line (invalid YAML) replaced
  with spaces.

### Usage

```bash
# on the robot
sudo cp 70-wolf-net.yaml /etc/netplan/
sudo chmod 600 /etc/netplan/70-wolf-net.yaml
sudoedit /etc/netplan/70-wolf-net.yaml     # set SSID, password, address, gateway
sudo netplan generate
sudo netplan apply
ip addr show wlan0                          # confirm the new address
```

The upstream `docs/wolf/04-ros-2-setup.md` walks through the same step (it calls
the file `60-wolf-net.yaml` and uses placeholder `"wifi-username"` /
`"wifi-password"`).
