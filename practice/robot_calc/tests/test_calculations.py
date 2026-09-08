"""
pytest suite for the mechatronics calculator.

Run from practice/robot_calc/ :   pytest
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import calculations  # noqa: E402
import parameters  # noqa: E402


# A deliberately simple parameter set with hand-checkable numbers.
# The differential-drive values match the worked PDF example.
P = {
    "mass_kg": 10.0,
    "wheel_radius_m": 0.1,
    "total_wheels": 4.0,
    "driven_wheels": 2.0,
    "top_speed_mps": 2.0,
    "accel_time_s": 4.0,
    "climb_angle_deg": 30.0,
    "rolling_resistance_coeff": 0.02,
    "surface_friction_coeff": 0.9,
    "gravity_mps2": 9.81,
    "drivetrain_efficiency": 0.8,
    "gear_ratio": 10.0,
    "motor_no_load_rpm": 300.0,
    "battery_voltage_nom_v": 12.0,
    "battery_capacity_ah": 10.0,
    "battery_usable_fraction": 0.8,
    "avg_current_draw_a": 5.0,
    "design_safety_factor": 1.5,
    "motor_stall_torque_nm": 0.8,
    "track_width_m": 0.5,
    "wheel_omega_left_rads": 4.0,
    "wheel_omega_right_rads": 6.0,
    "heading_deg": 45.0,
    "path_linear_speed_mps": 1.0,
    "path_radius_m": 2.0,
    "initial_speed_mps": 0.0,
    "moment_of_inertia_kgm2": 0.8,
    "angular_accel_rads2": 2.0,
}

COS30 = math.cos(math.radians(30.0))
NORMAL = 10.0 * 9.81 * COS30           # 84.9571 N
ROLLING = 0.02 * NORMAL               # 1.69914 N
GRADE = 10.0 * 9.81 * 0.5             # 49.05 N
ACCEL_FORCE = 10.0 * 0.5              # 5.0 N
TOTAL_FORCE = ACCEL_FORCE + ROLLING + GRADE


def outputs(calc_id, params=P):
    result = calculations.CALCS_BY_ID[calc_id].fn(params)
    return {q.name: q.value for q in result.outputs}


# --------------------------------------------------------------------------- #
# Set 1 - tractive effort
# --------------------------------------------------------------------------- #

def test_tractive_effort_values():
    o = outputs("tractive_effort")
    assert o["acceleration"] == pytest.approx(0.5)
    assert o["force: accelerate F_a"] == pytest.approx(ACCEL_FORCE)
    assert o["force: rolling resistance F_rr"] == pytest.approx(ROLLING, rel=1e-6)
    assert o["force: gravity on slope F_g"] == pytest.approx(GRADE, rel=1e-6)
    assert o["force: move on flat (steady)"] == pytest.approx(0.02 * 10.0 * 9.81)
    assert o["force: climb slope (steady)"] == pytest.approx(ROLLING + GRADE, rel=1e-6)
    assert o["force: total tractive F_total"] == pytest.approx(TOTAL_FORCE, rel=1e-6)
    assert o["torque: total at the wheels"] == pytest.approx(TOTAL_FORCE * 0.1, rel=1e-6)
    assert o["torque: per driven wheel"] == pytest.approx(TOTAL_FORCE * 0.1 / 2.0, rel=1e-6)
    assert o["torque: per motor (x safety factor)"] == pytest.approx(
        (TOTAL_FORCE * 0.1 / 2.0) / (10.0 * 0.8) * 1.5, rel=1e-6)
    assert o["traction: available at driven wheels"] == pytest.approx(
        0.9 * NORMAL * 0.5, rel=1e-6)
    assert o["traction: margin (available - needed)"] == pytest.approx(
        0.9 * NORMAL * 0.5 - TOTAL_FORCE, rel=1e-6)


def test_tractive_effort_slip_verdict():
    result = calculations.CALCS_BY_ID["tractive_effort"].fn(P)
    margin = next(q for q in result.outputs
                  if q.name == "traction: margin (available - needed)")
    assert "SLIP" in margin.note          # 38 N grip < 55.7 N needed

    grippy = dict(P, climb_angle_deg=0.0, top_speed_mps=0.2, accel_time_s=10.0)
    result = calculations.CALCS_BY_ID["tractive_effort"].fn(grippy)
    margin = next(q for q in result.outputs
                  if q.name == "traction: margin (available - needed)")
    assert margin.value > 0 and "OK" in margin.note


def test_tractive_effort_zero_accel_time_raises():
    with pytest.raises(ValueError):
        calculations.CALCS_BY_ID["tractive_effort"].fn(dict(P, accel_time_s=0.0))


# --------------------------------------------------------------------------- #
# Set 2 - speed & gearing
# --------------------------------------------------------------------------- #

def test_speed_gearing_values():
    o = outputs("speed_gearing")
    v_max = 300.0 / 60.0 * 2.0 * math.pi * 0.1
    assert o["max no-load linear speed"] == pytest.approx(v_max)          # m/s row (first)
    assert o["wheel angular speed at target top speed"] == pytest.approx(2.0 / 0.1)
    assert o["wheel speed at target top speed"] == pytest.approx(
        (2.0 / 0.1) / (2.0 * math.pi) * 60.0)
    assert o["motor shaft speed at target top speed"] == pytest.approx(
        (2.0 / 0.1) / (2.0 * math.pi) * 60.0 * 10.0)


# --------------------------------------------------------------------------- #
# Set 3 - battery & power
# --------------------------------------------------------------------------- #

def test_battery_power_values():
    o = outputs("battery_power")
    assert o["usable capacity"] == pytest.approx(8.0)
    assert o["runtime"] == pytest.approx(1.6)                 # hours row (first)
    assert o["range at top speed"] == pytest.approx(1.6 * 3600.0 * 2.0)  # metres row
    p_elec = ((ROLLING + GRADE) * 2.0) / 0.8
    assert o["drive power on the slope (electrical)"] == pytest.approx(p_elec, rel=1e-6)
    assert o["estimated pack current on the slope"] == pytest.approx(p_elec / 12.0, rel=1e-6)


def test_battery_power_zero_current_raises():
    with pytest.raises(ValueError):
        calculations.CALCS_BY_ID["battery_power"].fn(dict(P, avg_current_draw_a=0.0))


# --------------------------------------------------------------------------- #
# Set 4 - differential-drive kinematics (PDF Problems 1 & 2)
# --------------------------------------------------------------------------- #

def test_dd_kinematics_matches_pdf():
    o = outputs("dd_kinematics")
    assert o["forward: body linear velocity v"] == pytest.approx(0.5)
    assert o["forward: body angular velocity omega"] == pytest.approx(0.4)
    assert o["forward: global x_dot"] == pytest.approx(0.35355, rel=1e-4)
    assert o["forward: global y_dot"] == pytest.approx(0.35355, rel=1e-4)
    assert o["inverse: body angular velocity omega"] == pytest.approx(0.5)
    assert o["inverse: right wheel angular velocity"] == pytest.approx(11.25)
    assert o["inverse: left wheel angular velocity"] == pytest.approx(8.75)


# --------------------------------------------------------------------------- #
# Set 5 - differential-drive dynamics (PDF Problems 3 & 4)
# --------------------------------------------------------------------------- #

def test_dd_dynamics_matches_pdf():
    pdf = dict(P, mass_kg=20.0, top_speed_mps=2.0, initial_speed_mps=0.0,
               accel_time_s=4.0, driven_wheels=2.0, wheel_radius_m=0.1,
               moment_of_inertia_kgm2=0.8, angular_accel_rads2=2.0, track_width_m=0.5)
    o = outputs("dd_dynamics", pdf)
    assert o["straight-line: acceleration"] == pytest.approx(0.5)
    assert o["straight-line: total force"] == pytest.approx(10.0)
    assert o["straight-line: torque per driven wheel"] == pytest.approx(0.5)
    assert o["spin: chassis torque"] == pytest.approx(1.6)
    assert o["spin: right wheel motor torque"] == pytest.approx(0.32)
    assert o["spin: left wheel motor torque"] == pytest.approx(-0.32)


# --------------------------------------------------------------------------- #
# Cross-cutting checks
# --------------------------------------------------------------------------- #

def test_calcs_only_reference_real_parameters():
    real = set(parameters.load())
    for calc in calculations.CALCS:
        unknown = set(calc.uses) - real
        assert not unknown, f"{calc.id} references unknown params: {unknown}"


def test_every_parameter_is_used_by_some_set():
    real = set(parameters.load())
    used = {key for calc in calculations.CALCS for key in calc.uses}
    assert real - used == set(), f"unused parameters: {real - used}"


def test_default_params_run_clean_and_finite():
    flat = parameters.resolve(parameters.load())
    for calc in calculations.CALCS:
        result = calc.fn(flat)
        assert result.outputs
        for q in result.outputs:
            assert math.isfinite(q.value)
            assert q.unit


def test_renderers_produce_text():
    result = calculations.CALCS_BY_ID["tractive_effort"].fn(P)
    answer = calculations.render_answer(result)
    assert result.title in answer
    assert "force: total tractive F_total" in answer

    steps = calculations.render_steps(result)
    assert "Step 1:" in steps
    assert "RESULTS" in steps
    assert "Notes:" in steps
