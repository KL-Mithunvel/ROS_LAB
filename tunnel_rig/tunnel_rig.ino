/*
  Tunnel Rig - 4-motor tank drive, ESP32 DevKit V1 + Cytron MDD3A, Wi-Fi (UDP) control.

  - Left  motors (2, parallel) -> MDD3A channel 1 (M1A/M1B)
  - Right motors (2, parallel) -> MDD3A channel 2 (M2A/M2B)
  - MDD3A runs in PWM-PWM mode: forward = PWM on A, reverse = PWM on B, both 0 = brake.
  - The ESP32 joins the router (2.4 GHz, fixed IP) and listens for UDP packets on UDP_PORT.
    Packet:  "<seq>:<cmd>"   e.g. "1042:F"   (a bare "F" also works, for quick tests)
    Reply:   "<seq>,<rssi>,<speedLevel>,<lastCmd>"   e.g. "1042,-61,6,F"
    The PC panel uses the replies to draw the comm-health bar (RSSI, round-trip time, loss).

  Commands (case-insensitive):
    F forward   B backward   L spin left   R spin right
    G fwd-left  I fwd-right  H back-left   J back-right
    S stop (immediate)       ? ping only (no motion, does NOT feed the failsafe)
    0..9 speed level (9 = 100 %)    Q = same as 9

  Failsafe: no drive command for CMD_TIMEOUT_MS, or Wi-Fi lost -> motors stop.
  Wi-Fi credentials live in secrets.h (gitignored) - copy secrets.h.example and fill it in.

  Board: "ESP32 Dev Module" (esp32:esp32:esp32), core 3.x (uses ledcAttach/ledcWrite).
  Wiring: see README.md.  Network plan: see WIFI-PLAN.md.
*/
#include <WiFi.h>
#include <WiFiUdp.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copy secrets.h.example to secrets.h and fill in WIFI_SSID / WIFI_PASS."
#endif

// ================= CONFIG =================
// Fixed address on the router's LAN (outside its DHCP pool .100-.199).
const IPAddress LOCAL_IP(192, 168, 1, 60);
const IPAddress GATEWAY(192, 168, 1, 1);
const IPAddress SUBNET(255, 255, 255, 0);
const uint16_t  UDP_PORT = 4210;
const uint32_t  WIFI_RETRY_MS = 5000;

// MDD3A signal pins (see README wiring table)
const uint8_t PIN_L_A = 25;   // MDD3A M1A  left  forward
const uint8_t PIN_L_B = 26;   // MDD3A M1B  left  reverse
const uint8_t PIN_R_A = 32;   // MDD3A M2A  right forward
const uint8_t PIN_R_B = 33;   // MDD3A M2B  right reverse

// If a side runs backwards, flip it here instead of rewiring.
const bool INVERT_LEFT  = true;    // tested 2026-11-11: both sides ran backwards with false
const bool INVERT_RIGHT = true;

const uint32_t PWM_FREQ_HZ = 20000;      // above audible range
const uint8_t  PWM_BITS    = 8;          // duty 0..255
const uint8_t  DEFAULT_LEVEL = 6;        // speed level 0..9 at boot
const uint32_t CMD_TIMEOUT_MS = 500;     // 0 = disabled
const int      RAMP_PER_STEP = 12;       // duty change per RAMP_MS (acceleration limit)
const uint32_t RAMP_MS = 10;
// ==========================================

WiFiUDP udp;

int  speedLevel = DEFAULT_LEVEL;
int  tgtL = 0, tgtR = 0;         // target signed duty, -255..255
int  curL = 0, curR = 0;         // current signed duty
char lastCmdChar = 'S';          // reported back to the panel
uint32_t lastCmd = 0, lastRamp = 0, lastWifiTry = 0;
bool wifiWasUp = false;

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
  lastCmdChar = 'S';
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
      }
      drive = false;                              // ping '?', \r \n and unknown bytes: no motion
      break;
  }
  if (drive) { lastCmd = millis(); lastCmdChar = c; }
}

// ---------- Wi-Fi ----------
void startWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);                           // lower latency
  WiFi.setAutoReconnect(true);
  if (!WiFi.config(LOCAL_IP, GATEWAY, SUBNET)) Serial.println("[WiFi] static IP config failed");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  lastWifiTry = millis();
  Serial.printf("[WiFi] joining '%s' (2.4 GHz) as %s ...\n", WIFI_SSID, LOCAL_IP.toString().c_str());
}

void wifiLoop() {
  bool up = (WiFi.status() == WL_CONNECTED);
  if (up && !wifiWasUp) {
    udp.begin(UDP_PORT);
    Serial.printf("[WiFi] up, RSSI %d dBm, listening on udp/%u\n", WiFi.RSSI(), UDP_PORT);
  }
  if (!up && wifiWasUp) {
    udp.stop();
    stopNow();                                    // never keep driving without a link
    Serial.println("[WiFi] lost -> stop");
  }
  wifiWasUp = up;
  if (!up && millis() - lastWifiTry >= WIFI_RETRY_MS) {
    lastWifiTry = millis();
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.println("[WiFi] retrying...");
  }
}

void handleUdp() {
  int size = udp.parsePacket();
  while (size > 0) {
    char buf[32];
    int len = udp.read(buf, sizeof(buf) - 1);
    if (len <= 0) break;
    buf[len] = 0;

    long seq = 0;
    char cmd = 0;
    char* colon = strchr(buf, ':');
    if (colon) { *colon = 0; seq = atol(buf); cmd = colon[1]; }
    else       { cmd = buf[0]; }
    if (cmd) handleCommand(cmd);

    char reply[40];
    snprintf(reply, sizeof(reply), "%ld,%d,%d,%c", seq, WiFi.RSSI(), speedLevel, lastCmdChar);
    udp.beginPacket(udp.remoteIP(), udp.remotePort());
    udp.print(reply);
    udp.endPacket();

    size = udp.parsePacket();
  }
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
  startWiFi();
}

void loop() {
  wifiLoop();
  if (wifiWasUp) handleUdp();
  while (Serial.available()) handleCommand((char)Serial.read());   // USB serial for bench tests

  // Failsafe: no drive command -> stop
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
