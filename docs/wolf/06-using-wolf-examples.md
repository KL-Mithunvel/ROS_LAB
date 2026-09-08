# Using Wolf Examples

Out of the box Wolf is configured to be fully compatible with ROS 2 with simulation, visualisation and controlling real robot in the real world. However, for those who are interested in learning how the robot works, we have split the code base as tutorials where each step is followed to achieve a desired output.

> Before we progress, understand that once you begin following these tutorials, the base code which is already there with existing workspace if any on the robot will be deleted. This means the robot will be as good as new without any code uploaded. You either need to follow all the tutorials in this order, or upload the final tutorial folder which will have all codes installed.

> [!NOTE]
> To simulate wolf in a 3D space and control the real robot, `wolf-robot` package has to be installed on the developer machine. If you do not want to follow the tutorials and directly want to jump into testing the robot, clone the below repository into your workspace, build and start testing

[https://github.com/VEEROBOT/wolf-robot.git](https://github.com/VEEROBOT/wolf-robot.git)

Most ROS examples follow a multi folder structure where each folder is designed to showcase one activity. Since we are learning by building the robot step by step, we need to delete and recreate the package multiple times and then build it.
