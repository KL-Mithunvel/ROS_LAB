#!/usr/bin/env bash
# install.sh — set up a bare Ubuntu machine for the ROS_LAB repo.
#
# Installs ROS 2 (Humble on Ubuntu 22.04, Jazzy on Ubuntu 24.04), the optional
# components you ask for, clones the repo if needed, builds the Python
# environments and runs the projects' tests.
#
# Full documentation: setup/INSTALL.md.  Quick help: ./install.sh --help
#
# STATUS: written but not yet run on a clean Ubuntu. Use --dry-run first.

set -euo pipefail

REPO_URL="https://github.com/KL-Mithunvel/ROS_LAB.git"
DEFAULT_DIR="$HOME/ROS_LAB"

# ---- defaults (override with flags) -----------------------------------------
DISTRO=""            # empty = auto-detect from the Ubuntu release
TARGET_DIR=""        # empty = this checkout if run from one, else $DEFAULT_DIR
ASSUME_YES=0
DRY_RUN=0
WITH_ROS=1
WITH_NAV2=1          # waypoint mission: Nav2 + collision monitor + map server
WITH_LAB=1           # BeetleBot labs: turtlesim, teleop, rqt, cv_bridge, OpenCV
WITH_PRACTICE=1      # Python venvs + pytest for waypoint_mission, robot_calc
WITH_GAZEBO=0
WITH_BOTS=0          # git submodules under bots/ (large)

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Components (defaults: ros, nav2, lab, practice ON; gazebo, bots OFF)
  --with-nav2 / --without-nav2          Nav2 packages (waypoint mission)
  --with-lab / --without-lab            turtlesim, teleop, rqt, cv_bridge, OpenCV
  --with-practice / --without-practice  Python venvs + pytest
  --with-gazebo                         ros_gz simulator packages
  --with-bots                           git submodules in bots/ (large download)
  --no-ros                              skip ROS 2 entirely (Python tests only)
  --all                                 turn every component on

Other options
  --distro humble|jazzy   override the auto-detected ROS distro
  --dir PATH              where to clone the repo if not run from a checkout
                          (default: ~/ROS_LAB)
  -y, --yes               do not ask for confirmation
  --dry-run               print what would run, change nothing
  -h, --help              this text
EOF
}

# ---- argument parsing -------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --with-nav2) WITH_NAV2=1 ;;       --without-nav2) WITH_NAV2=0 ;;
    --with-lab) WITH_LAB=1 ;;         --without-lab) WITH_LAB=0 ;;
    --with-practice) WITH_PRACTICE=1 ;; --without-practice) WITH_PRACTICE=0 ;;
    --with-gazebo) WITH_GAZEBO=1 ;;
    --with-bots) WITH_BOTS=1 ;;
    --no-ros) WITH_ROS=0; WITH_NAV2=0; WITH_LAB=0; WITH_GAZEBO=0 ;;
    --all) WITH_ROS=1; WITH_NAV2=1; WITH_LAB=1; WITH_PRACTICE=1; WITH_GAZEBO=1; WITH_BOTS=1 ;;
    --distro) shift; DISTRO="${1:-}" ;;
    --dir) shift; TARGET_DIR="${1:-}" ;;
    -y|--yes) ASSUME_YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# ---- helpers ----------------------------------------------------------------
say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33mWARNING: %s\033[0m\n' "$*" >&2; }
die()  { printf '\033[31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# run CMD...: execute, or just print under --dry-run
run() {
  if [ "$DRY_RUN" -eq 1 ]; then printf '+ %s\n' "$*"; else "$@"; fi
}

SUDO="sudo"
if [ "$(id -u)" -eq 0 ]; then
  SUDO=""
  warn "running as root: ~/.bashrc and virtualenvs will belong to root."
fi

apt_install() { run $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"; }

# ---- 1. OS and distro checks ------------------------------------------------
say "Checking the operating system"
UBUNTU_VERSION=""
if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  [ "${ID:-}" = "ubuntu" ] && UBUNTU_VERSION="${VERSION_ID:-}"
fi

if [ "$WITH_ROS" -eq 1 ]; then
  if [ -z "$DISTRO" ]; then
    case "$UBUNTU_VERSION" in
      22.04) DISTRO=humble ;;
      24.04) DISTRO=jazzy ;;
      *)
        if [ "$DRY_RUN" -eq 1 ]; then
          warn "not Ubuntu 22.04/24.04 (found '${UBUNTU_VERSION:-none}'); dry-run assumes jazzy"
          DISTRO=jazzy
        else
          die "ROS 2 install supports Ubuntu 22.04 (Humble) and 24.04 (Jazzy); found '${UBUNTU_VERSION:-non-Ubuntu}'. Use WSL2/Ubuntu, a VM, or 'docker run -it ros:jazzy'. See setup/INSTALL.md."
        fi ;;
    esac
  fi
  case "$DISTRO" in
    humble) REQUIRED_OS=22.04 ;;
    jazzy)  REQUIRED_OS=24.04 ;;
    *) die "--distro must be humble or jazzy (got '$DISTRO')" ;;
  esac
  if [ -n "$UBUNTU_VERSION" ] && [ "$UBUNTU_VERSION" != "$REQUIRED_OS" ]; then
    die "ROS 2 $DISTRO needs Ubuntu $REQUIRED_OS; this is Ubuntu $UBUNTU_VERSION."
  fi
  if [ "$DRY_RUN" -eq 0 ] && ! dpkg --print-architecture | grep -q 64; then
    die "a 64-bit system is required (found $(dpkg --print-architecture))."
  fi
  if grep -qi microsoft /proc/version 2>/dev/null; then
    warn "WSL detected: ROS works for building/tests/RViz, but reaching a robot over Wi-Fi needs mirrored networking (see setup/INSTALL.md)."
  fi
