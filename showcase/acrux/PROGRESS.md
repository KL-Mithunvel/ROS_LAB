# Acrux showcase capture: progress (2026-11-02)

Goal: record video + screenshots of the Acrux waypoint mission for the portfolio site.

## Done
- Built `acrux_description`, `acrux_gazebo`, `acrux_navigation` in a scratch workspace; Gazebo
  sim ran (room2 world, `/scan`, camera). Sim-only fixes needed (not applied to the repo):
  - `acrux.gazebo`: `publish_odom` / `publish_odom_tf` are `false`, so Nav2 had no odom in sim.
  - `nav2_params.yaml`: AMCL `base_frame_id: base_footprint` does not exist (URDF uses `base_link`);
    `robot_model_type: differential` must be `nav2_amcl::DifferentialMotionModel` on Humble.
- Switched to the real robot (192.168.0.110, SSH key works). Sim shut down.
- `sensor-test.sh preflight` clean; drivers started and checked:
  camera colour/depth/points ~14.5 Hz PASS, LiDAR content PASS, `/scan` measured 11.5 Hz,
  motor bridge up (battery, wheel ticks, cmd_vel present).
  The script's `/scan` rate check reports "NO DATA" (probably QoS best-effort), not a real fault.
- Screen capture that works on this Wayland laptop: GStreamer
  `ximagesrc xid=<window id>` (root capture is black; find ids with `xwininfo -root -tree`).
  No ffmpeg installed; `vp8enc` + `webmmux` are available for video.

## Not done
- No robot movement, no mapping, no mission run, no video/screenshots of Acrux yet.
- Drivers may still be running on the robot (stopping them needs the robot sudo password):
  `waypoint_mission/tools/sensor-test.sh stop`.
- Still needed: map of the real room (or a saved map), home + 3-4 waypoint positions,
  then `mission_node.py --count N` via the GUI. Mission code has never run on the robot before.
