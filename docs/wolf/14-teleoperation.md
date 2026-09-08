# Teleoperation

Install joystick package on dev machine

```bash
sudo apt update
sudo apt install joystick jstest-gtk evtest
sudo apt install libcanberra-gtk-module libcanberra-gtk3-module -y
```

Once the libraries are installed, use evtest and jstest-gtk to check if all the buttons in the joystick are working. If yes, linux is detecting the joystick

To check if ROS2 is detecting the joystick, type:

```
ros2 run joy joy_enumerate_devices #Shows device ID. if this is not 0(zero), change it accordingly in joystick.yaml file
```

Now to connect joystick to ROS2, type

```
ros2 run joy joy_node
```

The above command creates topics for joystick. Check the topics using `ros2 topic list`. To see the values of joystick, type:

```
ros2 topic echo /joy  # to see axis and button values
ros2 param list # to see details about the joystick (parameters)
```

Now that everything seems working, we will launch our joystick launch file:

```
ros2 launch wolf-robot joystick.launch.py
ros2 param list # to see details about the joystick (parameters)
ros2 topic echo /diff_cont/cmd_vel_unstamped
# Pressing enable buttons (6 and 7) will activate joystick. Added as a safety feature, but can be disabled in joystick.yaml
```
