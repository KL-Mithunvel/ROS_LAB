#!/usr/bin/env python3
"""Generate the Gazebo warehouse world AND the matching Nav2 occupancy map from one list of obstacles.

    python3 gen_world.py            # writes worlds/warehouse.world, maps/warehouse.pgm, maps/warehouse.yaml

World frame == map frame. The warehouse floor is x 0..12, y 0..9 metres; the patrol zone grid in
zones_gz.yaml is 4 columns x 3 rows of 3 m cells over exactly that floor. The east wall has a 1 m door
(y 4..5) the intruder walks through.
"""
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
W, H = 12.0, 9.0
T = 0.2                                   # wall thickness
RES = 0.05                                # map resolution, m/pixel
MARGIN = 1.0

# (name, cx, cy, sx, sy, height, rgb)  axis-aligned boxes
WALL = (0.55, 0.57, 0.60)
BOXES = [
    ("wall_south", W / 2, -T / 2, W + 2 * T, T, 2.5, WALL),
    ("wall_north", W / 2, H + T / 2, W + 2 * T, T, 2.5, WALL),
    ("wall_west", -T / 2, H / 2, T, H, 2.5, WALL),
    ("wall_east_a", W + T / 2, 2.0 - T / 2, T, 4.0 + T, 2.5, WALL),       # y -0.2 .. 4.0
    ("wall_east_b", W + T / 2, 7.0 + T / 2, T, 4.0 + T, 2.5, WALL),       # y 5.0 .. 9.2
    ("rack_s1", 3.0, 3.0, 3.0, 0.6, 2.0, (0.85, 0.40, 0.10)),
    ("rack_s2", 9.0, 3.0, 3.0, 0.6, 2.0, (0.85, 0.40, 0.10)),
    ("rack_n1", 6.0, 6.0, 3.0, 0.6, 2.0, (0.10, 0.35, 0.70)),
    ("rack_n2", 10.5, 6.0, 3.0, 0.6, 2.0, (0.10, 0.35, 0.70)),
    ("crate_1", 6.0, 0.7, 0.8, 0.8, 0.8, (0.62, 0.45, 0.25)),
    ("crate_2", 11.3, 1.0, 0.8, 0.8, 0.8, (0.62, 0.45, 0.25)),
    ("crate_3", 0.7, 8.3, 0.8, 0.8, 0.8, (0.62, 0.45, 0.25)),
    ("crate_4", 6.0, 8.3, 0.8, 0.8, 1.2, (0.62, 0.45, 0.25)),
]
# (name, cx, cy, radius, height, rgb)
CYLS = [
    ("barrel_1", 3.4, 8.3, 0.3, 0.9, (0.15, 0.45, 0.25)),
    ("barrel_2", 3.9, 8.3, 0.3, 0.9, (0.15, 0.45, 0.25)),
]
INTRUDER_HOME = (13.8, 4.5)               # parked outside the door, out of every LiDAR line of sight


def box_sdf(name, cx, cy, sx, sy, h, rgb, static=True):
    r, g, b = rgb
    return f"""    <model name="{name}"><static>true</static><pose>{cx} {cy} {h/2} 0 0 0</pose>
      <link name="l"><collision name="c"><geometry><box><size>{sx} {sy} {h}</size></box></geometry></collision>
      <visual name="v"><geometry><box><size>{sx} {sy} {h}</size></box></geometry>
        <material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material></visual></link></model>"""


def cyl_sdf(name, cx, cy, rad, h, rgb):
    r, g, b = rgb
    return f"""    <model name="{name}"><static>true</static><pose>{cx} {cy} {h/2} 0 0 0</pose>
      <link name="l"><collision name="c"><geometry><cylinder><radius>{rad}</radius><length>{h}</length></cylinder></geometry></collision>
      <visual name="v"><geometry><cylinder><radius>{rad}</radius><length>{h}</length></cylinder></geometry>
        <material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material></visual></link></model>"""


def floor_mark(name, cx, cy, sx, sy, rgba):
    r, g, b, a = rgba
    return f"""    <model name="{name}"><static>true</static><pose>{cx} {cy} 0.004 0 0 0</pose>
      <link name="l"><visual name="v"><geometry><box><size>{sx} {sy} 0.008</size></box></geometry>
        <material><ambient>{r} {g} {b} {a}</ambient><diffuse>{r} {g} {b} {a}</diffuse></material></visual></link></model>"""


