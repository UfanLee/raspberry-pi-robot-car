# Experiment #03 — Basic Robot Movement

**Day:** 03  
**Platform:** Raspberry Pi 4 Robot Car  
**Language:** Python  
**Robot Library:** `LOBOROBOT`  
**Motor Controller:** PCA9685  
**Motors:** 4 DC Motors  

---

## Objective

The goal of this experiment was to understand and verify the basic movement system of the robot car.

Rather than only running the provided movement functions, this experiment investigated how high-level robot commands are translated into individual motor commands.

The experiment covered:

- Forward movement
- Backward movement
- Left and right rotation
- Left and right lateral movement
- Four diagonal movements
- Individual motor identification
- Motor direction combinations
- Source-code inspection
- Hardware verification

---

# 1. Robot Initialization

The robot is controlled through the `LOBOROBOT` class.

```python
from LOBOROBOT import LOBOROBOT

robot = LOBOROBOT()

print("Robot initialized successfully.")
```

The first movement test used a low speed and short duration for safety.

```python
print("Moving forward...")

robot.t_up(30, 1)

print("Stopping...")

robot.t_stop(1)

print("Test finished.")
```

Result:

```text
Moving forward...
Stopping...
Test finished.
```

The physical robot successfully moved forward and stopped.

**Status: SUCCESS**

---

# 2. Forward and Backward Movement

Forward:

```python
robot.t_up(30, 1)
robot.t_stop(1)
```

Backward:

```python
robot.t_down(30, 1)
robot.t_stop(1)
```

Both movements were successfully verified on the physical robot.

At the motor level:

```text
Forward:

M0 → Forward
M1 → Forward
M2 → Forward
M3 → Forward


Backward:

M0 → Backward
M1 → Backward
M2 → Backward
M3 → Backward
```

---

# 3. Turning

The next test verified rotational movement.

```python
robot.turnLeft(30, 1)
robot.t_stop(1)

robot.turnRight(30, 1)
robot.t_stop(1)
```

Inspection of the `LOBOROBOT` implementation showed:

### Turn Left

```text
M0 → Backward
M1 → Forward
M2 → Backward
M3 → Forward
```

### Turn Right

```text
M0 → Forward
M1 → Backward
M2 → Forward
M3 → Backward
```

These motor combinations rotate the robot instead of translating it laterally.

Both directions were successfully verified.

---

# 4. Lateral Movement

The robot can also move sideways while approximately maintaining its heading.

```python
robot.moveLeft(30, 1)
robot.t_stop(1)

robot.moveRight(30, 1)
robot.t_stop(1)
```

Motor combinations:

### Move Left

```text
M0 → Backward
M1 → Forward
M2 → Forward
M3 → Backward
```

### Move Right

```text
M0 → Forward
M1 → Backward
M2 → Backward
M3 → Forward
```

The physical robot successfully moved both left and right.

This demonstrated the difference between:

```text
Translation              Rotation

← Move Left              ↺ Turn Left
→ Move Right             ↻ Turn Right
```

---

# 5. Inspecting the LOBOROBOT Source Code

Instead of treating functions such as:

```python
robot.turnLeft(30, 1)
```

as black boxes, the `LOBOROBOT` implementation was inspected.

The basic control hierarchy is:

```text
High-Level Movement Command
            │
            ▼
        LOBOROBOT
            │
            ▼
         MotorRun()
            │
      ┌─────┴─────┐
      ▼           ▼
 Direction       Speed
      │           │
      ▼           ▼
Motor Driver      PWM
      └─────┬─────┘
            ▼
        DC Motors
            │
            ▼
     Physical Movement
```

The core motor command has the form:

```python
MotorRun(motor, direction, speed)
```

For example:

```python
MotorRun(0, 'forward', 30)
```

means:

```text
Motor     = 0
Direction = Forward
Speed     = 30
```

