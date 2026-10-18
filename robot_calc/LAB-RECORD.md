# Lab Record — Mobile-Robot Mechatronics Calculator

| | |
|---|---|
| **Student** | kl mithunvel |
| **Course** | BMHA314E — Autonomous Mobile Robots (practical) |
| **Experiment** | Numerical modelling of a mobile robot: tractive effort, motor sizing, speed/gearing, battery runtime, differential-drive kinematics and dynamics — as a menu-driven program |
| **Robot modelled** | VEEROBOT BeetleBot (seed values); any robot via `params.yaml` |
| **Period covered** | 2026-09-08 (all development done in one day) |
| **Status** | Program complete and unit-tested (14 tests). Several parameters are **estimates** (`confirm: true`) awaiting real BeetleBot values — sections marked ☐ are to be filled in. |

> **Honesty note.** The program's numbers are only as good as its inputs. Every parameter
> flagged `confirm: true` in `params.yaml` is a placeholder, so the shipped `SAMPLE_OUTPUT.md`
> shows the *method working*, not measured BeetleBot performance.

---

## 1. Aim
To write a program that computes, from a set of robot parameters, the quantities needed to size
and analyse a mobile robot — forces, torques, speed, gearing, battery runtime, and
differential-drive kinematics/dynamics — and shows both the results and the full working.

## 2. Apparatus and software
| Item | Detail |
|---|---|
| Language / tools | Python 3, PyYAML, pytest, `py -m venv` |
| Menu engine | `klm_menu.py`, copied verbatim from github.com/KL-Mithunvel/menu |
| Source problems | `docs/Kinematics and Dynamics_AMR_Problems.pdf` (worked differential-drive problems) |
| Robot data | `docs/beetlebot/01-introduction.md` (mass, pack voltage, capacity) |

## 3. Design
The user wanted a list of calculations, and for each: *view answer / view answer with steps /
edit parameters / run*.

| Decision | Choice |
|---|---|
| Parameters | `params.yaml`, each as `{value, unit, desc, confirm}` (28 parameters) |
| Structure | A `CALCS` registry; the menu is generated from it, so adding a set adds its menu entries |
| Granularity | First version: 20 single-output calculations. Judged too many → **regrouped into 5 sets**, each computing a whole group of related quantities |
| Output | A results table, or the full working (formula → substitution → result) then the table and notes |

### The five calculation sets
| # | Set | Computes |
|---|---|---|
| 1 | `tractive_effort` | acceleration; acceleration, rolling-resistance and slope forces; total tractive force; wheel torque, per-wheel and per-motor torque (gearbox efficiency, safety factor, % of stall); traction margin with slip verdict; maximum climbable slope |
| 2 | `speed_gearing` | max no-load speed (m/s, km/h); wheel rpm and motor-shaft rpm at the target speed |
| 3 | `battery_power` | usable capacity, runtime, range, drive power and pack current on the slope |
| 4 | `dd_kinematics` | differential-drive forward kinematics (wheel speeds → v, ω, ẋ, ẏ) and inverse kinematics (circular path → wheel speeds) |
| 5 | `dd_dynamics` | straight-line acceleration force/torque; pure-spin chassis torque, wheel couple, motor torques |

Sets 4 and 5 reproduce the numeric answers of the PDF problems when given its parameters
(asserted in the tests).

## 4. Chronological log

| Date | Commit | Work |
|---|---|---|
| 2026-09-08 | `5f88957` | **Menu system** — `klm_menu.py` engine and the first `main.py`; the PDF of worked problems added to `docs/` |
| 2026-09-08 | `f7eba9e` | **Calculations** — first version: `calculations.py` with 20 one-output calculations, `parameters.py`, `params.yaml`, `main.py`, 32 tests (PDF problems 1–4 added mid-task) |
| 2026-09-08 | `cb8c855` | **Regrouped into 5 sets** — `CalcResult` redesigned to hold a list of quantities; tests rewritten (12 cases); menu wording changed |
| 2026-09-08 | `5823e04` | **Docs and hardening** — `make_sample_output.py` + `SAMPLE_OUTPUT.md`; error handling reviewed: clean exit on Ctrl-C/Ctrl-D, malformed or missing `params.yaml` reported (not a traceback), `save()` asks before overwriting (the YAML rewrite drops comments), unknown keys skipped, 2 more tests → **14** |
| 2026-10-18 | — | Moved from `practice/robot_calc/` to the repo root as `robot_calc/` (lab experiment 6) |

