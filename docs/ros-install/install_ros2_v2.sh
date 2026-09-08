#!/usr/bin/env bash

set -euo pipefail

echo ""
echo "[Updating APT and Installing Essentials]"
echo ""

sudo apt update
sudo apt install -y software-properties-common curl gnupg2 lsb-release locales

echo ""
echo "[Setting up Locales]"
echo ""

sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

echo ""
echo "[Detecting Ubuntu Version and Architecture]"
echo ""

ARCH=$(uname -m)
RELEASE=$(lsb_release -c -s)

echo "Ubuntu Release: $RELEASE"
echo "System Architecture: $ARCH"

echo ""
echo "[Selecting Appropriate ROS 2 Version]"
echo ""

case "$RELEASE" in
  bionic)
    ROSDISTRO=eloquent
    ;;
  focal)
    ROSDISTRO=foxy
    ;;
  jammy)
    ROSDISTRO=humble
    ;;
  noble)
    ROSDISTRO=jazzy
    ;;
  *)
    echo "Ubuntu release '$RELEASE' not supported for this installer. Exiting..."
    exit 1
    ;;
esac

if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" ]]; then
    echo "[$ARCH architecture not supported. Exiting now]"
    exit 1
fi

echo ""
echo "[Adding ROS 2 APT Repository and Key]"
echo ""

sudo mkdir -p /usr/share/keyrings
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key | \
  gpg --dearmor | sudo tee /usr/share/keyrings/ros-archive-keyring.gpg > /dev/null

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

echo ""
echo "[Installing ROS 2 $ROSDISTRO]"
echo ""

sudo apt update

if [[ "$ARCH" == "x86_64" ]]; then
  sudo apt install -y ros-$ROSDISTRO-desktop-full
else
  sudo apt install -y ros-$ROSDISTRO-desktop
fi

echo ""
echo "[Installing Colcon and Development Tools]"
echo ""

sudo apt install -y python3-colcon-common-extensions \
  python3-rosdep python3-pip python3-pytest-cov libpython3-dev libbullet-dev \
  ros-dev-tools libasio-dev libtinyxml2-dev libcunit1-dev

python3 -m pip install -U \
  argcomplete flake8-blind-except flake8-builtins flake8-class-newline \
  flake8-comprehensions flake8-deprecated flake8-docstrings \
  flake8-import-order flake8-quotes pytest-repeat pytest-rerunfailures pytest

pip3 uninstall -y em || true

echo ""
echo "[Initializing rosdep]"
echo ""

sudo rosdep init || echo "rosdep already initialized"
rosdep update

echo ""
echo "[ROS 2 $ROSDISTRO Installation Complete!]"
echo ""

ROS_SETUP_LINE="source /opt/ros/$ROSDISTRO/setup.bash"

if ! grep -Fxq "$ROS_SETUP_LINE" "$HOME/.bashrc"; then
  echo "$ROS_SETUP_LINE" >> "$HOME/.bashrc"
  echo "[Added to .bashrc: $ROS_SETUP_LINE]"
else
  echo "[Already present in .bashrc]"
fi

echo ""
echo "[Please restart your terminal or run 'source ~/.bashrc' to apply changes.]"
echo ""
