## Install ROS 2 on Ubuntu
The below script installs compatible ROS 2 version after checking the Ubuntu Version

## Install Script
### Install script for installing ROS 2 on Ubuntu
### To install do the following from your command prompt: 

```
sudo apt-get update
sudo apt-get upgrade
wget https://raw.githubusercontent.com/VEEROBOT/ros-scripts/main/ROS2Install/install_ros2.sh
chmod 755 ./install_ros2.sh
sudo bash ./install_ros2.sh
```
### The script will take upto 15 minutes to install. 

### The below script includes the latest version of ROS on ubuntu 24.02

```
sudo apt-get update
sudo apt-get upgrade
wget https://raw.githubusercontent.com/VEEROBOT/ros-scripts/main/ROS2Install/install_ros2_v2.sh
chmod +x install_ros2_v2.sh
./install_ros2_v2.sh
```

### PiP3 Install for dev-tools
```
# Setup environment sourcing
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc

# rosdep setup
sudo rosdep init || echo "rosdep already initialized"
rosdep update

# Add pip user bin to path
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install Python dev tools with break-system-packages
pip3 install --break-system-packages -U argcomplete flake8-blind-except \
  flake8-builtins flake8-class-newline flake8-comprehensions \
  flake8-deprecated flake8-docstrings flake8-import-order \
  flake8-quotes pytest-repeat pytest-rerunfailures pytest

# Fix uninstall for em
pip3 uninstall --break-system-packages -y em || true

# Create and test workspace
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

For ROS dep update
```
rosdep update
```

### Errors
If for some reason, wget is not able to connect, add raw.githubusercontent.com ip to hosts file

```
sudo nano /etc/hosts
185.199.108.133 raw.githubusercontent.com
```
Save, Close and Try again. In some cases, you may have to restart the system. You can also set DNS 8.8.8.8 on your network to resolve this

