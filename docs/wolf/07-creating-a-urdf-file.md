# Creating a URDF File

In this section, we will understand how to build a URDF(Unified Robotics Description Format) file which is a variant of xml syntax which is used to model our wolf system for a simulated environment. We create a bunch of files in URDF files and a tool called xacro combiles them into a single complete URDF (Unified Robotics Description Format). This is passed to robot\_state\_publisher which makes the data available on the /robot\_description topic, and also broadcasts the appropriate transforms.

### Downloading first example:

On your development machine, download all the contents of this Github page.

[Wolf Tutorials](https://github.com/VEEROBOT/wolf-ros2-examples.git)

The download will have multiple folders each starting with t#. Save it in a location away from your workspace. (Eg: Downloads or Home directory)

If you do not have a GitHub account already, create one and login. Setup ssh connection between your machine and GitHub so that any modifications on either side can be in sync. For more information, follow the guide below:

[https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

```
cd dev_ws/src
```

From the downloaded folder, copy `wolf-robot` folder to `src` folder in your workspace.

```sh
cp -r <downloaded_directory>/t1_urdf_creation/wolf-robot /dev_ws/src
```

We need to build the workspace and compile the codes downloaded. But before that, we need to install required packages.

```sh
sudo apt install ros-foxy-xacro ros-foxy-joint-state-publisher-gui
```

Now we will build the workspace.

```sh
colcon build --symlink-install #this builds all packages inside src
```

If we now check contents (`ls`)in our workspace `cd /dev_ws`, we will find that there are other folders generated viz. `build`, `log`, `install`. If colcon build says successful, our package is compiled correctly and we can run the package.

### Visual Studio Code

The best way to edit files is using an IDE. VS Code helps in formatting and viewing all the files in our workspace. Since we have a few folders and files in our workspace, its a good time to open VS Code and go through all the files created, their extensions and code.

### Simulating our Robot in RVIZ2

Run the below commands, each on a separate terminal. Before running, make sure to source the environment on each terminal by typing `source install/setup.bash`. You may choose to add this to the bashrc file, but we will keep it like this for now.

```sh
ros2 launch wolf-robot rsp.launch.py # first terminal window
```

```sh
 ros2 run joint_state_publisher_gui joint_state_publisher_gui # second terminal window
```

```sh
rviz2 # third terminal window
```

This should open Rviz2. Rviz2 is a port of Rviz (ROS Visualization tool) is a graphical interface that allows users to view a simulated robot model, log sensor information from the robot's sensors, and replay the logged sensor information. By visualising what the robot is seeing, thinking, and doing, the user can debug a robot application from sensor inputs to planned actions.

On the Rviz window, set fixed frame to "*base\_link*" and add a "*RobotModel*". Add a TF (Transform System) to visualise the joints in our robot. This shows our simulated robot in a 3D world.

Since the collusion is also added in the code, check and uncheck Visual Enabled and Collusion Enabled to visualize the robot
