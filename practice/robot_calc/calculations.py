"""
calculations.py — mechatronics calculations for a mobile robot.

Each calculation is a function  fn(P) -> CalcResult  where P is the flat
parameter dict {key: float} produced by parameters.resolve().

A CalcResult carries:
  * the final value + unit
  * a list of Step objects (formula -> substitution -> result) for the
    "show full steps" view
  * optional notes and extra derived figures

To add a calculation:
  1. write  def calc_<name>(P): ... return CalcResult(...)
  2. add  Calc("<id>", "<menu title>", ["param_key", ...], calc_<name>)  to CALCS
The menu entries are generated from CALCS automatically.
"""

import math
from dataclasses import dataclass, field
from typing import Callable, List


# --------------------------------------------------------------------------- #
# Result structures
# --------------------------------------------------------------------------- #

@dataclass
class Step:
    text: str                 # what this step does, in words
    formula: str = ""         # symbolic form, e.g. "F = m * a"
    substitution: str = ""    # numbers plugged in
    result: str = ""          # the value this step produces


@dataclass
class CalcResult:
    quantity: str             # name of the thing computed
    value: float
    unit: str
    steps: List[Step] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    extras: List[tuple] = field(default_factory=list)   # (label, value, unit)


@dataclass
class Calc:
    id: str
    title: str
    uses: List[str]           # parameter keys this calculation reads
    fn: Callable


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _n(x, digits=4):
    """Format a number for display."""
    return f"{x:.{digits}g}"


def _require_positive(P, *keys):
    for key in keys:
        if P[key] <= 0:
            raise ValueError(f"'{key}' must be greater than 0 (got {P[key]})")


def _theta_rad(P):
    return math.radians(P["climb_angle_deg"])


def _acceleration(P):
    _require_positive(P, "accel_time_s")
    return P["top_speed_mps"] / P["accel_time_s"]


def _normal_force(P):
    """Weight component pressing the wheels onto the ground:  m * g * cos(theta)."""
    return P["mass_kg"] * P["gravity_mps2"] * math.cos(_theta_rad(P))


def _rolling_resistance(P):
    return P["rolling_resistance_coeff"] * _normal_force(P)


def _grade_force(P):
    """Weight component along the slope:  m * g * sin(theta)."""
    return P["mass_kg"] * P["gravity_mps2"] * math.sin(_theta_rad(P))


def _accel_force(P):
    return P["mass_kg"] * _acceleration(P)


def _total_tractive_force(P):
    """Force to accelerate up the slope against rolling resistance."""
    return _accel_force(P) + _rolling_resistance(P) + _grade_force(P)


def _mgcos_str(P):
    return f"{_n(P['mass_kg'])} * {_n(P['gravity_mps2'])} * cos({_n(P['climb_angle_deg'])} deg)"


def _mgsin_str(P):
    return f"{_n(P['mass_kg'])} * {_n(P['gravity_mps2'])} * sin({_n(P['climb_angle_deg'])} deg)"


# --------------------------------------------------------------------------- #
# Calculations
# --------------------------------------------------------------------------- #

def calc_acceleration(P):
    a = _acceleration(P)
    return CalcResult(
        "Acceleration required (rest to top speed)", a, "m/s^2",
        steps=[Step(
            "Average acceleration = speed gained / time taken",
            "a = v_top / t_acc",
            f"a = {_n(P['top_speed_mps'])} / {_n(P['accel_time_s'])}",
            f"{_n(a)} m/s^2")],
        notes=["Assumes constant (average) acceleration during the ramp-up."])


def calc_accel_force(P):
    a = _acceleration(P)
    f = _accel_force(P)
    return CalcResult(
        "Force to accelerate the robot", f, "N",
        steps=[
            Step("First find the acceleration",
                 "a = v_top / t_acc",
                 f"a = {_n(P['top_speed_mps'])} / {_n(P['accel_time_s'])}",
                 f"{_n(a)} m/s^2"),
            Step("Newton's second law: force = mass x acceleration",
                 "F_a = m * a",
                 f"F_a = {_n(P['mass_kg'])} * {_n(a)}",
                 f"{_n(f)} N"),
        ],
        notes=["This is only the part of the force that goes into speeding up.",
               "Add rolling resistance and any slope force separately."])


