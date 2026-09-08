# System Setup Guide

***

### Overview

#### What This Guide Covers

This guide walks you through the complete system setup process:

1. **WiFi Configuration** - Connect Beetlebot to your network
2. **SSH Access** - Remote terminal access to the robot
3. **Network Verification** - Ensure everything communicates properly
4. **Laptop Setup** - Install ROS2 on your development machine
5. **ROS2 Multi-Machine** - Configure laptop ↔ robot communication
6. **Verification Tests** - Confirm everything works

#### ⏱️ Time Required

* **Robot WiFi Setup:** 20 minutes
* **Laptop ROS2 Installation:** 30-60 minutes (depending on internet speed)
* **Network Configuration:** 15 minutes
* **Testing & Verification:** 15 minutes
* **Total:** 80-110 minutes (one-time setup)

#### 📚 Prerequisites

* ✅ Completed Getting Started - Robot boots and responds to joystick
* ✅ Robot fully charged
* ✅ Laptop/PC with Ubuntu 22.04 or 24.04 (required for ROS2 Jazzy)
* ✅ WiFi network with internet access
* ✅ Network password available
* ✅ HDMI monitor + keyboard (temporary, for initial robot setup)
* ✅ Or USB keyboard + micro-HDMI cable for Pi 5

#### 🛠️ What You'll Need

**For robot:**

* ✅ Beetlebot (powered on)
* ✅ HDMI monitor or TV
* ✅ USB keyboard
* ✅ Micro-HDMI to HDMI cable (Pi 5 uses micro-HDMI)
* ⚠️ Mouse optional (keyboard-only setup possible)

**For laptop:**

* ✅ Ubuntu 22.04 LTS or 24.04 LTS (native install recommended, not VM)
* ✅ 20GB+ free disk space
* ✅ Internet connection
* ✅ Admin/sudo access

***

### Part 1: Connecting to Beetlebot

#### Option A: Direct Connection (Recommended for First Setup)

**You'll need:**

* HDMI monitor
* USB keyboard
* Micro-HDMI to HDMI cable

**Steps:**

1. **Power off robot** (if currently on)
2. **Connect monitor:**
   * Pi 5 has 2× micro-HDMI ports
   * Use the port closest to USB-C power
   * Connect micro-HDMI → HDMI cable → monitor
3. **Connect keyboard:**
   * Plug USB keyboard into robot's side USB port
   * Or use any USB port if accessible
4. **Power on robot:**
   * Press power switch on back panel
   * Wait for boot (\~90 seconds)
   * You should see boot messages on monitor
5. **Login:**
   * **Username:** `robot`
   * **Password:** (provided by support - default not published for security)
   * Press Enter
6. **You should see terminal prompt:**

```
   robot@beetlebot:~$
```

**Success!** You're now at a terminal on the robot.

***

#### Option B: Ethernet Direct Connection (Alternative)

**If you don't have monitor/keyboard:**

1. **Connect laptop to robot via Ethernet cable** (back panel RJ45)
2. **Configure laptop Ethernet as static:**
   * IP: `192.168.xx.xxx`
   * Netmask: `255.255.255.0`
3. **SSH to robot:**

```bash
   ssh robot@192.168.29.101 # We will use this IP as example
```

4. **If this works, skip monitor setup!**

**Note:** Robot may not have static IP configured yet - this assumes factory config. If connection fails, use monitor method.

***

### Part 2: WiFi Configuration

#### Check Current Network Status

First, see what's currently configured:

```bash
# Check network interfaces
ip addr show

# You should see:
# - lo (loopback)
# - eth0 (Ethernet - may be down)
# - wlan0 (WiFi - this is what we'll configure)
```

#### Using the Setup Script (Recommended)

Your robot has a pre-installed setup script:

```bash
# Navigate to setup directory
cd ~/lyra_setup

# List available scripts
ls -la

# You should see:
# install_wifi.sh
# setup_hardware.sh
# setup_lyra_service.sh
```

#### Configure WiFi with Script

