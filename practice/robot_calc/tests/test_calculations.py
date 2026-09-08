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
    # differential-drive kinematics & dynamics (PDF example values)
    "track_width_m": 0.5,
    "wheel_omega_left_rads": 4.0,
    "wheel_omega_right_rads": 6.0,
    "heading_deg": 45.0,
    "path_linear_speed_mps": 1.0,
    "path_radius_m": 2.0,
    "initial_speed_mps": 0.0,
    "moment_of_inertia_kgm2": 0.8,
    "angular_accel_rads2": 2.0,
    "design_safety_factor": 1.5,
    "motor_stall_torque_nm": 0.8,
}

COS30 = math.cos(math.radians(30.0))
SIN30 = 0.5
NORMAL = 10.0 * 9.81 * COS30          # 84.9571 N
ROLLING = 0.02 * NORMAL              # 1.69914 N
GRADE = 10.0 * 9.81 * SIN30          # 49.05 N
ACCEL_FORCE = 10.0 * 0.5             # 5.0 N
TOTAL_FORCE = ACCEL_FORCE + ROLLING + GRADE

EXPECTED = {
    "acceleration": 0.5,
    "accel_force": 5.0,
    "friction_force": 0.9 * NORMAL * 0.5,
    "rolling_resistance": ROLLING,
    "gravity_slope": GRADE,
    "force_to_move": 0.02 * 10.0 * 9.81,
    "force_to_climb": ROLLING + GRADE,
    "total_force": TOTAL_FORCE,
    "total_torque": TOTAL_FORCE * 0.1,
    "torque_per_wheel": TOTAL_FORCE * 0.1 / 2.0,
    "motor_torque": (TOTAL_FORCE * 0.1 / 2.0) / (10.0 * 0.8) * 1.5,  # x safety factor
    "max_speed": 300.0 / 60.0 * 2.0 * math.pi * 0.1,
    "wheel_rpm": (2.0 / 0.1) / (2.0 * math.pi) * 60.0,
    "battery_runtime": 8.0 / 5.0,
    "drive_power": ((ROLLING + GRADE) * 2.0) / 0.8,
    "traction_check": 0.9 * NORMAL * 0.5 - TOTAL_FORCE,
    # differential-drive kinematics & dynamics (match the PDF worked answers)
    "fwd_kinematics": 0.1 * (6.0 + 4.0) / 2.0,          # v = 0.5 m/s
    "inv_kinematics": (1.0 + (1.0 / 2.0) * 0.5 / 2.0) / 0.1,  # w_r = 11.25 rad/s
    "dd_accel_torque": (10.0 * 0.5 / 2.0) * 0.1,        # tau = 0.25 N*m (m=10 here)
    "dd_spin_torque": (0.8 * 2.0 / 0.5) * 0.1,          # tau_r = 0.32 N*m
}


@pytest.mark.parametrize("calc_id, expected", EXPECTED.items())
def test_calc_value(calc_id, expected):
    result = calculations.CALCS_BY_ID[calc_id].fn(P)
    assert result.value == pytest.approx(expected, rel=1e-6)


def test_every_calc_has_an_expected_value():
    assert set(EXPECTED) == set(calculations.CALCS_BY_ID), "add the new calc to EXPECTED"


def test_calcs_only_reference_real_parameters():
    real = set(parameters.load())
    for calc in calculations.CALCS:
        unknown = set(calc.uses) - real
        assert not unknown, f"{calc.id} references unknown params: {unknown}"


def test_default_params_run_clean_and_finite():
    flat = parameters.resolve(parameters.load())
    for calc in calculations.CALCS:
        result = calc.fn(flat)
        assert math.isfinite(result.value)
        assert result.unit


def test_battery_runtime_extras():
    result = calculations.CALCS_BY_ID["battery_runtime"].fn(P)
    labels = {label for label, _, _ in result.extras}
    assert "range at top speed" in labels


def test_zero_accel_time_raises():
    bad = dict(P, accel_time_s=0.0)
    with pytest.raises(ValueError):
        calculations.CALCS_BY_ID["acceleration"].fn(bad)


def test_zero_current_raises():
    bad = dict(P, avg_current_draw_a=0.0)
    with pytest.raises(ValueError):
        calculations.CALCS_BY_ID["battery_runtime"].fn(bad)


def test_renderers_produce_text():
    result = calculations.CALCS_BY_ID["total_torque"].fn(P)
    assert "Total torque at the wheels" in calculations.render_answer(result)
    steps = calculations.render_steps(result)
    assert "Step 1:" in steps
    assert "ANSWER:" in steps


def test_pdf_problem1_forward_kinematics():
    p = dict(P, wheel_radius_m=0.1, track_width_m=0.5,
             wheel_omega_left_rads=4.0, wheel_omega_right_rads=6.0, heading_deg=45.0)
    r = calculations.CALCS_BY_ID["fwd_kinematics"].fn(p)
    assert r.value == pytest.approx(0.5)
    extras = {label: value for label, value, _ in r.extras}
    assert extras["body angular velocity omega"] == pytest.approx(0.4)
    assert extras["global x_dot"] == pytest.approx(0.35355, rel=1e-4)
    assert extras["global y_dot"] == pytest.approx(0.35355, rel=1e-4)


def test_pdf_problem2_inverse_kinematics():
    p = dict(P, wheel_radius_m=0.1, track_width_m=0.5,
             path_linear_speed_mps=1.0, path_radius_m=2.0)
    r = calculations.CALCS_BY_ID["inv_kinematics"].fn(p)
    assert r.value == pytest.approx(11.25)
    extras = {label: value for label, value, _ in r.extras}
    assert extras["left wheel angular velocity"] == pytest.approx(8.75)


def test_pdf_problem3_accel_torque():
    p = dict(P, mass_kg=20.0, top_speed_mps=2.0, initial_speed_mps=0.0,
             accel_time_s=4.0, driven_wheels=2.0, wheel_radius_m=0.1)
    r = calculations.CALCS_BY_ID["dd_accel_torque"].fn(p)
    assert r.value == pytest.approx(0.5)


def test_pdf_problem4_spin_torque():
    p = dict(P, moment_of_inertia_kgm2=0.8, angular_accel_rads2=2.0,
             track_width_m=0.5, wheel_radius_m=0.1)
    r = calculations.CALCS_BY_ID["dd_spin_torque"].fn(p)
    assert r.value == pytest.approx(0.32)
    extras = {label: value for label, value, _ in r.extras}
    assert extras["left wheel motor torque"] == pytest.approx(-0.32)


def test_traction_check_reports_slip_when_grip_is_low():
    slippy = dict(P, surface_friction_coeff=0.05)
    result = calculations.CALCS_BY_ID["traction_check"].fn(slippy)
    assert result.value < 0
    assert any("SLIP" in note for note in result.notes)