def calc_friction_force(P):
    frac = P["driven_wheels"] / P["total_wheels"]
    n = _normal_force(P)
    n_driven = n * frac
    f = P["surface_friction_coeff"] * n_driven
    return CalcResult(
        "Available friction / traction force (driven wheels)", f, "N",
        steps=[
            Step("Normal force from the whole robot",
                 "N = m * g * cos(theta)",
                 f"N = {_mgcos_str(P)}",
                 f"{_n(n)} N"),
            Step("Share of that weight carried by the driven wheels",
                 "N_driven = N * (driven_wheels / total_wheels)",
                 f"N_driven = {_n(n)} * ({_n(P['driven_wheels'])} / {_n(P['total_wheels'])})",
                 f"{_n(n_driven)} N"),
            Step("Maximum grip before the driven wheels slip",
                 "F_fric = mu_s * N_driven",
                 f"F_fric = {_n(P['surface_friction_coeff'])} * {_n(n_driven)}",
                 f"{_n(f)} N"),
        ],
        notes=["This is the traction limit - the most push the wheels can give.",
               "If driven_wheels = total_wheels then N_driven = N.",
               "Assumes weight is shared evenly across the wheels."])


def calc_rolling_resistance(P):
    n = _normal_force(P)
    f = _rolling_resistance(P)
    return CalcResult(
        "Rolling resistance force", f, "N",
        steps=[
            Step("Normal force pressing the wheels onto the ground",
                 "N = m * g * cos(theta)",
                 f"N = {_mgcos_str(P)}",
                 f"{_n(n)} N"),
            Step("Rolling resistance is proportional to the normal force",
                 "F_rr = C_rr * N",
                 f"F_rr = {_n(P['rolling_resistance_coeff'])} * {_n(n)}",
                 f"{_n(f)} N"),
        ],
        notes=["On flat ground set climb_angle_deg = 0 so cos(theta) = 1.",
               "C_rr (wheel/bearing drag) is not the same as mu_s (slip grip)."])


def calc_gravity_slope(P):
    f = _grade_force(P)
    return CalcResult(
        "Gravity force component along the slope", f, "N",
        steps=[Step(
            "Only the part of the weight pointing down the slope resists a climb",
            "F_g = m * g * sin(theta)",
            f"F_g = {_mgsin_str(P)}",
            f"{_n(f)} N")],
        notes=["theta = 0 -> F_g = 0.   theta = 90 deg -> F_g = m * g (full weight)."])


def calc_force_to_move(P):
    n = P["mass_kg"] * P["gravity_mps2"]           # flat ground -> cos(0) = 1
    f = P["rolling_resistance_coeff"] * n
    return CalcResult(
        "Force required to move the robot (flat, steady speed)", f, "N",
        steps=[
            Step("On flat ground at steady speed the only resistance is rolling resistance",
                 "F = C_rr * m * g",
                 f"F = {_n(P['rolling_resistance_coeff'])} * {_n(P['mass_kg'])} * {_n(P['gravity_mps2'])}",
                 f"{_n(f)} N"),
        ],
        notes=["Steady speed -> no acceleration term.  Flat ground -> no slope term.",
               "Uses climb angle = 0 whatever climb_angle_deg is set to."])


def calc_force_to_climb(P):
    rr = _rolling_resistance(P)
    gr = _grade_force(P)
    f = rr + gr
    return CalcResult(
        "Force needed to climb the slope (steady speed)", f, "N",
        steps=[
            Step("Rolling resistance on the slope",
                 "F_rr = C_rr * m * g * cos(theta)",
                 f"F_rr = {_n(P['rolling_resistance_coeff'])} * {_mgcos_str(P)}",
                 f"{_n(rr)} N"),
            Step("Weight component down the slope",
                 "F_g = m * g * sin(theta)",
                 f"F_g = {_mgsin_str(P)}",
                 f"{_n(gr)} N"),
            Step("Force to climb at steady speed = sum of the two",
                 "F_climb = F_rr + F_g",
                 f"F_climb = {_n(rr)} + {_n(gr)}",
                 f"{_n(f)} N"),
        ],
        notes=["Steady speed climb - no acceleration term.",
               "If the robot must also speed up on the slope, add the acceleration force."])


