//www.elegoo.com
// Merged line-following + obstacle-avoidance sketch for the Elegoo/VEEROBOT
// UNO Smart Robot Car Kit V3.0. Combines Line_tracking_car.ino (IR line
// sensors) with Obstacle_Avoidance_Car.ino (servo + HC-SR04 ultrasonic).
//
// Behaviour:
//   - default: follow the black line with a PID loop over the 3 IR sensors
//     (see "Line following" below).
//   - obstacle within OBSTACLE_DISTANCE_CM ahead: stop, probe left with the
//     servo-mounted ultrasonic; if clear, steer around it on the left. If
//     the left is blocked, probe right instead and steer around there. If
//     both sides are blocked, back off a little and let the next loop()
//     re-scan rather than push into the obstacle.
//   - after going around, creep forward sweeping the IR sensors (with a
//     timeout) until the line is found again, then resume line-following.
//
// Line following: the 3 binary sensors are turned into a small position
// error (x2 scale): L=-2, L+M=-1, M=0, M+R=+1, R=+2. error > 0 means the line
// is to the RIGHT, so the left wheel speeds up and the right wheel slows (and
// may reverse for a pivot). If the line is lost, the bot keeps turning
// towards the side it was last seen on, and stops after LOST_LINE_TIMEOUT_MS.
//
// UNTESTED ON HARDWARE. Before flashing this, run Hardware_Test/Hardware_Test.ino
// and copy the INVERT_MOTOR_DIRECTION / SWAP_SIDES values it settles on into
// the constants below (checklist: TODO.md "Hardware bring-up tests").
//
// Motor pin mapping and servo angle convention (10=right, 90=center,
// 180=left) are taken from Obstacle_Avoidance_Car.ino. Line_tracking_car.ino
// used a different pin layout where forward()/back() were swapped relative to
// their comments -- do not mix the two pin sets.

#include <Servo.h>
Servo myservo;

// ---- Ultrasonic + servo (from Obstacle_Avoidance_Car.ino) ----
const int Echo = A4;
const int Trig = A5;
const int SERVO_PIN = 3;

// ---- Motor driver (from Obstacle_Avoidance_Car.ino) ----
// Motor A = ENA/IN1/IN2, Motor B = ENB/IN3/IN4.
#define ENB 6
#define IN1 9
#define IN2 11
#define IN3 7
#define IN4 8
#define ENA 5

// ---- Line sensors (from Line_tracking_car.ino) ----
const int LT_R_PIN = 10;
const int LT_M_PIN = 4;
const int LT_L_PIN = 2;
#define LT_R !digitalRead(LT_R_PIN)
#define LT_M !digitalRead(LT_M_PIN)
#define LT_L !digitalRead(LT_L_PIN)

// ---- Hardware calibration (settle these with Hardware_Test.ino) ----
// true if the motor leads are wired with the opposite polarity from what
// Obstacle_Avoidance_Car.ino assumed (forward drives backward). Flips every
// direction pin, so forward<->back and pivot left<->right together.
const bool INVERT_MOTOR_DIRECTION = true;
// false: Motor A is the RIGHT wheel and Motor B the LEFT (derived from the
// original left() = A forward + B reverse). true if it is the other way round.
const bool SWAP_SIDES = false;

// ---- Speeds (PWM 0-255). Low values = more controllable; too low and the
// motors just hum without moving -- Hardware_Test.ino option 7 finds the
// minimum PWM that turns each wheel. ----
const int BASE_SPEED = 110;            // line-following cruise speed
const int MAX_SPEED = 200;             // clamp for either wheel during PID
const int carSpeed = 130;              // avoidance manoeuvres (forward/back/pivot)

// ---- PID (error is x2 scale, so normal range is -2..+2, lost line +-3) ----
const float KP = 40.0;                 // PWM per error unit
const float KI = 0.0;                  // integral barely helps with 3 binary sensors
const float KD = 20.0;                 // damps oscillation; raise if it weaves
const int INTEGRAL_LIMIT = 20;
const int LOST_ERROR = 3;              // error assumed while the line is lost
const unsigned long PID_INTERVAL_MS = 10;
const unsigned long LOST_LINE_TIMEOUT_MS = 2000;

