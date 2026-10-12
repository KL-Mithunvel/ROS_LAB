# 09 — Acrux gift-greeter mission: plan, design and runbook

> **What this file is:** the full plan for a real task — *Acrux carries gifts to 3 or 4 guests
> standing at pre-decided spots, waits at each until the operator says "yes", avoids anything
> unexpected, and drives home.* It is written in plain language on purpose.
> **Code:** [`practice/acrux_greeter/`](../../practice/acrux_greeter/README.md).
> **Status:** designed, state machine unit-tested (pytest), ROS parts **written but never run
> on Gazebo or the robot** — see §14 for everything still unverified.

Background reading: [`01-three-bots-architecture.md`](01-three-bots-architecture.md) §3 (Acrux
packages), [`07-localization-and-slam.md`](07-localization-and-slam.md),
[`08-navigation-and-path-planning.md`](08-navigation-and-path-planning.md).

---

## 1. The task and what was decided

Special guests will stand at fixed, pre-decided spots in the lab. Acrux (already in the lab)
has to drive to each guest and present a gift, then go home. We only learn the real guest
count (3 or 4) just before the event.

| Decision | Choice | Why |
|---|---|---|
| Max guests | **4** (a run with 3 uses the first 3 spots) | Spots are prepared in advance; the count is just a number |
| Present action | **Stop and wait.** Nothing else (no speech, no lights) for now | Gifts ride on top of the robot; guests take them |
| Moving on | **Live operator command** ("yes" = next) | A human confirms the gift was taken before the robot leaves |
| After the last guest | **Return home** (after the operator confirms the last gift) | Robot ends in a known, safe place |
| Unexpected obstacle | **Avoid, never hit anything or anyone** | Safety first; layered (§7) |
| Where the code runs | **Laptop over Wi-Fi**; safety layer **on the robot** | Safety must not depend on Wi-Fi |
| Map | **Does not exist yet** — must be made (§10) | Nothing to navigate on without it |
| Camera | **Test the Intel RealSense** (§9) | Sees obstacles the LiDAR plane misses |
| ROS distro on the robot | **Unknown — check in the lab** (§14) | `bots/acrux` targets Humble but the config looks older |
| Lights / extras | Later | Out of scope for v1 (§15) |

---

## 2. The idea in plain words

Think of a waiter with a list of tables. The waiter already knows how to walk around the room
without bumping into people (that is **Nav2**, which Acrux already has). We only write the
**list of tables and the rules for moving on** — a small "mission" program.

- The robot is never asked to *guess* how many guests there are. You tell it: `--count 3`.
- We always survey **4 spots**. With 3 guests the robot just ignores the 4th.
- At every guest the robot **stops and waits**. It only moves when you say so.

---

## 3. What runs where

```
 LAPTOP (Wi-Fi, same ROS_DOMAIN_ID)              ACRUX (on-board computer)
 ┌───────────────────────────────────┐          ┌─────────────────────────────────────────┐
 │ mission_node.py                    │  Nav2    │ Nav2: planner, controller, costmaps      │
 │  - reads guests.yaml               │  action  │ AMCL / localization (see §8)             │
 │  - you type y / s / r / p / h / q  │ ───────► │ LiDAR /scan   RealSense /camera/points   │
 │  - sends "go to pose" goals        │ NavigateTo│                                          │
 │ RViz (watch the map + robot)       │  Pose    │ collision_monitor  ◄── last-line safety  │
 └───────────────────────────────────┘          │   cmd_vel → [stop / slow] → base → wheels │
                                                 └─────────────────────────────────────────┘
```

Why split it this way:

- **The laptop is only the brain.** If Wi-Fi drops, the robot's own Nav2 finishes/stops safely
  and the **collision monitor, running on the robot, keeps protecting people**.
- **`mission_node.py` must be started directly in a terminal**, not with `ros2 launch`
  (`launch` does not forward your keyboard).
- Laptop needs ROS 2 **of the same distro as the robot** plus
  `ros-<distro>-nav2-simple-commander`. Plain Windows is not supported; use Ubuntu, a Docker
  host-network container, or WSL2 with **mirrored networking** (WSL2's default NAT blocks the
  multicast DDS needs — you will see an empty `ros2 topic list`).

