# 01 — Linux & the shell for ROS 2 work

ROS 2 development *is* Linux work: you build on Linux, you SSH into Linux robots, you read
Linux logs when something breaks. This file is the shell fluency that underpins everything
in `lab/` and `build/`. For each command: what it does, the **exact form you'll use**, and
the traps.

Two audiences in one file:
- **Foundations** (§1–§10) — general Linux every ROS user needs.
- **Deploying / operating a real robot** (§11–§15) — `systemd`, `udev`, `rosdep`, `vcs`,
  `git` for workspaces, networking & DDS discovery. You need these the moment you move past
  "run a launch file by hand".
- The **BeetleBot lab quick reference** (§16) is the old lab cheat-sheet, kept verbatim.

> **Where am I typing?** The single biggest source of mistakes when a PC and a robot are
> both open. Your prompt tells you:
> - `student@ros2-jazzy:~$` → the **dev PC / lab PC**
> - `veerobot@beetlebot-124:~$` → the **robot** (you got here via `ssh`)
> - `root@a1b2c3:/#` → inside a **container** (`docker run -it ros:jazzy`)
>
> `$` = normal user, `#` = root (careful). `~` = your home directory (`/home/<user>`).
> Put `hostname` in your prompt or run it when unsure. Every command in `lab/` is labelled
> **PC** or **robot** for this reason.

---

## 1. Filesystem navigation

| Command | What it does | Example |
|---|---|---|
| `pwd` | print working directory — "where am I" | `pwd` → `/home/veerobot` |
| `ls` | list files | `ls`, `ls -l` (long), `ls -a` (incl. hidden), `ls -la`, `ls -lh` (human sizes) |
| `ls -la /dev/ttyUSB*` | list with a glob — check a device exists + its permissions | |
| `cd <dir>` | change directory | `cd ~/ros2_ws`, `cd ~/ros2_ws/src/my_pkg/` |
| `cd` / `cd ~` | go to home | |
| `cd ..` | up one level | `cd ..` from `.../my_pkg/` → `.../src/` |
| `cd -` | back to the previous directory | toggles between two dirs |
| `tree -L 2` | show the directory tree, 2 levels deep | great for eyeballing a `src/` layout (`sudo apt install tree`) |
| `realpath <path>` / `readlink -f` | resolve a path to its absolute, symlink-free form | useful with `install/` symlinks |

**Path shorthand:** `~` = your home. `.` = current dir. `..` = parent. `-` (with `cd`) =
previous dir. Absolute paths start with `/` (filesystem root); everything else is relative
to `pwd`.

**`ls -la` decoded:** `-l` = long format (permissions, owner, group, size, date), `-a` =
show dotfiles. The first column is `drwxr-xr-x` — `d`=directory, then three permission
triplets (owner/group/others), each `rwx` (read/write/execute). See §5.

---

## 2. Creating, copying, moving, deleting

```bash
mkdir -p ~/ros2_ws/src            # -p: create every missing parent, don't error if it exists
rmdir <dir>                       # remove an EMPTY directory only
touch notes.txt                   # create an empty file (or bump its modified-time)

cp file1 file2                    # copy a file
cp -r dir1 dir2                   # -r: copy a directory and everything in it
cp -a src/ backup/               # -a: archive — recursive + preserve perms/timestamps/symlinks

mv old.txt new.txt                # rename
mv file.txt ~/Documents/          # move into a directory
mv -n a b                         # -n: never overwrite an existing target

rm file.txt                       # delete a file — PERMANENT, no recycle bin
rm -r some_dir                    # delete a directory tree
rm -rf build/ install/ log/       # -f: force, no prompts — the classic "clean my workspace"
```

> **`rm -rf` traps:** there is no undo. Never run it with a variable that might be empty
> (`rm -rf "$D/"` when `$D` is unset deletes `/`). Type the path out, or `ls` it first.
> `rm -rf build install log` in a workspace root is safe and routine; `rm -rf ~/` is a
> career-ender.

- Lab note: your own workspace is named after your register number, e.g.
  `mkdir -p ~/CS21B1042_ws/src` — never build into the robot's `~/lyra_ws`.

---

## 3. Reading and searching files

### Dump / page a file
```bash
cat file.py                       # print the whole file
cat -n file.py                    # ... with line numbers
less file.log                     # scrollable viewer: ↑/↓, PgUp/PgDn, /pattern to search, q to quit
head -n 40 file.log               # first 40 lines
tail -n 40 file.log               # last 40 lines
tail -f /var/log/syslog           # follow — print new lines as they're appended (Ctrl+C to stop)
```