```bash
# Run WiFi setup script
sudo ./install_wifi.sh "YOUR_WIFI_SSID" "YOUR_WIFI_PASSWORD" "192.168.29.101"

# Example:
# sudo ./install_wifi.sh "MyHomeWiFi" "mypassword123" "192.168.29.101"
```

**What this script does:**

1. Configures `wpa_supplicant` with your WiFi credentials
2. Sets static IP address (192.168.29.101 by default)
3. Disables WiFi power saving (prevents dropouts)
4. Configures auto-reconnect
5. Sets up proper network priorities

**Script output:**

```
[INFO] Configuring WiFi for SSID: YOUR_WIFI_SSID
[INFO] Setting static IP: 192.168.29.101
[INFO] Disabling power save mode
[INFO] Restarting network service
[INFO] WiFi configuration complete!
```

#### Verify WiFi Connection

```bash
# Check WiFi status
ip addr show wlan0

# Should show:
# inet 192.168.29.101/24 ...

# Test connectivity
ping -c 3 8.8.8.8

# Should see replies (Ctrl+C to stop)
```

#### Find Robot's IP Address

If you used DHCP instead of static IP:

```bash
# Show current IP
hostname -I

# First IP shown is typically WiFi address
```

**Write down this IP!** You'll need it for SSH.

***

### Part 3: SSH Access Setup

#### From Your Laptop (on Same WiFi Network)

**Ensure laptop is on same WiFi network as robot.**

```bash
# SSH to robot
ssh robot@192.168.29.101

# Or use hostname if mDNS works:
ssh robot@beetlebot.local

# Enter password when prompted
```

**First connection will show:**

```
The authenticity of host '192.168.29.101' can't be established.
ED25519 key fingerprint is SHA256:...
Are you sure you want to continue connecting (yes/no)?
```

**Type:** `yes` and press Enter

#### Setup SSH Keys (Optional but Recommended)

**Makes login password-free:**

```bash
# On YOUR LAPTOP (not robot):
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Press Enter for all prompts (use defaults)

# Copy key to robot
ssh-copy-id robot@192.168.29.101

# Enter robot password one last time

# Test passwordless login
ssh robot@192.168.29.101

# Should login without password!
```

#### Verify Robot Services

Once SSH'd into robot:

```bash
# Check if Lyra service is running
systemctl status lyra.service

# Should show:
# Active: active (running)
```

#### Test ROS2

```bash
# Source ROS2 (should be in .bashrc already)
source /opt/ros/jazzy/setup.bash
source ~/lyra_ws/install/setup.bash

# List running nodes
ros2 node list

# Should see:
# /lyra_node
# /lyra_odometry_node
# /lyra_teleop_node
# ... etc
```

**If nodes are running:** ✅ System is healthy!

***

### Part 4: Laptop ROS2 Installation

#### Check Ubuntu Version

```bash
# On your laptop
lsb_release -a

# Should show:
# Ubuntu 22.04 LTS (Jammy) - ROS2 Humble
# OR
# Ubuntu 24.04 LTS (Noble) - ROS2 Jazzy ← Preferred
```

**Important:** Robot runs ROS2 Jazzy. For best compatibility, laptop should also run Jazzy (Ubuntu 24.04).

***

#### Install ROS2 Jazzy (Ubuntu 24.04)

**Official installation method:**

```bash
# Ensure locale supports UTF-8
sudo apt update && sudo apt install locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Setup sources
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y

# Add ROS2 GPG key
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add repository to sources list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | \
  sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Update package index
sudo apt update

# Install ROS2 Jazzy Desktop (includes RViz, tools)
sudo apt install ros-jazzy-desktop -y

# This will take 15-30 minutes depending on internet speed
```

#### Install Additional Tools

```bash
# Install colcon (build tool)
sudo apt install python3-colcon-common-extensions -y

# Install rosdep (dependency manager)
sudo apt install python3-rosdep -y
sudo rosdep init
rosdep update

# Install useful ROS2 tools
sudo apt install ros-jazzy-joint-state-publisher \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-rviz2 \
  ros-jazzy-xacro \
  ros-jazzy-rqt-graph-twist-keyboard \
  ros-jazzy-rqt-* -y
```

