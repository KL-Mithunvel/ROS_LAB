# Controlling motors from ROS

Wolf has four motors connected to quadrature encoders. Users can control motors directly from raspberry pi serial command.

### Installing necessary packages

To send serial commands from raspberry pi to micro controller board, we need to install `python3-serial package.` Make sure to install the below package on the `@robot` machine and not on the `@dev` machine.

```
sudo apt install python3-serial
```

Run `miniterm` with baud rate of `57600` (set on the micro controller board) on `USB0`. If unsure on which usb it is connected, check by typing `lsusb`. If Lidar is also connected, board can be connected to USB0 or USB1. In later part of tutorial, we will see how to hard code a particular port for different peripherals. To exit miniterm, press CTRL+]

```markup
    miniterm -e /dev/ttyUSB0 57600 #e for echo, USB0 is the port and 57600 is baud rate
```

The micro controller is configured as per the below commands. However, we are interested in only motor speed and encoder counts:

```sh
ANALOG_READ    'a'    # a <arg1> : Return analog value of arg1
GET_BAUDRATE   'b'    # b : Will return baud rate of motor controller
PIN_MODE       'c'    # Not used
DIGITAL_READ   'd'    # d <arg1> : Return digital value of arg1
READ_ENCODERS  'e'    # e : Return Encoder Values of all four encoders
READ_GYRO      'g'    # g : Return Gyro Values in x,y,z order
READ_ACCEL     'h'    # h : Return Accelerometer Values in x,y,z order
READ_IR_VALUE  'i'    # i : Return Sharp Sensor Values in fl, fr, bl, br order
MOTOR_SPEEDS   'm'    # m <arg1> <arg2> <arg3> <arg4> : Run motors (closed loop) as per arg values
MOTOR_RAW_PWM  'o'    # o <arg1> <arg2> <arg3> <arg4> : Run motors (open loop) as per arg values
PING           'p'    # Not used
RESET_ENCODERS 'r'    # r : Reset all encoder values to zero
SERVO_WRITE    's'    # Not used
SERVO_READ     't'    # Not used
UPDATE_PID     'u'    # Not used
DIGITAL_WRITE  'w'    # w <arg1> : Write a digital value to arg1 pin
ANALOG_WRITE   'x'    # x <arg1> : Write an analog value to arg1 pin
ZOMBIE_DRIVE   'z'    # z : Drive in autonomous mode <TBD>
FRONTLEFT       0
FRONTRIGHT      1
BACKLEFT        2
BACKRIGHT       3
```

Type `e` and it should output encoder count. If robot has not moved, it will echo `0 0 0 0`

To run the robot, type the m and `o` commands. However, make sure robot wheels are not touching the ground, or it is safe to drive as it moves the robot for 2 seconds in the said speed.

### PWM based motor control

`o 127 127 127 127` # This will run the motors at 50% speed straight

`o -255 -255 -255 -255` # This will run the motors at 1000% speed reverse

### Encoder based motor control

Counts per rotation of wolf motor (CPR) is 560 and PID is running at 28hz. So, to get one rotation per second, we need to send 20 ticks. The Motor driver is designed to make sure it receives signal every 2 seconds. If any signal in 2 seconds, robot stops.

`m 20 20 20 20` # run the motor for 2 seconds at 1 revolutions per second

When trying encoder based motor control, the motor does not run complete two runs for 2 seconds. This is a latency issue due to Wi-Fi setup. If you set m to 25, then the wheels turn at exactly 1 revolutions per second. However, for continuous run, or navigation, it takes 20 ticks per revolution.

Reset Encoder Count

To reset the encoder count, type `r` without any arguments. This resets all encoders to 0 (zero).

### GUI based motor Control

Copy `serial_motor_demo` package from downloaded folder to `dev_ws/src`. Push the package to your GitHub repository and clone the same package on the `@robot` machine. If you need a direct link to download on your raspberry pi, clone the below repository on your pi.

```sh
git clone https://github.com/VEEROBOT/serial_motor_demo-main.git
```

`@robot`, type:

```sh
ros2 run serial_motor_demo driver --ros-args -p serial_port:=/dev/ttyUSB0 -p baud:=57600 -p loop_rate:=28 -p encoder_cpr:=560 # on the robot
```

`@dev`, type:

```sh
ros2 run serial_motor_demo gui # on the development machine
```

Use the sliders on GUI to move motors either on raw speed mode (o) or feedback mode (`m`).
