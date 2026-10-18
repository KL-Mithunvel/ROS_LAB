# Lab Record — UNO Smart Robot Car: Line Following with Obstacle Avoidance

| | |
|---|---|
| **Student** | kl mithunvel |
| **Course** | BMHA314E — Autonomous Mobile Robots (practical) |
| **Experiment** | Sensor-based reactive control of a small differential-drive car: PID line following with ultrasonic obstacle avoidance (Arduino, no ROS) |
| **Platform** | UNO Smart Robot Car Kit V3.0 (Elegoo/VEEROBOT): Arduino UNO, L298-type motor driver, 3 IR line sensors, HC-SR04 ultrasonic on a servo |
| **Period covered** | 2026-09-23 → 2026-09-24 (software); hardware testing partly done, mostly pending |
| **Status** | Merged sketch was flashed once and partly observed; the **PID rewrite and the `Hardware_Test` sketch have only been compiled**. Sections marked ☐ are to be filled in from the bench. |

> **Honesty note.** Section 4 lists what the user actually observed on the car. Everything
> else — the PID gains, speeds, timings — is an untested estimate until the bring-up checklist
> in `TODO.md` is done.

---

## 1. Aim
To make the car follow a black line using three IR sensors and a PID controller, detect an
obstacle ahead with an ultrasonic sensor, steer around it, and re-acquire the line.

## 2. Apparatus
| Item | Detail |
|---|---|
| Controller | Arduino UNO, 9600 baud serial |
| Drive | Two DC motors via H-bridge: ENA=5, IN1=9, IN2=11 (Motor A); ENB=6, IN3=7, IN4=8 (Motor B) |
| Line sensors | Right = pin 10, Middle = pin 4, Left = pin 2 (digital, black line = on-line) |
| Obstacle sensing | HC-SR04: Echo = A4, Trig = A5; mounted on a servo at pin 3 (10° = right, 90° = centre, 180° = left) |
| Software | Arduino IDE 1.8.x (`Servo` library) |

## 3. Software in this folder (`line_follow_obstacle_avoid/`)
| File | Origin | Role |
|---|---|---|
| `Line_tracking_car.ino` | vendor example | Basic line follower (original) |
| `Obstacle_Avoidance_Car.ino` | vendor example | Basic ultrasonic avoidance (original) |
| `Line_Follow_Obstacle_Avoid_Car.ino` | **own** | Merged + PID line following + avoidance state machine |
| `Hardware_Test/Hardware_Test.ino` | **own** | Serial-menu bring-up and calibration sketch |
| `../readme.md` | vendor | One-line kit description |

## 4. Chronological log

| Date | Commit | Work |
|---|---|---|
| 2026-09-23 | `4ce56da`, `7a50cad` | Kit README and vendor sketches added to the repo |
| 2026-09-23 | `4204e40` | **Merged** the two vendor sketches: line-follow by default; on an obstacle < 20 cm stop, probe left with the servo, steer around if clear, else probe right, else back off and re-scan; after the detour creep forward until the IR sensors find the line again |
| 2026-09-24 | `6fd767a` | **PID line following** and the **hardware test sketch** (below) |
| 2026-10-18 | — | Moved from `docs/UNO Smart Robot Car Kit/` to the repo root as `uno_car/` (lab experiment 7) |

### 4.1 Finding while merging
The two vendor sketches name their motor functions inconsistently: `Line_tracking_car.ino`'s
`forward()`/`back()` drive the *same pin states* as `Obstacle_Avoidance_Car.ino`'s
`back()`/`forward()`. The line-tracking sketch's names are swapped relative to its own
`Serial.println` text. The merged sketch standardises on the obstacle-avoidance pin mapping.
**Never mix the two pin sets.**

### 4.2 Observed on the hardware (2026-09-24, user report on the merged sketch)
| Observation | Interpretation |
|---|---|
| Upload failed first: `unable to open port COM6`, `not in sync` | Port / CH340 driver / cable — not the code (it compiled) |
| Car drove **in reverse** along the line | Motor polarity opposite to the vendor assumption → `INVERT_MOTOR_DIRECTION` introduced |
| After inverting: drove forward and turned **right** correctly, but did **not turn left**, though the Serial log showed `L:1` | Pin bug ruled out (left/right are exact mirrors under the invert flag) |
| Car "easily moves out of the line" | See diagnosis below |