### Search inside files — `grep`
```bash
grep "cmd_vel" my_node.py                 # lines containing the text
grep -rn "cmd_vel" src/                   # -r recursive, -n line numbers — search a whole tree
grep -i "error" latest.log                # -i case-insensitive
grep -v "DEBUG" latest.log                # -v invert — lines NOT matching
ros2 topic list | grep scan               # filter another command's output (see §4)
```

### Find files by name/type — `find`
```bash
find . -name "*.launch.py"                # every launch file under here
find ~/ros2_ws -name "*.yaml" -path "*config*"
find . -type d -name "build"              # -type d = directories only (f = files)
find . -name "*.pyc" -delete              # find and act
find /dev -name "ttyUSB*"                 # what serial devices exist
```

### Where is a command / what is it — `which`, `type`, `man`
```bash
which ros2                         # /opt/ros/jazzy/bin/ros2  (the path that will run)
type -a python3                    # every match on PATH, plus aliases/builtins
man ls                            # the manual page (q to quit; /pattern to search)
ls --help | less                  # most tools also have --help (faster than man)
```

### Edit — `nano` (simple) or `vim` (everywhere)
`nano file.py` — shortcuts shown at the bottom, `^` = **Ctrl**:

| Keys | Action |
|---|---|
| `Ctrl+O`, `Enter` | write out (save) |
| `Ctrl+X` | exit (prompts if unsaved) |
| `Ctrl+K` / `Ctrl+U` | cut / paste the current line |
| `Ctrl+W` | search; `Ctrl+\` search-and-replace |
| `Ctrl+_` | go to line number |

`nano -i` keeps indentation stable when pasting Python. On a robot with only `vi`/`vim`:
`i` to insert, `Esc` then `:wq` to save+quit, `:q!` to quit without saving.

---

## 4. Redirection, pipes, and chaining

```bash
cmd > out.txt          # send stdout to a file (OVERWRITE)
cmd >> out.txt         # append instead
cmd 2> err.txt         # send stderr (fd 2) to a file
cmd > all.txt 2>&1     # both streams into one file
cmd 2>/dev/null        # discard errors
cmd | less             # pipe stdout into another command's stdin
cmd | tee out.txt      # print AND save at once
```

| Operator | Meaning | Example |
|---|---|---|
| `\|` | pipe A's output into B | `ros2 node list \| grep ekf` |
| `;` | run B after A regardless | `cd ~/ros2_ws ; colcon build` |
| `&&` | run B **only if A succeeded** (exit 0) | `colcon build && source install/setup.bash` |
| `\|\|` | run B **only if A failed** | `ping -c1 host \|\| echo "unreachable"` |
| `&` | run A in the background | `rviz2 &` |
| `xargs` | turn stdin into arguments for B | `cat requirements.txt \| xargs sudo apt install -y` |

`ros2 topic echo /scan > scan.txt` captures a LiDAR sample; `colcon build && source
install/setup.bash` is the pattern you'll type a hundred times (only source if the build
worked).

---

## 5. Permissions, ownership, execution

```
-rwxr-xr-x  1  veerobot  dialout  8.0K  Jan 10 12:00  script.py
 │└┬┘└┬┘└┬┘     └───┬──┘  └──┬──┘
 │ owner group others   owner   group
 │
 file type (- file, d dir, l symlink)
```

```bash
chmod +x my_node.py               # add execute for everyone — needed to run ./my_node.py
chmod 755 my_node.py              # rwx / r-x / r-x  (owner / group / others)
chmod 644 config.yaml             # rw- / r-- / r--  (typical data file)
chmod u+x,go-w file               # symbolic: user +execute, group/other -write
```
Octal digits: `r=4 w=2 x=1`, summed per triplet. `755` = `4+2+1 / 4+1 / 4+1`.

```bash
sudo chown veerobot:veerobot file.txt      # change owner:group
sudo chown -R $USER ~/ros2_ws               # -R recursive — fix a tree you cloned as root
```

A Python ROS node needs `#!/usr/bin/env python3` as its first line **and** `chmod +x` to be
run directly or picked up by `ros2 run` when installed as a script.

