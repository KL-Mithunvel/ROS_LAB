/*
  Tunnel Rig - 4-motor tank drive, ESP32 DevKit V1 + Cytron MDD3A, Android Classic Bluetooth.

  - Left  motors (2, parallel) -> MDD3A channel 1 (M1A/M1B)
  - Right motors (2, parallel) -> MDD3A channel 2 (M2A/M2B)
  - MDD3A runs in PWM-PWM mode: forward = PWM on A, reverse = PWM on B, both 0 = brake.
  - Bluetooth Classic SPP (BluetoothSerial, built into the ESP32 core). Android only.
    Pair "TunnelRig", then send single characters from a serial-Bluetooth app.

  Commands (case-insensitive):
    F forward   B backward   L spin left   R spin right
    G fwd-left  I fwd-right  H back-left   J back-right
    S stop (immediate)
    0..9 speed level (0 = stopped-speed, 9 = 100 %)
    q   full speed (same as 9)

  Failsafe: if no drive command arrives for CMD_TIMEOUT_MS the motors stop.
  Joystick apps resend the command while a button is held, so hold = drive, release = stop.
  Set CMD_TIMEOUT_MS to 0 to disable (a single tap then drives until you send S).

  Board: "ESP32 Dev Module" (esp32:esp32:esp32), core 3.x (uses ledcAttach/ledcWrite).
  Wiring: see README.md.
*/
#include <BluetoothSerial.h>

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error "Bluetooth Classic is not enabled for this board - select 'ESP32 Dev Module'."
#endif

// ================= CONFIG =================
const char* BT_NAME = "TunnelRig";

// MDD3A signal pins (see README wiring table)
const uint8_t PIN_L_A = 25;   // MDD3A M1A  left  forward
const uint8_t PIN_L_B = 26;   // MDD3A M1B  left  reverse
const uint8_t PIN_R_A = 32;   // MDD3A M2A  right forward
const uint8_t PIN_R_B = 33;   // MDD3A M2B  right reverse

// If a side runs backwards, flip it here instead of rewiring.
const bool INVERT_LEFT  = false;
const bool INVERT_RIGHT = false;

const uint32_t PWM_FREQ_HZ = 20000;      // above audible range
const uint8_t  PWM_BITS    = 8;          // duty 0..255
const uint8_t  DEFAULT_LEVEL = 6;        // speed level 0..9 at boot
const uint32_t CMD_TIMEOUT_MS = 500;     // 0 = disabled
const int      RAMP_PER_STEP = 12;       // duty change per RAMP_MS (acceleration limit)
const uint32_t RAMP_MS = 10;
// ==========================================

BluetoothSerial SerialBT;

int  speedLevel = DEFAULT_LEVEL;
int  tgtL = 0, tgtR = 0;         // target signed duty, -255..255
int  curL = 0, curR = 0;         // current signed duty
uint32_t lastCmd = 0, lastRamp = 0;

// Write a signed duty (-255..255) to one MDD3A channel.
void driveChannel(uint8_t pinA, uint8_t pinB, int duty, bool invert) {
  if (invert) duty = -duty;
  if (duty >= 0) { ledcWrite(pinA, duty);  ledcWrite(pinB, 0); }
  else           { ledcWrite(pinA, 0);     ledcWrite(pinB, -duty); }
}

void applyOutputs() {
  driveChannel(PIN_L_A, PIN_L_B, curL, INVERT_LEFT);
  driveChannel(PIN_R_A, PIN_R_B, curR, INVERT_RIGHT);
}

void stopNow() {                 // immediate stop, no ramp
  tgtL = tgtR = curL = curR = 0;
  applyOutputs();
}

int levelToDuty(int level) { return (level * 255) / 9; }

// lPct / rPct: each side's share of the current speed level, -100..100 (negative = reverse).
void setDrive(int lPct, int rPct) {
  int duty = levelToDuty(speedLevel);
  tgtL = duty * lPct / 100;
  tgtR = duty * rPct / 100;
}

int stepToward(int cur, int tgt) {
  if (cur < tgt) return min(cur + RAMP_PER_STEP, tgt);
  if (cur > tgt) return max(cur - RAMP_PER_STEP, tgt);
  return cur;
}

void handleCommand(char c) {
  if (c >= 'a' && c <= 'z') c -= 32;             // upper-case
  bool drive = true;
  switch (c) {
    case 'F': setDrive( 100,  100); break;
    case 'B': setDrive(-100, -100); break;
    case 'L': setDrive(-100,  100); break;       // spin on the spot
    case 'R': setDrive( 100, -100); break;
    case 'G': setDrive(  40,  100); break;       // forward + left
    case 'I': setDrive( 100,   40); break;       // forward + right
    case 'H': setDrive( -40, -100); break;       // back + left
    case 'J': setDrive(-100,  -40); break;       // back + right
    case 'S': stopNow(); drive = false; break;
    case 'Q': speedLevel = 9; drive = false; break;
    default:
      if (c >= '0' && c <= '9') {
        speedLevel = c - '0';
        // re-scale a move that is already in progress
        int base = max(abs(tgtL), abs(tgtR));
        if (base > 0) {
          int newBase = levelToDuty(speedLevel);
          tgtL = (int)((long)tgtL * newBase / base);
          tgtR = (int)((long)tgtR * newBase / base);
        }
        Serial.printf("[SPEED] level %d\n", speedLevel);
        SerialBT.printf("speed %d\n", speedLevel);
      }
      drive = false;                              // ignore \r \n and unknown bytes
      break;
  }
  if (drive) lastCmd = millis();
}

void setup() {
  Serial.begin(115200);
  delay(200);

  // Outputs low BEFORE anything else so the motors stay off at boot.
  const uint8_t pins[] = {PIN_L_A, PIN_L_B, PIN_R_A, PIN_R_B};
  for (uint8_t p : pins) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
    if (!ledcAttach(p, PWM_FREQ_HZ, PWM_BITS)) {
      Serial.printf("[PWM] ledcAttach failed on GPIO%u - halting\n", p);
      while (true) delay(1000);
    }
  }
  stopNow();

  if (!SerialBT.begin(BT_NAME)) {
    Serial.println("[BT] failed to start - halting");
    while (true) delay(1000);
  }
  Serial.printf("[BT] ready. Pair with '%s' on Android and open a serial-Bluetooth app.\n", BT_NAME);
}

void loop() {
  while (SerialBT.available()) handleCommand((char)SerialBT.read());
  while (Serial.available())   handleCommand((char)Serial.read());   // USB serial for bench tests

  // Failsafe: link lost / no commands -> stop
  if (CMD_TIMEOUT_MS && (tgtL || tgtR || curL || curR) && millis() - lastCmd > CMD_TIMEOUT_MS) {
    stopNow();
    Serial.println("[FAILSAFE] no command -> stop");
  }

  if (millis() - lastRamp >= RAMP_MS) {
    lastRamp = millis();
    if (curL != tgtL || curR != tgtR) {
      curL = stepToward(curL, tgtL);
      curR = stepToward(curR, tgtR);
      applyOutputs();
    }
  }
}