def calc_total_tractive_force(P):
    fa = _accel_force(P)
    rr = _rolling_resistance(P)
    gr = _grade_force(P)
    f = fa + rr + gr
    return CalcResult(
        "Total tractive force required", f, "N",
        steps=[
            Step("Acceleration force",
                 "F_a = m * (v_top / t_acc)",
                 f"F_a = {_n(P['mass_kg'])} * ({_n(P['top_speed_mps'])} / {_n(P['accel_time_s'])})",
                 f"{_n(fa)} N"),
            Step("Rolling resistance",
                 "F_rr = C_rr * m * g * cos(theta)",
                 f"F_rr = {_n(P['rolling_resistance_coeff'])} * {_mgcos_str(P)}",
                 f"{_n(rr)} N"),
            Step("Gravity component along the slope",
                 "F_g = m * g * sin(theta)",
                 f"F_g = {_mgsin_str(P)}",
                 f"{_n(gr)} N"),
            Step("Total force the drivetrain must provide",
                 "F_total = F_a + F_rr + F_g",
                 f"F_total = {_n(fa)} + {_n(rr)} + {_n(gr)}",
                 f"{_n(f)} N"),
        ],
        notes=["Worst case: accelerating up the slope at the same time.",
               "For flat cruising set climb_angle_deg = 0 and a long accel_time_s."])


def calc_total_wheel_torque(P):
    f = _total_tractive_force(P)
    _require_positive(P, "wheel_radius_m")
    r = P["wheel_radius_m"]
    t = f * r
    return CalcResult(
        "Total torque at the wheels", t, "N*m",
        steps=[
            Step("Total tractive force (see 'Total tractive force required')",
                 "F_total = F_a + F_rr + F_g",
                 f"F_total = {_n(f)} N",
                 f"{_n(f)} N"),
            Step("Torque = force x wheel radius",
                 "T_total = F_total * r",
                 f"T_total = {_n(f)} * {_n(r)}",
                 f"{_n(t)} N*m"),
        ],
        notes=["Combined torque delivered at all the driven wheels' contact patches."])


def calc_torque_per_driven_wheel(P):
    f = _total_tractive_force(P)
    _require_positive(P, "wheel_radius_m", "driven_wheels")
    r = P["wheel_radius_m"]
    nd = P["driven_wheels"]
    t_total = f * r
    t = t_total / nd
    return CalcResult(
        "Torque per driven wheel", t, "N*m",
        steps=[
            Step("Total wheel torque",
                 "T_total = F_total * r",
                 f"T_total = {_n(f)} * {_n(r)}",
                 f"{_n(t_total)} N*m"),
            Step("Split equally between the driven wheels",
                 "T_wheel = T_total / driven_wheels",
                 f"T_wheel = {_n(t_total)} / {_n(nd)}",
                 f"{_n(t)} N*m"),
        ],
        notes=["Assumes every driven wheel carries an equal share of the load."])


def calc_motor_torque_each(P):
    f = _total_tractive_force(P)
    _require_positive(P, "wheel_radius_m", "driven_wheels", "gear_ratio",
                      "drivetrain_efficiency", "design_safety_factor")
    r = P["wheel_radius_m"]
    nd = P["driven_wheels"]
    gr = P["gear_ratio"]
    eff = P["drivetrain_efficiency"]
    sf = P["design_safety_factor"]
    t_wheel = f * r / nd
    t_motor = t_wheel / (gr * eff)
    t_spec = t_motor * sf

    notes = ["T_spec is the continuous torque to look for when choosing a motor.",
             "Direct-drive wheel? set gear_ratio = 1 and drivetrain_efficiency = 1.",
             "gear_ratio, drivetrain_efficiency and the safety factor are estimates."]
    stall = P.get("motor_stall_torque_nm", 0.0)
    if stall > 0:
        notes.append(f"T_spec is {_n(100.0 * t_spec / stall)}% of motor_stall_torque_nm "
                     f"({_n(stall)} N*m) - keep it well under 100%.")
    return CalcResult(
        "Torque required from each motor (with safety factor)", t_spec, "N*m",
        steps=[
            Step("Torque needed at each driven wheel",
                 "T_wheel = F_total * r / driven_wheels",
                 f"T_wheel = {_n(f)} * {_n(r)} / {_n(nd)}",
                 f"{_n(t_wheel)} N*m"),
            Step("Reflect through the gearbox and divide by its efficiency",
                 "T_motor = T_wheel / (gear_ratio * eta)",
                 f"T_motor = {_n(t_wheel)} / ({_n(gr)} * {_n(eff)})",
                 f"{_n(t_motor)} N*m"),
            Step("Apply the design safety factor to get the motor spec",
                 "T_spec = T_motor * safety_factor",
                 f"T_spec = {_n(t_motor)} * {_n(sf)}",
                 f"{_n(t_spec)} N*m"),
        ],
        extras=[("bare requirement (no safety factor)", t_motor, "N*m")],
        notes=notes)