def world_sdf():
    parts = [box_sdf(*b) for b in BOXES] + [cyl_sdf(*c) for c in CYLS]
    marks = [floor_mark("floor", W / 2, H / 2, W, H, (0.72, 0.72, 0.70, 1)),
             floor_mark("dock_zone", 1.5, 1.5, 2.9, 2.9, (0.95, 0.80, 0.15, 1))]
    for i, x in enumerate((3.0, 6.0, 9.0)):
        marks.append(floor_mark(f"gridline_x{i}", x, H / 2, 0.04, H, (0.35, 0.38, 0.40, 1)))
    for i, y in enumerate((3.0, 6.0)):
        marks.append(floor_mark(f"gridline_y{i}", W / 2, y, W, 0.04, (0.35, 0.38, 0.40, 1)))
    ix, iy = INTRUDER_HOME
    intruder = f"""    <model name="intruder"><pose>{ix} {iy} 0.85 0 0 3.14159</pose>
      <link name="l"><gravity>false</gravity>
        <inertial><mass>10</mass><inertia><ixx>1</ixx><iyy>1</iyy><izz>1</izz></inertia></inertial>
        <collision name="c"><geometry><box><size>0.4 0.4 1.7</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>0.4 0.4 1.7</size></box></geometry>
          <material><ambient>0.95 0.15 0.10 1</ambient><diffuse>0.95 0.15 0.10 1</diffuse></material></visual></link></model>"""
    return f"""<?xml version="1.0"?>
<sdf version="1.6">
  <world name="warehouse">
    <gui><camera name="user_camera"><pose>6 -4.2 13.5 0 1.0 1.5708</pose><view_controller>orbit</view_controller></camera></gui>
    <physics type="ode"><max_step_size>0.004</max_step_size><real_time_update_rate>250</real_time_update_rate></physics>
    <plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so"><ros><namespace>/</namespace></ros><update_rate>10</update_rate></plugin>
    <include><uri>model://sun</uri></include>
    <light name="lamp_a" type="point"><pose>3 4.5 6 0 0 0</pose><diffuse>0.7 0.7 0.65 1</diffuse><attenuation><range>20</range><constant>0.6</constant><linear>0.02</linear><quadratic>0.002</quadratic></attenuation><cast_shadows>false</cast_shadows></light>
    <light name="lamp_b" type="point"><pose>9 4.5 6 0 0 0</pose><diffuse>0.7 0.7 0.65 1</diffuse><attenuation><range>20</range><constant>0.6</constant><linear>0.02</linear><quadratic>0.002</quadratic></attenuation><cast_shadows>false</cast_shadows></light>
    <model name="ground"><static>true</static><link name="l">
      <collision name="c"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>
        <surface><friction><ode><mu>1.0</mu><mu2>1.0</mu2></ode></friction></surface></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal><size>60 60</size></plane></geometry>
        <material><ambient>0.25 0.26 0.27 1</ambient><diffuse>0.25 0.26 0.27 1</diffuse></material></visual></link></model>
{chr(10).join(marks)}
{chr(10).join(parts)}
{intruder}
    <!-- virtual camera above the south wall looking over the whole floor: /overview/image_raw (for recordings that
         do not depend on the Gazebo window being visible) -->
    <model name="overview_cam"><static>true</static><pose>6 -3.2 10.5 0 0.95 1.5708</pose>
      <link name="l"><sensor name="cam" type="camera"><always_on>true</always_on><update_rate>10</update_rate>
        <camera><horizontal_fov>1.15</horizontal_fov><image><width>1280</width><height>720</height><format>R8G8B8</format></image><clip><near>0.1</near><far>60</far></clip></camera>
        <plugin name="overview_plugin" filename="libgazebo_ros_camera.so"><camera_name>overview</camera_name><frame_name>overview_cam</frame_name></plugin>
      </sensor></link></model>
  </world>
</sdf>
"""


def raster_map():
    x0, y0 = -MARGIN, -MARGIN
    w = int(round((W + 2 * MARGIN) / RES)); h = int(round((H + 2 * MARGIN) / RES))
    xs = x0 + (np.arange(w) + 0.5) * RES
    ys = y0 + (np.arange(h) + 0.5) * RES
    X, Y = np.meshgrid(xs, ys)                      # row index = y (bottom-up)
    img = np.full((h, w), 205, np.uint8)            # unknown outside
    img[(X > 0) & (X < W) & (Y > 0) & (Y < H)] = 254
    for _, cx, cy, sx, sy, *_ in BOXES:
        img[(abs(X - cx) <= sx / 2) & (abs(Y - cy) <= sy / 2)] = 0
    for _, cx, cy, r, *_ in CYLS:
        img[(X - cx) ** 2 + (Y - cy) ** 2 <= r * r] = 0
    # the wall ring is "known occupied"; paint a 1-px-thick halo of unknown outside it as-is
    return np.flipud(img), (x0, y0)                 # PGM row 0 is the top


def main():
    (HERE / "worlds").mkdir(exist_ok=True); (HERE / "maps").mkdir(exist_ok=True)
    (HERE / "worlds" / "warehouse.world").write_text(world_sdf())
    img, (x0, y0) = raster_map()
    with open(HERE / "maps" / "warehouse.pgm", "wb") as f:
        f.write(b"P5\n# generated by gen_world.py\n%d %d\n255\n" % (img.shape[1], img.shape[0])); f.write(img.tobytes())
    (HERE / "maps" / "warehouse.yaml").write_text(
        f"image: warehouse.pgm\nresolution: {RES}\norigin: [{x0}, {y0}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n")
    print("wrote worlds/warehouse.world and maps/warehouse.{pgm,yaml}", img.shape)


if __name__ == "__main__":
    main()