---

## 4. The three stages

### Stage A — before the event (once)

1. Bring Acrux up and **make a map** of the lab (§10).
2. **Survey** the home position and the 4 guest spots as map coordinates (§10).
3. Put them in `guests.yaml`, set `surveyed: true`.
4. Test the camera (§9) and the safety layer (§7).
5. Rehearse with cardboard "guests" (§12).

### Stage B — just before the event

1. Power on Acrux, bring up the stack, confirm localization (§8, §11).
2. Count the guests. Start the mission with that number:
   `python3 mission_node.py --count 3`.

### Stage C — during the event (what the program does)

```
IDLE ─ you press y ─► NAVIGATING (guest 1) ─ arrived ─► AT_GUEST  (STOPS, waits)
                         ▲                                   │ you press y (gift taken)
                         └───────── more guests? ◄───────────┘
                                          │ no
                                          ▼
                                   RETURNING_HOME ─ arrived ─► DONE
```

Nothing moves by itself: **first `y` starts the run, every later `y` releases the robot from
a guest.**

---

## 5. The state machine (`mission.py`)

| State | Meaning | Leaves when |
|---|---|---|
| `IDLE` | Ready, not moving | `y` → `NAVIGATING` |
| `NAVIGATING` | Driving to a guest | Arrives → `AT_GUEST`; fails → retry, then `BLOCKED` |
| `AT_GUEST` | Stopped in front of guest, waiting | `y` → next guest (or `RETURNING_HOME` if none left) |
| `PAUSED` | Operator paused; goal cancelled | `p` → resumes same target |
| `BLOCKED` | Navigation failed after auto-retry | `r` retry / `s` skip / `h` home |
| `RETURNING_HOME` | Driving to the home pose | Arrives → `DONE` |
| `DONE` / `ABORTED` | Finished / operator quit | — |

Design choices worth knowing (all covered by `tests/test_mission.py`):

- **The logic has no ROS in it.** `mission.py` takes events (commands, Nav2 results) and returns
  actions (navigate, cancel, print). `mission_node.py` carries the actions out. That is why the
  logic can be tested on any PC.
- **Failed goal → one automatic retry**, then `BLOCKED`: the robot stops and *asks you*. It never
  silently gives up and never loops forever.
- **Stale Nav2 results are ignored** (e.g. a "cancelled" notice arriving after you paused).
- **"n"/"no" are not commands** — they must never be mistaken for "yes".

---

## 6. Live commands

Type in the terminal running `mission_node.py` (Enter alone = yes), **or** publish to
`/greeter/command` (`std_msgs/String`) from anywhere — handy for a joystick button or a tiny
GUI later:

```bash
ros2 topic pub --once /greeter/command std_msgs/msg/String "{data: 'y'}"
```

| Type | Command | Effect |
|---|---|---|
| `y` / Enter | next | Start, or release the robot from the current guest |
| `s` | skip | Driving/blocked: give up this guest, go to the next. Waiting at a guest: drop the *next* guest without visiting |
| `r` | retry | Blocked/paused: send the same goal again |
| `p` | pause / resume | Cancel the goal and stand still; press again to continue to the same target |
| `h` | home | Cancel, drop all remaining guests, drive home |
| `q` | quit | Cancel the goal and exit |
| `?` | status | State, target, who is left, visited, skipped |

---

## 7. Obstacles and safety (do not skip this section)

"Don't hit anything or anyone" is met with **layers**, because any one layer can fail:

| # | Layer | Where | What it does | Status |
|---|---|---|---|---|
| 1 | **Nav2 costmaps** | Robot | Obstacles from `/scan` (LiDAR) and `/camera/points` (RealSense) are painted into the costmap; the planner routes around them and re-plans live | Exists in `acrux_navigation/config/nav2_params.yaml` (inflation 0.55 m) |
| 2 | **Speed cap** | Robot | DWB `max_vel_x: 0.3` m/s | Exists |
| 3 | **Collision monitor** | Robot | A box in front of the robot: any LiDAR points inside the *stop* box force velocity to 0; inside the larger *slowdown* box speed ×0.3. Works even if the planner misbehaves | **New — this plan** (`config/collision_monitor.yaml`, `launch/safety.launch.py`); **not yet run** |
| 4 | **Operator** | Laptop | `p` pause, `h` home, `q` quit, plus Ctrl+C cancels the goal | **New** |
| 5 | **Physical e-stop / hand on the power** | Robot | Someone within reach of the robot at all times | Must be arranged |

### What happens if someone steps in front mid-drive

Layer 1 re-plans around them. If they get too close, layer 3 slows then stops the robot. If
Nav2 can't find a way, the goal fails → one auto-retry → `BLOCKED` → the robot **stands still
and asks you** (`r`, `s` or `h`).

### The three things you must verify before trusting layer 3

1. **Topic wiring.** The collision monitor must sit *between* Nav2's final velocity and the
   topic the base listens on. Acrux's README says the base takes `/cmd_vel`; whether Nav2
   publishes `/cmd_vel` directly or via `cmd_vel_nav` → velocity smoother → `cmd_vel_smoothed`
   → `/cmd_vel` depends on the Nav2 version and was **not confirmable from the source here**.
   On the robot, with Nav2 up:
   ```bash
   ros2 topic info /cmd_vel -v          # who publishes, who subscribes
   ros2 topic list | grep cmd_vel       # cmd_vel_nav? cmd_vel_smoothed?
   ```
   Then launch with the real names, and make sure **Nav2 no longer publishes straight to the
   topic the monitor writes**, or two nodes will fight over the wheels:
   ```bash
   ros2 launch ~/acrux_greeter/launch/safety.launch.py cmd_vel_in:=<nav2 output> cmd_vel_out:=cmd_vel
   ```
   Passing test: wave a cardboard box in front while teleoperating — the robot must stop even
   though you keep commanding forward.
2. **Frames.** The polygons are in `base_link` (what Acrux's costmaps use). Confirm with
   `ros2 run tf2_tools view_frames`.
3. **Scan topic.** Config reads `/scan`. Acrux can remap the LiDAR to `/lidar/scan` when
   `merge_scan:=True` (`autobringup.launch.py`) — then `/scan` is the merged one; check
   `ros2 topic hz /scan`.

### Known limits (be honest with yourself)

- A 2D LiDAR sees **one horizontal slice**. Table edges, chair seats, handbags and legs below
  or above that slice are invisible → that is why the RealSense test (§9) matters.
- The stop box is **front only.** A "stop" zone blocks *all* motion including reversing, so a
  full ring would trap the robot beside a guest. Rotating in place beside someone is covered by
  the costmap and by the operator, not the monitor.
- **Gifts/tray on top of the robot must not sit in the LiDAR plane or the camera view**, or the
  robot will treat its own cargo as an obstacle (or the monitor will freeze it). Check the
  scan in RViz with the gifts loaded.
- The guest standoff must be **≥ 0.8 m (robot centre to guest)** or the guest is inside the
  stop box at the goal. See the comment block in `guests.yaml`.
- Acrux is **~0.76 × 0.80 m**: leave wide lanes between guests (≈1.5 m or more); each guest is
  an obstacle with a 0.55 m inflation halo, and a goal inside that halo can be unreachable.

---

## 8. Localization — the part most likely to bite

For the robot to drive to *saved coordinates* it must know where it is **on the saved map**.
That is AMCL's job (or SLAM in localization mode).

**What the source shows** (`bots/acrux`, read for this plan):

- `autobringup.launch.py` with `exploration:=False map_file:=…` starts `map_server` and the
  Nav2 navigation launch, **but nothing in the repo launches the `amcl` node** (it only has an
  `amcl:` block in `nav2_params.yaml`).
- It *also* still starts `cartographer_node` in **mapping** mode (`lidar.lua` has no
  `pure_localization`), which publishes its own `map → odom`.

So "navigate on a saved map" in the shipped launch may mean *Cartographer builds a new map
starting from wherever the robot was switched on* — your surveyed coordinates would then be
**in a different map frame**. This is not certain from reading alone, so **verify on the robot
first** (§11 step 3):

```bash
ros2 node list | grep -i -E "amcl|cartographer|map_server"
ros2 run tf2_ros tf2_echo map odom            # who owns map -> odom?
```

Two ways forward — pick one in the lab and write the outcome in §14:

| Option | How | Trade-off |
|---|---|---|
| **A. AMCL on the saved map (recommended)** | Run `nav2_bringup`'s `localization_launch.py` (AMCL + `map_server`) with the saved `.yaml` and Acrux's `amcl` params; make sure Cartographer is **not** also publishing `map → odom` | Proper, repeatable, survives power cycles. Needs initial pose each run |
| **B. One continuous SLAM session** | Map, survey spots and run the event in the **same** Cartographer session without restarting | Works with the shipped launch; but one reboot or drift ruins the survey |

Give AMCL its starting point: place the robot on the **home marker**, then either use
RViz "2D Pose Estimate" or run `mission_node.py --set-initial-pose` (publishes the `home` pose).
If the pose is wrong, **everything** else is wrong — verify by watching the laser scan line up
with the map walls in RViz *before* pressing `y`.

---

## 9. Testing the Intel RealSense camera

Acrux's `autobringup.launch.py` has `realsense:=True` by default (D435i via
`acrux_firmware/launch/realsense_d435i.launch.py`) and both Nav2 costmaps read
`/camera/points`. Goal of the test: *does it see things the LiDAR can't, and do those show up
as obstacles?*