// ---- Obstacle avoidance tuning ----
const int OBSTACLE_DISTANCE_CM = 20;
const int OBSTACLE_CONFIRM_COUNT = 2;  // consecutive close pings before reacting
const unsigned long PING_INTERVAL_MS = 100;
const unsigned long AVOID_TURN_MS = 400;
const unsigned long AVOID_FORWARD_MS = 600;
const unsigned long LINE_SEARCH_TIMEOUT_MS = 3000;

// ---- Diagnostics ----
const unsigned long DEBUG_INTERVAL_MS = 200;  // 9600 baud: printing every loop would stall the PID

// ---- State ----
unsigned long lastPidTime = 0;
unsigned long lastPingTime = 0;
unsigned long lastDebugTime = 0;
unsigned long lostSince = 0;
bool lostActive = false;
int lastDistance = 0;
int obstacleHits = 0;
int prevError = 0;
int lastSeenError = 0;
int integral = 0;
int dbgError = 0;
int dbgLeft = 0;
int dbgRight = 0;

void driveWrite(int pin, int state) {
  digitalWrite(pin, INVERT_MOTOR_DIRECTION ? !state : state);
}

// speed: -255..255, positive = forward.
void setMotorA(int speed) {
  speed = constrain(speed, -255, 255);
  if (speed >= 0) {
    driveWrite(IN1, LOW);
    driveWrite(IN2, HIGH);
  } else {
    driveWrite(IN1, HIGH);
    driveWrite(IN2, LOW);
  }
  analogWrite(ENA, abs(speed));
}

void setMotorB(int speed) {
  speed = constrain(speed, -255, 255);
  if (speed >= 0) {
    driveWrite(IN3, HIGH);
    driveWrite(IN4, LOW);
  } else {
    driveWrite(IN3, LOW);
    driveWrite(IN4, HIGH);
  }
  analogWrite(ENB, abs(speed));
}

void setWheels(int leftSpeed, int rightSpeed) {
  if (SWAP_SIDES) {
    setMotorA(leftSpeed);
    setMotorB(rightSpeed);
  } else {
    setMotorA(rightSpeed);
    setMotorB(leftSpeed);
  }
}

void forward() { setWheels(carSpeed, carSpeed); }
void back()    { setWheels(-carSpeed, -carSpeed); }
void left()    { setWheels(-carSpeed, carSpeed); }
void right()   { setWheels(carSpeed, -carSpeed); }

void stopCar() {
  digitalWrite(ENA, LOW);
  digitalWrite(ENB, LOW);
}

