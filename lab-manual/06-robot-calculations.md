# Experiment 6 — Mobile-robot mechatronics calculations

## 1. Aim
To size a mobile robot numerically — tractive effort, motor torque, speed and gearing, battery runtime — and to analyse a differential-drive robot's kinematics and dynamics, using a menu-driven Python program (`robot_calc/`) and checking it against hand calculations.

## 2. Learning outcomes
Compute the forces a drive system must overcome; convert wheel torque to motor torque through a gearbox; relate wheel and motor rpm to linear speed; estimate battery runtime and range; apply forward and inverse kinematics of a differential-drive robot; estimate torque for straight-line acceleration and for spinning in place.

## 3. Apparatus
- Any computer with Python 3.10+ (Windows, Linux or macOS) — no robot or ROS needed
- `robot_calc/` from this repo (`main.py`, `params.yaml`)
- `docs/Kinematics and Dynamics_AMR_Problems.pdf` (worked problems)
- Robot data sheet: mass, wheel radius, gear ratio, motor rpm and stall torque, battery voltage and capacity (BeetleBot figures: `docs/beetlebot/01-introduction.md`)
- Calculator for hand checks

## 4. Theory
Symbols: *m* mass, *g* = 9.81, *θ* slope, *r* wheel radius, *L* track width, *G* gear ratio, *η* efficiency.

**4.1 Tractive effort (set 1)**

| Quantity | Formula |
|---|---|
| Acceleration to top speed | a = v_top / t_acc |
| Normal force | N = m·g·cos θ |
| Acceleration force | F_a = m·a |
| Rolling resistance | F_rr = C_rr·N |
| Slope force | F_g = m·g·sin θ |
| **Total tractive force** | F_total = F_a + F_rr + F_g |
| Wheel torque | T_total = F_total·r ; per driven wheel T_wheel = T_total / n_driven |
| Motor torque | T_motor = T_wheel / (G·η) ; specified T_spec = T_motor·SF |
| Grip available | F_traction = μ_s·N·(driven/total wheels) |
| Traction margin | F_traction − F_total (negative ⇒ wheels slip); steepest slope tan θ_max = μ_s·(driven/total) − C_rr |

C_rr (wheel and bearing drag) and μ_s (the grip limit before slipping) are different coefficients.

**4.2 Speed and gearing (set 2)** — ω = rpm/60·2π ; v = ω·r ; ω_target = v_top/r ; rpm_motor = rpm_wheel·G.

**4.3 Battery (set 3)** — Q_usable = Q_pack·usable fraction ; runtime t = Q_usable/I_avg ; range d = t·3600·v_top ; climbing force F_climb = C_rr·m·g·cos θ + m·g·sin θ ; P_elec = F_climb·v_top/η ; I = P_elec/V_pack.

**4.4 Differential-drive kinematics (set 4)**
- Forward: v_r = r·ω_r, v_l = r·ω_l ; **v = r(ω_r + ω_l)/2**, **ω = r(ω_r − ω_l)/L** ; ẋ = v cos θ, ẏ = v sin θ.
- Inverse (circular path of radius R at speed v): ω = v/R ; v_r = v + ωL/2, v_l = v − ωL/2 ; wheel ω = v_wheel/r.

**4.5 Differential-drive dynamics (set 5)**
- Straight line: a = (v_f − v_i)/t ; F_total = m·a ; F_wheel = F_total/n_driven ; τ = F_wheel·r.
- Pure spin: T_chassis = I·α ; the wheel forces form a couple, F = T_chassis/L ; τ_r = F·r, τ_l = −F·r (the left motor brakes).

## 5. Pre-lab questions
1. Why must the slope term vanish when `climb_angle_deg = 0`?
2. If the wheel output speed is 200 rpm and G = 30, what is the motor-shaft speed?
3. Derive v and ω of a differential-drive robot from the two wheel speeds.
4. Why does a motor sized only for steady speed fail to accelerate the robot?

## 6. Procedure
1. Set up:
   ```bash
   cd robot_calc
   python3 -m venv .venv && source .venv/bin/activate     # Windows: py -m venv .venv ; .venv\Scripts\activate
   pip install -r requirements.txt
   pytest                                                  # expect all tests pass
   python main.py
   ```
2. **Hand calculation first.** For the BeetleBot values in `params.yaml`, compute set 1 by hand and write each step.
3. In the menu choose `c` (calculation sets) → set 1 `tractive_effort` → `s` (results with full working). Compare line by line with your hand work.
4. Repeat for sets 2 and 3. Use `e` inside a set to edit only the parameters it uses (e.g. change `climb_angle_deg` to 10° and record the change in motor torque).
5. **PDF problems.** Set the parameters to those of Problems 1–4 in the PDF (use `e`), run sets 4 and 5, and compare with the printed answers.
6. Replace the `confirm: true` estimates with the real values from the data sheet / measurement (wheel radius with a ruler, track width, mass on a scale), run all sets, and save with `v` (it asks first; saving rewrites `params.yaml` and drops its comments — keep a copy).
7. Regenerate the sample output if you changed a formula or default: `python make_sample_output.py`.
8. *(Optional, with a robot)* measure top speed over a known distance and runtime on a battery, and compare with the prediction.

## 7. Observations

**7.1 Parameters used**

| Parameter | Value | Unit | Source (data sheet / measured / estimate) |
|---|---|---|---|
| mass | | kg | |
| wheel radius | | m | |
| gear ratio | | – | |
| track width | | m | |
| top speed, accel time | | m/s, s | |
| battery voltage, capacity | | V, Ah | |

**7.2 Set 1 — hand vs program**

| Quantity | Hand | Program |
|---|---|---|
| Acceleration (m/s²) | | |
| F_a, F_rr, F_g (N) | | |
| F_total (N) | | |
| Wheel torque, per-wheel torque (N·m) | | |
| Torque per motor (N·m), % of stall | | |
| Traction margin (N), verdict | | |

**7.3 Sets 2–3**

| Quantity | Value |
|---|---|
| No-load speed (m/s, km/h) | |
| Wheel rpm / motor rpm at target speed | |
| Runtime (min) / range (km) | |
| Drive power (W) / pack current (A) | |

**7.4 PDF problems (sets 4–5)**

| Problem | Quantity | PDF | Program |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |

**7.5 Sensitivity** — change one parameter at a time:

| Parameter changed | From → to | Quantity affected | Change |
|---|---|---|---|
| climb angle | 0° → 10° | torque per motor | |
| mass | | runtime | |

## 8. Result
☐ State the sized motor torque and the margin against stall, the predicted runtime, and that the program matches the hand calculations and the PDF answers.

## 9. Viva questions
1. List the three components of tractive force and which dominates on the flat.
2. Why include the gearbox efficiency and a safety factor in motor torque?
3. Why can the traction margin be negative even when the motor has enough torque?
4. Why is one motor torque negative in the pure-spin case?
5. How does doubling the gear ratio change motor torque and motor rpm?
6. What assumptions does the model make (even weight distribution, rigid payload, no slip in the kinematics)?
7. Which parameters in your run were estimates, and how would you measure them?
