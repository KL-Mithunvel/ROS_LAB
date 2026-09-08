# Getting Started with Beetlebot

***

### Before You Begin

#### ⏱️ Time Required

* **Unboxing & Inspection:** 10 minutes
* **Initial Charging:** 8 hours (first time only)
* **System Setup:** 60-90 minutes (one-time configuration)
* **First Drive:** 20 minutes

#### ✅ What You'll Need

* ✅ Beetlebot robot (in transport case)
* ✅ Laptop or PC with Ubuntu 22.04/24.04
* ✅ WiFi network with internet access
* ✅ Power outlet for charging
* ✅ 2× AAA batteries (for controller)
* ⚠️ **8 hours for first charge!** (Plan accordingly)

#### 📚 Prerequisites

* Basic Linux command line knowledge (helpful, not required)
* Familiarity with SSH (helpful, not required)
* No prior ROS2 experience needed!

***

### Step 1: Unboxing & Inspection

#### 📦 Unpack Carefully

1. **Open transport case** - Remove Beetlebot carefully
2. **Check for damage** - Inspect chassis, wheels, sensors
3. **Verify contents** - Ensure all items present (see checklist below)

#### ✅ Contents Checklist

Verify you have everything:

* [ ] **Beetlebot robot** - Fully assembled
* [ ] **Wireless controller** - Cosmic Byte Nexus or Similar
* [ ] **USB RF dongle** - For controller (may already be plugged into robot)
* [ ] **12V 2A charger** - With 2.1mm jack
* [ ] **Optional camera mount** - Metal bracket (in box, not mounted)
* [ ] **Documentation QR code** - On box or instruction card
* [ ] **Transport case** - For storage and transport

**Missing items?** Contact <support@veerobot.com> immediately with your order number.

***

### Step 2: Initial Hardware Inspection

\[PLACEHOLDER: Top-down photo with labeled callouts]

#### Physical Inspection Checklist

Walk around the robot and verify:

**Front:**

* [ ] **Camera visible** - Raspberry Pi Camera behind camera hole
* [ ] **Front wheels** - Spin freely, no damage to treads
* [ ] **Chassis intact** - No cracks or loose parts

**Top:**

* [ ] **LiDAR mounted** - RPLidar C1 centered on front of top plate
* [ ] **Top plate secure** - Top plate with hinge firmly attached
* [ ] **No loose wires** - All cables secured

**Back:**

\[PLACEHOLDER: Back panel photo with labels]

* [ ] **RJ45 connector** - Ethernet port accessible
* [ ] **Power switch** - Flat button with red LED ring (should be OFF - no glow)
* [ ] **Reset button** - Small tactile button (raised button)
* [ ] **Charging port** - 2.1mm jack accessible
* [ ] **OLED display** - May or may not be present (optional feature)

**Sides:**

* [ ] **USB port** - RF dongle may already be inserted (removable)
* [ ] **Wheels** - All 4 wheels spin freely
* [ ] **No obstructions** - Nothing blocking wheel movement

**Bottom:**

* [ ] **Battery secure** - Battery firmly mounted (do not remove unless instructed)
* [ ] **No loose screws** - All mounting hardware tight
* [ ] **Wheels clear ground** - Robot sits level

#### ⚠️ Issues Found?

**If anything is damaged or missing:**

1. Take clear photos
2. Email <support@veerobot.com> immediately
3. Do NOT power on if damage is visible
4. Include your order number

**If everything looks good:** → Continue to Step 3

***

### Step 3: Controller Setup

#### Install Batteries

The Cosmic Byte Nexus controller requires 2× AAA batteries:

1. **Flip controller over** - Find battery compartment on back
2. **Slide cover open** - Usually a tab to press and slide
3. **Insert 2× AAA batteries** - Match polarity (+/- markings)
4. **Close cover** - Slide back until it clicks

#### Verify Controller Power

1. **Toggle power button** - Bottom center of the dongle
2. **LED should light up** - Controller is powered
3. **If LED doesn't light:** Check battery polarity and contact

#### Locate RF Dongle

The USB RF dongle may be:

* **Option A:** Already plugged into robot's side USB port
* **Option B:** Inside the battery compartment of the controller

**If dongle is not plugged:** Keep it safe - you'll plug it in after first boot.

***

### Step 4: First Charge (IMPORTANT!)

#### ⚠️ Critical First Step

**Your robot ships at \~50% charge (storage mode) and MUST be charged for 8 hours before first use.**