> **Serial-port permission trap:** `/dev/ttyUSB0` / `/dev/ttyAMA0` are owned by group
> `dialout`. `chmod 666 /dev/ttyUSB0` "works" but resets on replug. The real fix is §6
> (add yourself to `dialout`) — and for a stable *name*, §12 (`udev`).

---

## 6. Users, groups, and `sudo`

```bash
whoami                            # your username
id                                # your uid/gid + all groups
groups                            # just the group names — check for 'dialout', 'video', 'input'
sudo <cmd>                        # run one command as root (asks for YOUR password)
sudo -i                           # an interactive root shell (use sparingly)
sudo !!                           # re-run the previous command with sudo
```

```bash
sudo usermod -aG dialout $USER    # serial devices (LiDAR, MCU bridge)
sudo usermod -aG video $USER      # cameras (/dev/video*)
sudo usermod -aG input $USER      # joysticks (/dev/input/*)
# group changes need a fresh login (or: newgrp dialout) to take effect
```

`-aG` = **append** to the named **G**roup. Forgetting `-a` (`usermod -G dialout`) *replaces*
all your supplementary groups — you can lose `sudo`. Always `-aG`.

---

## 7. Environment: `source`, `export`, `~/.bashrc`

The part people find mysterious. Read it twice — every "ROS command not found" and every
"the PC can't see the robot" traces back here.

### `export VAR=value` — an environment variable
```bash
export ROS_DOMAIN_ID=42
echo $ROS_DOMAIN_ID               # read it back ($ = "value of")
env | grep ROS                    # every ROS-related variable currently set
unset ROS_DOMAIN_ID              # remove it
```
An env var is a named value the shell passes to every program it launches. It lasts **only
for that terminal** — a new terminal starts clean unless `~/.bashrc` sets it.

ROS 2 env vars you'll meet:

| Variable | Does |
|---|---|
| `ROS_DOMAIN_ID` (0–101) | DDS "channel" — nodes only see nodes with the **same** ID. Set it the same in every terminal, every machine. |
| `ROS_LOCALHOST_ONLY=1` | confine discovery to one machine — must be **off** for a PC↔robot setup |
| `ROS_DISTRO` | `jazzy` / `humble` — set by `setup.bash`, don't set by hand |
| `RMW_IMPLEMENTATION` | which DDS vendor (`rmw_fastrtps_cpp`, `rmw_cyclonedds_cpp`) — all nodes must match |
| `ROS_AUTOMATIC_DISCOVERY_RANGE` | `SUBNET` (default) / `LOCALHOST` / `OFF` / `SYSTEM_DEFAULT` — modern replacement knob for discovery scope |
| `AMENT_PREFIX_PATH`, `PYTHONPATH` | package/module search paths — set by `setup.bash`, inspect if imports fail |

### `source <script>` — run a script *in the current shell*
```bash
source /opt/ros/jazzy/setup.bash          # base ROS 2 install — the "underlay"
source ~/ros2_ws/install/setup.bash       # your built workspace — an "overlay" (source AFTER the underlay)
```
Normally a script runs in a child shell and its variables vanish when it ends. `source`
(synonym: `.`) runs the lines **as if you typed them**, so `PATH`, `AMENT_PREFIX_PATH`,
etc. stick. `ros2` only becomes a command *after* you source the underlay.

