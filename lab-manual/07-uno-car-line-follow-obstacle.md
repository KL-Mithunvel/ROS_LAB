# Experiment 7 — UNO Smart Robot Car: PID line following with obstacle avoidance

*(Arduino experiment — no ROS. It contrasts a small reactive controller with the ROS 2 stacks of Experiments 2–5.)*

## 1. Aim
To program the UNO Smart Robot Car to follow a black line using three IR sensors and a PID loop, detect obstacles with a servo-mounted ultrasonic sensor, steer around them, and re-acquire the line.

## 2. Learning outcomes
Read digital line sensors and form an error signal; tune P, I and D terms; drive two DC motors with PWM through an H-bridge; measure distance with an ultrasonic sensor; build a small state machine; calibrate hardware (motor polarity, left/right) before trusting control code.

## 3. Apparatus
| Item | Detail |
|---|---|
| Kit | UNO Smart Robot Car Kit V3.0: Arduino UNO, motor driver, 2 DC motors, 3 IR line sensors, HC-SR04, servo, battery |
| Track | Black tape (≈2 cm) on a light floor, with a curve; boxes as obstacles |
| PC | Arduino IDE 1.8.x or 2.x, USB cable, CH340 driver if required |
| Code | `uno_car/line_follow_obstacle_avoid/`: `Hardware_Test/Hardware_Test.ino`, `Line_Follow_Obstacle_Avoid_Car.ino` (originals `Line_tracking_car.ino`, `Obstacle_Avoidance_Car.ino`) |

Pin map: motor A = ENA 5 / IN1 9 / IN2 11, motor B = ENB 6 / IN3 7 / IN4 8; IR right = 10, middle = 4, left = 2; ultrasonic Echo = A4, Trig = A5; servo = 3 (10° right, 90° centre, 180° left).

## 4. Theory
**Line error.** Each IR sensor is digital (on the line = 1). The three bits give a position error, scaled ×2: L = −2, L+M = −1, M = 0, M+R = +1, R = +2. Positive error means the line is to the right. If the line is lost the error is held at ±3 toward the side where it was last seen, and the car stops after 2 s.

**PID.** correction = Kp·e + Ki·∫e + Kd·(e − e_prev)/Δt. The wheel speeds are `BASE_SPEED ± correction`. With only five discrete error values Ki contributes little (set to 0); Kd damps weaving. A slow sensor-to-motor loop causes overshoot — so the sketch avoids blocking calls.

**Differential drive.** Different PWM on the two sides turns the car; the sign of the PWM sets direction. The H-bridge direction pins (IN1–IN4) select forward or reverse; ENA/ENB take the PWM. Wiring polarity varies per car, hence the calibration flags `INVERT_MOTOR_DIRECTION` and `SWAP_SIDES`.

**Ultrasonic ranging.** The HC-SR04 emits a pulse and times the echo: distance = (echo time × 343 m/s) / 2. `0` means no echo. The sketch pings every 100 ms with a 6 ms timeout and needs two consecutive close readings (< 20 cm) to react.

**Avoidance state machine.** Obstacle ahead → stop → servo to the left, read distance → if clear, turn left, go forward, return; otherwise probe right; if both blocked, back off and re-scan → creep forward sweeping the IR sensors (3 s timeout) until the line is found → resume line following.

## 5. Pre-lab questions
1. Why does the car reverse if the motor leads are wired the other way?
2. Why do `pulseIn()` with a long timeout and frequent `Serial.print` hurt control quality?
3. With sensors L, M, R what is the error when L and M see the line?
4. Why is the integral term usually unhelpful with three binary sensors?

## 6. Procedure
**Safety:** wheels **off the ground** (car on a stand) for all motor tests.