#### Charging Procedure

1. **Verify robot is OFF**
   * Check power switch on back - should be in OFF position
   * Red LED ring should NOT be glowing
2. **Connect charger**
   * Plug charger into wall outlet (wait for LED on charger brick)
   * Insert 2.1mm jack into charging port on robot's back panel
   * **Polarity:** Center positive (standard) - can't reverse, don't force
3. **Verify charging started**
   * **Charger LED should be RED** (charging)
   * If LED is green immediately, try pressing power switch once (sometimes needed)
4. **Wait 8 hours** ⏰
   * Yes, really! First charge conditions the battery
   * Charger is smart - won't overcharge
   * LED will turn GREEN when complete (may take 6-8 hours)
   * **Note:** Sometimes charger stops at 12.4-12.5V (slightly before full) - this is normal
5. **After 8 hours:**
   * Charger LED should be green
   * If still red after 8 hours, that's okay - unplug anyway
   * Battery is now conditioned and ready for use

#### Charging Best Practices

**For all future charges:**

* Normal charging: **4 hours**
* Charge when voltage <10.5V
* Can charge while powered ON or OFF
* Store at \~50% charge if not using for >2 weeks
* Charge in well-ventilated area
* Place on non-flammable surface

***

### Step 5: First Power-On

#### 🎉 Time to Boot Your Robot!

After charging is complete:

1. **Disconnect charger** - Unplug from robot and wall
2. **Position robot safely**
   * Place on flat, stable surface
   * Ensure 1 meter clear space around robot
   * Nothing blocking wheels
