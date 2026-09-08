# robot_calc — mobile-robot mechatronics calculator

A small menu-driven CLI study tool (lab exercise). You set a handful of robot
parameters, then it works out the mechatronics quantities you need when sizing a
mobile robot's drivetrain — force, torque, speed, battery runtime — and shows
either the bare answer or the full worked steps.

Built on the [`klm_menu`](https://github.com/KL-Mithunvel/menu) engine, same
pattern as [`Furnace_simulation`](https://github.com/KL-Mithunvel/Furnace_simulation).

## Run it

```powershell
cd practice\robot_calc
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

(Linux/macOS: `python3 -m venv .venv && source .venv/bin/activate`.)

## Menu

```
Mobile Robot Mechatronics Calculator
  c  All calculations ........ pick one, then:
        a  View answer only
        s  View answer with full steps
        e  Edit the parameters this calculation uses
        r  Run / recalculate
  e  Edit robot parameters ... edit every parameter
  p  Print all parameters
  v  Save parameters to params.yaml
  l  Reload parameters from params.yaml
  x  Exit
```

Parameter edits stay in memory until you choose **Save** — then they are written
back to `params.yaml`.

## Calculations

| id | what it gives |
|----|---------------|
| `acceleration` | average acceleration to reach top speed in the set time |
| `accel_force` | force to produce that acceleration (`F = m a`) |
| `friction_force` | grip available at the driven wheels before they slip (`mu_s N`) |
| `rolling_resistance` | rolling/bearing drag (`C_rr N`) |
| `gravity_slope` | weight component down the slope (`m g sin theta`) |
| `force_to_move` | force to move on flat ground at steady speed |
| `force_to_climb` | force to climb the slope at steady speed (rolling + gravity) |
| `total_force` | total tractive force = accel + rolling + gravity |
| `total_torque` | total wheel torque (`F_total r`) |
| `torque_per_wheel` | that torque split across the driven wheels |
| `motor_torque` | torque per motor: wheel torque through the gearbox + efficiency, times a design safety factor, checked against motor stall torque |
| `max_speed` | no-load top speed from wheel rpm and radius |
| `wheel_rpm` | wheel rev/min needed for the target top speed |
| `battery_runtime` | runtime and range from capacity and average current |
| `drive_power` | power/current to hold top speed up the slope |
| `traction_check` | does the required force exceed the available grip? |
| `fwd_kinematics` | diff-drive forward kinematics: wheel speeds -> body `v`, `omega`, and global `x_dot`, `y_dot` |
| `inv_kinematics` | diff-drive inverse kinematics: circular path (`R`, `v`) -> wheel angular velocities |
| `dd_accel_torque` | straight-line acceleration torque per wheel (frictionless, no gearbox) |
| `dd_spin_torque` | pure spin-on-the-spot: torque from each wheel motor (one drives, one brakes) |

The last four are the worked cases from
`docs/Kinematics and Dynamics_AMR_Problems.pdf` (differential-drive kinematics
and dynamics). Each reproduces the handout's answer when you set its parameters
to the values in the PDF — see the notes printed with each one. They use the
extra parameters `track_width_m`, `wheel_omega_left_rads`, `wheel_omega_right_rads`,
`heading_deg`, `path_linear_speed_mps`, `path_radius_m`, `initial_speed_mps`,
`moment_of_inertia_kgm2`, `angular_accel_rads2`.

### Sign conventions / assumptions

* `climb_angle_deg = 0` makes every slope term vanish — use it for flat-ground work.
* Two different coefficients: `rolling_resistance_coeff` (C_rr, wheel drag) and
  `surface_friction_coeff` (mu_s, the slip/grip limit). They are not the same thing.
* Weight is assumed evenly spread across the wheels, payload rigid and level.
* `max_speed` treats `motor_no_load_rpm` as the **wheel** output speed (after the
  gearbox). `motor_torque` uses `gear_ratio` to go from wheel torque to motor torque.

## Parameters (`params.yaml`)

Each entry is `{value, unit, desc, confirm}`. `confirm: true` marks a seed value
that is an estimate — replace it with a real figure for your robot. The seeds are
for the VEEROBOT BeetleBot (`docs/beetlebot/01-introduction.md`); mass, pack
voltage and capacity are from its spec sheet, the rest (`wheel_radius_m`,
`gear_ratio`, `motor_no_load_rpm`, `accel_time_s`, `climb_angle_deg`, the
coefficients) are placeholders.

## Add a calculation

1. In `calculations.py`, write a function that returns a `CalcResult`:

   ```python
   def calc_wheelbase_turn_radius(P):
       r = P["track_width_m"] / 2.0 / math.tan(math.radians(P["steer_angle_deg"]))
       return CalcResult(
           "Minimum turn radius", r, "m",
           steps=[Step("Ackermann geometry",
                       "R = (track / 2) / tan(delta)",
                       f"R = ({P['track_width_m']}/2) / tan({P['steer_angle_deg']} deg)",
                       f"{r:.4g} m")],
           notes=["..."])
   ```

2. Add any new parameters to `params.yaml`.
3. Register it in the `CALCS` list:

   ```python
   Calc("turn_radius", "Minimum turn radius",
        ["track_width_m", "steer_angle_deg"], calc_wheelbase_turn_radius),
   ```

4. Add an expected value to `tests/test_calculations.py` (`EXPECTED`).

The menu entry and its sub-menu are generated from `CALCS` automatically.

## Tests

```powershell
.venv\Scripts\activate
pytest
```
