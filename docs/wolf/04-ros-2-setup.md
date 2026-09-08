# ROS 2 Setup

## Installing ROS 2

### Development Machine Setup

#### ROS 2 Installation on Linux Distribution

In order to complete ROS 2 installation and this tutorial, we need a Linux machine for development. ROS distributions are tightly integrated with Linux distributions. Hence it is essential to make sure we select the right Linux version for the right ROS 2 distribution. ROS distributions are fully compatible with Ubuntu and ROS distributions are planned according to respective Ubuntu Versions.

The latest version of Ubuntu at the time of this writing is Ubuntu 22.04 LTS (Long Term Support) and the compatible ROS 2 Version is Humble Hawksbill. However not all packages are fully implemented.

ROS 2 Foxy Fitzroy is fully tested long term support version and hence we need to install that over Ubuntu 20.04 distribution.

#### Install Ubuntu 20.04 and ROS 2 Foxy on developer machine

To begin with, install Ubuntu 20.04 distribution on a laptop or a PC. Laptop is preferred since latest laptops come with Bluetooth and WiFi support built-in. This will help us in later part of the tutorial when we connect to network. We use a developer machine to make sure all the heavy work is done on a remote machine while the robot has minimal overhead tasks to perform. Secondly, the developer machine has a screen where all visuals and GUI can be viewed while robot works on headless mode.

Install the desktop version of Ubuntu from the link below:

[Choose the Desktop version of Ubuntu](https://releases.ubuntu.com/focal/)

Installing ROS 2 on Ubuntu means you need to run a set of commands in a particular sequence. A detailed explanation and steps are mentioned on ros.org website. If for some reason, you would want to take the longer way (and sometimes it's better to learn this way) of installation, follow the link on ros.org page to complete installation.

[Installing ROS 2 Foxy Fitzroy on Ubuntu Focal](https://docs.ros.org/en/foxy/Installation/Ubuntu-Install-Debians.html)

To make things easier, we at VEEROBOT have created a script that performs all those activities in a sequence. The script installs ROS 2, ROS 2 dependencies, Colcon and few required python packages. To begin installation:

```
sudo apt-get update
sudo apt-get upgrade
wget https://raw.githubusercontent.com/VEEROBOT/ros-scripts/main/ROS2Install/install_ros2.sh
chmod 755 ./install_ros2.sh
sudo bash ./install_ros2.sh
```

The above script takes up-to 15 minutes depending on the speed of your machine. When prompted, type "Y" or "y" to continue installation. Once the installation is complete, a *`Installation Complete!`* confirmation message is shown. You may delete the installation file if required.

> [!NOTE]
> The above script installs [colcon](https://colcon.readthedocs.io/en/released/) and also sets up the environment by sourcing
>
> `source /opt/ros/$ROS_DISTRO/setup.bash`
>
> `source /opt/ros/foxy/setup.bash # Specific to foxy`
>
> You may check the \~/.bashrc file to confirm if the above line is added to the file.

If for some reason colcon is not installed by the script, then the below command may be used:

```
sudo apt install python3-colcon-common-extensions
```

Once installation is successful, update and upgrade the distribution to get the latest updates:

```
sudo apt update
sudo apt upgrade -y
```

#### Additional Packages

There are few more packages required to be installed to make working with ROS easier:

1. Install Git to access GitHub: `sudo apt install git`
2. Install VSCode: `sudo snap install --classic code`
3. Extensions on VSCode:
   1. Remote – Development (from Microsoft)
   2. URDF (from smilerobotics)
   3. ROS - from Microsoft

> [!NOTE]
> The tutorial assumes that the user name and machine name on development machine is `dev@robot`. If you set a different name, change scripts in further tutorials accordingly.

### Robot Machine Setup

#### ROS 2 Installation on Robot

Installing ROS 2 on desktop or laptop is seemingly much easier than installing on robot machine. On Wolf, we use a Raspberry Pi 4 development board. Since the robot comes fully assembled, the Pi already comes loaded with Ubuntu Server 20.04 and ROS 2 Foxy pre-installed. If for some reason, you may still need to install (or reinstall) this setup on a different SD card or Raspberry Pi, we have a pre-built image which can be directly burnt on SD card. Make sure the card is at least 16GB.

Download Raspberry Pi Image in the below link. The image has following setup pre-installed:

* Ubuntu 20.04 : Server Image
* ROS 2 (Foxy) : Installed with environment setup
* OpenSSH : Server to talk to remote PC
* Git : To download packages from GitHub
* Network Setup : `@192.168.1.xxx`requires reconfiguration if using a different network and IP address). The 'xxx' will be configured prior to delivery of robot and will be printed on the box.
* User ID: `wolf`
* Password: `wolf@123`

Since Raspberry Pi runs on headless mode (no GUI or Display), we need a way to access it.

Once installation is successful, update and upgrade the distribution to get the latest updates:

```sh
sudo apt update
sudo apt upgrade -y
```

### Wolf Robot Network Setup

All our Wolf robots come with a travel network router `Wolf_2.4G` and `Wolf_5G` with default setup at 2.4Ghz and IP address as `192.168.1.1` and username, password as `wolf`and `wolf@123`. If you have followed above setup and if the said router is connected, then connecting to pi is as simple as typing ssh `pi@192.168.1.136` (or whatever IP address is mentioned on the box) on development machine. Enter the user ID (`wolf`) and password (`wolf@123`) of raspberry pi and it should be logged in. For multiple robots, you can edit and change the address in *yaml* file as described below. Hostname will generally be `rosbot`.

There are times when one needs to connect to a different WiFi adaptor, or if multiple robots are supposed to be controlled. In those cases, we need to manually configure Raspberry Pi. This requires users to remove the top plate of Wolf, connect a network cable, connect to wired network and access pi through local ssh, telnet or other means. Once connected, follow the below guide to change network settings:

```sh
cd /etc/netplan
ls # check if 50-cloud-init.yaml is already generated
sudo nano 60-wolf-net.yaml #create a new yaml file and paste below contents
```

```sh
network:
  ethernets:
    eth0:
      dhcp4: true
      optional: true
  version: 2
  wifis:
    wlan0:
      dhcp4: no
      addresses: [192.168.1.136/24]
      gateway4: 192.168.1.1
      nameservers:
        addresses: [192.168.8.1,8.8.8.8,192.168.1.1]
      access-points:
        "wifi-username":
          password: "wifi-password"
```

Change the addresses, `gateway4`, `nameserver`, `username` and `password` as per your setup. y*aml* files follow strict indentation: 2 spaces per indent and do not tab.

If all goes well, type the following to apply the changes and you should have a working network connection:

```bash
sudo netplan generate
sudo netplan apply
# type ip addr to check if new address is visible
```

If for some reason ssh is not working, a workaround is to allow traffic through UFW

```sh
sudo ufw status    # if this says inactive
sudo ssh-keygen –A
sudo ufw allow ssh
```

Ubuntu goes to sleep after 15 minutes if there is no activity. On raspberry pi, there is no way to wake the pi without restarting the robot. This will be an issue during development where most of the development happens on the development machine while pi is idle. The best way to resolve this is to disable sleep on pi. The second command is used to enable sleep in case you need to revert to default setup.

```sh
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
# sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

Ubuntu updates on automatic and sometimes the system locks the files until upgrade completes. We can avoid this (not recommended) using the below script:

```sh
sudo nano /etc/apt/apt.conf.d/20auto-upgrades # use this to disable unattended upgrades
```

### Talking to Pi from the Development Machine

If everything goes well, your robot should be ready to talk to development machine. Unlike ROS 1, ROS 2 does not require any Master - Slave setup. Any and all ROS systems in the same setup can communicate between each other.

Open a terminal on development machine and type:

```sh
source /opt/ros/foxy/setup.bash	# on dev machine root directory
ros2 run demo_nodes_cpp talker
```

This runs a talker node (example) and sends (publishes) a message every second on the network. Any ROS 2 system on the same network can listen (subscribe) to this message.

Open another terminal window and type ssh `pi@192.168.1.136` and enter the credentials. This should connect developer machine to robot machine.

```sh
source /opt/ros/foxy/setup.bash	#  on robot root directory
ros2 run demo_nodes_cpp listener
```

Now the terminal should echo the message received from the development machine. To keep things simple, we will call development machine as `@dev` and robot machine as `@robot` where both the terminals are connected on the development machine.

### Creating Workspace

A workspace is a directory containing ROS 2 packages. Before using ROS 2, it’s necessary to source your ROS 2 installation workspace in the terminal you plan to work in. This makes ROS 2’s packages available for you to use in that terminal.

You also have the option of sourcing an “overlay” – a secondary workspace where you can add new packages without interfering with the existing ROS 2 workspace that you’re extending, or “underlay”. Your underlay must contain the dependencies of all the packages in your overlay. Packages in your overlay will override packages in the underlay. It’s also possible to have several layers of underlays and overlays, with each successive overlay using the packages of its parent underlays.

To create a workspace on development machine:

```sh
mkdir dev_ws/src # on development machine
colcon build
sudo reboot # This is not required, but done to refresh all other installations
```

To create a workspace on robot machine:

```sh
mkdir robot_ws/src # on robot
colcon build
sudo reboot now # This is not required, but done to refresh all other installations
```

If in case colcon is freezing, then reduce the parallel execution using the below command:

```bash
colcon build --parallel-workers <number>
colcon build --parallel-workers 1 #1 is the least while also making sure everything compiles
# Refer : https://colcon.readthedocs.io/en/released/reference/executor-arguments.html
```

If in case, any package is already built, we can override it using below command:

```bash
--allow-overriding <package>
--allow-overriding teleop_twist_joy
# Refer : https://github.com/colcon/colcon-core/issues/469
```

This completes the installation. Other required packages will be installed as we progress through the tutorials.