1. **Is it alive?** (robot)
   ```bash
   ros2 topic list | grep -i camera
   ros2 topic hz /camera/points            # should be a steady rate, not 0
   ```
   If missing: USB 3 port/cable, power, and `realsense:=True`.
2. **See it.** In RViz (laptop) add `PointCloud2` on `/camera/points`, fixed frame
   `base_link`. The cloud should sit in front of the robot, floor roughly at z ≈ 0.
3. **Does it catch what LiDAR misses?** Put a box on a chair seat / a table-edge overhang at
   a height *above or below* the LiDAR plane. LiDAR scan: nothing. Local costmap
   (`/local_costmap/costmap`): should show it.
4. **Is it fooled?** Floor reflections, sunlight, black/shiny surfaces and glass can produce
   holes or ghost obstacles. Drive past a window and a glossy floor; the costmap must not
   fill with phantom walls that block the route.
5. **Load/latency.** Note CPU use (`top`) and whether `/scan` rate drops with the camera on.
6. **Decide:** if the cloud is stable and sensible, enable the commented `realsense` source
   in `config/collision_monitor.yaml`; if not, run with `realsense:=False` and rely on LiDAR +
   the operator (and say so in the log).

Record your results in the §14 table.

---

## 10. Making the map and surveying the spots

**Make the map** (robot on, laptop for RViz/teleop; commands from `bots/acrux/README.md`):

```bash
# robot — SLAM mode
ros2 launch acrux_bringup autobringup.launch.py exploration:=True
# laptop — drive slowly around the whole area, including along the guest spots
ros2 run teleop_twist_keyboard teleop_twist_keyboard
# save when the map looks complete (robot)
ros2 run nav2_map_server map_saver_cli -f ~/maps/lab
#   (Acrux also ships: ros2 launch acrux_navigation map_saver.launch.py map_file_path:=...)
```

