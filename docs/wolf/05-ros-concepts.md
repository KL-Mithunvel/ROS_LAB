# ROS Concepts

### ROS Distribution

ROS stands for Robot Operating System. However it is not actually an OS, but a set of common libraries and tools used to build complex robotic systems. ROS is generally designed to run on Ubuntu operating system though newer versions work on Microsoft Windows too. The development of ROS is overseen by Open Robotics. Beginners should start using ROS on Ubuntu systems.

### Nodes

ROS Nodes are processes that perform some computation or task. The nodes themselves are really software processes but with the capability to register with the ROS Master node and communicate with other nodes in the system. The ROS design idea is that each node is independent and interacts with other nodes using the ROS communication capability. The Master node is described in the ROS Master section to follow.

One of the strengths of ROS is that a particular task, such as controlling a wheeled mobile robot, can be separated into a series of simpler tasks. The tasks can include the perception of the environment using a camera or laser scanner, map making, planning a route, monitoring the battery level of the robot's battery, and controlling the motors driving the wheels of the robot. Each of these actions might consist of a ROS node or a series of nodes to accomplish the specific tasks.

A node can independently execute code to perform its task but can also communicate with other nodes by sending or receiving messages. The messages can consist of data, commands, or other information necessary for the application.

Some of the examples of nodes are:

* Reading data from a sensor
* Sending control signals to a motor
* Receiving operator controls from a joystick
* Displaying a visualization to an operator

```sh
ros2 run <package_name> <node_name> # To run a node
ros2 node list # To see all the nodes currently running on our network
```

### Topics and Messages

Nodes provide information for other nodes, as a camera feed would do, for example. Such a node is said to publish information that can be received by other nodes. This information in ROS is called a Topic. A topic defines the types of messages that will be sent between nodes.

The nodes that transmit data publish the topic name and the type of message to be sent. The actual data is published by the node. A node can subscribe to a topic and transmitted messages on that topic are received by the node subscribing.

```sh
ros2 topic list # To see all the available topics being published
ros2 topic echo <topic name> # To see the messages being published
```

### Messages <a href="#ch01lvl2sec20" id="ch01lvl2sec20"></a>

ROS messages are defined by the type of message and the data format. The ROS package named std\_msgs, for example, has messages of type String which consist of a string of characters. Other message packages for ROS have messages used for robot navigation or robotic sensors.

### Services

Services offer a single request/reply communication from one node to another whereas topics can be used to share any message between any nodes. In other words, ROS service is a client/server system.

```sh
ros2 service list # To see a list of all services available
ros2 service call <service_name> <service_message> # To call a service with the command
```

### Launch Files

This is a scripting system that lets us configure and launch a bunch of nodes together in a group. Launch files are generally written in python. To launch a launch file:

```sh
ros2 launch <package_name> <launch_file_name> # To run a launch file from a package
ros2 launch /path/to/launch/file # To run a launch file directly
```

### Creating a workspace

A workspace is a directory where we keep all our project files in. One workspace can have multiple projects. Its a common practice to place all code under `dev_ws` workspace.

```sh
mkdir -p ~/dev_ws/src
cd ~/dev_ws
colcon build --symlink-install
```

### Creating a Package

A package is a way to group together a bunch of related files, e.g. executables, config files, launch scripts. The below script will create an empty workspace

```sh
ros2 pkg create --build-type ament_cmake test_package
```

### Test Package

Once an empty package is created using the above script, open vscode and create two files called `talker.launch.py` and `listener.launch.py`

```python
# talker.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='demo_nodes_cpp',
            executable='talker'
        )
    ])
```

```python
# listener.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='demo_nodes_py',
            executable='listener'
        )
    ])
```

Update the CMAKELists. This tells colcon everything it needs to build and install the package

```
install(DIRECTORY launch
 DESTINATION share/${PROJECT_NAME}
)
```

Update package.xml which provides any additional dependencies to build our package. Any additional information like email ID, Description of the package can be populated here.

```xml
<exec_depend>demo_nodes_cpp</exec_depend>
<exec_depend>demo_nodes_py</exec_depend>
```

Now that all the files are updated, run : `colcon build --symlink-install`

### Testing the package

First we need to source the workspace with : `source install/setup.bash`. Make sure you are in the workspace directory.

Now run the launch files:

```sh
ros2 launch test_package talker.launch.py
ros2 launch test_package listener.launch.py
```
