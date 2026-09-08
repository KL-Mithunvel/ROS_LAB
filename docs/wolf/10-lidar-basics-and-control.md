# LiDAR Basics & Control

Active optical sensors such as 2D LiDAR's (Light Detection And Ranging) are used to perform scanning and detection of surfaces surrounding our robot. These electronic sensors emit light on the horizontal plane, usually the X-Y plane. Based on the captured reflected light, an accurate representation of the distance of the object is known.

Wolf uses RPLIDAR A1 which runs clockwise to perform a 360 degree omnidirectional laser range scanning for its surrounding environment and then generate an outline map for the environment.

### RPLIDAR A1 Specifications

| Key Parameters     | Value       |
| ------------------ | ----------- |
| Measuring Range    | 0.15m - 12m |
| Sampling Frequency | 8K          |
| Rotational Speed   | 5.5Hz       |
| Angular Resolution | ≤1°         |
| System Voltage     | 5V          |
| System Current     | 100mA       |
| Output             | UART Serial |

### LiDAR Data in Simulation

To simulate LiDar in Gazebo and Rviz, copy `wolf-robot` folder from`t5_lidar_interface` to workspace. Run Gazebo with our previous construction world:

```sh
ros2 launch wolf-robot launch_sim.launch.py world:=./src/wolf-robot/worlds/construction.world
```

Run Teleop Keyboard to control our simulated robot

```sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard # to control the robot
```

You can see the scanned data in Gazebo. Run rviz2 to see obstacle points on Rviz window

### LiDAR on a Real Robot

We need to install LiDAR package to communicate and control our LiDAR. Install the package `@robot` and *not* on the `@dev` machine.

```sh
sudo apt install ros-foxy-rplidar-ros
```

In the next terminal, run rplidar\_composition

```sh
ros2 run rplidar_ros rplidar_composition --ros-args -p serial_port:=/dev/ttyUSB1 -p frame_id:=laser_frame -p angle_compensate:=true -p scan_mode:=Standard #Upper case S
```

Since there are two devices connected to USB, it sometimes may clash and not respond. To assign a port for a sensor:

```sh
ls /dev/serial # this shows by ID or by Path
ls /dev/serial/by-path # This gives the location of serial port connected. If we connect to same sensor to same port everytime, this is a better option.
```

Note down the path of LiDAR and update \<path> in command below.

```sh
ros2 run rplidar_ros rplidar_componsition --ros-args -p serial_port:=/dev//dev/serial/by-path/<path> -p frame_id:=laser_frame -p angle_compensate:=true -p scan_mode:=Standard
```

We can also find more details of the device if required. Connect USB device (only 1) to laptop and type as below

```bash
lsusb #this gives the list of devices connected
# If only one device is connected, we can easily consider as connected to ttyUSB0
# Register the device by typing:

~$ TTYDEVICE="ttyUSB0"
~$  sudo echo -e "$(udevadm info -a -n /dev/${TTYDEVICE} | grep ATTRS{idVendor}) \n$(udevadm info -a -n /dev/${TTYDEVICE} | grep ATTRS{idProduct}) \n$(udevadm info -a -n /dev/${TTYDEVICE} | grep ATTRS{serial}) \n"
    ATTRS{idVendor}=="10c4"
    ATTRS{idVendor}=="1d6b"
    ATTRS{idProduct}=="ea60"
    ATTRS{idProduct}=="0002"
    ATTRS{serial}=="0001"
    ATTRS{serial}=="0000:04:00.3"

# The result shown is for a Lidar connected to laptop. If I connect ESP32 board, then:
~$ sudo echo -e "$(udevadm info -a -n /dev/${TTYDEVICE} | grep ATTRS{idVendor}) \n$(udevadm info -a -n /dev/${TTYDEVICE} | grep ATTRS{idProduct}) \n$(udevadm info -a -n /dev/${TTYDEVICE} | grep ATTRS{serial}) \n"
    ATTRS{idVendor}=="10c4"
    ATTRS{idVendor}=="1d6b"
    ATTRS{idProduct}=="ea60"
    ATTRS{idProduct}=="0002"
    ATTRS{serial}=="c20ee93782abed1192f70a9aa7669f5d"
    ATTRS{serial}=="0000:04:00.3"

```

To start or stop the motor, type the following command on `@dev` machine to run service:

```sh
ros2 service call /start_motor std_srvs/srv/Empty {}    # to start the motor
ros2 service call /stop_motor std_srvs/srv/Empty {}    # to stop the motor
```

To check if rp\_lidar service (or any ROS 2 Services) are running, type:

```sh
ros2 service list # This provides a list of services being run
```

### Launch File

All the commands to run and control LiDAR is placed in a launch file. To launch LiDAR control, type the following on `@robot` machine:

```sh
ros2 launch wolf-robot rplidar.launch.py #check and add package name
```

Lastly, if in some cases the launch file terminal is stuck, open a new windows and type the following to kill the service:

```sh
killall rplidar_composition #Type this in a new window with ssh login
```