def calc_max_speed(P):
    _require_positive(P, "wheel_radius_m")
    rpm = P["motor_no_load_rpm"]
    r = P["wheel_radius_m"]
    omega = rpm / 60.0 * 2.0 * math.pi
    v = omega * r
    return CalcResult(
        "Maximum (no-load) linear speed", v, "m/s",
        steps=[
            Step("Convert wheel speed from rev/min to rad/s",
                 "omega = rpm / 60 * 2*pi",
                 f"omega = {_n(rpm)} / 60 * 2*pi",
                 f"{_n(omega)} rad/s"),
            Step("Linear speed at the wheel rim",
                 "v = omega * r",
                 f"v = {_n(omega)} * {_n(r)}",
                 f"{_n(v)} m/s"),
        ],
        extras=[("in km/h", v * 3.6, "km/h")],
        notes=["motor_no_load_rpm is taken as the wheel output speed (after the gearbox).",
               "No-load figure - real top speed under load is lower.",
               "If your rpm figure is the motor-shaft speed, divide it by gear_ratio first."])


def calc_wheel_rpm_at_top_speed(P):
    _require_positive(P, "wheel_radius_m")
    v = P["top_speed_mps"]
    r = P["wheel_radius_m"]
    omega = v / r
    rpm = omega / (2.0 * math.pi) * 60.0
    return CalcResult(
        "Wheel speed at the target top speed", rpm, "rpm",
        steps=[
            Step("Angular speed of the wheel",
                 "omega = v / r",
                 f"omega = {_n(v)} / {_n(r)}",
                 f"{_n(omega)} rad/s"),
            Step("Convert rad/s to rev/min",
                 "rpm = omega / (2*pi) * 60",
                 f"rpm = {_n(omega)} / (2*pi) * 60",
                 f"{_n(rpm)} rpm"),
        ],
        notes=["Handy for choosing a motor + gearbox: the wheel must reach this speed."])


def calc_battery_runtime(P):
    _require_positive(P, "avg_current_draw_a")
    cap = P["battery_capacity_ah"]
    frac = P["battery_usable_fraction"]
    i_avg = P["avg_current_draw_a"]
    usable = cap * frac
    runtime_h = usable / i_avg
    range_m = runtime_h * 3600.0 * P["top_speed_mps"]
    return CalcResult(
        "Battery runtime", runtime_h, "h",
        steps=[
            Step("Usable capacity before the low-voltage cutoff",
                 "Q_usable = Q_pack * usable_fraction",
                 f"Q_usable = {_n(cap)} * {_n(frac)}",
                 f"{_n(usable)} Ah"),
            Step("Runtime = usable capacity / average current",
                 "t = Q_usable / I_avg",
                 f"t = {_n(usable)} / {_n(i_avg)}",
                 f"{_n(runtime_h)} h"),
            Step("Distance if driving at top speed the whole time",
                 "d = t * 3600 * v_top",
                 f"d = {_n(runtime_h)} * 3600 * {_n(P['top_speed_mps'])}",
                 f"{_n(range_m)} m"),
        ],
        extras=[("runtime in minutes", runtime_h * 60.0, "min"),
                ("range at top speed", range_m / 1000.0, "km")],
        notes=["avg_current_draw_a is an estimate - measure it with a power meter or "
               "by logging /battery_voltage and pack current.",
               "Fold the Pi + LiDAR + electronics draw into avg_current_draw_a.",
               "Peukert effect ignored - fine for a rough figure."])


