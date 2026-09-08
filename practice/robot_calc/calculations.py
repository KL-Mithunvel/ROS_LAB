"""
calculations.py — mechatronics calculations for a mobile robot.

The calculations are bundled into a small number of *sets*. Each set is a
function  fn(P) -> CalcResult  where P is the flat parameter dict {key: float}
produced by parameters.resolve(). Running a set works out every quantity in that
group at once:

  * tractive_effort  - acceleration, all the forces, wheel & motor torque, traction
  * speed_gearing    - top speed, wheel rpm, motor rpm
  * battery_power     - runtime, range, drive power, pack current
  * dd_kinematics     - differential-drive forward + inverse kinematics
  * dd_dynamics       - differential-drive straight-line acceleration + pure spin

A CalcResult carries:
  * title    - heading for the set
  * outputs  - the list of Quantity results (name, value, unit, optional note)
  * steps    - Step objects (formula -> substitution -> result) for "full working"
  * notes    - caveats / assumptions

To add a quantity: compute it inside the relevant set function and append a
Quantity to `outputs` (and a Step if you want it in the working). To add a whole
new set: write  def calc_<name>(P): ... return CalcResult(...)  and register it in
CALCS. The menu is generated from CALCS.
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
class Quantity:
    name: str
    value: float
    unit: str
    note: str = ""            # optional inline note, e.g. "WHEELS SLIP"


@dataclass
class CalcResult:
    title: str
    outputs: List[Quantity] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class Calc:
    id: str
    title: str
    uses: List[str]           # parameter keys this set reads
    fn: Callable


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _n(x, digits=4):
    """Format a number for display (avoid scientific notation for ordinary sizes)."""
    ax = abs(x)
    if 1000.0 <= ax < 1e12:
        return f"{x:,.0f}" if abs(x - round(x)) < 0.05 else f"{x:,.1f}"
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
    """Weight component pressing the wheels onto the ground: m * g * cos(theta)."""
    return P["mass_kg"] * P["gravity_mps2"] * math.cos(_theta_rad(P))


def _rolling_resistance(P):
    return P["rolling_resistance_coeff"] * _normal_force(P)


def _grade_force(P):
    """Weight component along the slope: m * g * sin(theta)."""
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
# Set 1 - Tractive effort: forces, wheel & motor torque, traction
# --------------------------------------------------------------------------- #

def calc_tractive_effort(P):
    _require_positive(P, "accel_time_s", "wheel_radius_m", "driven_wheels",
                      "total_wheels", "gear_ratio", "drivetrain_efficiency",
                      "design_safety_factor")

    r = P["wheel_radius_m"]
    n_drive = P["driven_wheels"]
    gr = P["gear_ratio"]
    eff = P["drivetrain_efficiency"]
    sf = P["design_safety_factor"]
    mu = P["surface_friction_coeff"]
    crr = P["rolling_resistance_coeff"]

    a = _acceleration(P)
    normal = _normal_force(P)
    f_a = _accel_force(P)
    f_rr = _rolling_resistance(P)
    f_g = _grade_force(P)
    drive_frac = n_drive / P["total_wheels"]
    f_traction = mu * normal * drive_frac
    f_move_flat = crr * P["mass_kg"] * P["gravity_mps2"]
    f_climb_steady = f_rr + f_g
    f_total = f_a + f_rr + f_g

    t_total = f_total * r
    t_per_wheel = t_total / n_drive
    t_motor = t_per_wheel / (gr * eff)
    t_motor_spec = t_motor * sf

    margin = f_traction - f_total
    slope_val = mu * drive_frac - crr
    max_climb = math.degrees(math.atan(slope_val)) if slope_val > 0 else 0.0

    stall = P.get("motor_stall_torque_nm", 0.0)
    motor_note = f"bare {_n(t_motor)} N*m"
    if stall > 0:
        motor_note += f"; {_n(100.0 * t_motor_spec / stall)}% of stall"

    outputs = [
        Quantity("acceleration", a, "m/s^2"),
        Quantity("force: accelerate F_a", f_a, "N"),
        Quantity("force: rolling resistance F_rr", f_rr, "N"),
        Quantity("force: gravity on slope F_g", f_g, "N"),
        Quantity("force: move on flat (steady)", f_move_flat, "N"),
        Quantity("force: climb slope (steady)", f_climb_steady, "N"),
        Quantity("force: total tractive F_total", f_total, "N"),
        Quantity("torque: total at the wheels", t_total, "N*m"),
        Quantity("torque: per driven wheel", t_per_wheel, "N*m"),
        Quantity("torque: per motor (x safety factor)", t_motor_spec, "N*m", motor_note),
        Quantity("traction: available at driven wheels", f_traction, "N"),
        Quantity("traction: margin (available - needed)", margin, "N",
                 "OK - grips" if margin >= 0 else "WHEELS SLIP"),
        Quantity("traction: max climb angle before slip", max_climb, "deg"),
    ]
    steps = [
        Step("Average acceleration to reach top speed",
             "a = v_top / t_acc",
             f"a = {_n(P['top_speed_mps'])} / {_n(P['accel_time_s'])}",
             f"{_n(a)} m/s^2"),
        Step("Normal force pressing the wheels onto the ground",
             "N = m * g * cos(theta)",
             f"N = {_mgcos_str(P)}",
             f"{_n(normal)} N"),
        Step("Force to accelerate the mass (Newton's second law)",
             "F_a = m * a",
             f"F_a = {_n(P['mass_kg'])} * {_n(a)}",
             f"{_n(f_a)} N"),
        Step("Rolling resistance (proportional to the normal force)",
             "F_rr = C_rr * N",
             f"F_rr = {_n(crr)} * {_n(normal)}",
             f"{_n(f_rr)} N"),
        Step("Weight component down the slope",
             "F_g = m * g * sin(theta)",
             f"F_g = {_mgsin_str(P)}",
             f"{_n(f_g)} N"),
        Step("Total tractive force = accelerate + roll + climb",
             "F_total = F_a + F_rr + F_g",
             f"F_total = {_n(f_a)} + {_n(f_rr)} + {_n(f_g)}",
             f"{_n(f_total)} N"),
        Step("Torque at the wheels",
             "T_total = F_total * r",
             f"T_total = {_n(f_total)} * {_n(r)}",
             f"{_n(t_total)} N*m"),
        Step("Split equally between the driven wheels",
             "T_wheel = T_total / driven_wheels",
             f"T_wheel = {_n(t_total)} / {_n(n_drive)}",
             f"{_n(t_per_wheel)} N*m"),
        Step("Through the gearbox and its efficiency, then apply the safety factor",
             "T_motor = T_wheel / (gear_ratio * eta) ;  T_spec = T_motor * SF",
             f"T_motor = {_n(t_per_wheel)} / ({_n(gr)} * {_n(eff)}) = {_n(t_motor)} ;  "
             f"T_spec = {_n(t_motor)} * {_n(sf)}",
             f"{_n(t_motor_spec)} N*m"),
        Step("Grip available at the driven wheels (their share of the weight)",
             "F_traction = mu_s * N * (driven / total)",
             f"F_traction = {_n(mu)} * {_n(normal)} * ({_n(n_drive)}/{_n(P['total_wheels'])})",
             f"{_n(f_traction)} N"),
        Step("Traction margin, and the steepest slope the wheels can hold",
             "margin = F_traction - F_total ;  tan(theta_max) = mu_s*(driven/total) - C_rr",
             f"margin = {_n(f_traction)} - {_n(f_total)} ;  "
             f"theta_max = atan({_n(slope_val)})",
             f"margin {_n(margin)} N ;  theta_max {_n(max_climb)} deg"),
    ]
    notes = [
        "For flat ground set climb_angle_deg = 0 (all slope terms vanish).",
        "C_rr (rolling drag) and mu_s (slip/grip) are different coefficients.",
        "'per motor' torque assumes the load is shared equally by the driven wheels;",
        "  direct-drive wheel -> set gear_ratio = 1 and drivetrain_efficiency = 1.",
        "Weight is assumed even across the wheels, payload rigid and level.",
    ]
    return CalcResult("Tractive effort - forces, wheel & motor torque, traction",
                      outputs, steps, notes)


# --------------------------------------------------------------------------- #
# Set 2 - Speed, wheel rpm & gearing
# --------------------------------------------------------------------------- #

def calc_speed_gearing(P):
    _require_positive(P, "wheel_radius_m", "gear_ratio")
    r = P["wheel_radius_m"]
    rpm_noload = P["motor_no_load_rpm"]
    v_top = P["top_speed_mps"]
    gr = P["gear_ratio"]

    omega_noload = rpm_noload / 60.0 * 2.0 * math.pi
    v_max = omega_noload * r
    omega_target = v_top / r
    rpm_wheel_target = omega_target / (2.0 * math.pi) * 60.0
    rpm_motor_target = rpm_wheel_target * gr

    outputs = [
        Quantity("max no-load linear speed", v_max, "m/s"),
        Quantity("max no-load linear speed (km/h)", v_max * 3.6, "km/h"),
        Quantity("wheel angular speed at target top speed", omega_target, "rad/s"),
        Quantity("wheel speed at target top speed", rpm_wheel_target, "rpm"),
        Quantity("motor shaft speed at target top speed", rpm_motor_target, "rpm"),
    ]
    steps = [
        Step("Convert the wheel-output no-load speed to rad/s",
             "omega = rpm / 60 * 2*pi",
             f"omega = {_n(rpm_noload)} / 60 * 2*pi",
             f"{_n(omega_noload)} rad/s"),
        Step("No-load linear speed at the wheel rim",
             "v_max = omega * r",
             f"v_max = {_n(omega_noload)} * {_n(r)}",
             f"{_n(v_max)} m/s  ({_n(v_max * 3.6)} km/h)"),
        Step("Wheel angular speed needed for the target top speed",
             "omega_target = v_top / r",
             f"omega_target = {_n(v_top)} / {_n(r)}",
             f"{_n(omega_target)} rad/s"),
        Step("Convert to wheel rev/min, then to motor rev/min via the gear ratio",
             "rpm_wheel = omega_target / (2*pi) * 60 ;  rpm_motor = rpm_wheel * gear_ratio",
             f"rpm_wheel = {_n(omega_target)}/(2*pi)*60 = {_n(rpm_wheel_target)} ;  "
             f"rpm_motor = {_n(rpm_wheel_target)} * {_n(gr)}",
             f"rpm_wheel {_n(rpm_wheel_target)} ;  rpm_motor {_n(rpm_motor_target)}"),
    ]
    notes = [
        "motor_no_load_rpm is taken as the wheel output speed (after the gearbox).",
        "No-load figure - real top speed under load is lower.",
        "motor shaft speed = wheel speed x gear_ratio (choose a motor that reaches it).",
    ]
    return CalcResult("Speed, wheel rpm & gearing", outputs, steps, notes)


# --------------------------------------------------------------------------- #
# Set 3 - Battery runtime, range & drive power
# --------------------------------------------------------------------------- #

def calc_battery_power(P):
    _require_positive(P, "avg_current_draw_a", "drivetrain_efficiency",
                      "battery_voltage_nom_v")
    cap = P["battery_capacity_ah"]
    frac = P["battery_usable_fraction"]
    i_avg = P["avg_current_draw_a"]
    v_top = P["top_speed_mps"]
    eff = P["drivetrain_efficiency"]
    volts = P["battery_voltage_nom_v"]

    usable = cap * frac
    runtime_h = usable / i_avg
    range_m = runtime_h * 3600.0 * v_top

    f_climb = _rolling_resistance(P) + _grade_force(P)
    p_mech = f_climb * v_top
    p_elec = p_mech / eff
    i_climb = p_elec / volts

    outputs = [
        Quantity("usable capacity", usable, "Ah"),
        Quantity("runtime", runtime_h, "h"),
        Quantity("runtime (minutes)", runtime_h * 60.0, "min"),
        Quantity("range at top speed", range_m, "m"),
        Quantity("range at top speed (km)", range_m / 1000.0, "km"),
        Quantity("drive power on the slope (electrical)", p_elec, "W"),
        Quantity("estimated pack current on the slope", i_climb, "A"),
    ]
    steps = [
        Step("Usable capacity before the low-voltage cutoff",
             "Q_usable = Q_pack * usable_fraction",
             f"Q_usable = {_n(cap)} * {_n(frac)}",
             f"{_n(usable)} Ah"),
        Step("Runtime = usable capacity / average current",
             "t = Q_usable / I_avg",
             f"t = {_n(usable)} / {_n(i_avg)}",
             f"{_n(runtime_h)} h  ({_n(runtime_h * 60.0)} min)"),
        Step("Distance if driving at top speed the whole time",
             "d = t * 3600 * v_top",
             f"d = {_n(runtime_h)} * 3600 * {_n(v_top)}",
             f"{_n(range_m)} m  ({_n(range_m / 1000.0)} km)"),
        Step("Force to hold top speed up the slope",
             "F_climb = C_rr*m*g*cos(theta) + m*g*sin(theta)",
             f"F_climb = {_n(_rolling_resistance(P))} + {_n(_grade_force(P))}",
             f"{_n(f_climb)} N"),
        Step("Electrical power and pack current for that",
             "P_elec = F_climb * v_top / eta ;  I = P_elec / V_pack",
             f"P_elec = {_n(f_climb)} * {_n(v_top)} / {_n(eff)} = {_n(p_elec)} ;  "
             f"I = {_n(p_elec)} / {_n(volts)}",
             f"P_elec {_n(p_elec)} W ;  I {_n(i_climb)} A"),
    ]
    notes = [
        "avg_current_draw_a is an estimate - measure it with a power meter.",
        "Fold the Pi + LiDAR + electronics draw into avg_current_draw_a.",
        "Compare 'pack current on the slope' with avg_current_draw_a for a sanity check.",
        "Peukert effect ignored - fine for a rough figure.",
    ]
    return CalcResult("Battery runtime, range & drive power", outputs, steps, notes)


# --------------------------------------------------------------------------- #
# Set 4 - Differential-drive kinematics (forward & inverse)
#   worked cases from docs/Kinematics and Dynamics_AMR_Problems.pdf (Problems 1-2)
# --------------------------------------------------------------------------- #

def calc_dd_kinematics(P):
    _require_positive(P, "track_width_m", "wheel_radius_m", "path_radius_m")
    r = P["wheel_radius_m"]
    ell = P["track_width_m"]

    # Forward: wheel angular velocities -> body twist -> global velocities
    w_l = P["wheel_omega_left_rads"]
    w_r = P["wheel_omega_right_rads"]
    theta = math.radians(P["heading_deg"])
    v = r * (w_r + w_l) / 2.0
    omega = r * (w_r - w_l) / ell
    x_dot = v * math.cos(theta)
    y_dot = v * math.sin(theta)

    # Inverse: circular path (R, v) -> required wheel angular velocities
    v_path = P["path_linear_speed_mps"]
    big_r = P["path_radius_m"]
    omega_path = v_path / big_r
    v_r_req = v_path + omega_path * ell / 2.0
    v_l_req = v_path - omega_path * ell / 2.0
    w_r_req = v_r_req / r
    w_l_req = v_l_req / r

    outputs = [
        Quantity("forward: body linear velocity v", v, "m/s"),
        Quantity("forward: body angular velocity omega", omega, "rad/s"),
        Quantity("forward: global x_dot", x_dot, "m/s"),
        Quantity("forward: global y_dot", y_dot, "m/s"),
        Quantity("inverse: body angular velocity omega", omega_path, "rad/s"),
        Quantity("inverse: right wheel ground speed", v_r_req, "m/s"),
        Quantity("inverse: left wheel ground speed", v_l_req, "m/s"),
        Quantity("inverse: right wheel angular velocity", w_r_req, "rad/s"),
        Quantity("inverse: left wheel angular velocity", w_l_req, "rad/s"),
    ]
    steps = [
        Step("FORWARD - each wheel's ground speed is radius x angular velocity",
             "v_r = r*w_r ,  v_l = r*w_l",
             f"v_r = {_n(r)}*{_n(w_r)} = {_n(r * w_r)} ,  v_l = {_n(r)}*{_n(w_l)} = {_n(r * w_l)}",
             f"v_r = {_n(r * w_r)} m/s ,  v_l = {_n(r * w_l)} m/s"),
        Step("FORWARD - body velocity = average; body rotation = difference / track width",
             "v = r*(w_r + w_l)/2 ,  omega = r*(w_r - w_l)/L",
             f"v = {_n(r)}*({_n(w_r)}+{_n(w_l)})/2 ,  "
             f"omega = {_n(r)}*({_n(w_r)}-{_n(w_l)})/{_n(ell)}",
             f"v = {_n(v)} m/s ,  omega = {_n(omega)} rad/s"),
        Step("FORWARD - rotate the body velocity into the global frame by the heading",
             "x_dot = v*cos(theta) ,  y_dot = v*sin(theta)",
             f"x_dot = {_n(v)}*cos({_n(P['heading_deg'])} deg) ,  "
             f"y_dot = {_n(v)}*sin({_n(P['heading_deg'])} deg)",
             f"x_dot = {_n(x_dot)} m/s ,  y_dot = {_n(y_dot)} m/s"),
        Step("INVERSE - body rotation needed to hold the circular path",
             "omega = v / R",
             f"omega = {_n(v_path)} / {_n(big_r)}",
             f"{_n(omega_path)} rad/s"),
        Step("INVERSE - wheel ground speeds from the body twist (v, omega)",
             "v_r = v + omega*L/2 ,  v_l = v - omega*L/2",
             f"v_r = {_n(v_path)} + {_n(omega_path)}*{_n(ell)}/2 ,  "
             f"v_l = {_n(v_path)} - {_n(omega_path)}*{_n(ell)}/2",
             f"v_r = {_n(v_r_req)} m/s ,  v_l = {_n(v_l_req)} m/s"),
        Step("INVERSE - convert wheel ground speed to wheel angular velocity",
             "w = v_wheel / r",
             f"w_r = {_n(v_r_req)}/{_n(r)} ,  w_l = {_n(v_l_req)}/{_n(r)}",
             f"w_r = {_n(w_r_req)} rad/s ,  w_l = {_n(w_l_req)} rad/s"),
    ]
    notes = [
        "FORWARD uses wheel_omega_left_rads / wheel_omega_right_rads / heading_deg.",
        "INVERSE uses path_linear_speed_mps / path_radius_m (positive R turns left).",
        "Standard differential-drive model: no wheel slip, both wheels on the ground.",
    ]
    return CalcResult("Differential-drive kinematics (forward & inverse)",
                      outputs, steps, notes)


# --------------------------------------------------------------------------- #
# Set 5 - Differential-drive dynamics (straight-line acceleration & pure spin)
#   worked cases from docs/Kinematics and Dynamics_AMR_Problems.pdf (Problems 3-4)
# --------------------------------------------------------------------------- #

def calc_dd_dynamics(P):
    _require_positive(P, "accel_time_s", "driven_wheels", "wheel_radius_m",
                      "track_width_m")
    r = P["wheel_radius_m"]
    ell = P["track_width_m"]

    # Straight-line acceleration (frictionless, no gearbox)
    a = (P["top_speed_mps"] - P["initial_speed_mps"]) / P["accel_time_s"]
    f_total = P["mass_kg"] * a
    f_wheel = f_total / P["driven_wheels"]
    tau_wheel = f_wheel * r

    # Pure spin on the spot (v = 0)
    inertia = P["moment_of_inertia_kgm2"]
    alpha = P["angular_accel_rads2"]
    t_chassis = inertia * alpha
    f_couple = t_chassis / ell
    tau_r = f_couple * r
    tau_l = -tau_r

    outputs = [
        Quantity("straight-line: acceleration", a, "m/s^2"),
        Quantity("straight-line: total force", f_total, "N"),
        Quantity("straight-line: force per driven wheel", f_wheel, "N"),
        Quantity("straight-line: torque per driven wheel", tau_wheel, "N*m"),
        Quantity("spin: chassis torque", t_chassis, "N*m"),
        Quantity("spin: wheel force (couple)", f_couple, "N"),
        Quantity("spin: right wheel motor torque", tau_r, "N*m"),
        Quantity("spin: left wheel motor torque", tau_l, "N*m", "negative = brakes/reverses"),
    ]
    steps = [
        Step("STRAIGHT-LINE - required linear acceleration",
             "a = (v_f - v_i) / t",
             f"a = ({_n(P['top_speed_mps'])} - {_n(P['initial_speed_mps'])}) / {_n(P['accel_time_s'])}",
             f"{_n(a)} m/s^2"),
        Step("STRAIGHT-LINE - total force, split over the driven wheels, then torque",
             "F_total = m*a ;  F_wheel = F_total/driven_wheels ;  tau = F_wheel*r",
             f"F_total = {_n(P['mass_kg'])}*{_n(a)} = {_n(f_total)} ;  "
             f"F_wheel = {_n(f_total)}/{_n(P['driven_wheels'])} = {_n(f_wheel)} ;  "
             f"tau = {_n(f_wheel)}*{_n(r)}",
             f"tau = {_n(tau_wheel)} N*m per wheel"),
        Step("SPIN - torque to angularly accelerate the chassis",
             "T_chassis = I * alpha",
             f"T_chassis = {_n(inertia)} * {_n(alpha)}",
             f"{_n(t_chassis)} N*m"),
        Step("SPIN - the two wheels form a couple: T_chassis = F * L",
             "F = T_chassis / L",
             f"F = {_n(t_chassis)} / {_n(ell)}",
             f"{_n(f_couple)} N"),
        Step("SPIN - convert each wheel force to a motor torque (opposite signs)",
             "tau_r = F*r ,  tau_l = -F*r",
             f"tau_r = {_n(f_couple)}*{_n(r)} ,  tau_l = -{_n(f_couple)}*{_n(r)}",
             f"tau_r = {_n(tau_r)} N*m ,  tau_l = {_n(tau_l)} N*m"),
    ]
    notes = [
        "Both cases: no friction, no slip, no gearbox (the PDF 'Problem 3 / 4' model).",
        "STRAIGHT-LINE: set mass_kg=20, top_speed_mps=2, accel_time_s=4, driven_wheels=2, "
        "wheel_radius_m=0.1 -> tau = 0.5 N*m (matches the handout).",
        "SPIN: set moment_of_inertia_kgm2=0.8, angular_accel_rads2=2, track_width_m=0.5, "
        "wheel_radius_m=0.1 -> tau_r = 0.32, tau_l = -0.32 (matches the handout).",
        "For a realistic drive-torque figure with friction and a gearbox, use 'Tractive effort'.",
    ]
    return CalcResult("Differential-drive dynamics (acceleration & pure spin)",
                      outputs, steps, notes)


# --------------------------------------------------------------------------- #
# Registry  (menu order)
# --------------------------------------------------------------------------- #

CALCS = [
    Calc("tractive_effort",
         "Tractive effort - forces, wheel & motor torque, traction",
         ["mass_kg", "top_speed_mps", "accel_time_s", "rolling_resistance_coeff",
          "surface_friction_coeff", "gravity_mps2", "climb_angle_deg", "wheel_radius_m",
          "total_wheels", "driven_wheels", "gear_ratio", "drivetrain_efficiency",
          "design_safety_factor", "motor_stall_torque_nm"],
         calc_tractive_effort),
    Calc("speed_gearing",
         "Speed, wheel rpm & gearing",
         ["motor_no_load_rpm", "wheel_radius_m", "top_speed_mps", "gear_ratio"],
         calc_speed_gearing),
    Calc("battery_power",
         "Battery runtime, range & drive power",
         ["battery_capacity_ah", "battery_usable_fraction", "avg_current_draw_a",
          "top_speed_mps", "rolling_resistance_coeff", "mass_kg", "gravity_mps2",
          "climb_angle_deg", "drivetrain_efficiency", "battery_voltage_nom_v"],
         calc_battery_power),
    Calc("dd_kinematics",
         "Differential-drive kinematics (forward & inverse)",
         ["wheel_radius_m", "track_width_m", "wheel_omega_left_rads",
          "wheel_omega_right_rads", "heading_deg", "path_linear_speed_mps",
          "path_radius_m"],
         calc_dd_kinematics),
    Calc("dd_dynamics",
         "Differential-drive dynamics (acceleration & pure spin)",
         ["mass_kg", "top_speed_mps", "initial_speed_mps", "accel_time_s",
          "driven_wheels", "wheel_radius_m", "moment_of_inertia_kgm2",
          "angular_accel_rads2", "track_width_m"],
         calc_dd_dynamics),
]

CALCS_BY_ID = {c.id: c for c in CALCS}


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #

def _render_outputs(outputs):
    lines = []
    width = max(len(q.name) for q in outputs)
    prev_group = None
    for q in outputs:
        group = q.name.split(":")[0] if ":" in q.name else None
        if prev_group is not None and group != prev_group:
            lines.append("")
        prev_group = group
        tail = f"   ({q.note})" if q.note else ""
        lines.append(f"  {q.name:<{width}} = {_n(q.value):>12} {q.unit}{tail}")
    return lines


def render_answer(result):
    """The results table for a set, no working."""
    lines = [f"=== {result.title} ===", ""]
    lines += _render_outputs(result.outputs)
    return "\n".join(lines)


def render_steps(result):
    """Full working, then the results table and the notes."""
    lines = [f"=== {result.title} ===", ""]
    for idx, step in enumerate(result.steps, start=1):
        lines.append(f"Step {idx}: {step.text}")
        if step.formula:
            lines.append(f"        {step.formula}")
        if step.substitution:
            lines.append(f"        {step.substitution}")
        if step.result:
            lines.append(f"        => {step.result}")
        lines.append("")
    lines.append("-" * 60)
    lines.append("RESULTS")
    lines += _render_outputs(result.outputs)
    if result.notes:
        lines.append("")
        lines.append("Notes:")
        for note in result.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)