3. **Power ON!**
   * Locate power switch on back panel (flat button)
   * Press firmly once (you'll feel a faint click)
   * **Red LED ring should illuminate** immediately
   * This means power is flowing
4. **Wait for boot** (\~60-90 seconds)
   * Raspberry Pi is booting Ubuntu + ROS2
   * You won't see much happening (headless system)
   * **Controller LED indicators** (if dongle plugged in):
     * **Green LED:** Power (should be on)
     * **Red LED ON:** Pi is still booting (wait...)
     * **Red LED OFF:** Pi has booted! ✅ (system is ready)
5. **First boot checklist:**
   * [ ] Power LED glowing red (on back panel)
   * [ ] RF dongle green LED on (if plugged in)
   * [ ] RF dongle red LED off after \~90 seconds
   * [ ] No smoke, strange smells, or unusual sounds
   * [ ] LiDAR may spin briefly (motor test) - normal!

#### What's Happening Inside?

During boot, the robot is:

1. Booting Ubuntu 24.04 on Raspberry Pi 5 (\~30 seconds)
2. Starting ROS2 Jazzy services (\~15 seconds)
3. Launching Lyra bridge (STM32 communication) (\~10 seconds)
4. Starting joystick control node (\~5 seconds)
5. Running system health checks (\~10 seconds)
6. Ready for operation! (\~90 seconds total)

⚠️ After boot (Red LED turns off), wait for 10-15 seconds for controller to stabilize

***

### Step 6: Verify Controller Connection

#### Test Controller Pairing

The controller should auto-pair with the RF dongle:

1. **Ensure RF dongle is in robot** (or plug it in now)
2. **Turn on controller** (press power button)
3. **Controller LED should be solid** (not blinking)
   * **Solid = Connected** ✅
   * **Blinking = Not connected** ❌

#### If Controller Won't Pair:

**Try this sequence:**

1. Power off robot (press power switch)
2. Remove RF dongle from robot
3. Wait 10 seconds
4. Plug dongle back into robot
5. Power on robot
6. Wait for boot (90 seconds)
7. Turn on controller
8. Should connect within 5-10 seconds

**Still not pairing?**

* Try different USB port on robot (if accessible)
* Check controller batteries are fresh
* Controller may need re-pairing (see troubleshooting section)

***

### Step 7: First Movement Test

#### ⚠️ Safety First!

Before moving the robot:

* ✅ Robot on flat, clear surface
* ✅ 1+ meter clearance all around
* ✅ You are ready to press power switch if needed (emergency stop)
* ✅ Nothing valuable nearby (just in case!)

#### The Deadman Switch

**Critical concept:** Beetlebot has a "deadman switch" for safety.

* **Left Bumper (LB)** = ARM/ENABLE button
* **Robot will ONLY move when LB is pressed and held**
* Release LB → robot stops immediately and disarms

Think of it like a "dead man's switch" on industrial equipment - release the button, everything stops.

#### First Drive Attempt

1. **Hold Left Bumper (LB)** - Press and HOLD with left index finger
   * Robot is now ARMED
2. **Gently push left stick forward** - Just a tiny bit
   * Robot should move slowly forward
   * Keep LB pressed the whole time!
3. **Release left stick** - Robot should slowly stop (but stay armed)
4. **Release LB button** - Robot disarms (extra safety)

#### ✅ Success Indicators:

If you see/experience:

* ✅ Robot moved forward when stick pushed
* ✅ Robot stopped when stick released
* ✅ Robot stopped when LB released
* ✅ Smooth, controlled motion (not jerky)
* ✅ All 4 wheels turning in same direction

**Congratulations!** Your robot is working correctly!

#### ❌ Troubleshooting First Drive:

**Robot doesn't move at all:**

* Is LB button actually pressed? (try pressing harder)
* Is controller connected? (check LED is solid, not blinking)
* Is battery charged? (should be after 8-hour charge)
* Try power-cycling robot (off/on)

**Robot moves backward instead of forward:**

* This is a configuration issue (rare) - contact support
* Do NOT attempt to fix yourself

**Robot spins in circles:**

* One side may have reversed wiring - contact support

**Robot moves but jerky/stuttering:**

* Check battery voltage (may need charging despite initial charge)
* Check all 4 wheels spin freely

**Only some wheels move:**

* Motor connection issue - contact support
* Do NOT attempt to disassemble

Robot moves opposite to joystick movement on strict angular movement

* This is by design so that back left and back right aligns with ROS

***

### Step 8: Controller Button Familiarization

\[PLACEHOLDER: Controller diagram with labeled buttons]

Now that robot responds, learn the controls:

#### Essential Buttons:

**Left Bumper (LB)** - Top left shoulder button

* **Function:** ARM/DISARM (deadman switch)
* **Usage:** Must hold for any movement
* **Safety:** Release to stop immediately

**Left Stick** - Left analog joystick

* **Y-Axis (up/down):** Forward/Backward speed
* **Function:** Controls linear velocity
* **Range:** Push gently for slow, full push for max speed

**Right Stick** - Right analog joystick

* **X-Axis (left/right):** Turn left/right
* **Function:** Controls rotation (angular velocity)
* **Range:** Gentle = slow turn, full = sharp turn

**Right Bumper (RB)** - Top right shoulder button

* **Function:** TURBO mode (optional, hold with LB)
* **Effect:** Doubles max speed (use carefully!)
* **Usage:** Hold both LB + RB for faster movement

#### Control Practice Exercise:

Try these maneuvers (remember to hold LB!):

1. **Forward/Backward:**
   * Hold LB
   * Push left stick up → forward
   * Push left stick down → backward
   * Release stick → stop
2. **Turning in place:**
   * Hold LB
   * Push right stick left → spin counterclockwise
   * Push right stick right → spin clockwise
   * Release stick → stop spinning
3. **Drive in curves:**
   * Hold LB
   * Push left stick forward (moving forward)
   * Push right stick left while moving → curved left turn
   * Push right stick right while moving → curved right turn
4. **Turbo mode** (advanced):
   * Hold LB + RB together
   * Push left stick forward → faster than normal
   * Use with caution! More speed = less control

**Practice for 5-10 minutes until comfortable!**

***

### Step 9: Safe Shutdown

When done practicing:

#### Proper Shutdown Sequence:

1. **Stop the robot**
   * Release all controls (LB, sticks)
   * Robot should be stationary
2. **Power off robot**
   * Press power switch on back panel
   * Red LED will turn off
   * Wait 10 seconds for Pi to fully shutdown
3. **Turn off controller**
   * Press power button to turn off
   * Saves battery life
4. **Charging (if needed)**
   * Check battery voltage if possible
   * If <11V, charge before next use
   * Normal charge: 4 hours

**Do NOT:**

* ❌ Pull battery connector while powered on
* ❌ Press reset button unless system is frozen
* ❌ Leave robot powered on unattended

***

### What's Next?

#### ✅ If Everything Worked:

**Congratulations!** You've successfully:

* ✅ Unboxed and inspected your robot
* ✅ Charged the battery properly
* ✅ Powered on for the first time
* ✅ Connected the controller
* ✅ Driven the robot successfully
* ✅ Learned basic controls

#### 🚀 Ready for Next Steps:

**Choose your path:**

**Option A: Quick Start (Impatient Users)**\
→ Skip ahead to **Hardware Familiarization** tutorial\
→ Start driving and learning by doing\
→ Come back to setup later when needed

**Option B: Proper Setup (Recommended)**\
→ Continue to **System Setup Guide**\
→ Configure WiFi, SSH, development environment\
→ Then proceed to tutorials in order

**Option C: Just Want to Drive**\
→ You can already drive with the joystick!\
→ Robot auto-starts joystick control on every boot\
→ No additional setup needed for basic teleoperation\
→ Setup required only for: mapping, navigation, development

#### 📚 Recommended Path for Learning:

```
1. Getting Started (you are here!) ✅
2. System Setup Guide (WiFi, SSH, network)
3. Hardware Familiarization (understand your robot)
4. ROS2 Communication & Tools (learn ROS2 basics)
5. Continue through tutorials...
```

***

### Quick Reference Card

**Print or screenshot this for easy access:**

```
╔═══════════════════════════════════════════════════════╗
║           BEETLEBOT QUICK REFERENCE                   ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  POWER ON:    Press power switch (back panel)         ║
║  BOOT TIME:   90 seconds (wait for red LED off)       ║
║                                                       ║
║  ARM:         Hold Left Bumper (LB)                   ║
║  FORWARD:     Left stick up (while holding LB)        ║
║  BACKWARD:    Left stick down                         ║
║  TURN:        Right stick left/right                  ║
║  TURBO:       Hold LB + RB together                   ║
║  STOP:        Release LB button                       ║
║                                                       ║
║  BATTERY:                                             ║
║    12.6V = Full charge                                ║
║    11.1V = Nominal (good)                             ║
║    10.5V = Recharge soon                              ║
║    9.3V = System shutdown (BMS cutoff)                ║
║                                                       ║
║  CHARGING:                                            ║
║    First time: 8 hours                                ║
║    Normal: 4 hours                                    ║
║    LED Red = Charging                                 ║
║    LED Green = Full                                   ║
║                                                       ║
║  EMERGENCY:   Press power switch OFF                  ║
║                                                       ║
║  SUPPORT:     support@veerobot.com                    ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

***

### Troubleshooting

#### Power Issues

**Robot won't turn on (red LED doesn't light):**

* Battery completely dead? (charge for 4 hours)
* Battery connector loose? (check connection, don't force)
* Power switch faulty? (contact support)

**Robot turns on but Controller LEDs don't light:**

* Dongle not fully inserted? (remove and reinsert)
* Dongle in wrong port? (try different USB port if accessible)
* Dongle faulty? (contact support)

#### Controller Issues

**Controller won't connect (LED keeps blinking):**

* Remove and reinsert RF dongle
* Power cycle robot (off, wait 10s, on)
* Replace controller batteries

**Controller connected but robot doesn't respond:**

* Are you holding LB button? (must be pressed!)
* Controller batteries low? (replace)
* ROS2 not started yet? (wait full 90 seconds after boot)
* Restart robot as sometimes Start up services might not not have started

#### Movement Issues

**Robot moves but very slow:**

* Battery voltage low? (charge battery)
* Not in turbo mode? (normal - 0.5 m/s is default)
* Wheels obstructed? (check for debris)

**Robot stops after a few seconds:**

* This is normal safety behavior (500ms timeout)
* Keep sending commands (hold sticks)
* Prevents runaway if controller disconnects

#### Charging Issues

**Charger LED stays green (won't charge):**

* Battery already full (check voltage)
* Charger polarity reversed? (should only fit one way)
* Try power-cycling robot once (sometimes needed)

**Charger LED never turns green:**

* Battery may be deeply discharged (charge overnight)
* May stop at 12.4-12.5V (acceptable, use anyway)
* Charger may be faulty (contact support)

***

### Getting Help

**Need assistance?**

1. **Check this troubleshooting section first**
2. **Search documentation** at <https://docs.veerobot.com>
3. **Email support** at <support@veerobot.com> with:
   * Clear description of problem
   * What you've tried
   * Photos/videos if possible
   * When you purchased robot

**Expected response time:** Within 24 hours (business days)

***

**Successfully completed Getting Started?** → Continue to System Setup Guide

**Want to start learning immediately?** → Jump to Hardware Familiarization

***

*Last Updated: January 2026*\
*Page 2 of Beetlebot Documentation*