fi

# ---- 2. Summary and confirmation --------------------------------------------
onoff() { [ "$1" -eq 1 ] && echo yes || echo no; }
say "Plan"
cat <<EOF
  ROS 2 distro        : ${DISTRO:-n/a}
  ROS 2 (desktop)     : $(onoff "$WITH_ROS")
  Nav2 (waypoint)     : $(onoff "$WITH_NAV2")
  Lab tools           : $(onoff "$WITH_LAB")
  Python venvs+tests  : $(onoff "$WITH_PRACTICE")
  Gazebo (ros_gz)     : $(onoff "$WITH_GAZEBO")
  bots/ submodules    : $(onoff "$WITH_BOTS")
  Dry run             : $(onoff "$DRY_RUN")
EOF
if [ "$ASSUME_YES" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  printf 'Proceed? This uses sudo and downloads several GB. [y/N] '
  read -r reply
  case "$reply" in y|Y|yes|YES) ;; *) echo "Aborted."; exit 1 ;; esac
fi

# ---- 3. Base packages -------------------------------------------------------
say "Installing base packages"
run $SUDO apt-get update
apt_install git curl gnupg lsb-release ca-certificates software-properties-common \
            locales build-essential python3 python3-venv python3-pip \
            openssh-client rsync

if [ "$WITH_ROS" -eq 1 ]; then
  # ---- 4. ROS 2 --------------------------------------------------------------
  say "Setting up UTF-8 locale"
  run $SUDO locale-gen en_US en_US.UTF-8
  run $SUDO update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

  say "Adding the ROS 2 apt repository"
  run $SUDO add-apt-repository -y universe
  KEYRING=/usr/share/keyrings/ros-archive-keyring.gpg
  if [ ! -s "$KEYRING" ]; then
    run $SUDO curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o "$KEYRING"
  fi
  LIST=/etc/apt/sources.list.d/ros2.list
  if [ ! -e "$LIST" ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "+ write $LIST (deb [signed-by=$KEYRING] http://packages.ros.org/ros2/ubuntu <codename> main)"
    else
      echo "deb [arch=$(dpkg --print-architecture) signed-by=$KEYRING] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
        | $SUDO tee "$LIST" >/dev/null
    fi
  fi
  run $SUDO apt-get update

  say "Installing ROS 2 $DISTRO desktop and build tools (this takes a while)"
  apt_install "ros-$DISTRO-desktop" python3-colcon-common-extensions \
              python3-rosdep python3-vcstool python3-argcomplete
  if [ ! -e /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    run $SUDO rosdep init
  fi
  run rosdep update

  if [ "$WITH_NAV2" -eq 1 ]; then
    say "Installing Nav2 packages (waypoint mission)"
    apt_install "ros-$DISTRO-nav2-bringup" "ros-$DISTRO-nav2-simple-commander" \
                "ros-$DISTRO-nav2-msgs" "ros-$DISTRO-nav2-collision-monitor" \
                "ros-$DISTRO-nav2-map-server" "ros-$DISTRO-slam-toolbox"
  fi
  if [ "$WITH_LAB" -eq 1 ]; then
    say "Installing lab tools (turtlesim, teleop, rqt, vision)"
    apt_install "ros-$DISTRO-turtlesim" "ros-$DISTRO-teleop-twist-keyboard" \
                "ros-$DISTRO-rqt" "ros-$DISTRO-rqt-graph" "ros-$DISTRO-cv-bridge" \
                python3-opencv python3-numpy
  fi
  if [ "$WITH_GAZEBO" -eq 1 ]; then
    say "Installing Gazebo bridge packages"
    apt_install "ros-$DISTRO-ros-gz"
  fi

  say "Adding ROS to ~/.bashrc"
  SRC_LINE="source /opt/ros/$DISTRO/setup.bash"
  if ! grep -qF "$SRC_LINE" "$HOME/.bashrc" 2>/dev/null; then
    if [ "$DRY_RUN" -eq 1 ]; then echo "+ append '$SRC_LINE' to ~/.bashrc"
    else echo "$SRC_LINE" >> "$HOME/.bashrc"; fi
  fi
fi

# ---- 5. Repository ----------------------------------------------------------
say "Locating the repository"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -z "$TARGET_DIR" ] && [ -d "$SCRIPT_DIR/../waypoint_mission" ] && [ -e "$SCRIPT_DIR/../.git" ]; then
  REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  echo "Using this checkout: $REPO_DIR"
else
  REPO_DIR="${TARGET_DIR:-$DEFAULT_DIR}"
  if [ -e "$REPO_DIR/.git" ]; then
    echo "Updating existing clone: $REPO_DIR"
    run git -C "$REPO_DIR" pull --ff-only
  else
    echo "Cloning into: $REPO_DIR"
    run git clone "$REPO_URL" "$REPO_DIR"
  fi
fi
if [ "$WITH_BOTS" -eq 1 ]; then
  say "Fetching bots/ submodules (large)"
  run git -C "$REPO_DIR" submodule update --init --recursive
fi

# ---- 6. Python environments and tests ---------------------------------------
TEST_FAILED=0
make_venv() {   # make_venv DIR [extra venv flags...]
  local dir="$1"; shift
  if [ ! -d "$dir/.venv" ]; then run python3 -m venv "$@" "$dir/.venv"; fi
  run "$dir/.venv/bin/python" -m pip install --quiet --upgrade pip
  run "$dir/.venv/bin/python" -m pip install --quiet -r "$dir/requirements.txt"
}
run_tests() {   # run_tests DIR NAME
  say "Running tests: $2"
  if [ "$DRY_RUN" -eq 1 ]; then echo "+ (cd $1 && .venv/bin/python -m pytest -q)"; return; fi
  if ! (cd "$1" && .venv/bin/python -m pytest -q); then TEST_FAILED=1; fi
}

if [ "$WITH_PRACTICE" -eq 1 ]; then
  say "Creating Python environments"
  # --system-site-packages lets the mission venv see ROS's rclpy when ROS is installed
  make_venv "$REPO_DIR/waypoint_mission" --system-site-packages
  make_venv "$REPO_DIR/practice/robot_calc"
  run_tests "$REPO_DIR/waypoint_mission" "waypoint_mission (expect 60 passed)"
  run_tests "$REPO_DIR/practice/robot_calc" "robot_calc"
fi

# ---- 7. Verify ROS imports --------------------------------------------------
IMPORT_FAILED=0
if [ "$WITH_ROS" -eq 1 ] && [ "$WITH_NAV2" -eq 1 ]; then
  say "Checking the mission node's ROS imports"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "+ source /opt/ros/$DISTRO/setup.bash && python3 -c 'import rclpy, nav2_simple_commander...'"
  else
    set +u
    # shellcheck disable=SC1090
    . "/opt/ros/$DISTRO/setup.bash"
    set -u
    if python3 -c "import rclpy; from nav2_simple_commander.robot_navigator import BasicNavigator; from geometry_msgs.msg import PoseStamped; from std_msgs.msg import String" 2>/dev/null; then
      echo "OK: rclpy and nav2_simple_commander import."
    else
      warn "ROS imports failed - open a NEW terminal (so ~/.bashrc loads ROS) and re-run, or check the install log."
      IMPORT_FAILED=1
    fi
  fi
fi

# ---- 8. Summary -------------------------------------------------------------
say "Done"
echo "Repository : $REPO_DIR"
[ "$WITH_ROS" -eq 1 ] && echo "ROS 2      : $DISTRO  (open a new terminal, or: source /opt/ros/$DISTRO/setup.bash)"
if [ "$TEST_FAILED" -ne 0 ] || [ "$IMPORT_FAILED" -ne 0 ]; then
  warn "some checks failed - see the output above and setup/INSTALL.md (Troubleshooting)."
  exit 1
fi
cat <<EOF

Next steps
  Study guides     : $REPO_DIR/learn/README.md
  Lab manual       : $REPO_DIR/lab-manual/00-front-matter.md
  Waypoint mission : $REPO_DIR/waypoint_mission/README.md
     cd $REPO_DIR/waypoint_mission
     export ROS_DOMAIN_ID=<n>          # same as the robot
     python3 mission_node.py --count 3 # after surveying waypoints.yaml
  Practise without a robot: ros2 run turtlesim turtlesim_node
EOF
