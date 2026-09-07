# 07 — Localization and SLAM

Layers 4–5 (`03` §7–8). The theory — what an EKF does, how a particle filter works, how
SLAM Toolbox's pose graph and loop closure work, Cartographer's submaps — is written out
with real config values in **`01-three-bots-architecture.md` §5.1–5.2**. Read that first.

This file is the **builder's** view: which config knobs matter for a new robot, the frame
rules that must hold across every YAML, and the failure modes and how to read them.

---

## 1. Two questions, two TF edges

| Question | Answer | TF edge | Character |
|---|---|---|---|
| "How have I moved since startup?" | wheel + IMU odometry, fused | `odom → base_link` | smooth, high-rate, **drifts** |
| "Where am I on this map?" | scan matched against a map | `map → odom` | accurate, **jumps** on correction |

`odom → base_link` comes from `robot_localization` (§3). `map → odom` comes from **either**
`slam_toolbox` (while mapping, §6) **or** `nav2_amcl` (while navigating a saved map, §5) —
never both at once.

---

## 2. Odometry sources

| Source | Gives | Notes |
|---|---|---|
| Wheel encoders | x, y, yaw (integrated), vx, vyaw | drifts on slip; skid-steer yaw is unreliable |
| IMU | orientation, angular velocity, linear accel | great for yaw *rate*; accel too noisy to integrate to position |
| Visual/RGB-D odometry (`rtabmap`, `vslam`) | full 6-DOF pose | needs texture/features; heavier compute |
| GPS / GNSS | absolute lat/lon → x, y (with `navsat_transform`) | outdoor only; fuse in a *second* EKF (§3) |
| Wheel + IMU (the common indoor combo) | trust wheels for translation, IMU for rotation | BeetleBot / Acrux default |

---

## 3. `robot_localization` EKF

One `ekf_node`, one `ekf.yaml`. It fuses any number of `odom*`, `imu*`, `pose*`, `twist*`
inputs into `/odometry/filtered` + the `odom → base_link` TF.

```yaml
ekf_filter_node:
  ros__parameters:
    frequency: 30.0
    two_d_mode: true                 # planar robot: zero out z, roll, pitch
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom                # <-- this EKF outputs odom->base_link
    publish_tf: true

    odom0: /diff_drive_controller/odom
    odom0_config: [false, false, false,     # x, y, z
                   false, false, false,     # roll, pitch, yaw
                   true,  true,  false,     # vx, vy, vz   <- trust wheel *velocity*
                   false, false, true,      # vroll, vpitch, vyaw
                   false, false, false]     # ax, ay, az
    odom0_differential: false

    imu0: /imu/data
    imu0_config: [false, false, false,
                  false, false, false,
                  false, false, false,
                  false, false, true,       # vyaw   <- trust IMU yaw rate
                  true,  false, false]       # ax     (optional)
    imu0_differential: false
    imu0_remove_gravitational_acceleration: true
```