Tips: move slowly, close loops (come back to the start), keep people out of the room while
mapping, and map **with the furniture where it will be on the day**. Copy the `.yaml`/`.pgm`
off the robot with `scp` — do **not** commit them (they're gitignored).

**Survey the spots** (map must be loaded and localized):

1. Mark the 4 guest spots and the home spot on the floor with tape.
2. For each: drive the robot there by hand, facing the guest direction, and read the pose:
   ```bash
   ros2 topic echo /amcl_pose --once        # x, y, and orientation quaternion
   ```
   Or, in RViz, click **2D Goal Pose** on the spot and `ros2 topic echo /goal_pose --once`.
3. Convert the quaternion to yaw (`yaw = 2·atan2(z, w)` for a flat robot) or just read the
   heading you set in RViz.
4. Type the numbers into `guests.yaml` (**centre of robot**, ≥ 0.8 m from the guest's feet).
5. Set `surveyed: true`. Re-survey if the map is ever rebuilt.

---

## 11. Event-day runbook

**Before guests arrive**

| # | Step | Where | Check |
|---|---|---|---|
| 1 | Same Wi-Fi; `export ROS_DOMAIN_ID=<n>` in **every** terminal | both | `ros2 topic list` on the laptop shows the robot's topics |
| 2 | Bring up Acrux on the **saved map** (§8 option A or B) | robot | RViz shows the map |
| 3 | Check who owns `map → odom`; robot parked on **home marker**; set initial pose | robot/laptop | Scan lines up with the walls |
| 4 | Start safety layer: `ros2 launch …/safety.launch.py cmd_vel_in:=… cmd_vel_out:=…` | robot | Box-in-front test stops the robot (§7) |
| 5 | Load the gifts; confirm they are **not** in the scan/camera view | robot | RViz scan is clean |
| 6 | Speed capped ≤ 0.3 m/s; **someone within reach of the power/e-stop** | — | — |
| 7 | One dry run with cardboard guests | — | Visits every spot and returns |

**Go time**

```bash
# laptop, in the folder with mission_node.py
source /opt/ros/<distro>/setup.bash
export ROS_DOMAIN_ID=<n>
python3 mission_node.py --count 3      # the number of guests TODAY
```

Then: `y` → robot goes to guest 1 → it stops → guest takes the gift → you press `y` → next…
After the last `y` it drives home and the program reports `DONE`.

**If it goes wrong:** `p` (pause) → think → `p` (resume) or `h` (home). Anything alarming:
**hit the e-stop first, then use the terminal.**

---

## 12. Testing ladder (cheap → real)

| Rung | What | Proves |
|---|---|---|
| 0 | `pytest` in `practice/acrux_greeter/` (done — 60 tests) | State machine and config logic |
| 1 | Gazebo: `ros2 launch acrux_gazebo spawn_robot.launch.py` + Nav2, run with `--sim --allow-unsurveyed` and sim-map coordinates | Node ↔ Nav2 wiring, command handling |
| 2 | Real robot, wheels **lifted**, command a goal | Messages flow, nothing crashes |
| 3 | Real robot, empty room, 1 spot | Localization + arrival accuracy |
| 4 | Cardboard guests at all 4 spots; throw a box into the path | Avoidance + collision monitor + `BLOCKED` flow |
| 5 | Full dress rehearsal with real people who know it's a test, 3 and 4 guests | Timing, standoff, operator handover |

---

## 13. Risks and fixes

| Risk | Symptom | Fix |
|---|---|---|
| Localization wrong (§8) | Drives to the wrong place / into walls | Verify scan-vs-map before `y`; re-set initial pose |
| Monitor wired wrong | Robot ignores it, or two nodes fight → jerky | `ros2 topic info -v`; test with a box |
| Guest inside stop box at goal | Robot stops short and won't move | Standoff ≥ 0.8 m; re-survey |
| Goal inside inflation halo | "Goal failed"/`BLOCKED` at a spot | Move the spot back / widen lane; check `inflation_radius` |
| Gifts seen as obstacles | Robot refuses to move, phantom obstacle in front | Re-position tray; check scan/costmap |
| Wi-Fi dropout | Laptop loses robot | Robot's Nav2 + monitor still protect; reconnect; `?` for status |
| Wrong `ROS_DOMAIN_ID` / WSL2 NAT | Empty `ros2 topic list` | Same ID in every terminal; mirrored networking / native Linux |
| Map out of date (furniture moved) | AMCL jumps, plans fail | Re-map the day before; same furniture on the day |
| Battery | Brown-outs, odd motion | Full charge; check before the event |

---

## 14. Open items — not verified, check in the lab

Fill the right-hand column in and keep this section honest; it is the real status of the plan.

| # | Open item | How to check | Result |
|---|---|---|---|
| 1 | **ROS distro on Acrux** (repo says Humble; its `nav2_params.yaml` uses Galactic-era `nav2_recoveries` names) | `printenv ROS_DISTRO`; `ros2 pkg list \| grep nav2` | |
| 2 | **Is AMCL launched at all** when `exploration:=False`? Who owns `map → odom`? (§8) | `ros2 node list`; `tf2_echo map odom` | |
| 3 | **Real `cmd_vel` chain** (Nav2 → ? → base) (§7) | `ros2 topic info /cmd_vel -v` | |
| 4 | `nav2_collision_monitor` installed on the robot? Humble param names correct (`max_points`)? | `ros2 pkg list \| grep collision`; node log on start | |
| 5 | RealSense usable? Stable cloud? CPU cost? (§9) | §9 steps | |
| 6 | Laptop OS / ROS install (native Ubuntu? WSL2?) and `nav2_simple_commander` present | `python3 -c "import nav2_simple_commander"` | |
| 7 | Real guest spots, home, lane widths, floor markers | §10 | |
| 8 | Is the LiDAR mounted so the gifts don't intrude on its plane? | RViz scan with gifts loaded | |
| 9 | Does `nav2_simple_commander`'s `goToPose`/`cancelTask` behave as `mission_node.py` assumes on this version? | Gazebo rung 1 | |

---

## 15. Later (not in v1)

- **Lights**: status LEDs via the existing firmware/`hubble_scripts` path (idle / driving /
  arrived / blocked). Natural hook: `Driver.execute()` already sees every `Message` and state
  change.
- **Auto guest detection** (camera/LiDAR leg clustering) to *suggest* the count or skip empty
  spots. Optional; the manual `--count` stays the reliable path.
- **Joystick "next" button** publishing to `/greeter/command` — no node changes needed.
- **Gift-taken sensing** (weight / button) instead of the operator's `y`.

---

## 16. Viva-style questions this plan lets you answer

1. *Why is the mission logic separate from the ROS node?* Testable without a robot; the node
   is a thin adapter. (§5)
2. *How does the robot handle 3 vs 4 guests?* Always 4 surveyed slots; `--count N` uses the
   first N. (§2)
3. *Why stop and wait for a command instead of a timer?* A human confirms the gift was taken;
   a timer would drive off while the guest is mid-pickup. (§1, §6)
4. *What stops it hitting a person?* Four layers: costmap re-planning, speed cap, the
   collision monitor on the robot, and the operator/e-stop — and which layer covers which
   failure. (§7)
5. *Why run the safety layer on the robot, not the laptop?* Wi-Fi can drop. (§3)
6. *Why can a 2D LiDAR miss a table?* It sees a single slice; that is why we test the depth
   camera. (§7, §9)
7. *What is the most likely thing to go wrong, and how do you detect it?* Localization on the
   saved map; check the scan against the walls in RViz. (§8)

---

## Sources

- `bots/acrux/acrux_navigation/config/nav2_params.yaml` — footprint, inflation 0.55, DWB
  `max_vel_x: 0.3`, `/scan` + `/camera/points` sources, AMCL block.
- `bots/acrux/acrux_bringup/launch/autobringup.launch.py` — `exploration`, `map_file`,
  `realsense`, `merge_scan` arguments; no AMCL launch.
- `bots/acrux/acrux_slam/launch/cartographer.launch.py`, `config/lidar.lua` — mapping mode,
  `provide_odom_frame`.
- `bots/acrux/acrux_navigation/launch/navigation.launch.py` — `map_server` + Nav2 navigation.
- `bots/acrux/README.md` — `/cmd_vel`, run commands.
- Nav2 docs: *Collision Monitor* (`nav2_collision_monitor`), *Simple Commander API*
  (`nav2_simple_commander`); see [`../foundations/03-official-docs-index.md`](../foundations/03-official-docs-index.md).
  Parameter names and defaults were written from memory of the Humble docs and are listed as
  unverified in §14.