def calc_drive_power(P):
    _require_positive(P, "drivetrain_efficiency", "battery_voltage_nom_v")
    rr = _rolling_resistance(P)
    gr = _grade_force(P)
    f_climb = rr + gr
    v = P["top_speed_mps"]
    eff = P["drivetrain_efficiency"]
    p_mech = f_climb * v
    p_elec = p_mech / eff
    i = p_elec / P["battery_voltage_nom_v"]
    return CalcResult(
        "Drive power to sustain top speed on the slope", p_elec, "W",
        steps=[
            Step("Force to hold top speed up the slope",
                 "F = C_rr*m*g*cos(theta) + m*g*sin(theta)",
                 f"F = {_n(rr)} + {_n(gr)}",
                 f"{_n(f_climb)} N"),
            Step("Mechanical power = force x speed",
                 "P_mech = F * v_top",
                 f"P_mech = {_n(f_climb)} * {_n(v)}",
                 f"{_n(p_mech)} W"),
            Step("Electrical power in, allowing for drivetrain losses",
                 "P_elec = P_mech / eta",
                 f"P_elec = {_n(p_mech)} / {_n(eff)}",
                 f"{_n(p_elec)} W"),
            Step("Current drawn from the pack",
                 "I = P_elec / V_pack",
                 f"I = {_n(p_elec)} / {_n(P['battery_voltage_nom_v'])}",
                 f"{_n(i)} A"),
        ],
        extras=[("estimated pack current", i, "A")],
        notes=["Steady-state climb only - no acceleration term.",
               "Compare this current with avg_current_draw_a in the runtime calc."])


def calc_traction_check(P):
    _require_positive(P, "total_wheels")
    frac = P["driven_wheels"] / P["total_wheels"]
    n = _normal_force(P)
    f_avail = P["surface_friction_coeff"] * n * frac
    f_req = _total_tractive_force(P)
    margin = f_avail - f_req
    ok = margin >= 0
    slope_val = P["surface_friction_coeff"] * frac - P["rolling_resistance_coeff"]
    max_angle = math.degrees(math.atan(slope_val)) if slope_val > 0 else 0.0
    return CalcResult(
        "Traction margin (available friction - required force)", margin, "N",
        steps=[
            Step("Friction (grip) available at the driven wheels",
                 "F_avail = mu_s * m*g*cos(theta) * (driven/total)",
                 f"F_avail = {_n(P['surface_friction_coeff'])} * {_n(n)} * "
                 f"({_n(P['driven_wheels'])}/{_n(P['total_wheels'])})",
                 f"{_n(f_avail)} N"),
            Step("Tractive force required (accelerating up the slope)",
                 "F_req = F_a + F_rr + F_g",
                 f"F_req = {_n(f_req)} N",
                 f"{_n(f_req)} N"),
            Step("Traction margin",
                 "margin = F_avail - F_req",
                 f"margin = {_n(f_avail)} - {_n(f_req)}",
                 f"{_n(margin)} N"),
        ],
        notes=[f"Verdict: {'OK - the wheels grip' if ok else 'WHEELS SLIP - not enough traction'}.",
               f"Approx. max climb angle before slip (steady speed): {_n(max_angle)} deg.",
               "Assumes equal weight on each wheel and a rigid, level payload."])


# --------------------------------------------------------------------------- #
# Differential-drive kinematics & dynamics
# (worked cases from docs/Kinematics and Dynamics_AMR_Problems.pdf)
# --------------------------------------------------------------------------- #

def calc_forward_kinematics(P):
    """Problem 1 - wheel speeds -> body twist -> global velocities."""
    _require_positive(P, "track_width_m")
    r = P["wheel_radius_m"]
    w_l = P["wheel_omega_left_rads"]
    w_r = P["wheel_omega_right_rads"]
    ell = P["track_width_m"]
    theta = math.radians(P["heading_deg"])

    v = r * (w_r + w_l) / 2.0
    omega = r * (w_r - w_l) / ell
    x_dot = v * math.cos(theta)
    y_dot = v * math.sin(theta)
    return CalcResult(
        "Forward kinematics - body linear velocity v", v, "m/s",
        steps=[
            Step("Each wheel's ground speed is radius x its angular velocity",
                 "v_r = r*w_r ,  v_l = r*w_l",
                 f"v_r = {_n(r)}*{_n(w_r)} = {_n(r * w_r)} ,  v_l = {_n(r)}*{_n(w_l)} = {_n(r * w_l)}",
                 f"v_r = {_n(r * w_r)} m/s ,  v_l = {_n(r * w_l)} m/s"),
            Step("Body linear velocity is the average of the two wheel speeds",
                 "v = (v_r + v_l) / 2 = r*(w_r + w_l) / 2",
                 f"v = {_n(r)}*({_n(w_r)} + {_n(w_l)}) / 2",
                 f"{_n(v)} m/s"),
            Step("Body angular velocity is the speed difference over the track width",
                 "omega = (v_r - v_l) / L = r*(w_r - w_l) / L",
                 f"omega = {_n(r)}*({_n(w_r)} - {_n(w_l)}) / {_n(ell)}",
                 f"{_n(omega)} rad/s"),
            Step("Rotate the body velocity into the global frame by the heading theta",
                 "x_dot = v*cos(theta) ,  y_dot = v*sin(theta)",
                 f"x_dot = {_n(v)}*cos({_n(P['heading_deg'])} deg) ,  "
                 f"y_dot = {_n(v)}*sin({_n(P['heading_deg'])} deg)",
                 f"x_dot = {_n(x_dot)} m/s ,  y_dot = {_n(y_dot)} m/s"),
        ],
        extras=[("body angular velocity omega", omega, "rad/s"),
                ("global x_dot", x_dot, "m/s"),
                ("global y_dot", y_dot, "m/s")],
        notes=["Standard differential-drive model: no wheel slip, both wheels on the ground.",
               "theta is the robot's heading in the global frame."])


