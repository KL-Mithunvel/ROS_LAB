#!/usr/bin/env bash

set -e

sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl gnupg2 lsb-release -y

ARCH=$(uname -i)
RELEASE=$(lsb_release -c -s)

echo ""
echo "[Setting up Locales]"
echo ""

sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

echo ""
echo "[Selecting appropriate ROS2 Version]"
echo ""

if [ $RELEASE == "bionic" ]
    then
        ROSDISTRO=eloquent

elif [ $RELEASE == "focal" ]
    then
        ROSDISTRO=foxy

elif [ $RELEASE == "jammy" ]
    then
        ROSDISTRO=humble
else
    echo "$RELEASE OS Release not supported. Exiting now"
    exit
fi

if [ $ARCH != "x86_64" ] && [ $ARCH != "aarch64" ]
    then
        echo "[$ARCH architecture not supported. Exiting now]"
        exit
fi

RELEASE_FILE=$ROSDISTRO$ARCH

# Add the ROS 2 apt repository
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key  -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

echo "Installing ROS $ROSDISTRO on $ARCH architecture"
sudo apt update

echo ""
echo "[Installing Python 3 and Colcon]"
echo ""

sudo apt install python3-colcon-core -y
sudo apt install python3-colcon-common-extensions -y

if [ $ARCH == "x86_64" ]
    then
        sudo apt install -y ros-$ROSDISTRO-desktop-full

elif [ $ARCH == "aarch64" ]
    then
        sudo apt install -y ros-$ROSDISTRO-desktop
fi

echo ""
echo "[Installing Required Packages]"
echo ""

sudo apt update && sudo apt install libpython3-dev \
  libbullet-dev python3-pip python3-pytest-cov ros-dev-tools -y
  
# install some pip packages needed for testing
python3 -m pip install -U argcomplete flake8-blind-except \
  flake8-builtins flake8-class-newline flake8-comprehensions \
  flake8-deprecated flake8-docstrings flake8-import-order \
  flake8-quotes pytest-repeat pytest-rerunfailures pytest
# install Fast-RTPS dependencies
sudo apt install --no-install-recommends libasio-dev libtinyxml2-dev -y
# install Cyclone DDS dependencies
sudo apt install --no-install-recommends libcunit1-dev -y
# Install python3 libraries
pip3 install -U argcomplete pytest-rerunfailures

# Install colcon extensions
sudo apt install python3-colcon-common-extensions python3-rosdep -y
# Remove conflicting em package
pip3 uninstall em

echo ""
echo "[Init and Update rosdep]"
echo ""

sudo rosdep init
rosdep update

echo ""
echo "[ROS $ROSDISTRO installation complete!]"
echo ""

echo ""
echo "[Setting up environment by sourcing the following file]"
echo "source /opt/ros/$ROSDISTRO/setup.bash"
echo ""

echo "source /opt/ros/$ROSDISTRO/setup.bash" >> $HOME/.bashrc

echo ""
echo "[Environment is Setup. Restart terminal and you are ready to go!]"
echo ""

echo "Installation of $ROSDISTRO Complete!"
