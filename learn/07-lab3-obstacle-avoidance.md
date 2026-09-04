# 07 — Lab 3: the obstacle-avoidance node

**Goal of this lab:** deploy a Python `rclpy` node onto the robot's own workspace, register
it as a runnable command, build it, and run it so the robot drives and steers itself around
obstacles using the LiDAR. Source: both `docs/BEETLEBOT  Obstacle_avoid.txt` (v1) and
`docs/BEETLEBOT Updated _Obstacle_avoid.txt` (v2 / "Updated"). The full line-by-line read of
the v2 code (windowing math, state machine) already lives in `02-ros2-concepts.md` §5 — this
file is the deployment checklist plus a side-by-side of what changed between v1 and v2 and
why, since nothing else in this repo compares the two versions.

Runs entirely **on the robot, via SSH** (two terminals, same as Lab 2).

---

## Step 1 — Terminal 1: bringup (same as Lab 2 Step 2)

```bash
ssh veerobot@192.168.0.<robotNumber>
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash
export ROS_DOMAIN_ID=<robotNumber>
ros2 launch lyra_bringup robot.launch.py
```
Leave running — the obstacle-avoidance node needs live `/scan` data from this.

## Step 2 — Terminal 2: edit the node's source file

```bash
ssh veerobot@192.168.0.<robotNumber>
cd ~/lyra_ws/src/lyra_control/lyra_control/
nano obstacle_avoidance.py
```
Clear any existing content (`Ctrl+K` repeatedly — see `01-linux-commands.md` §3), then paste
in the script (v1 or v2, see comparison below), save (`Ctrl+O`, `Enter`), exit (`Ctrl+X`).

```bash
chmod +x obstacle_avoidance.py     # make it executable — 01-linux-commands.md §4
```

## Step 3 — Register it as a runnable command

```bash
cd ~/lyra_ws/src/lyra_control/
nano setup.py
```
Find the `console_scripts` list in `entry_points` and add one line:
```python
entry_points={
    'console_scripts': [
        'cmd_vel_mux = lyra_control.cmd_vel_mux:main',
        'joy_teleop_wrapper = lyra_control.joy_teleop_wrapper:main',
        'obstacle_avoid = lyra_control.obstacle_avoidance:main',   # <-- add this line
    ],
},
```
**Why this step exists:** `ros2 run <pkg> <name>` only knows about names listed here — it
maps the command name (`obstacle_avoid`) to a Python `module:function` (`main()` in
`obstacle_avoidance.py`). Without this entry, the file exists but `ros2 run` can't find it.
(`02-ros2-concepts.md` §3, "`package.xml` and `setup.py`".)

## Step 4 — Build and source

```bash
cd ~/lyra_ws
colcon build --packages-select lyra_control
source install/setup.bash
```
`--packages-select lyra_control` rebuilds just that one package instead of the whole
workspace — much faster on the Pi. **You must re-`source` after every build**, in every
terminal that will run the node, or `ros2 run` still won't see the new entry point.

## Step 5 — Run it

```bash
ros2 run lyra_control obstacle_avoid
```
The robot should start driving forward and steering away from anything closer than its
safe-distance threshold. Watch the log lines it prints (`Front: … | Left: … | Right: …` for
v2) to see what it's reacting to.

## Step 6 — Stop it safely

```
Ctrl+C
```
Both versions install a `SIGINT` handler (`signal.signal(signal.SIGINT, self.signal_handler)`)
that intercepts `Ctrl+C` and, **before** exiting, publishes a zero `Twist` 20 times at 50 ms
intervals — guaranteeing the last thing the motors hear is "stop", instead of leaving them
mid-command if the process just died. This is why you `Ctrl+C` this node directly rather than
disarming first.

---

## v1 vs v2: what changed, and why

| | v1 (`BEETLEBOT  Obstacle_avoid.txt`) | v2 / "Updated" (`BEETLEBOT Updated _Obstacle_avoid.txt`) |
|---|---|---|
| LiDAR zones | one **front** window only (`num_readings // 6`, ≈60° centred ahead) | three zones: **front** (`num_readings // 12`, ≈30° — narrower/more precise), **left**, **right** (`num_readings // 6` each) |
| Distance thresholds | one: `safe_distance = 0.5 m` | two: `front_distance = 0.45 m` ("directly ahead" — urgent) and `safe_distance = 0.5 m` ("somewhat blocked" — precautionary) |
| Reaction to an obstacle | stop forward motion, turn **always the same direction** (`angular.z = +turn_speed`, fixed) | compares `left_distance` vs `right_distance` and turns toward whichever side is **actually clearer** |
| Reaction when *very* close (< 0.45 m) | not distinguished — same fixed turn | **reverses first** (`reversing = True`, timed 0.8 s via `time.time()`), *then* picks the clearer side to turn into |
| Invalid-reading filtering | inline list comprehension per callback | dedicated `get_valid_ranges()` helper, reused for all three zones |
| `Ctrl+C` safety handler | present, identical in both | present, identical in both |

**Why v2 is the one to actually study for the viva** (per `.CLAUDE/CLAUDE.md`'s technical
debt table): v1's fixed-direction turn is a real limitation — if it's blocked on its
turning side too, it can get stuck oscillating instead of escaping. v2's "check both sides,
turn toward the clearer one" plus "back off first if it's *very* close" is a small but
genuine improvement in robustness, and it's the version the full code walkthrough in
`02-ros2-concepts.md` §5 (windowing math, the reversing state machine, the `SIGINT` handler)
is written against.

---

## Checklist — can you do this from memory?

- [ ] Explain why editing `setup.py`'s `entry_points` is necessary before `ros2 run` works
- [ ] `colcon build --packages-select <pkg>` then re-`source` — in that order, every time
- [ ] State the two distance thresholds in v2 and what happens at each
- [ ] Explain why v2 compares left vs right instead of always turning one way
- [ ] Explain what the `SIGINT` handler does and why it publishes zero 20 times, not once
- [ ] Know the full deployment path from memory: `nano` script → `chmod +x` → `nano setup.py`
      → `colcon build` → `source` → `ros2 run`

Full code walkthrough (windowing math, the reversing state machine, line by line): see
`02-ros2-concepts.md` §5. Emergency stops beyond `Ctrl+C`: `03-beetlebot-runbook.md`.