The `*_config` matrix is the whole game: **which fields of each sensor to fuse.** Classic
setup — wheels for `vx`, IMU for `vyaw`. Fusing absolute `yaw` from two sources fights;
fusing wheel `yaw` on a skid-steer poisons the estimate (this is the Acrux "IMU config all
false" bug — `01` §3/§5.1: only wheel odom fused, so it drifts on turns).

Other knobs: `process_noise_covariance` (higher = trust the model less, react to
measurements more), `*_differential` (integrate pose deltas instead of absolute — use for a
second source of the same quantity to avoid conflicts).

**GPS / outdoor:** run **two** EKFs — one `world_frame: odom` (local, continuous), one
`world_frame: map` (global, GPS-corrected) — plus `navsat_transform_node`. `robot_localization`
docs cover the dual-EKF pattern.

### IMU prep

Raw IMUs give angular velocity + accel but not always fused orientation. Add
`imu_filter_madgwick` (or `imu_complementary_filter`) to produce `/imu/data` with a valid
`orientation`. IMU frame axes must follow **REP-145** (x forward, y left, z up); a rotated
mount needs a static transform or the driver's frame param set right.

---

## 4. `nav2_amcl` (localize on a saved map)

```yaml
amcl:
  ros__parameters:
    base_frame_id: base_link
    odom_frame_id: odom
    global_frame_id: map
    scan_topic: scan
    min_particles: 500
    max_particles: 2000
    laser_model_type: likelihood_field
    max_beams: 60
    update_min_d: 0.2            # metres of motion before re-weighting
    update_min_a: 0.2            # radians
    robot_model_type: nav2_amcl::DifferentialMotionModel   # or OmniMotionModel
    alpha1..alpha5: 0.2         # odometry noise model — raise if odom is rough
    set_initial_pose: false     # true + initial_pose:{x,y,yaw} to skip the RViz step
```

Tuning: raise `alpha*` if the robot's odometry is noisy (AMCL will trust the scan more);
raise `min/max_particles` if it gets lost in symmetric spaces; `update_min_d/a` trades CPU
for responsiveness. If AMCL "jumps," the map or the scan-to-map alignment is off.

---

## 5. SLAM Toolbox (build the map)

```yaml
slam_toolbox:
  ros__parameters:
    mode: mapping
    odom_frame: odom
    map_frame: map
    base_frame: base_link
    scan_topic: /scan
    resolution: 0.05
    minimum_travel_distance: 0.15      # only update the map after this much motion
    minimum_travel_heading: 0.35
    do_loop_closing: true
    loop_search_maximum_distance: 3.0
```

- **`async_slam_toolbox_node`** (online async) — default; keeps up in real time, drops scans
  if it must. Use this on a robot.
- **`sync_slam_toolbox_node`** — processes every scan; use offline against a bag for the
  best possible map.
- Save: `ros2 run nav2_map_server map_saver_cli -f maps/my_map` → `.pgm` + `.yaml` for AMCL.
  SLAM Toolbox can *also* serialize its pose graph (`.posegraph` + `.data`) so you can
  **resume mapping later** or run its own localization mode.

**Localization without AMCL:** `mode: localization` + `map_file_name:` loads the serialized
graph and does scan-match localization (often smoother than AMCL). Either works with Nav2;
AMCL is the more common default.

### Cartographer (alternative)

Use when SLAM Toolbox struggles in large/loopy/feature-poor spaces, or you want tighter
IMU integration. Config is a `.lua` file (`01` §5.2 walks BeetleBot-vs-Acrux differences).
Same output contract: `/map` + `map → odom` TF.

---

## 6. The frame-consistency checklist

`map`, `odom`, `base_link` (or `base_footprint`) must be spelled **identically** across:

- the URDF (`build/04`)
- `controllers.yaml` (`odom_frame_id`, `base_frame_id`)
- `ekf.yaml` (`odom_frame`, `base_link_frame`, `world_frame`)
- `amcl` params (`odom_frame_id`, `base_frame_id`, `global_frame_id`)
- `slam_toolbox` params (`odom_frame`, `map_frame`, `base_frame`)
- `nav2_params.yaml` costmaps (`global_frame`, `robot_base_frame`)

One mismatch (`base_link` vs `base_footprint`) and TF silently won't connect the two halves
of the tree. `ros2 run tf2_tools view_frames` after bringup — the tree must be one piece.

---

## 7. Tuning workflow and failure modes

Fix bottom-up — never tune AMCL/Nav2 while odometry is wrong.

1. **Odometry alone** (`build/06` §7): drive a measured square, `/odom` should roughly
   return to origin. Off by a scale factor → wheel geometry. Yaw way off → you're fusing
   wheel yaw on a skid-steer; use IMU.
2. **EKF**: `/odometry/filtered` should be smoother than `/odom` and not lag. Drift on turns
   → IMU not actually fused (check the `imu0_config` yaw-rate slot) or IMU frame wrong.
3. **SLAM**: drive slowly; the map should not smear or double walls. Smearing → odometry too
   rough for the scan-match window; double walls on return → loop closure not triggering
   (raise `loop_search_maximum_distance`).
4. **AMCL**: particle cloud should converge after a short drive and track the robot. Jumping
   → map/scan mismatch or `alpha*` too low. Lost in a corridor → more particles.

| Log message | Meaning | Fix |
|---|---|---|
| `Message Filter dropping message ... for reason 'discarding message because the queue is full'` | TF for the scan's stamp not available in time | check `use_sim_time`, EKF publishing, frame names |
| `lookup would require extrapolation into the future` | asked for a transform newer than latest | use `Time()` (latest), or a small wait; check clocks |
| `Timed out waiting for transform from base_link to map` | the `map→odom` or `odom→base_link` edge is missing | `view_frames`; is SLAM/AMCL up and active? |
| AMCL pose snaps across the room | global localization picked a wrong symmetric hypothesis | set an initial pose (RViz "2D Pose Estimate") |
| Map drifts/rotates slowly while mapping | odometry yaw drift, no loop closure yet | slow down, revisit start, check IMU fusion |

---

## 8. Verifying

```bash
ros2 topic echo /odometry/filtered --once          # EKF output exists
ros2 run tf2_ros tf2_echo map base_link            # full chain resolves
ros2 topic hz /map                                  # SLAM publishing
ros2 lifecycle get /amcl                            # active (navigation mode)
# RViz: Map on /map, LaserScan on /scan (Fixed Frame: map) — scan should sit ON the walls
```

---

Next: `08-navigation-and-path-planning.md`.
