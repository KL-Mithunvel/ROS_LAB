# robot_calc — mobile-robot mechatronics calculator

A small menu-driven CLI study tool (lab exercise). You set a handful of robot
parameters, then pick a **calculation set** — each set works out a whole group of
related mechatronics quantities at once (all the forces and torques, or speed and
gearing, or battery life, ...) and shows either the results table alone or the
full working.

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
  c  Calculation sets ......... pick one, then:
        a  View results only
        s  View results with full working
        e  Edit the parameters this set uses
        r  Run / recalculate
  e  Edit robot parameters ... edit every parameter
  p  Print all parameters
  v  Save parameters to params.yaml
  l  Reload parameters from params.yaml
  x  Exit
```

Parameter edits stay in memory until you choose **Save** — which asks first,
then rewrites `params.yaml` with the current values. The rewrite drops the
hand-written comments in the file (the values and key order are kept), so keep a
copy if the comments matter to you.

## The 5 calculation sets

### 1. `tractive_effort` — forces, wheel & motor torque, traction
Acceleration to reach top speed; the acceleration force, rolling resistance and
gravity-on-slope force; force to move on the flat and force to climb (both at
steady speed); the total tractive force; total wheel torque, torque per driven
wheel, and torque per motor (through the gearbox + efficiency, times the design
safety factor, as a % of motor stall torque); the friction available at the
driven wheels, the traction margin with a slip verdict, and the steepest slope
the wheels can hold.

### 2. `speed_gearing` — speed, wheel rpm & gearing
Max no-load linear speed (m/s and km/h) from the wheel-output rpm and radius; the
wheel angular speed and rpm needed for the target top speed; and the motor-shaft
rpm that implies through the gear ratio.

### 3. `battery_power` — battery runtime, range & drive power
Usable capacity, runtime (h and min), range at top speed (m and km), the
electrical drive power to hold top speed up the slope, and the pack current that
draws.

### 4. `dd_kinematics` — differential-drive kinematics (forward & inverse)
**Forward:** wheel angular velocities → body `v`, `omega`, and global `x_dot`,
`y_dot`. **Inverse:** a circular path (`path_radius_m`, `path_linear_speed_mps`) →
the wheel ground speeds and angular velocities to follow it.

### 5. `dd_dynamics` — differential-drive dynamics (acceleration & pure spin)
**Straight-line:** acceleration, total force, force per driven wheel and torque
per wheel (frictionless, no gearbox). **Pure spin:** chassis torque from `I·alpha`,
the wheel-force couple, and the right/left motor torques (the left one is
negative — it brakes).

Sets 4 and 5 are the worked problems from
`docs/Kinematics and Dynamics_AMR_Problems.pdf` — they reproduce the handout's
numbers when the parameters are set to the PDF's values (asserted in the tests).

**[`SAMPLE_OUTPUT.md`](SAMPLE_OUTPUT.md)** has every set run on the default
`params.yaml`, with the full working and the results table. Regenerate it after
changing a formula or a default with `python make_sample_output.py`.

### Assumptions

* `climb_angle_deg = 0` makes every slope term vanish — use it for flat-ground work.
* Two different coefficients: `rolling_resistance_coeff` (C_rr, wheel/bearing drag)
  and `surface_friction_coeff` (mu_s, the slip/grip limit). Not the same thing.
* Weight is assumed even across the wheels, payload rigid and level.
* `motor_no_load_rpm` is the **wheel** output speed (after the gearbox); the
  motor-shaft speed is that times `gear_ratio`.

## Parameters (`params.yaml`)

Each entry is `{value, unit, desc, confirm}`. `confirm: true` marks a seed value
that is an estimate — replace it with a real figure for your robot. The seeds are
for the VEEROBOT BeetleBot (`docs/beetlebot/01-introduction.md`); mass, pack
voltage and capacity are from its spec sheet, the rest (`wheel_radius_m`,
`gear_ratio`, `motor_no_load_rpm`, `accel_time_s`, `climb_angle_deg`,
`track_width_m`, `moment_of_inertia_kgm2`, the coefficients, the diff-drive
example inputs) are placeholders.

## Add a quantity or a set

To add one quantity to an existing set: compute it inside that set's function in
`calculations.py` and append a `Quantity(name, value, unit)` to `outputs` (and a
`Step(...)` if you want it shown in the working).

To add a whole new set:

```python
def calc_turn_radius(P):
    r = P["track_width_m"] / 2.0 / math.tan(math.radians(P["steer_angle_deg"]))
    return CalcResult(
        "Minimum turn radius",
        outputs=[Quantity("minimum turn radius", r, "m")],
        steps=[Step("Ackermann geometry",
                    "R = (track / 2) / tan(delta)",
                    f"R = ({_n(P['track_width_m'])}/2) / tan({_n(P['steer_angle_deg'])} deg)",
                    f"{_n(r)} m")])
```

1. Add any new parameters to `params.yaml`.
2. Register the set in `CALCS`:
   `Calc("turn_radius", "Minimum turn radius", ["track_width_m", "steer_angle_deg"], calc_turn_radius)`
3. Add a test in `tests/test_calculations.py`.

The menu entry and its sub-menu are generated from `CALCS` automatically.

## Tests

```powershell
.venv\Scripts\activate
pytest
```