def calc_inverse_kinematics(P):
    """Problem 2 - desired circular path -> required wheel angular velocities."""
    _require_positive(P, "path_radius_m", "wheel_radius_m")
    v = P["path_linear_speed_mps"]
    big_r = P["path_radius_m"]
    ell = P["track_width_m"]
    r = P["wheel_radius_m"]

    omega = v / big_r
    v_r = v + omega * ell / 2.0
    v_l = v - omega * ell / 2.0
    w_r = v_r / r
    w_l = v_l / r
    return CalcResult(
        "Inverse kinematics - right wheel angular velocity", w_r, "rad/s",
        steps=[
            Step("Body angular velocity needed to hold the circle",
                 "omega = v / R",
                 f"omega = {_n(v)} / {_n(big_r)}",
                 f"{_n(omega)} rad/s"),
            Step("Wheel ground speeds from the body twist (v, omega)",
                 "v_r = v + omega*L/2 ,  v_l = v - omega*L/2",
                 f"v_r = {_n(v)} + {_n(omega)}*{_n(ell)}/2 ,  "
                 f"v_l = {_n(v)} - {_n(omega)}*{_n(ell)}/2",
                 f"v_r = {_n(v_r)} m/s ,  v_l = {_n(v_l)} m/s"),
            Step("Convert wheel ground speed to wheel angular velocity",
                 "w = v_wheel / r",
                 f"w_r = {_n(v_r)}/{_n(r)} ,  w_l = {_n(v_l)}/{_n(r)}",
                 f"w_r = {_n(w_r)} rad/s ,  w_l = {_n(w_l)} rad/s"),
        ],
        extras=[("left wheel angular velocity", w_l, "rad/s"),
                ("right wheel ground speed", v_r, "m/s"),
                ("left wheel ground speed", v_l, "m/s"),
                ("body angular velocity", omega, "rad/s")],
        notes=["Positive R turns left (counter-clockwise); the right wheel runs faster.",
               "Set path_linear_speed_mps and path_radius_m for the manoeuvre you want."])


def calc_dd_accel_torque(P):
    """Problem 3 - straight-line acceleration, frictionless, torque per wheel."""
    _require_positive(P, "accel_time_s", "driven_wheels", "wheel_radius_m")
    a = (P["top_speed_mps"] - P["initial_speed_mps"]) / P["accel_time_s"]
    f_total = P["mass_kg"] * a
    n_drive = P["driven_wheels"]
    f_wheel = f_total / n_drive
    tau = f_wheel * P["wheel_radius_m"]
    return CalcResult(
        "Straight-line acceleration torque per wheel (no friction)", tau, "N*m",
        steps=[
            Step("Required linear acceleration",
                 "a = (v_f - v_i) / t",
                 f"a = ({_n(P['top_speed_mps'])} - {_n(P['initial_speed_mps'])}) / {_n(P['accel_time_s'])}",
                 f"{_n(a)} m/s^2"),
            Step("Total force for linear motion (Newton's second law)",
                 "F_total = m * a",
                 f"F_total = {_n(P['mass_kg'])} * {_n(a)}",
                 f"{_n(f_total)} N"),
            Step("Split equally between the driven wheels (symmetric, straight)",
                 "F_wheel = F_total / driven_wheels",
                 f"F_wheel = {_n(f_total)} / {_n(n_drive)}",
                 f"{_n(f_wheel)} N"),
            Step("Torque at each wheel",
                 "tau = F_wheel * r",
                 f"tau = {_n(f_wheel)} * {_n(P['wheel_radius_m'])}",
                 f"{_n(tau)} N*m"),
        ],
        extras=[("linear acceleration", a, "m/s^2"),
                ("total force", f_total, "N"),
                ("force per wheel", f_wheel, "N")],
        notes=["No friction, no slip, no gearbox - this is the PDF 'Problem 3' model.",
               "To reproduce the handout: mass_kg=20, top_speed_mps=2, accel_time_s=4, "
               "driven_wheels=2, wheel_radius_m=0.1 -> tau = 0.5 N*m.",
               "For a realistic figure use 'Torque required from each motor' instead."])


