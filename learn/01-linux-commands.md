# 01 — Linux commands for the BeetleBot lab

Every terminal command you actually touch in this lab, grouped by what you're doing.
For each: what it does, the **exact form the lab uses**, and the traps.

> **Where am I typing?** The single biggest source of lab mistakes. Your prompt tells you:
> - `student@ros2-jazzy:~$` → you're on the **lab PC**
> - `veerobot@beetlebot-...:~$` → you're on the **robot** (you got here by `ssh`)
> The `$` means a normal user; `#` means root (be careful). `~` is your home directory.

---

## 1. Moving around the filesystem

| Command | What it does | Lab example |
|---|---|---|
| `pwd` | print working directory — "where am I" | `pwd` → `/home/veerobot` |
| `ls` | list files | `ls`, `ls -la` (long + hidden), `ls -la /dev/ttyAMA0` |
| `cd <dir>` | change directory | `cd ~/lyra_ws`, `cd ~/lyra_ws/src/lyra_control/lyra_control/` |
| `cd` or `cd ~` | go to home | |
| `cd ..` | up one level | `cd ..` from `.../lyra_control/` → `.../src/` |
| `cd -` | back to previous directory | |

**Path shorthand:** `~` = your home (`/home/veerobot`). `.` = current dir. `..` = parent.
Absolute paths start with `/` (from filesystem root); everything else is relative to `pwd`.

**`ls -la` decoded:** `-l` = long format (permissions, owner, size, date), `-a` = show
hidden files (names starting with `.`). You'll use `ls -la /dev/ttyAMA0` to check the
serial port exists and see its permissions.

---

## 2. Creating directories and files

```bash
mkdir -p ~/ros2_ws/src
```

- `mkdir` = make directory.
- `-p` = "parents": create every missing directory in the path, and **don't error if it
  already exists**. Without `-p`, `mkdir ~/ros2_ws/src` fails if `~/ros2_ws` doesn't exist yet.
- Lab note: the handout says name it with your **register number** (e.g. `mkdir -p ~/CS21B1042_ws/src`).

```bash
touch myfile.txt          # create an empty file (or update its timestamp)
```

---

## 3. Reading and editing files

### `cat` — dump a file to the screen
```bash
cat README.md
cat ~/.ros/log/latest/*/stdout       # * is a wildcard: all matching paths
```

### `nano` — the editor the lab uses

```bash
nano obstacle_avoidance.py
```

Nano shows shortcuts at the bottom. `^` means **Ctrl**. The ones you need:

| Keys | Action |
|---|---|
| `Ctrl+O` then `Enter` | **O**utput = save (nano calls it "Write Out") |
| `Ctrl+X` | e**X**it (prompts to save if unsaved) |
| `Ctrl+K` | **K**ut (cut) the current line — the handout says "hold Ctrl+K until the file is empty" to clear it before pasting the new script |
| `Ctrl+W` | **W**here is = search |
| `Ctrl+\` | search and replace |
| Arrow keys | move the cursor (no mouse) |

**Pasting into nano:** just right-click / Ctrl+Shift+V in the terminal — nano takes it as
typed text. Watch for auto-indent mangling Python; if it happens, `nano -i` or paste
carefully.

### `>` and `>>` — redirect output into a file

```bash
ros2 topic echo /scan > scan_output.txt      # overwrite scan_output.txt with the output
something >> log.txt                          # append instead of overwrite
```

`>` sends what would have printed to the screen into a file instead. `>>` appends.
You'll use `ros2 topic echo /scan > scan_output.txt` to capture a LiDAR sample.

---

## 4. Permissions and execution

```bash
chmod +x obstacle_avoidance.py
```

- `chmod` = change mode (permissions). `+x` = add the "executable" bit so the file can be
  run as a program (`./obstacle_avoidance.py`).
- You do this after creating a Python node script so ROS / the shell can execute it.
- `chmod 666 /dev/ttyAMA0` (seen in troubleshooting) = give everyone read+write on the
  serial port. `6` = read(4)+write(2), three digits = owner/group/others. This is a
  temporary hack; the proper fix is adding your user to the `dialout` group.

```bash
sudo usermod -a -G dialout $USER     # add yourself to the 'dialout' group (serial access)
sudo usermod -a -G input $USER       # 'input' group (joystick access)
# log out and back in for group changes to take effect
```

- `sudo` = "do this as the superuser (root)". Needed for system changes. It'll ask for
  your password. Only use it when a command genuinely needs it.
- `-a -G <group>` = **a**ppend the user to **G**roup (without `-a` you'd *replace* all their
  groups — dangerous).
- `$USER` = environment variable holding your username.

---

## 5. Networking — connecting to the robot

### `ping` — is the robot reachable?
```bash
ping 192.168.0.128
```
Sends packets and prints replies. Success = network path is good. **Stop it with `Ctrl+C`**
(it runs forever otherwise). Timeouts = wrong network, robot off, or wrong IP.

### `ssh` — open a remote terminal on the robot
```bash
ssh veerobot@192.168.0.128
ssh veerobot@beetlebot-124.local     # by hostname instead of IP (.local = mDNS)
```
- Form: `ssh <username>@<host>`. It asks for the **robot's** password (`veerobot`), not
  your PC password. First connection asks to trust the host key — type `yes`.
- After this, every command runs **on the robot** until you `exit` (or `Ctrl+D`).
- The lab needs **two SSH sessions** = two terminals, both `ssh`'d in: one for bringup,
  one for driving.

### `scp` — copy files between PC and robot
```bash
scp local_file.txt veerobot@192.168.0.128:/home/veerobot/      # PC  -> robot
scp veerobot@192.168.0.128:~/my_map.yaml ./                    # robot -> PC
scp -r myfolder veerobot@192.168.0.128:/home/veerobot/         # -r = whole folder
scp veerobot@192.168.0.128:'~/maps/*' ./maps/                  # all files in a folder
```
Form: `scp <source> <destination>`, where a remote path is `user@host:path`. `-r` for
directories. Use it to pull your saved map / rosbag / `scan_output.txt` off the robot.

### `exit` / `Ctrl+D`
Leave the SSH session, back to your PC shell.

---

## 6. Environment: `source`, `export`, `~/.bashrc`

This is the part people find mysterious. Read it twice.

### `export VAR=value` — set an environment variable
```bash
export ROS_DOMAIN_ID=129
```
An environment variable is a named value the shell hands to every program it starts.
`ROS_DOMAIN_ID` tells ROS 2 which "channel" to talk on — **the PC and robot must set the
same number** or they can't see each other's nodes/topics. It only lasts for that terminal;
open a new terminal and you must `export` it again (or put it in `~/.bashrc`).

Check it: `echo $ROS_DOMAIN_ID` (the `$` reads the variable's value).

Other ROS env vars you'll meet: `ROS_DISTRO` (=`jazzy`), `ROS_LOCALHOST_ONLY`.

### `source <script>` — run a script *in the current shell*
```bash
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
```
Normally running a script starts a *new* shell, so any variables it sets vanish when it
ends. `source` (or its synonym `.`) runs the script's lines **as if you typed them**, so the
variables *stick* in your current terminal.

The ROS `setup.bash` files add ROS to your `PATH` (so `ros2` becomes a command), set
`AMENT_PREFIX_PATH`, `PYTHONPATH`, etc. Two layers:
- `/opt/ros/jazzy/setup.bash` — the **base** ROS 2 install (the "underlay")
- `~/lyra_ws/install/setup.bash` — your built **workspace** (the "overlay"), source it
  *after* the base so your packages are found

**You must `source` both in every new terminal** (PC and robot) before `ros2` commands work.

### `~/.bashrc` — commands that run automatically for every new terminal
```bash
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```
`~/.bashrc` is a script bash runs each time you open an interactive terminal. Appending the
`source` line there (`>>` = append) means you don't have to type it every time. To apply
changes immediately without opening a new terminal: `source ~/.bashrc`.

> Trap: if `.bashrc` sources a workspace that fails to build, every new terminal spews
> errors. Also, `ROS_DOMAIN_ID` is per-person here, so the lab has you `export` it manually
> rather than bake a wrong value into `.bashrc`.

---

## 7. Package management (`apt`)

```bash
sudo apt update                              # refresh the list of available packages
sudo apt install ros-jazzy-turtlesim         # install a package
sudo apt install ros-jazzy-nav2-map-server
```
- `apt` = Debian/Ubuntu package manager. `update` refreshes the catalog (does **not**
  upgrade anything); `install` downloads + installs.
- ROS 2 packages are named `ros-<distro>-<package>`, e.g. `ros-jazzy-turtlesim`,
  `ros-jazzy-teleop-twist-keyboard`.
- Needs `sudo` (system-wide change).

---

## 8. Processes and signals

| Action | How |
|---|---|
| Stop the foreground program | **`Ctrl+C`** — sends `SIGINT` ("interrupt"). This is how you stop a launch, a `ros2 topic echo`, a `ping`, your obstacle-avoidance node. |
| Force-kill a frozen program | `Ctrl+\` (`SIGQUIT`), or from another terminal `kill <pid>` / `pkill -f <name>` |
| Suspend to background | `Ctrl+Z`, then `bg` / `fg` / `jobs` (rarely needed here) |
| See running processes | `htop` (interactive, `q` to quit) or `ps aux | grep ros` |
| End the shell / SSH session | `exit` or `Ctrl+D` |

**Why `Ctrl+C` matters here:** the obstacle-avoidance node installs a `SIGINT` handler that
publishes zero-velocity 20× before exiting — so `Ctrl+C` *stops the wheels*. Killing it any
other way (`kill -9`) skips that and the robot keeps rolling on its last command.

---

## 9. Inspecting the system

```bash
echo $ROS_DISTRO            # -> jazzy
ros2 --version
df -h                       # disk space, human-readable
du -sh ~/.ros/log           # size of the ROS log directory
free -h                     # memory
uname -a                    # kernel / arch
ip addr    (or  ip a)       # this machine's IP addresses
groups                      # which groups you're in (check for 'dialout', 'input')
```

---

## 10. Chaining commands

| Operator | Meaning | Example from the handouts |
|---|---|---|
| `;` | run B after A, regardless of A's result | `cd ~/lyra_ws; colcon build` |
| `&&` | run B **only if A succeeded** | `... pub -t 50 ... && ... pub -t 15 ...` (drive, then forced stop) |
| `\|\|` | run B only if A **failed** | |
| `\|` | pipe A's output into B's input | `ros2 node list \| grep ekf`, `groups \| grep input` |
| `&` | run A in the background | (not common in this lab) |

`grep <pattern>` filters lines containing the pattern — `ros2 topic list | grep scan`
shows just the scan-related topics.

---

## 11. The absolute-minimum cheat sheet

```bash
# connect
ping 192.168.0.<n>                       # Ctrl+C to stop
ssh veerobot@192.168.0.<n>               # password: veerobot

# every new terminal, PC and robot
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<n>

# edit a node
nano file.py        # Ctrl+K clear, paste, Ctrl+O Enter save, Ctrl+X exit
chmod +x file.py

# build your workspace
cd ~/<reg>_ws && colcon build && source install/setup.bash

# stop anything
Ctrl+C

# pull a file off the robot
scp veerobot@192.168.0.<n>:~/my_map.yaml ./
```

Next: `02-ros2-concepts.md`.
