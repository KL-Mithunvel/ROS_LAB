//www.elegoo.com
// Merged line-following + obstacle-avoidance sketch for the Elegoo/VEEROBOT
// UNO Smart Robot Car Kit V3.0. Combines Line_tracking_car.ino (IR line
// sensors) with Obstacle_Avoidance_Car.ino (servo + HC-SR04 ultrasonic).
//
// Behaviour:
//   - default: follow the black line with the 3 IR sensors.
//   - obstacle within OBSTACLE_DISTANCE_CM ahead: stop, probe left with the
//     servo-mounted ultrasonic; if clear, steer around it on the left. If
//     the left is blocked, probe right instead and steer around there. If
//     both sides are blocked, back off a little and let the next loop()
//     re-scan rather than push into the obstacle.
//   - after going around, creep forward sweeping the IR sensors (with a
//     timeout) until the line is found again, then resume line-following.
//
// Motor pin mapping and servo angle convention (10=right, 90=center,
// 180=left) are taken from Obstacle_Avoidance_Car.ino, since its
// forward()/back() functions match their own Serial print comments.
// Line_tracking_car.ino used a different pin layout where forward()/back()
// were swapped relative to their comments -- do not mix the two pin sets.

#include <Servo.h>
Servo myservo;

// ---- Ultrasonic + servo (from Obstacle_Avoidance_Car.ino) ----
const int Echo = A4;
const int Trig = A5;
const int SERVO_PIN = 3;

// ---- Motor driver (from Obstacle_Avoidance_Car.ino) ----
#define ENB 6
#define IN1 9
#define IN2 11
#define IN3 7
#define IN4 8
#define ENA 5
const int carSpeed = 170;

// ---- Line sensors (from Line_tracking_car.ino) ----
#define LT_R !digitalRead(10)
#define LT_M !digitalRead(4)
#define LT_L !digitalRead(2)

// ---- Tuning ----
const int OBSTACLE_DISTANCE_CM = 20;
const unsigned long AVOID_TURN_MS = 400;
const unsigned long AVOID_FORWARD_MS = 600;
const unsigned long LINE_SEARCH_TIMEOUT_MS = 3000;

void forward() {
  analogWrite(ENA, carSpeed);
  analogWrite(ENB, carSpeed);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void back() {
  analogWrite(ENA, carSpeed);
  analogWrite(ENB, carSpeed);
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void left() {
  analogWrite(ENA, carSpeed);
  analogWrite(ENB, carSpeed);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void right() {
  analogWrite(ENA, carSpeed);
  analogWrite(ENB, carSpeed);
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void stopCar() {
  digitalWrite(ENA, LOW);
  digitalWrite(ENB, LOW);
}

// Distance in cm, or 0 on echo timeout (nothing in range).
int getDistance() {
  digitalWrite(Trig, LOW);
  delayMicroseconds(2);
  digitalWrite(Trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(Trig, LOW);
  unsigned long duration = pulseIn(Echo, HIGH, 30000UL); // 30 ms timeout ~5 m
  if (duration == 0) return 0;
  return (int)(duration / 58);
}

bool onLine() {
  return LT_M || LT_L || LT_R;
}

void followLineStep() {
  if (LT_M) {
    forward();
  } else if (LT_R) {
    right();
  } else if (LT_L) {
    left();
  } else {
    stopCar();
  }
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
  stopCar();
}

void loop() {
  int distance = getDistance();
  if (distance > 0 && distance <= OBSTACLE_DISTANCE_CM) {
    avoidObstacle();
    return;
  }
  followLineStep();
}