**A. Upload and bring-up (`Hardware_Test`)**
1. Arduino IDE: Tools → Board = Arduino Uno, correct port. Copy `Hardware_Test.ino` into a folder named `Hardware_Test` if the IDE complains. Upload. If the port cannot be opened: check Device Manager / CH340 driver, close any open Serial Monitor.
2. Open the Serial Monitor at **9600 baud**. Type a menu letter + Enter; any key aborts a test.
3. **IR sensors** (menu `1`): put black tape under L, M, R in turn; `on-line` must be 1 on black and 0 on white, on the correct physical side. Adjust the module trim-pot if a sensor flickers.
4. **Ultrasonic** (menu `2`): ruler at 10, 20, 50 cm.
5. **Servo** (menu `3`): note which side faces forward at 10° and at 180°.
6. **Motors** (menus `4`, `5`): which wheel turns for motor A and B, and in which direction.
7. **Drive sequence** (menu `6`): forward, back, pivot left, pivot right. If forward/back are reversed press `i` (invert); if only the pivots are mirrored press `w` (swap sides); repeat until all four are right. Note the final `invert` and `swap`.
8. **Minimum PWM** (menu `7`): first PWM value at which each wheel turns; `BASE_SPEED` should be ~30 above the higher one.

**B. Line following**
9. In `Line_Follow_Obstacle_Avoid_Car.ino` copy your `INVERT_MOTOR_DIRECTION` and `SWAP_SIDES`, set `BASE_SPEED`. Upload.
10. **PID dry run, wheels up:** slide black under one sensor at a time and read `L M R E SL SR D` in the Serial Monitor. Expect L only → E = −2 with SL < SR; R only → E = +2 with SL > SR; M only → E = 0 with SL = SR; none → keeps turning to the last side, then stops after 2 s.
11. **On the track:** start with Kp = 40, Ki = 0, Kd = 20. Tune in this order: raise **Kp** until it follows curves, then raise **Kd** to stop weaving, **Ki** last (probably leave 0). Record each trial.

**C. Obstacle avoidance**
12. Place a box on the line ≈ 40 cm ahead. Observe detection distance, the direction chosen, and whether the line is re-found. Repeat with the left side blocked, then both sides blocked.

## 7. Observations

**7.1 Bring-up**

| Test | Observed |
|---|---|
| IR: L / M / R on black, on white | |
| Ultrasonic at 10 / 20 / 50 cm | |
| Servo: 10° faces ___ ; 180° faces ___ | |
| Motor A = ___ wheel ; motor B = ___ wheel | |
| Final `invert` = ___ ; `swap` = ___ | |
| Minimum PWM: A = ___ ; B = ___ | |

**7.2 PID dry run**

| Sensor state | E | SL | SR | As expected? |
|---|---|---|---|---|
| L only | | | | |
| M only | | | | |
| R only | | | | |
| none (after 2 s) | | | | |

**7.3 Tuning**

| Trial | Kp | Kd | Ki | BASE_SPEED | Behaviour | Lap time (s) |
|---|---|---|---|---|---|---|
| 1 | 40 | 20 | 0 | 110 | | |
| 2 | | | | | | |
| 3 | | | | | | |

**7.4 Obstacle avoidance**

| Trial | Obstacle | Detected at (cm) | Direction | Line re-found? |
|---|---|---|---|---|
| 1 | on line | | | |
| 2 | left blocked | | | |
| 3 | both blocked | | | |

## 8. Result
☐ State the final gains and speeds, whether the car completed the track and avoided the obstacle, and the main problems found.

## 9. Viva questions
1. Explain the error table and why a lost line keeps the last direction.
2. What does each of Kp, Ki, Kd do, and what symptom tells you each is wrong?
3. Why was the original sketch slow to react, and how does the new loop fix that?
4. How does the ultrasonic sensor compute distance? What does a reading of 0 mean?
5. Why calibrate motor polarity before tuning the PID?
6. Why must the two vendor sketches' pin mappings not be mixed?
7. Compare this controller with the obstacle-avoidance node of Experiment 3 and the Nav2 mission of Experiment 5: sensing, control, and failure modes.