The speed is controlled using PWM duty cycle, while motor direction is controlled through direction signals.

---

# 6. Physical Motor Identification

The four motors were tested individually to determine the relationship between software motor IDs and physical wheel positions.

Test:

```python
import time

for motor in range(4):

    print(f"Testing Motor {motor}")

    robot.MotorRun(motor, 'forward', 25)
    time.sleep(0.5)

    robot.MotorStop(motor)
    time.sleep(1)
```

The physical mapping was determined experimentally:

| Motor ID | Physical Wheel |
|---|---|
| Motor 0 | Front Left (FL) |
| Motor 1 | Front Right (FR) |
| Motor 2 | Rear Left (RL) |
| Motor 3 | Rear Right (RR) |

Therefore:

```text
                FRONT
                  ↑

         M0               M1
    Front Left       Front Right


         M2               M3
     Rear Left        Rear Right
```

This mapping was determined through direct hardware testing rather than assumption.

---

# 7. Motor Direction Matrix

After inspecting the source code and identifying the physical motors, the movement commands can be represented as a motor direction matrix.

Legend:

```text
F = Forward
B = Backward
S = Stop / not actively driven
```

| Robot Movement | M0 FL | M1 FR | M2 RL | M3 RR |
|---|---:|---:|---:|---:|
| ↑ Forward | F | F | F | F |
| ↓ Backward | B | B | B | B |
| ← Move Left | B | F | F | B |
| → Move Right | F | B | B | F |
| ↺ Turn Left | B | F | B | F |
| ↻ Turn Right | F | B | F | B |
| ↖ Forward Left | S | F | F | S |
| ↗ Forward Right | F | S | S | F |
| ↙ Backward Left | B | S | S | B |
| ↘ Backward Right | S | B | B | S |

This matrix provides a much clearer understanding of how robot movement emerges from combinations of individual wheel commands.

---

# 8. Diagonal Movement

The diagonal movements use two diagonally related motors while the other two motors are not actively driven.

## Forward Left ↖

```python
robot.MotorStop(0)
robot.MotorRun(1, 'forward', 30)
robot.MotorRun(2, 'forward', 30)
robot.MotorStop(3)
```

Result:

```text
↖ Forward Left
```

The robot successfully moved diagonally toward the front-left.

The Front Left motor (`M0`) and Rear Right motor (`M3`) were not actively driven during this movement.

---

## Forward Right ↗

```python
robot.MotorRun(0, 'forward', 30)
robot.MotorStop(1)
robot.MotorStop(2)
robot.MotorRun(3, 'forward', 30)
```

Expected motor state:

```text
M0 FL → Forward
M1 FR → Stop
M2 RL → Stop
M3 RR → Forward
```

---

## Backward Left ↙

```python
robot.MotorRun(0, 'backward', 30)
robot.MotorStop(1)
robot.MotorStop(2)
robot.MotorRun(3, 'backward', 30)
```

Expected motor state:

```text
M0 FL → Backward
M1 FR → Stop
M2 RL → Stop
M3 RR → Backward
```

---

## Backward Right ↘

```python
robot.MotorStop(0)
robot.MotorRun(1, 'backward', 30)
robot.MotorRun(2, 'backward', 30)
robot.MotorStop(3)
```

Expected motor state:

```text
M0 FL → Stop
M1 FR → Backward
M2 RL → Backward
M3 RR → Stop
```

---

# 9. Source Code Issue Found

During source-code inspection, a suspicious implementation was found in `forward_Left()`.

Original implementation:

```python
def forward_Left(self, speed, t_time):
    self.MotorStop(0)
    self.MotorRun(1, 'forward', speed)
    self.MotorRun(2, 'forward', speed)
    self.MotorStop(0)
    time.sleep(t_time)
```

`MotorStop(0)` appears twice.

Based on the symmetry of the other diagonal movement functions, the intended implementation appears to be:

```python
def forward_Left(self, speed, t_time):
    self.MotorStop(0)
    self.MotorRun(1, 'forward', speed)
    self.MotorRun(2, 'forward', speed)
    self.MotorStop(3)
    time.sleep(t_time)
```

The corrected motor combination was tested directly:

```text
M0 FL → Stop
M1 FR → Forward
M2 RL → Forward
M3 RR → Stop
```

The physical robot successfully moved toward the front-left.

This experiment demonstrated the importance of not treating library code as a black box.

---

# 10. Movement Model

The robot can now perform several types of planar motion:

```text
                 ↑
              Forward

        ↖                    ↗
  Forward Left          Forward Right


← Move Left      [ ROBOT ]      Move Right →


        ↙                    ↘
 Backward Left         Backward Right

              Backward
                 ↓
```

In addition, the robot can rotate:

```text
↺ Turn Left

↻ Turn Right
```

Therefore, the basic movement system includes:

```text
Longitudinal Translation
        +
Lateral Translation
        +
Diagonal Translation
        +
Rotation
```

This provides the low-level movement primitives required for future autonomous control.

---

# 11. From Motor Commands to Robot Motion

A key lesson from this experiment is that a robot movement command is ultimately a combination of individual wheel commands.

```text
Motor 0 ─┐
Motor 1 ─┤
Motor 2 ─┼──→ Combined Robot Motion
Motor 3 ─┘
```

At a higher level, future robot control can be thought of in terms of:

```text
vx → lateral velocity
vy → longitudinal velocity
ω  → angular velocity
```

Eventually, higher-level systems such as computer vision or autonomous navigation can generate movement decisions that are translated into these low-level motor commands.

For example:

```text
Camera
   ↓
Computer Vision
   ↓
Obstacle Detection
   ↓
Decision
   ↓
Stop / Turn / Move
   ↓
Motor Direction Matrix
   ↓
Motor Driver
   ↓
Physical Robot Motion
```

---

# Experiment Summary

The development process for Day 03 was:

```text
Initialize Robot
       ↓
Forward Test
       ↓
Backward Test
       ↓
Left / Right Rotation
       ↓
Left / Right Translation
       ↓
Inspect LOBOROBOT Source
       ↓
Understand MotorRun()
       ↓
Test Motors Individually
       ↓
Map Motor IDs to Physical Wheels
       ↓
Build Motor Direction Matrix
       ↓
Predict Diagonal Movement
       ↓
Hardware Verification
       ↓
Identify Suspicious Library Code
```

## What I Learned

This experiment introduced several important robotics concepts:

- Four-motor control
- PWM motor speed control
- Motor direction control
- High-level vs low-level robot APIs
- Physical motor mapping
- Longitudinal movement
- Lateral movement
- Rotational movement
- Diagonal movement
- Motor direction matrices
- Source-code inspection
- Hardware debugging
- Experimental verification

Most importantly, the robot movement functions are no longer black boxes.

Instead of only knowing:

```python
robot.moveLeft(30, 1)
```

I can now reason about:

```text
Desired Robot Motion
        ↓
Individual Wheel Directions
        ↓
MotorRun()
        ↓
PWM + Direction Control
        ↓
Physical Motion
```

---

## Progress

```text
Day 01 — Passive Buzzer
Raspberry Pi → Physical Output

Day 02 — User Button
Physical Input → Raspberry Pi

Day 03 — Robot Movement
Raspberry Pi → Motor Control → Physical Motion
```

The project has now progressed from basic GPIO input/output to physical robot actuation.

---

## Next Steps

Future experiments can build on this movement layer with:

- Speed control experiments
- Movement calibration
- Precise turning
- Button-controlled movement
- Obstacle detection
- Ultrasonic sensing
- Camera input
- Computer vision
- Autonomous navigation
- Closed-loop control

---

## Status

**Experiment #03 — Basic Robot Movement: SUCCESS**