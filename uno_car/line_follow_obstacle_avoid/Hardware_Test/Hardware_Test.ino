// Hardware bring-up test for the UNO Smart Robot Car Kit (Elegoo V3.0).
// Run this BEFORE Line_Follow_Obstacle_Avoid_Car.ino. Open the Serial Monitor
// at 9600 baud (line ending: "Newline" or "No line ending"), type a command
// letter and press Enter. Any key aborts a running test.
//
// Put the bot on a stand with the wheels OFF the ground for motor tests.
// Pin map / motor helpers mirror the main sketch -- keep them in sync.

#include <Servo.h>
Servo myservo;

const int Echo = A4;
const int Trig = A5;
const int SERVO_PIN = 3;

#define ENB 6
#define IN1 9
#define IN2 11
#define IN3 7
#define IN4 8
#define ENA 5

const int LT_R_PIN = 10;
const int LT_M_PIN = 4;
const int LT_L_PIN = 2;

// Runtime-adjustable so calibration needs no reflash; copy the final values
// into INVERT_MOTOR_DIRECTION / SWAP_SIDES in the main sketch.
bool invertDir = true;
bool swapSides = false;
int testSpeed = 120;

enum Mode { IDLE, SENSORS, ULTRASONIC };
Mode mode = IDLE;
unsigned long lastPrint = 0;

void driveWrite(int pin, int state) {
  digitalWrite(pin, invertDir ? !state : state);
}

void setMotorA(int speed) {
  speed = constrain(speed, -255, 255);
  if (speed >= 0) { driveWrite(IN1, LOW);  driveWrite(IN2, HIGH); }
  else            { driveWrite(IN1, HIGH); driveWrite(IN2, LOW); }
  analogWrite(ENA, abs(speed));
}

void setMotorB(int speed) {
  speed = constrain(speed, -255, 255);
  if (speed >= 0) { driveWrite(IN3, HIGH); driveWrite(IN4, LOW); }
  else            { driveWrite(IN3, LOW);  driveWrite(IN4, HIGH); }
  analogWrite(ENB, abs(speed));
}

void setWheels(int leftSpeed, int rightSpeed) {
  if (swapSides) { setMotorA(leftSpeed); setMotorB(rightSpeed); }
  else           { setMotorA(rightSpeed); setMotorB(leftSpeed); }
}

void stopCar() {
  digitalWrite(ENA, LOW);
  digitalWrite(ENB, LOW);
}

int getDistance() {
  digitalWrite(Trig, LOW);
  delayMicroseconds(2);
  digitalWrite(Trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(Trig, LOW);
  unsigned long duration = pulseIn(Echo, HIGH, 30000UL);
  if (duration == 0) return 0;
  return (int)(duration / 58);
}

// Waits up to ms; returns false (and stops the motors) if a key was typed.
bool waitMs(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    if (Serial.available()) {
      while (Serial.available()) Serial.read();
      stopCar();
      Serial.println("-- aborted --");
      return false;
    }
  }
  return true;
}

void printMenu() {
  Serial.println();
  Serial.println("=== Hardware test menu ===");
  Serial.println("1  IR sensors: live raw + on-line values (Ctrl: any key stops)");
  Serial.println("2  Ultrasonic: live distance, servo centred");
  Serial.println("3  Servo sweep 10 / 90 / 180 with distance at each");
  Serial.println("4  Motor A only: forward 1.5 s, stop, reverse 1.5 s");
  Serial.println("5  Motor B only: forward 1.5 s, stop, reverse 1.5 s");
  Serial.println("6  Drive sequence: forward, back, pivot left, pivot right");
  Serial.println("7  PWM ramp on each motor (find the minimum PWM that moves it)");
  Serial.println("i  toggle INVERT_MOTOR_DIRECTION");
  Serial.println("w  toggle SWAP_SIDES");
  Serial.println("+ / -  test speed +/-10");
  Serial.println("s  stop motors, back to menu");
  Serial.print("Current: invertDir="); Serial.print(invertDir);
  Serial.print(" swapSides="); Serial.print(swapSides);
  Serial.print(" testSpeed="); Serial.println(testSpeed);
}