#### Setup ROS2 Environment

```bash
# Add to .bashrc for automatic sourcing
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc

# Source for current terminal
source ~/.bashrc

# Verify installation
ros2 --version
# Should show: ros2 cli version: jazzy
```

***

### Part 5: Multi-Machine ROS2 Configuration

#### Understanding ROS2 Networking

**Key concepts:**

**ROS\_DOMAIN\_ID:**

* Isolates ROS2 networks
* Value: 0-101 (default: 0)
* Must match on all machines!

**DDS Discovery:**

* ROS2 uses DDS (Data Distribution Service)
* Automatic peer discovery on same network
* Works via multicast UDP

**Firewall:**

* Must allow ROS2 traffic
* Or disable firewall (not recommended for production)

***

#### Configure Laptop for Robot Communication

**On your laptop:**

```bash
# Edit .bashrc
nano ~/.bashrc

# Add these lines at the end:
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$HOME/cyclonedds.xml

# Save (Ctrl+X, Y, Enter)

# Source changes
source ~/.bashrc
```

#### Create CycloneDDS Configuration

```bash
# Create config file
nano ~/cyclonedds.xml
```

**Paste this configuration:**

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Domain>
    <General>
      <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
      <AllowMulticast>true</AllowMulticast>
      <MaxMessageSize>65500B</MaxMessageSize>
    </General>
    <Discovery>
      <ParticipantIndex>auto</ParticipantIndex>
      <Peers>
        <Peer address="192.168.29.101"/>
      </Peers>
    </Discovery>
  </Domain>
</CycloneDDS>
```

**Save and exit** (Ctrl+X, Y, Enter)

**Update peer address if your robot uses different IP!**

***

#### Configure Firewall (Ubuntu)

**Option A: Allow ROS2 Traffic (Recommended)**

```bash
# Allow DDS multicast
sudo ufw allow from 192.168.29.0/24

# Or allow specific ports
sudo ufw allow 7400:7410/udp
sudo ufw allow 7400:7410/tcp
```

**Option B: Disable Firewall (Quick but less secure)**

```bash
sudo ufw disable
```

***

### Part 6: Verification Tests

#### Test 1: Basic Connectivity

**From laptop:**

```bash
# Ping robot
ping -c 3 192.168.29.101

# Should see replies with <10ms latency
```

#### Test 2: SSH Connection

```bash
# SSH to robot
ssh robot@192.168.29.101

# Should connect without issues
```

#### Test 3: ROS2 Node Discovery

**On laptop (Terminal 1):**

```bash
# List nodes on robot
ros2 node list

# Should see robot's nodes:
# /lyra_node
# /lyra_odometry_node
# /lyra_teleop_node
# etc.
```

**If you see nodes:** ✅ Multi-machine ROS2 works!

**If no nodes appear:**

* Check `ROS_DOMAIN_ID` matches (robot and laptop both = 0)
* Check firewall allows traffic
* Verify on same WiFi network
* Check CycloneDDS config has correct IP

***

#### Test 4: Topic Echo

**On laptop:**

```bash
# Echo telemetry from robot
ros2 topic echo /lyra/battery

# Should see battery voltage updating:
# voltage: 12.1
# ---
# voltage: 12.1
# ---
```

**Try other topics:**

```bash
# Wheel odometry
ros2 topic echo /odom

# Drive robot with joystick - see values change!

# IMU data
ros2 topic echo /lyra/imu
```

***

#### Test 5: RViz Visualization

**On laptop:**

```bash
# Launch RViz
rviz2

# In RViz:
# 1. Change Fixed Frame to "odom"
# 2. Add → By Topic → /odom → Odometry
# 3. Add → By Topic → /scan → LaserScan
# 4. Drive robot with joystick
# 5. Watch odometry trail appear!
```

\[PLACEHOLDER: Screenshot of RViz showing odometry]

**If you see visualization:** ✅ Complete system working!

***

#### Test 6: Remote Control from Laptop

**On laptop:**

```bash
# Install keyboard teleop (if not already)
sudo apt install ros-jazzy-teleop-twist-keyboard

