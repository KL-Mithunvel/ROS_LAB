# Visualising in Gazebo

A Gazebo simulation is a robot simulation made with Gazebo, a 3D simulator with the ability to accurately and efficiently simulate populations of robots in complex indoor and outdoor environments. With Gazebo you are able to create a 3D scenario on your computer with robots, obstacles and many other objects. Gazebo also uses a physical engine for illumination, gravity, inertia, etc. You can evaluate and test your robot in difficult or dangerous scenarios without any harm to your robot. Most of the time it is faster to run a simulator instead of starting the whole scenario on your real robot.

### Installing Gazebo

Gazebo is not installed in ROS 2 by default. We will install the classic version of gazebo.

```
sudo apt install ros-foxy-gazebo-ros-pkgs
```

### Copying Gazebo example files

Copy `wolf-robot` folder from `t3_gazebo_teleoperation` to `src` folder in your workspace.

```
ros2 run joint_state_publisher_gui joint_state_publisher_gui use_sim_time:=true
```

The above command runs joint state publisher. It also makes sure simulated time is set to true so that gazebo sets the time and all other packages are in sync. We can even check if simulated time is being used by typing:

```
ros2 param get /robot_state_publisher use_sim_time #it should say true
```

With all the checks correct, try the following code to visualize your robot in a 3D simulated world. Remember to type each one in a new terminal tab or window after sourcing it.

```
ros2 launch wolf-robot rsp.launch.py
ros2 run joint_state_publisher_gui joint_state_publisher_gui use_sim_time:=true
ros2 launch gazebo_ros gazebo.launch.py # to launch gazebo window
ros2 run gazebo_ros spawn_entity.py -topic robot_description -entity wolf_bot
```

### Launch Files

To make things easy, all the above scripts can be included in a single launch file. Launch files basically allow different nodes and services to be run in a sequential order. Launch files have an xml structure and end with a .launch extension.

```
ros2 launch wolf-robot launch_sim.launch.py
```

### Controlling a Simulated Robot

To Control the robot in simulated world, we can run teleop (teleoperation) twist keyboard.

```sh
ros2 run teleop_twist_keyboard teleop_twist_keyboard # to control the robot
```

We have created a construction world file called construction.world with few objects placed already. To view this world in gazebo, use:

```sh
ros2 launch wolf-robot launch_sim.launch.py world:=./src/wolf-robot/worlds/construction.world
```

Lastly, To check if `cmd_val` is passed, type : `ros2 topic echo /cmd_vel`

> [!NOTE]
> For the next tutorial, we may have to replace the files again. If you have any comparison tools, its best to compare the folders and check what has changed and what has not.
>
> Also, open VSCode and check the flow of files launched and nodes started.

> [!NOTE]
> Those of you who are using github, can use it to directly upload code from the terminal and keep track of all changes. After the end of each tutorial, push changes to github and verify what has changed.