def calc_dd_spin_torque(P):
    """Problem 4 - pure spin on the spot, torque from each wheel motor."""
    _require_positive(P, "track_width_m", "wheel_radius_m")
    inertia = P["moment_of_inertia_kgm2"]
    alpha = P["angular_accel_rads2"]
    ell = P["track_width_m"]
    r = P["wheel_radius_m"]

    t_chassis = inertia * alpha
    f = t_chassis / ell
    tau_r = f * r
    tau_l = -f * r
    return CalcResult(
        "Pure-spin torque - right wheel motor", tau_r, "N*m",
        steps=[
            Step("Torque to angularly accelerate the chassis (Newton's second law, rotation)",
                 "T_chassis = I * alpha",
                 f"T_chassis = {_n(inertia)} * {_n(alpha)}",
                 f"{_n(t_chassis)} N*m"),
            Step("The two wheels form a couple about the centre: T_chassis = F * L",
                 "F = T_chassis / L",
                 f"F = {_n(t_chassis)} / {_n(ell)}",
                 f"{_n(f)} N"),
            Step("Convert each wheel force to a motor torque (opposite signs)",
                 "tau_r = F * r ,  tau_l = -F * r",
                 f"tau_r = {_n(f)}*{_n(r)} ,  tau_l = -{_n(f)}*{_n(r)}",
                 f"tau_r = {_n(tau_r)} N*m ,  tau_l = {_n(tau_l)} N*m"),
        ],
        extras=[("chassis torque", t_chassis, "N*m"),
                ("wheel force (couple)", f, "N"),
                ("left wheel motor torque", tau_l, "N*m")],
        notes=["Pure rotation, v = 0: right motor drives forward, left motor drives backward.",
               "A negative left torque means the left motor must brake / reverse.",
               "To reproduce the handout: I=0.8, angular_accel_rads2=2, L=0.5, r=0.1 "
               "-> tau_r = 0.32 N*m, tau_l = -0.32 N*m."])


# --------------------------------------------------------------------------- #
# Registry  (menu order)
# --------------------------------------------------------------------------- #