# Launch keyboard control
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Follow on-screen instructions:
# u i o
# j k l
# m , .

# Press keys to drive robot!
```

**Robot should respond to laptop keyboard!** ✅

***

### Part 7: Optional Advanced Setup

#### Setup Hostname Resolution (mDNS)

**Makes `beetlebot.local` work instead of IP address:**

**On robot:**

```bash
# Install Avahi (mDNS)
sudo apt install avahi-daemon avahi-utils

# Set hostname
sudo hostnamectl set-hostname beetlebot

# Restart avahi
sudo systemctl restart avahi-daemon
```

**Test from laptop:**

```bash
# Ping by hostname
ping beetlebot.local

# SSH by hostname
ssh robot@beetlebot.local
```

***

#### Setup VS Code Remote Development

**On laptop:**

```bash
# Install VS Code (if not already)
sudo snap install code --classic

# Install Remote-SSH extension
code --install-extension ms-vscode-remote.remote-ssh
```

**Configure connection:**

1. Open VS Code
2. Press F1 → "Remote-SSH: Connect to Host"
3. Enter: `robot@192.168.29.101`
4. Select Linux
5. Enter password (or use SSH keys for passwordless)

**Now you can edit robot's code directly from laptop!**

***

#### Setup Synchronized Time (Important for Sensor Fusion)

**On robot:**

```bash
# Install chrony (NTP client)
sudo apt install chrony

# Enable and start
sudo systemctl enable chrony
sudo systemctl start chrony

# Check sync status
chronyc tracking

# Should show time synchronized
```

**Why important?** Sensor fusion (EKF) requires accurate timestamps. If robot and laptop clocks differ >100ms, fusion may fail.

***

### Part 8: Creating a Development Workspace

#### Setup on Laptop

**Create workspace for your code:**

```bash
# Create workspace
mkdir -p ~/beetlebot_ws/src
cd ~/beetlebot_ws

# Clone Beetlebot packages (if available)
# cd src
# git clone https://github.com/yourusername/beetlebot_ros2.git

# For now, we'll create a test package
cd ~/beetlebot_ws/src
ros2 pkg create test_beetlebot --build-type ament_python

# Build workspace
cd ~/beetlebot_ws
colcon build

# Source workspace
source ~/beetlebot_ws/install/setup.bash

# Add to .bashrc for automatic sourcing
echo "source ~/beetlebot_ws/install/setup.bash" >> ~/.bashrc
```

***

### Part 9: Network Troubleshooting

#### Problem: Can't See Robot Nodes

**Check list:**

```bash
# 1. Verify ROS_DOMAIN_ID matches
# On laptop:
echo $ROS_DOMAIN_ID  # Should be 0

# On robot (SSH):
echo $ROS_DOMAIN_ID  # Should be 0

# 2. Check DDS implementation
echo $RMW_IMPLEMENTATION  # Should be rmw_cyclonedds_cpp

# 3. Test network connectivity
ping 192.168.29.101  # Should work

# 4. Check firewall
sudo ufw status  # Should be disabled or allowing ROS2 traffic

# 5. Restart ROS2 daemon
ros2 daemon stop
ros2 daemon start
ros2 node list  # Try again
```

***

#### Problem: High Latency

**Test latency:**

```bash
# Ping test
ping -c 100 192.168.29.101 | tail -1

# Should see average <5ms
# If >20ms, WiFi may be congested
```

**Fixes:**

* Use 5GHz WiFi instead of 2.4GHz (less crowded)
* Move closer to router
* Check for WiFi interference
* Use Ethernet cable for critical operations

***

#### Problem: Topics Drop/Intermittent

**Check topic bandwidth:**

```bash
# Monitor topic rate
ros2 topic hz /scan