### Bugs found and fixed in review
| Bug | Fix |
|---|---|
| Traceback on Ctrl-C / Ctrl-D / end of piped input | `main()` catches `EOFError`/`KeyboardInterrupt` |
| Non-numeric value in YAML crashed a calculation | `resolve()` moved inside the `try`; `ArithmeticError` also caught |
| Malformed `params.yaml` gave a raw YAML error | wrapped as `ValueError` with each entry checked for a `value` key |
| Save silently overwrote the file | asks first; handles `OSError` |

## 5. Procedure used to verify
1. Create the venv and install requirements; `py_compile` clean.
2. `pytest` — **14 passed** (re-run after the 2026-10-18 move).
3. Drive all 5 sets through the menu with piped input (results and working views); `params.yaml` unchanged by the run.
4. Compare sets 4–5 with the PDF's worked answers (done by the tests).

## 6. Observations and results

### 6.1 Program vs hand calculation (PDF problems)
| Problem | Quantity | PDF answer | Program answer | Match? |
|---|---|---|---|---|
| 1 | ☐ | ☐ | ☐ | ☐ |
| 2 | ☐ | ☐ | ☐ | ☐ |
| 3 | ☐ | ☐ | ☐ | ☐ |
| 4 | ☐ | ☐ | ☐ | ☐ |

### 6.2 Real BeetleBot parameters (replace the `confirm: true` estimates)
| Parameter | Seed (estimate) | Real value | Source |
|---|---|---|---|
| `wheel_radius_m` | | ☐ | |
| `gear_ratio` | | ☐ | |
| `motor_no_load_rpm` (wheel output) | | ☐ | |
| `track_width_m` | | ☐ | |
| `accel_time_s` | | ☐ | |
| `climb_angle_deg` | | ☐ | |
| `moment_of_inertia_kgm2` | | ☐ | |
| `rolling_resistance_coeff`, `surface_friction_coeff` | | ☐ | |

### 6.3 Results for the real robot
| Set | Key output | Value | Comment |
|---|---|---|---|
| tractive_effort | torque per motor / % of stall | ☐ | ☐ |
| tractive_effort | traction margin, slip verdict | ☐ | ☐ |
| speed_gearing | motor rpm at target speed | ☐ | ☐ |
| battery_power | runtime / range | ☐ | ☐ |
| dd_kinematics | wheel speeds for the test circle | ☐ | ☐ |
| dd_dynamics | spin torque | ☐ | ☐ |

### 6.4 Prediction vs measurement (optional, with the robot)
| Quantity | Predicted | Measured | Error % |
|---|---|---|---|
| Top speed (m/s) | ☐ | ☐ | ☐ |
| Runtime (min) | ☐ | ☐ | ☐ |

## 7. Result (to be completed)
☐ State that the program reproduces the handout answers and give the sized motor torque and runtime for the real robot.

## 8. Viva questions
1. Why is the total tractive force the sum of acceleration, rolling-resistance and slope terms?
2. Why do rolling resistance C_rr and the friction coefficient μ_s differ? Which limits slip?
3. How is motor torque obtained from wheel torque, and why include gearbox efficiency and a safety factor?
4. Derive v = r(ω_r + ω_l)/2 and ω = r(ω_r − ω_l)/L.
5. In the pure-spin case why is one motor torque negative?
6. Why was the program regrouped from 20 calculations into 5 sets?
7. What is the effect of `climb_angle_deg = 0`?

## 9. Conclusion (to be completed)
☐ Write after replacing the estimated parameters.

## 10. Files
See [`README.md`](README.md) (run instructions, how to add a set) and [`SAMPLE_OUTPUT.md`](SAMPLE_OUTPUT.md).
