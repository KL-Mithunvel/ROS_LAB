# Nav2 Optimization Guide

***

This guide provides targeted optimizations for Beetlebot's `nav2_params.yaml` configuration to improve obstacle avoidance and navigation reliability, particularly when navigating tight spaces or corridors.

By applying these tuning suggestions, you can significantly enhance the smoothness of the robot's trajectories and prevent common edge-case navigation freezing.

### 1. Costmap Inflation Radius

**Symptom:** The robot attempts to drive too close to walls or pauses frequently when navigating narrow corridors.

**Optimization:** Increase the `inflation_radius` in both `local_costmap` and `global_costmap`.

* **Current Typical Value:** `0.25m` to `0.3m`
* **Suggested Value:** `0.7m` to `1.0m` (along with a slightly lower `cost_scaling_factor`)
* **Reasoning:** A larger inflation radius creates a stronger cost gradient away from walls, encouraging the global planner to naturally route the robot down the center of hallways rather than hugging edges.

***

### 2. Velocity-Scaled Lookahead

**Symptom:** The robot's trajectory becomes erratic or the robot stops near obstacles because it is looking too far ahead on the path.

**Optimization:** Enable dynamic scaling of the lookahead distance in the `FollowPath` controller (Regulated Pure Pursuit).

* **Setting:** Change `use_velocity_scaled_lookahead_dist` to `true`.
* **Reasoning:** When enabled, the controller will use the `min_lookahead_dist` (e.g., `0.2m`) when driving slowly or maneuvering near obstacles, and the standard `lookahead_dist` (e.g., `0.4m`) when driving at speed. This allows for much finer control and prevents looking "through" adjacent obstacles.

***

### 3. Rotate to Heading Angle Threshold

**Symptom:** The robot swings its corners into walls when trying to turn while moving forward.

**Optimization:** Reduce the threshold at which the robot decides to rotate in place rather than driving in a wide arc.

* **Setting:** Decrease `rotate_to_heading_min_angle` from `0.785` (45°) to `0.2` or `0.3` rad (11-17°).
* **Reasoning:** For a skid-steer base, rotating in place is often safer in tight quarters. A lower threshold ensures the robot rotates to face its path before driving forward, minimizing outward corner sweeping.

***

### 4. Transform Tolerance

**Symptom:** Jerky braking or delayed obstacle avoidance, especially when moving quickly.

**Optimization:** Reduce `transform_tolerance` across AMCL, costmaps, and the controller.

* **Current Value:** `1.0` seconds
* **Suggested Value:** `0.2` to `0.5` seconds
* **Reasoning:** A high tolerance can mask latency issues on slower CPUs, but it allows the navigation stack to use stale position data (up to 1 second old). Tuning this down ensures the robot reacts to obstacles based on its true, real-time position.

***

### 5. Reversing Behavior

**Symptom:** The robot gets stuck in corners and cannot back up fluidly to clear the turn.

**Optimization:** Allow the local controller to reverse.

* **Setting:** Change `allow_reversing` to `true` in the `FollowPath` configuration.
* **Reasoning:** Allowing the Regulated Pure Pursuit controller to plan reverse maneuvers provides an immediate, smooth escape from tight spots without triggering the slower, generic backup recovery behavior.