### 4.3 Diagnosis and redesign (reasoned, not measured)
Cause of the overshoot: `loop()` pinged the ultrasonic every iteration with
`pulseIn(..., 30000)`, which blocks up to 30 ms on every no-echo ping, plus a Serial print
(~20 ms at 9600 baud) every pass — a very slow sensor-to-motor loop — and `left()`/`right()`
were full-strength pivots.

Changes made:
| Change | Detail |
|---|---|
| **PID over 3 binary sensors** | error ×2 scale: L=−2, L+M=−1, M=0, M+R=+1, R=+2; lost line → keep turning to the last-seen side, stop after 2 s |
| Per-wheel PWM | `setMotorA/B`, `setWheels`; the car curves instead of pivoting |
| Constants | `BASE_SPEED` 110, `carSpeed` 170→130, `KP` 40, `KI` 0, `KD` 20 |
| Faster loop | ultrasonic every 100 ms with a 6 ms timeout; 2 consecutive close pings needed; Serial diagnostics throttled to 200 ms |
| Calibration flags | `INVERT_MOTOR_DIRECTION`, `SWAP_SIDES` (assumes Motor A = right wheel, B = left) |
| **`Hardware_Test.ino`** | menu: IR raw/on-line, ultrasonic, servo sweep, Motor A/B alone, drive sequence, PWM ramp; runtime toggles `i` invert, `w` swap, `+`/`−` test speed |

### 4.4 Verification so far
Both sketches compile with zero warnings (Arduino IDE's `avr-g++ -fsyntax-only`, ATmega328P,
`Servo` library). **No run of the PID version on hardware.**

## 5. Procedure (bench, in order — mirrors `TODO.md` "hardware bring-up tests")
Full steps are in `lab-manual/07-uno-car-line-follow-obstacle.md`. Summary: upload works → IR
sensors → ultrasonic → servo direction → each motor → drive sequence (settle invert/swap) →
minimum PWM → PID dry run with wheels off ground → track tuning (KP, then KD, then KI) →
obstacle avoidance.

## 6. Observations and results

### 6.1 Bring-up tests
| # | Test | Expected | Observed | Pass? |
|---|---|---|---|---|
| 0 | Upload | no port error | ☐ | ☐ |
| 1 | IR sensors L/M/R | black → `on-line=1` | ☐ | ☐ |
| 2 | Ultrasonic at 10 / 20 / 50 cm | within ±2 cm; `0` = no echo | ☐ / ☐ / ☐ | ☐ |
| 3 | Servo | 10° = right, 180° = left | ☐ | ☐ |
| 4/5 | Motor A / B | A = right, B = left | A: ☐  B: ☐ | ☐ |
| 6 | Drive sequence | forward/back/pivots correct | invert = ☐  swap = ☐ | ☐ |
| 7 | Minimum PWM | — | A = ☐  B = ☐ | ☐ |
| 8 | PID dry run | L only → E=−2, SL<SR; R only → E=+2; M only → E=0 | ☐ | ☐ |

### 6.2 PID tuning on the track
| Trial | KP | KD | KI | BASE_SPEED | Result (stays on line? oscillates?) | Lap time (s) |
|---|---|---|---|---|---|---|
| 1 | 40 | 20 | 0 | 110 | ☐ | ☐ |
| 2 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |
| 3 | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ |

### 6.3 Obstacle avoidance
| Trial | Obstacle position | Detected at (cm) | Direction taken | Re-found line? | Remarks |
|---|---|---|---|---|---|
| 1 | on line, centre | ☐ | ☐ | ☐ | ☐ |
| 2 | left side blocked | ☐ | ☐ | ☐ | ☐ |
| 3 | both sides blocked | ☐ | ☐ | ☐ | ☐ |

## 7. Result (to be completed)
☐ State whether the car followed the line, the final tuned gains, and whether avoidance and line re-acquisition worked.

## 8. Viva questions
1. How are three binary sensors turned into an error value? Why ×2?
2. What do P, I and D each do here? Why is KI = 0?
3. Why did blocking `pulseIn` and Serial printing make the car overshoot?
4. How does the car behave when the line is lost?
5. How does the HC-SR04 measure distance (speed of sound, round trip)?
6. Why must the two vendor sketches' pin mappings not be mixed?
7. What are `INVERT_MOTOR_DIRECTION` and `SWAP_SIDES` for, and how are they found?
8. Compare this reactive controller with ROS 2 Nav2 (Experiment 5).

## 9. Conclusion (to be completed)
☐ Write after the bench tests.

## 10. Known wrinkle
The Arduino IDE expects each sketch in a folder of the same name; `line_follow_obstacle_avoid/`
holds several `.ino` files. Copy each into its own folder before opening it in the IDE.