void testSensorsTick() {
  Serial.print("L(pin2) raw="); Serial.print(digitalRead(LT_L_PIN));
  Serial.print(" on-line="); Serial.print(!digitalRead(LT_L_PIN));
  Serial.print(" | M(pin4) raw="); Serial.print(digitalRead(LT_M_PIN));
  Serial.print(" on-line="); Serial.print(!digitalRead(LT_M_PIN));
  Serial.print(" | R(pin10) raw="); Serial.print(digitalRead(LT_R_PIN));
  Serial.print(" on-line="); Serial.println(!digitalRead(LT_R_PIN));
}

void testServoSweep() {
  const int angles[] = {90, 10, 90, 180, 90};
  for (int i = 0; i < 5; i++) {
    myservo.write(angles[i]);
    Serial.print("servo angle "); Serial.print(angles[i]);
    if (!waitMs(700)) return;
    Serial.print("  distance cm = "); Serial.println(getDistance());
  }
  Serial.println("Note which physical side the sensor faced at 10 and at 180.");
  Serial.println("Main sketch assumes 10 = RIGHT, 180 = LEFT.");
}

void testSingleMotor(bool motorA) {
  Serial.print("Motor "); Serial.print(motorA ? "A" : "B");
  Serial.print(" FORWARD at PWM "); Serial.println(testSpeed);
  Serial.println("Note: which wheel (left/right/front/rear) spins, and which way.");
  if (motorA) setMotorA(testSpeed); else setMotorB(testSpeed);
  if (!waitMs(1500)) return;
  stopCar();
  if (!waitMs(700)) return;
  Serial.println("REVERSE");
  if (motorA) setMotorA(-testSpeed); else setMotorB(-testSpeed);
  if (!waitMs(1500)) return;
  stopCar();
  Serial.println("done");
}

void testDriveSequence() {
  const char *names[] = {"FORWARD", "BACK", "PIVOT LEFT (expect: turns counter-clockwise)",
                         "PIVOT RIGHT (expect: turns clockwise)"};
  const int lw[] = {1, -1, -1, 1};
  const int rw[] = {1, -1, 1, -1};
  for (int i = 0; i < 4; i++) {
    Serial.println(names[i]);
    setWheels(lw[i] * testSpeed, rw[i] * testSpeed);
    if (!waitMs(1200)) return;
    stopCar();
    if (!waitMs(800)) return;
  }
  Serial.println("done. If FORWARD went backward -> press i. If left/right pivots are");
  Serial.println("mirrored but forward/back are right -> press w. Re-run 6 to confirm.");
}

void testPwmRamp() {
  for (int m = 0; m < 2; m++) {
    Serial.print("Ramping Motor "); Serial.println(m == 0 ? "A" : "B");
    for (int pwm = 30; pwm <= 255; pwm += 10) {
      Serial.print("PWM "); Serial.println(pwm);
      if (m == 0) setMotorA(pwm); else setMotorB(pwm);
      if (!waitMs(500)) return;
    }
    stopCar();
    if (!waitMs(800)) return;
  }
  Serial.println("Record the first PWM at which each wheel actually turned (with load).");
}

void handleCommand(char c) {
  if (c == '\n' || c == '\r' || c == ' ') return;
  stopCar();
  mode = IDLE;
  switch (c) {
    case '1': mode = SENSORS; myservo.write(90); Serial.println("IR sensors -- slide a black line under each sensor:"); break;
    case '2': mode = ULTRASONIC; myservo.write(90); Serial.println("Ultrasonic -- put an object in front:"); break;
    case '3': testServoSweep(); break;
    case '4': testSingleMotor(true); break;
    case '5': testSingleMotor(false); break;
    case '6': testDriveSequence(); break;
    case '7': testPwmRamp(); break;
    case 'i': invertDir = !invertDir; break;
    case 'w': swapSides = !swapSides; break;
    case '+': testSpeed = min(testSpeed + 10, 255); break;
    case '-': testSpeed = max(testSpeed - 10, 30); break;
    case 's': break;
    default: Serial.print("unknown command: "); Serial.println(c); break;
  }
  if (mode == IDLE) printMenu();
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
  printMenu();
}

void loop() {
  if (Serial.available()) handleCommand(Serial.read());

  if (mode != IDLE && millis() - lastPrint >= 250) {
    lastPrint = millis();
    if (mode == SENSORS) testSensorsTick();
    else { Serial.print("distance cm = "); Serial.println(getDistance()); }
  }
}