// Distance in cm, or 0 on echo timeout (nothing within ~1 m). The short
// timeout keeps a no-echo ping from blocking the PID loop for long.
int getDistance() {
  digitalWrite(Trig, LOW);
  delayMicroseconds(2);
  digitalWrite(Trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(Trig, LOW);
  unsigned long duration = pulseIn(Echo, HIGH, 6000UL);
  if (duration == 0) return 0;
  return (int)(duration / 58);
}

bool onLine() {
  return LT_M || LT_L || LT_R;
}

// Returns false if no sensor sees the line; otherwise sets error (x2 scale).
bool readLineError(int &error) {
  bool l = LT_L, m = LT_M, r = LT_R;
  int count = (l ? 1 : 0) + (m ? 1 : 0) + (r ? 1 : 0);
  if (count == 0) return false;
  int sum = (r ? 2 : 0) - (l ? 2 : 0);
  error = sum / count;
  return true;
}

void resetPid() {
  prevError = 0;
  integral = 0;
  lastSeenError = 0;
  lostActive = false;
  obstacleHits = 0;
  lastPidTime = millis();
  lastPingTime = millis();
}

void followLineStep() {
  unsigned long now = millis();
  if (now - lastPidTime < PID_INTERVAL_MS) return;
  lastPidTime = now;

  int error = 0;
  if (readLineError(error)) {
    lostActive = false;
    if (error != 0) lastSeenError = error;
  } else {
    if (!lostActive) {
      lostActive = true;
      lostSince = now;
    }
    if (now - lostSince > LOST_LINE_TIMEOUT_MS) {
      stopCar();
      dbgError = 0; dbgLeft = 0; dbgRight = 0;
      return;
    }
    if (lastSeenError > 0) error = LOST_ERROR;
    else if (lastSeenError < 0) error = -LOST_ERROR;
    else error = 0;  // last seen centred: assume a gap and keep going straight
  }

  integral = constrain(integral + error, -INTEGRAL_LIMIT, INTEGRAL_LIMIT);
  float correction = KP * error + KI * integral + KD * (error - prevError);
  prevError = error;

  int leftSpeed = constrain(BASE_SPEED + (int)correction, -MAX_SPEED, MAX_SPEED);
  int rightSpeed = constrain(BASE_SPEED - (int)correction, -MAX_SPEED, MAX_SPEED);
  setWheels(leftSpeed, rightSpeed);

  dbgError = error;
  dbgLeft = leftSpeed;
  dbgRight = rightSpeed;
}

// Turn toward goLeft, drive past the obstacle, turn back, then creep
// forward sweeping the IR sensors until the line is found again (or we
// time out and stop).
void driveAroundAndReacquireLine(bool goLeft) {
  if (goLeft) left(); else right();
  delay(AVOID_TURN_MS);

  forward();
  delay(AVOID_FORWARD_MS);

  if (goLeft) right(); else left();
  delay(AVOID_TURN_MS);

  unsigned long start = millis();
  bool found = false;
  while (millis() - start < LINE_SEARCH_TIMEOUT_MS) {
    if (onLine()) { found = true; break; }
    forward();
  }
  stopCar();

  if (!found) {
    Serial.println("Line not reacquired after avoiding obstacle - stopped.");
  }
}

// Obstacle ahead: probe left, then right if left is blocked, then steer
// around whichever side is clear. If both are blocked, back off and let
// the next loop() re-scan.
void avoidObstacle() {
  stopCar();
  delay(150);

  myservo.write(180); // look left
  delay(500);
  int leftDistance = getDistance();
  myservo.write(90);
  delay(300);

  bool leftClear = (leftDistance == 0) || (leftDistance > OBSTACLE_DISTANCE_CM);
  if (leftClear) {
    Serial.println("Obstacle ahead - steering left around it.");
    driveAroundAndReacquireLine(true);
    return;
  }

  myservo.write(10); // left blocked -- look right instead
  delay(500);
  int rightDistance = getDistance();
  myservo.write(90);
  delay(300);

  bool rightClear = (rightDistance == 0) || (rightDistance > OBSTACLE_DISTANCE_CM);
  if (rightClear) {
    Serial.println("Left blocked - steering right around obstacle instead.");
    driveAroundAndReacquireLine(false);
    return;
  }

  Serial.println("Both sides blocked - backing off.");
  back();
  delay(300);
  stopCar();
}

void setup() {
  Serial.begin(9600);
  myservo.attach(SERVO_PIN);
  myservo.write(90);
  pinMode(Echo, INPUT);
  pinMode(Trig, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(LT_L_PIN, INPUT);
  pinMode(LT_M_PIN, INPUT);
  pinMode(LT_R_PIN, INPUT);
  stopCar();
  resetPid();
  Serial.print("PID line follower ready. INVERT=");
  Serial.print(INVERT_MOTOR_DIRECTION);
  Serial.print(" SWAP_SIDES=");
  Serial.println(SWAP_SIDES);
}

void loop() {
  unsigned long now = millis();

  // Obstacle check runs on its own slower clock so it doesn't slow the PID.
  if (now - lastPingTime >= PING_INTERVAL_MS) {
    lastPingTime = now;
    lastDistance = getDistance();
    if (lastDistance > 0 && lastDistance <= OBSTACLE_DISTANCE_CM) {
      obstacleHits++;
    } else {
      obstacleHits = 0;
    }
  }

  if (obstacleHits >= OBSTACLE_CONFIRM_COUNT) {
    avoidObstacle();
    resetPid();
    return;
  }

  followLineStep();

  // Rate-limited diagnostics (Serial Monitor, 9600 baud).
  if (now - lastDebugTime >= DEBUG_INTERVAL_MS) {
    lastDebugTime = now;
    Serial.print("L:"); Serial.print(LT_L);
    Serial.print(" M:"); Serial.print(LT_M);
    Serial.print(" R:"); Serial.print(LT_R);
    Serial.print(" E:"); Serial.print(dbgError);
    Serial.print(" SL:"); Serial.print(dbgLeft);
    Serial.print(" SR:"); Serial.print(dbgRight);
    Serial.print(" D:"); Serial.println(lastDistance);
  }
}
