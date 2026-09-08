# ROS Introduction

ROS (Robot Operating System) is an Open Source system for controlling robots from an external device or make it run autonomously. A ROS system is comprised of a number of independent nodes, each of which communicates with the other nodes using a publish/subscribe messaging model. For example, a particular sensor’s driver might be implemented as a node, which publishes sensor data in a stream of messages. These messages could be consumed by any number of other nodes, including filters, loggers, and also higher-level systems such as guidance, pathfinding, etc.

ROS provides the services you would expect from an operating system, including hardware abstraction, low-level device control, implementation of commonly-used functionality, message-passing between processes, and package management. It also provides tools and libraries for obtaining, building, writing, and running code across multiple computers.

Software in ROS is organized as packages, and offers good modularity and reusability. Using the ROS message-passing middleware and hardware abstraction layer, developers can create tons of robotic capabilities, such as mapping and navigation (in mobile robots). Almost all capabilities in ROS will be robot agnostic so that all kinds of robots can use it. New robots can directly use this capability package without modifying any code inside the package.

The ROS project was started in 2007 in Stanford University under the name Switchyard. Later on, in 2008, the development was undertaken by a robotic research start-up called Willow Garage. The major development in ROS happened in Willow Garage. In 2013, the Willow Garage researchers formed the Open Source Robotics Foundation (OSRF). ROS is actively maintained by OSRF now.

> Although the same says Robot Operating System, ROS is per say not an entire operating system. It is a framework and set of tools that provide functionality of an operating system on a heterogeneous computer cluster. Its usefulness is not limited to robots, but the majority of tools provided are focused on working with peripheral hardware

ROS (1) currently runs on only Linux Systems. However the newer version of ROS 2 is designed to run on other OS's like OS X and Windows