# Should be steady (~10 Hz for LiDAR)
# If fluctuating wildly, network issues
```

**Fixes:**

* Reduce topic rates (downsample data)
* Use QoS profiles (reliable vs best-effort)
* Check WiFi signal strength: `iwconfig wlan0`

***

### Part 10: Configuration Summary

#### Quick Reference - Network Settings

**Robot (Beetlebot):**

```
Hostname: beetlebot
IP Address: 192.168.29.101 (static)
Gateway: 192.168.29.1 (your router)
Username: robot
ROS_DOMAIN_ID: 0
ROS2 Version: Jazzy
```

**Laptop:**

```
IP Address: DHCP (auto) or static on same subnet
ROS_DOMAIN_ID: 0
ROS2 Version: Jazzy (recommended)
DDS: CycloneDDS
```

***

#### Files to Backup

**Keep copies of these configurations:**

```bash
# On robot:
~/lyra_setup/install_wifi.sh
/etc/netplan/50-cloud-init.yaml  # WiFi config
~/.bashrc  # Environment variables

# On laptop:
~/cyclonedds.xml  # DDS config
~/.bashrc  # Environment variables
```

***

### Part 11: Next Steps

#### ✅ Setup Complete Checklist

Verify you've completed:

* [ ] Robot connected to WiFi with static IP
* [ ] SSH access from laptop to robot (passwordless recommended)
* [ ] ROS2 Jazzy installed on laptop
* [ ] Multi-machine ROS2 communication working
* [ ] Can see robot's nodes from laptop (`ros2 node list`)
* [ ] Can echo robot's topics (`ros2 topic echo /odom`)
* [ ] RViz can visualize robot data
* [ ] Can control robot from laptop keyboard
* [ ] Development workspace created
* [ ] Time synchronized (optional but recommended)

***

#### 🎯 You're Now Ready For:

**All Tutorials:**

* Hardware Familiarization (can use laptop + SSH now)
* ROS2 Communication & Tools
* All sensor tutorials
* SLAM Mapping with visualization
* Autonomous Navigation

**Development:**

* Write custom nodes on laptop
* Test on real robot
* Use RViz for debugging
* Record and analyze rosbags

***

#### 📚 Recommended Next Steps

**Path 1: Learning (Recommended)** → Start with ROS2 Communication & Tools → Learn ROS2 commands and debugging → Then proceed through tutorials in order

**Path 2: Quick Start** → Launch RViz and drive around → Visualize sensors in real-time → Get familiar with tools

**Not comfortable yet?**

Read through the tutorials carefully before driving! (No simulation available yet—start moving slowly in a clear space!)

***

### Troubleshooting Reference

#### Common Issues & Solutions

| Problem                | Solution                                               |
| ---------------------- | ------------------------------------------------------ |
| Can't SSH to robot     | Check IP with monitor, verify WiFi connected           |
| No nodes visible       | Check ROS\_DOMAIN\_ID=0 on both machines               |
| Topics not updating    | Restart ROS2 daemon: `ros2 daemon stop` then `start`   |
| RViz shows nothing     | Check Fixed Frame matches topic frame (usually "odom") |
| High latency           | Use 5GHz WiFi, move closer to router, or use Ethernet  |
| Robot stops responding | Check battery voltage, may need charging               |
| Firewall blocking      | Allow ports: `sudo ufw allow 7400:7410/udp`            |
| Time sync errors       | Install chrony on robot: `sudo apt install chrony`     |

***

### Getting Help

**Still stuck?**

1. **Check documentation:** <https://docs.veerobot.com>
2. **ROS2 Jazzy docs:** <https://docs.ros.org/en/jazzy/>
3. **Email support:** <support@siliris.com> with:
   * Clear description of problem
   * What you've tried
   * Output of diagnostic commands
   * Network configuration details

**Expected response:** Within 24 hours (business days)

***

**System Setup Complete!** 🎉

→ Continue to ROS2 Communication & Tools\
→ Or jump to Tutorial Index

***

*Last Updated: January 2026*\
*Setup Guide - One-Time Configuration*
