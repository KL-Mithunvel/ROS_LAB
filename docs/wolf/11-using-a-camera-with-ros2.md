# Using a Camera with ROS2

Wolf comes with a Raspberry Pi Camera attached to the front of the robot. Just like previous tutorials, we will run a script to visalize the world in 3D using simulation tools and then implement the same using a real camera.

To start a camera interface, we need a camera driver node. The node communicates with whatever camera is attached to Wolf. That driver node then takes the data stream coming from the camera, and publishes it to a topic of type `sensor_msgs/Image`. Since images use a lot of data, we may also need to compress them before sending via network from one system to another.

### Simulating Camera in Gazebo

Copy`wolf-robot` folder from t6\_camera\_interface from your downloaded folder to source folder and compile. If you check the code in VSCode, you may observe that laser (LiDAR) is disabled. This is just to make sure we see the camera interface correctly.

Install drivers required to communicate with camera.

```sh
sudo apt install ros-foxy-image-transport-plugins
sudo apt install ros-foxy-rqt-image-view
sudo apt install ros-foxy-rmw-cyclonedds-cpp #hidden gem. Will avoid odom erros
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp #source this to check
```

Add `RMW_IMPLEMENTATION` to \~/.bashrc to source it on each new terminal.

```sh
sudo apt update
sudo apt upgrade -y # reboot if required
```

Run the below commands in different terminal windows to open gazebo and spawn our robot

```sh
ros2 launch wolf-robot launch_sim.launch.py world:=./src/wolf-robot/worlds/construction.world
ros2 run teleop_twist_keyboard teleop_twist_keyboard # to control the robot
rviz2
ros2 run rqt_image_view rqt_image_view
```

`rqt_image_view` is used to view images streamed from Image node. Once rviz is open, add interface for camera and image topics. Run the above command, refresh rqt\_image view and check if image is updating by driving the robot.

### Tips:

```sh
ros2 run image_transport list_transports
```

The above command provides a list of all different type of image format our system knows: Compressed, Compressed Depth, Raw and Theora

In some situations, we may need to compress images before sending it between systems.

```sh
ros2 run image_transport republish compressed raw --ros-args -r in/compresed:=/camera/image_raw/compressed -r out:=/camera/image_raw/uncompressed
```

### Connecting and Streaming from a Real Camera

To use a real camera, we need to install drivers. Let's begin by installing a v4l (video for linux) camera driver on `@robot` system.

```sh
sudo apt install libraspberrypi-bin v4l-utils ros-foxy-v4l2-camera
```

There are many drivers available for different camera's and settings. We use v4l2 driver which is easy to configure and use. Advanced users can choose other available drivers, or write their own.

Once we add drivers, users should be added to video groups. To check if you (user) is in video group:

```sh
groups    # shows list of users
sudo usermod -aG video <username> # only if user is not in groups, or VHCI failed
```

In our tests, we have seen that even though active user is visible in groups, it has to be explicitly added again. Once adding to groups, reboot your robot machine.

```sh
vcgencmd get_camera # check if camera is detected and supported
```

If the message says no camera supported or found, add to below commands to */boot/firmware/config.txt* file

```sh
start_x=1
gpu_mem=128
camera_autodetect=0
```

When you run get\_camera, it should say `detected = 1` and `supported=1`. If for some reason it still says not detected, then check camera cable if it is not connected, or is damaged.

Now that the camera driver is installed and assuming everything is going good, we can initiate raspberry pi camera with the below command. However, do note that this does not do anything as there is no GUI or display attached to the robot. Run the script and check if there are any error messages.

To stream video from the camera to development system, we need to install a package to make sure video is compressed before transfer. If required, we can also install image-view if we plan to connect a display to raspberry pi.

```sh
sudo apt install ros-foxy-image-transport-plugins #similar to dev
sudo apt install ros-foxy-rqt-image-view # optional
```

```sh
raspistill -k # x and enter to close
v4l2-ctl --list-devices # this lists all video devices. xx-v4l2 is the one we need.
```

Kill the `raspistill` service and type the following in a terminal

```sh
ros2 run v4l2_camera v4l2_camera_node --ros-args -p image_size:="[640,480]" -p camera_frame_id:=camera_link_optical
```

This will start steaming video from raspberry pi camera.

To make things simpler, we have a launch file for camera.

```
ros2 launch wolf-robot camera.launch.py
```

Once the launch file is invoked, open rqt\_image\_view in the developer machine and choose image\_raw/compressed

```
ros2 run rqt_image_view rqt_image_view
```

Streaming compressed images from raspberry pi to developer machine may not work always due to the way rqt\_image\_view works. Restart rqt\_image\_view or the terminal a couple of times to view the images.