**Underlay vs overlay:** the underlay is `/opt/ros/<distro>`. An overlay is a workspace's
`install/`; sourcing it *after* the underlay makes its packages shadow same-named ones
below. You can stack several (base → robot's `~/lyra_ws` → your `~/ros2_ws`). More detail:
`02-ros2-concepts.md` §3.

### `~/.bashrc` — runs for every new interactive terminal
```bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
echo 'source ~/ros2_ws/install/setup.bash' >> ~/.bashrc
source ~/.bashrc                            # apply now without opening a new terminal
```
Convenient, with two traps: (1) if `.bashrc` sources a workspace that fails to build, every
new terminal spews errors; (2) baking a wrong `ROS_DOMAIN_ID` in there is worse than typing
it — in the lab, `export` the ID manually so it's always deliberate.

---

## 8. SSH and working on a remote robot

### `ssh` — a remote shell
```bash
ssh veerobot@192.168.0.124                  # user@host — asks for the ROBOT's password
ssh veerobot@beetlebot-124.local            # by mDNS hostname (.local) instead of IP
ssh -X veerobot@robot                       # forward X11 so remote GUI apps draw on your screen
```
First connection asks you to trust the host key — `yes`. Everything after runs **on the
robot** until `exit` / `Ctrl+D`.

### SSH keys — stop typing the password
```bash
ssh-keygen -t ed25519 -C "me@laptop"        # once, on the PC — accept defaults, optional passphrase
ssh-copy-id veerobot@192.168.0.124          # installs your public key on the robot
ssh veerobot@192.168.0.124                  # now logs in with no password
```

### `~/.ssh/config` — aliases + defaults
```
Host bot
    HostName 192.168.0.124
    User veerobot
    ForwardX11 yes
```
Now `ssh bot`, `scp file bot:~/`, `rsync ... bot:` all work.

### Moving files — `scp` and `rsync`
```bash
scp local.txt veerobot@robot:/home/veerobot/        # PC → robot
scp veerobot@robot:~/my_map.yaml ./                  # robot → PC
scp -r my_folder veerobot@robot:~/                    # -r whole folder

rsync -avz ./src/ veerobot@robot:~/ros2_ws/src/       # sync a tree, only changed files
rsync -avz --delete ./src/ bot:~/ros2_ws/src/         # + delete files removed locally
rsync -avz --exclude build --exclude install --exclude log ./ bot:~/ros2_ws/
```
`rsync` beats `scp` for code: incremental, resumable, can exclude `build/`. Trailing-slash
on the source (`./src/`) means "contents of", no slash means "the dir itself".

### Multiple panes over one SSH — `tmux`
A launch file needs its own terminal; so does teleop; so does `ros2 topic echo`. Rather than
3 SSH sessions:
```bash
tmux                     # start a session
#   Ctrl+b then "   split horizontally     Ctrl+b then %   split vertically
#   Ctrl+b then arrow   move between panes
#   Ctrl+b then d   detach (leaves everything RUNNING)
tmux attach              # reattach later — survives your SSH dropping
```
This is how you keep a bringup launch alive when your Wi-Fi blips. `screen` is the older
equivalent if `tmux` isn't installed.

---

## 9. Networking and ROS 2 discovery

### Inspect the network
```bash
ip a                          # this machine's interfaces + IP addresses  (short for `ip addr`)
ip route                      # default gateway / routing table
hostname -I                   # just my IP address(es)
nmcli device wifi list        # visible Wi-Fi networks (NetworkManager)
nmcli device wifi connect BEETLEBOT_5G password '<pw>'
ping -c 4 192.168.0.124       # -c 4 = four packets then stop (no -c = forever, Ctrl+C)
```

### How ROS 2 nodes find each other
ROS 2 has **no `roscore`**. Nodes discover each other with **DDS**, which by default sends
**multicast** packets to `239.255.0.1` on the local subnet, then switches to unicast. For a
PC and robot to see each other:

1. **Same subnet** — both `192.168.0.x`, same router. `ip a` on each to confirm.
2. **Same `ROS_DOMAIN_ID`** — in *every* terminal on *both* machines.
3. **`ROS_LOCALHOST_ONLY` unset** (or `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`).
4. **Multicast not blocked** — some Wi-Fi APs and VPNs drop it; the firewall must allow it.

```bash
ros2 daemon stop && ros2 daemon start        # restart the CLI's discovery cache after network changes
ros2 doctor --report | less                  # dumps RMW, domain ID, network — first stop when discovery fails
```

### Firewall — `ufw`
```bash
sudo ufw status
sudo ufw allow in proto udp to 239.255.0.1        # allow DDS multicast (if ufw is active)
sudo ufw disable                                   # simplest for a trusted lab network
```

### When multicast is genuinely unavailable — Discovery Server
On networks that block multicast (many corporate/campus Wi-Fis), run a unicast rendezvous
point instead:
```bash
fastdds discovery --server-id 0 --listening-address 192.168.0.5 --port 11811   # on one host
export ROS_DISCOVERY_SERVER=192.168.0.5:11811                                   # on every node's shell
```

---

## 10. Processes, jobs, and signals

| Action | How |
|---|---|
| Stop the foreground program | **`Ctrl+C`** → `SIGINT`. Stops a launch, `ros2 topic echo`, `ping`, your node. Nodes should shut down cleanly on this. |
| Suspend to background | `Ctrl+Z`, then `bg` (resume in background) / `fg` (bring back) / `jobs` (list) |
| Start something backgrounded | `rviz2 &` |
| Keep running after logout | `nohup <cmd> &` or start it in `tmux` |
| Force-kill by name | `pkill -f teleop_twist_keyboard` (`-f` matches the whole command line) |
| Force-kill by PID | `kill <pid>`; `kill -9 <pid>` = `SIGKILL`, unblockable, last resort |
| See what's running | `htop` (interactive, `q` quits; `F4` filter) or `ps aux \| grep ros` |
| What's using a port/device | `sudo lsof /dev/ttyUSB0`, `sudo fuser -k /dev/ttyUSB0` |

> `SIGINT` (`Ctrl+C`) lets a node run its shutdown handler — e.g. BeetleBot's
> obstacle-avoidance node publishes zero-velocity 20× before exiting, so `Ctrl+C` *stops the
> wheels*. `kill -9` skips all of that and the robot keeps rolling on its last command. Use
> `-9` only when nothing else works.

---

## 11. `systemd` and logs — how a deployed robot runs its stack

On your dev machine you type `ros2 launch ...`. On a **fielded robot**, the stack is a
`systemd` **service** that starts on boot, restarts on crash, and logs centrally. Acrux does
exactly this (`./development.sh` stops the service so you can run things by hand;
`./demo.sh` restores it).

```bash
systemctl status lyra-bringup.service        # is it running? recent log lines, PID, uptime
sudo systemctl stop lyra-bringup             # stop it (so you can launch manually)
sudo systemctl start lyra-bringup
sudo systemctl restart lyra-bringup
sudo systemctl disable --now lyra-bringup    # stop + never start on boot
sudo systemctl enable --now lyra-bringup     # start now + on every boot
systemctl list-units --type=service | grep -i ros
```

### Logs — `journalctl`
```bash
journalctl -u lyra-bringup.service           # everything that service ever logged
journalctl -u lyra-bringup -f                 # follow live (like tail -f)
journalctl -u lyra-bringup -b                 # only since the last boot
journalctl -u lyra-bringup --since "10 min ago"
journalctl -p err -b                          # priority err and worse, this boot
```

### A minimal robot service (for reference — `build/03` shows the full pattern)
```ini
# /etc/systemd/system/lyra-bringup.service
[Unit]
Description=Lyra bringup
After=network-online.target

[Service]
User=veerobot
ExecStart=/bin/bash -lc 'source /opt/ros/jazzy/setup.bash && source /home/veerobot/lyra_ws/install/setup.bash && ros2 launch lyra_bringup robot.launch.py'
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
After editing a unit file: `sudo systemctl daemon-reload`.

ROS 2 also keeps its own per-run logs at `~/.ros/log/` — `ls -t ~/.ros/log/ | head`, and
`du -sh ~/.ros/log` when disk fills up.

---

## 12. `udev` rules — stable names for USB devices

Plug in a LiDAR and an IMU and they become `/dev/ttyUSB0` and `/dev/ttyUSB1` — but the
numbers **swap** depending on plug order / boot timing, and then your launch file opens the
wrong one. `udev` rules give a device a permanent, meaningful name.

```bash
udevadm info -a -n /dev/ttyUSB0 | grep -E "idVendor|idProduct|serial"   # find the device's IDs
```
```
# /etc/udev/rules.d/99-robot.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", ATTRS{serial}=="0001", SYMLINK+="rplidar", MODE="0666"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="lyra", MODE="0666"
```
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger    # apply without rebooting
ls -l /dev/rplidar                                              # -> /dev/rplidar -> ttyUSB0
```
Now the driver config says `/dev/rplidar`, order-independent, and `MODE="0666"` fixes
permissions permanently (better than `chmod 666` every boot, §5).

---

## 13. Installing packages: `apt`, `rosdep`, `pip`, `vcs`

### `apt` — system + ROS packages
```bash
sudo apt update                              # refresh the catalog (does NOT upgrade anything)
sudo apt install ros-jazzy-turtlesim ros-jazzy-nav2-bringup
sudo apt search ros-jazzy-slam               # find package names
apt-cache show ros-jazzy-slam-toolbox        # version, deps, description
sudo apt remove --purge <pkg>
```
ROS 2 packages are `ros-<distro>-<name>`, and the name uses **dashes** where the ROS
package uses underscores: `slam_toolbox` → `ros-jazzy-slam-toolbox`.

### `rosdep` — install a source workspace's declared dependencies
Every package lists its deps in `package.xml`. `rosdep` reads all of them and `apt install`s
what's missing — you run this once after cloning a workspace:
```bash
sudo rosdep init          # once per machine (ROS installs usually did this already)
rosdep update             # per user, refresh the dependency database
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
#   --from-paths src  scan every package under src/
#   --ignore-src      don't try to apt-install things you're building yourself
#   -r                keep going on errors     -y   assume yes
```

### `pip` + `venv` — Python libs that aren't ROS packages
Prefer `apt`/`rosdep` for anything ROS. For pure-Python extras, use a virtualenv so you
don't pollute the system Python that ROS depends on:
```bash
python3 -m venv ~/.venvs/tools && source ~/.venvs/tools/bin/activate
pip install <lib> && pip freeze > requirements.txt
```
(`uv venv` / `uv pip` is a faster drop-in worth adopting.) Note: activating a venv can
shadow ROS's Python packages — keep tool venvs separate from running nodes.

### `vcs` — clone many repos from a list
Bigger robots ship a `.repos` file instead of one git URL:
```bash
sudo apt install python3-vcstool
cd ~/ros2_ws
vcs import src < my_robot.repos       # clones every repo listed, at the pinned ref
vcs pull src                          # update them all
```

---

## 14. `git` for ROS workspaces

```bash
git clone https://github.com/you/my_robot.git ~/ros2_ws/src/my_robot
git status ; git add -A ; git commit -m "message" ; git push
git submodule update --init --recursive        # this repo vendors BeetleBot/acrux/jetbot as submodules
```

A workspace's `.gitignore` must exclude the build output:
```
build/
install/
log/
```
Commit `src/` (your packages, `package.xml`, `setup.py`/`CMakeLists.txt`, `launch/`,
`config/`) — never `build/install/log`, never `.pgm`/`.yaml` maps or `rosbag2_*` dirs.

---

## 15. System inspection

```bash
df -h                       # disk space per filesystem, human units
du -sh ~/.ros/log ~/ros2_ws/build     # size of specific directories
free -h                     # RAM / swap
uname -a                    # kernel + architecture (aarch64 on a Pi, x86_64 on the PC)
lsb_release -a              # Ubuntu version (24.04 → Jazzy, 22.04 → Humble)
nproc                       # CPU core count (colcon build --parallel-workers)
lsusb ; lscpu ; lsblk       # USB devices / CPU details / block devices
sensors                     # temperatures (sudo apt install lm-sensors) — Pis throttle when hot
echo $ROS_DISTRO ; ros2 --version
```

---

## 16. Shell ergonomics (do this from day one)

- **Tab completion** — press `Tab` to complete commands, paths, and (with ROS sourced)
  `ros2` subcommands, node names, topic names. Press it twice to list options.
- **History** — `↑`/`↓` cycle recent commands; `Ctrl+R` then type = reverse search;
  `!!` = last command (`sudo !!`); `!$` = last argument of the previous command.
- **Editing a line** — `Ctrl+A` start, `Ctrl+E` end, `Ctrl+W` delete word back,
  `Ctrl+U` clear line, `Ctrl+L` clear screen.
- **Aliases** — in `~/.bashrc`:
  ```bash
  alias cb='colcon build --symlink-install'
  alias sr='source install/setup.bash'
  alias rd='rosdep install --from-paths src --ignore-src -r -y'
  ```
- **`Ctrl+C` vs `Ctrl+D`** — `Ctrl+C` kills the running command; `Ctrl+D` sends EOF (ends an
  SSH session or an interactive Python/`ros2 topic pub` reading stdin).

---

## 17. BeetleBot lab quick reference

Everything above is general. This is the lab-day minimum — see `../lab/01-lab-day-runbook.md`
for the full procedure and `../lab/00-course-and-lab-map.md` for which lab is which.

```bash
# connect (PC)
ping 192.168.0.<n>                       # Ctrl+C to stop
ssh veerobot@192.168.0.<n>               # password: veerobot

# every new terminal, PC and robot
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash      # on the PC: source YOUR ~/<reg>_ws/install/setup.bash
export ROS_DOMAIN_ID=<n>

# edit a node (robot)
nano file.py        # Ctrl+K clear, paste, Ctrl+O Enter save, Ctrl+X exit
chmod +x file.py

# build your workspace
cd ~/<reg>_ws && colcon build && source install/setup.bash

# stop anything
Ctrl+C

# pull a file off the robot (PC)
scp veerobot@192.168.0.<n>:~/my_map.yaml ./
```

Next: `02-ros2-concepts.md`.