CALCS = [
    Calc("acceleration", "Acceleration required (rest to top speed)",
         ["top_speed_mps", "accel_time_s"], calc_acceleration),
    Calc("accel_force", "Acceleration force",
         ["mass_kg", "top_speed_mps", "accel_time_s"], calc_accel_force),
    Calc("friction_force", "Friction / traction force (driven wheels)",
         ["surface_friction_coeff", "mass_kg", "gravity_mps2", "climb_angle_deg",
          "driven_wheels", "total_wheels"], calc_friction_force),
    Calc("rolling_resistance", "Rolling resistance force",
         ["rolling_resistance_coeff", "mass_kg", "gravity_mps2", "climb_angle_deg"],
         calc_rolling_resistance),
    Calc("gravity_slope", "Gravity force on a slope",
         ["mass_kg", "gravity_mps2", "climb_angle_deg"], calc_gravity_slope),
    Calc("force_to_move", "Force required to move the robot (flat)",
         ["rolling_resistance_coeff", "mass_kg", "gravity_mps2"], calc_force_to_move),
    Calc("force_to_climb", "Force needed to climb the slope",
         ["rolling_resistance_coeff", "mass_kg", "gravity_mps2", "climb_angle_deg"],
         calc_force_to_climb),
    Calc("total_force", "Total tractive force required",
         ["mass_kg", "top_speed_mps", "accel_time_s", "rolling_resistance_coeff",
          "gravity_mps2", "climb_angle_deg"], calc_total_tractive_force),
    Calc("total_torque", "Total torque at the wheels",
         ["mass_kg", "top_speed_mps", "accel_time_s", "rolling_resistance_coeff",
          "gravity_mps2", "climb_angle_deg", "wheel_radius_m"], calc_total_wheel_torque),
    Calc("torque_per_wheel", "Torque per driven wheel",
         ["mass_kg", "top_speed_mps", "accel_time_s", "rolling_resistance_coeff",
          "gravity_mps2", "climb_angle_deg", "wheel_radius_m", "driven_wheels"],
         calc_torque_per_driven_wheel),
    Calc("motor_torque", "Torque required from each motor",
         ["mass_kg", "top_speed_mps", "accel_time_s", "rolling_resistance_coeff",
          "gravity_mps2", "climb_angle_deg", "wheel_radius_m", "driven_wheels",
          "gear_ratio", "drivetrain_efficiency", "design_safety_factor",
          "motor_stall_torque_nm"], calc_motor_torque_each),
    Calc("max_speed", "Maximum (no-load) linear speed",
         ["motor_no_load_rpm", "wheel_radius_m"], calc_max_speed),
    Calc("wheel_rpm", "Wheel speed at the target top speed",
         ["top_speed_mps", "wheel_radius_m"], calc_wheel_rpm_at_top_speed),
    Calc("battery_runtime", "Battery runtime and range",
         ["battery_capacity_ah", "battery_usable_fraction", "avg_current_draw_a",
          "top_speed_mps"], calc_battery_runtime),
    Calc("drive_power", "Drive power to sustain top speed on the slope",
         ["rolling_resistance_coeff", "mass_kg", "gravity_mps2", "climb_angle_deg",
          "top_speed_mps", "drivetrain_efficiency", "battery_voltage_nom_v"],
         calc_drive_power),
    Calc("traction_check", "Traction check (does it slip?)",
         ["surface_friction_coeff", "rolling_resistance_coeff", "mass_kg", "gravity_mps2",
          "climb_angle_deg", "driven_wheels", "total_wheels", "top_speed_mps",
          "accel_time_s"], calc_traction_check),

    # Differential-drive kinematics & dynamics (AMR problems PDF)
    Calc("fwd_kinematics", "Diff-drive forward kinematics (wheel speeds -> body + global)",
         ["wheel_radius_m", "track_width_m", "wheel_omega_left_rads",
          "wheel_omega_right_rads", "heading_deg"], calc_forward_kinematics),
    Calc("inv_kinematics", "Diff-drive inverse kinematics (circular path -> wheel speeds)",
         ["path_linear_speed_mps", "path_radius_m", "track_width_m", "wheel_radius_m"],
         calc_inverse_kinematics),
    Calc("dd_accel_torque", "Diff-drive straight-line acceleration torque (no friction)",
         ["mass_kg", "top_speed_mps", "initial_speed_mps", "accel_time_s",
          "driven_wheels", "wheel_radius_m"], calc_dd_accel_torque),
    Calc("dd_spin_torque", "Diff-drive pure-spin wheel torque",
         ["moment_of_inertia_kgm2", "angular_accel_rads2", "track_width_m",
          "wheel_radius_m"], calc_dd_spin_torque),
]

CALCS_BY_ID = {c.id: c for c in CALCS}


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #

def render_answer(result):
    """One-line answer, plus any extra derived figures."""
    lines = [f"{result.quantity}:  {_n(result.value)} {result.unit}"]
    for label, value, unit in result.extras:
        lines.append(f"    {label}:  {_n(value)} {unit}")
    return "\n".join(lines)


def render_steps(result):
    """Full worked solution."""
    lines = [f"=== {result.quantity} ===", ""]
    for idx, step in enumerate(result.steps, start=1):
        lines.append(f"Step {idx}: {step.text}")
        if step.formula:
            lines.append(f"        {step.formula}")
        if step.substitution:
            lines.append(f"        {step.substitution}")
        if step.result:
            lines.append(f"        => {step.result}")
        lines.append("")
    lines.append(f"ANSWER:  {_n(result.value)} {result.unit}")
    for label, value, unit in result.extras:
        lines.append(f"         {label}:  {_n(value)} {unit}")
    if result.notes:
        lines.append("")
        lines.append("Notes:")
        for note in result.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)
