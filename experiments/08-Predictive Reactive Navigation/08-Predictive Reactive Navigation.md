# Task 8.7 — Predictive Reactive Navigation

## 1. Project Overview

**Project:** Raspberry Pi Autonomous Robot Car  
**Task:** 8.7 — Predictive Reactive Navigation  
**Platform:** Raspberry Pi 4B  
**Robot:** LOBOROBOT Four-Wheel Mecanum Robot  
**Programming Language:** Python  
**Development Environment:** Jupyter Notebook  
**Experiment Duration:** 35.8 seconds (300-second target)  
**Final Status:** `TOO_CLOSE`

### Objective

The objective of Task 8.7 was to upgrade the robot from traditional threshold-based obstacle avoidance to predictive reactive navigation.

Previous versions relied primarily on a fixed stopping distance. The robot moved forward until an obstacle was detected within a predefined threshold, then stopped and rotated to find a new direction.

Task 8.7 introduced distance trend estimation and Time to Collision (TTC) prediction so that the robot could identify approaching obstacles earlier and adjust its motion proactively.

The system was designed to:

- Continuously monitor ultrasonic distance measurements.
- Estimate how quickly the robot was approaching an obstacle.
- Predict potential collision risk using TTC.
- Reduce motor speed when approaching obstacles.
- Initiate avoidance before reaching the normal stopping threshold.
- Preserve continuous turning and obstacle search capabilities.
- Record experimental results for subsequent analysis.

The system does not implement SLAM, map construction, or global path planning. Its navigation is reactive and uses only the available onboard sensors.

---

## 2. Hardware Configuration

| Component | Specification | Function |
|---|---|---|
| Main controller | Raspberry Pi 4B | Sensor processing and decision-making |
| Robot chassis | Four-wheel Mecanum platform | Robot locomotion |
| Motor controller | LOBOROBOT | Motor direction and PWM control |
| Ultrasonic sensor | GPIO 20 (TRIG), GPIO 21 (ECHO) | Forward obstacle distance measurement |
| Camera and pan-tilt platform | Existing robot camera system | Available for vision experiments; not used for predictive navigation |

### Robot Dimensions

| Dimension | Measurement |
|---|---|
| Width | 15 cm |
| Length | 23 cm |
| Height | 20 cm |

The ultrasonic sensor was fixed relative to the robot chassis. Therefore, the robot changed its sensing direction by rotating its entire body rather than rotating the camera platform.

No additional hardware was introduced for this task.

---

## 3. Software Architecture

The Task 8.7 controller combines sensor acquisition, distance trend estimation, predictive decision-making, motor speed control, and obstacle recovery.

### Navigation Pipeline

```text
             Ultrasonic Sensor
                    |
                    v
             Distance Filtering
                    |
                    v
           Distance History Buffer
                    |
                    v
          Closing-Speed Estimation
                    |
                    v
             TTC Calculation
                    |
                    v
             Decision System
                    |
        +-----------+-----------+
        |           |           |
        v           v           v
      CRUISE      CAUTION      AVOID
        |           |           |
        v           v           v
     PWM 30       PWM 27     Stop Moving
                                |
                                v
                      Continuous Rotation
                                |
                                v
                       Clearance Check
                                |
                       +--------+--------+
                       |                 |
                       v                 v
                  Safe Route        Recovery Failure
                       |                 |
                       v                 v
                  Resume Motion      Safe Stop
```

The robot uses state-based decision-making to select an action based on measured distance, estimated approach speed, and TTC.

---

## 4. Predictive Navigation Algorithm

### 4.1 Distance Acquisition

The ultrasonic sensor measures the distance between the robot and nearby objects in the sensor's forward direction.

Raw distance measurements are processed using a median-based filtering method.

The controller also detects invalid readings and applies sensor recovery procedures when necessary.

The distance validation range was extended to 400 cm after earlier experiments demonstrated that readings slightly above 300 cm were being incorrectly rejected.

### 4.2 Distance Trend Estimation

The system stores recent distance measurements in a fixed-length history buffer.

By comparing earlier measurements with more recent ones, the controller estimates the rate at which the measured distance is decreasing.

The estimated closing speed is defined as:

\[
v_c = \frac{d_{\text{previous}} - d_{\text{current}}}{\Delta t}
\]

Where:

- \(v_c\): Estimated closing speed in cm/s
- \(d_{\text{previous}}\): Earlier distance measurement
- \(d_{\text{current}}\): Current distance measurement
- \(\Delta t\): Elapsed time between measurements

Positive closing speed indicates that the measured distance is decreasing.

This estimate is based on ultrasonic observations rather than wheel odometry. Consequently, it may be affected by sensor noise, changing reflection surfaces, and moving obstacles.

### 4.3 Time to Collision (TTC)

Time to Collision is estimated using:

\[
TTC = \frac{d}{v_c}, \quad v_c > 0
\]

Where:

- \(d\): Current measured distance
- \(v_c\): Estimated closing speed

A smaller TTC indicates a potentially more urgent obstacle-avoidance situation.

In this project, TTC serves as a reactive risk indicator rather than an exact prediction of physical collision time.

### 4.4 Predictive Avoidance

The controller evaluates whether the robot should begin avoiding an obstacle before reaching the standard stopping threshold.

Key configuration values included:

| Parameter | Value |
|---|---:|
| Normal motor PWM | 30 |
| Caution motor PWM | 27 |
| Standard stopping distance | 50 cm |
| Clearance threshold | 70 cm |
| Critical distance | 30 cm |
| Caution distance | 100 cm |
| TTC caution threshold | 3.5 s |
| TTC avoidance threshold | 1.8 s |
| Minimum estimated closing speed | 8 cm/s |
| Predictive confirmations | 2 |

An early avoidance event requires consecutive observations that satisfy the predictive risk conditions.

The robot then stops forward movement and enters its obstacle search procedure.

---

## 5. Predictive Speed Control

Task 8.7 introduced two forward movement states.

### CRUISE

The robot maintains its normal forward speed when the measured environment is considered sufficiently clear.

```python
CRUISE_PWM = 30
```

### CAUTION

The robot reduces its PWM command when an obstacle becomes closer or the estimated TTC suggests an increasing risk.

```python
CAUTION_PWM = 27
```

The intended improvement was to create a smoother transition between normal forward motion and obstacle avoidance.

However, experimental results showed frequent switching between these two states.

This indicated that the controller was overly sensitive to fluctuations in ultrasonic distance measurements.

Furthermore, a lower PWM command does not guarantee a proportionally lower ground speed, particularly without wheel-speed feedback.

---

## 6. Continuous Obstacle Search

The robot retained the continuous turning strategy developed in previous tasks.

When obstacle avoidance was triggered, the robot:

1. Stopped forward motion.
2. Selected its preferred turning direction.
3. Began rotating continuously.
4. Measured ultrasonic distance during rotation.
5. Searched for consecutive measurements indicating an open direction.
6. Stopped rotation and verified the candidate direction.
7. Resumed forward movement only after successful verification.

This approach avoided the repetitive stop-turn-measure-stop pattern seen in earlier versions.

The navigation controller also maintained a preferred turning direction based on previous successful avoidance actions.

A bounded recovery mechanism was included to prevent uncontrolled repeated searches.

---

## 7. Experimental Procedure

### Test Environment

The experiment was performed in an indoor environment containing walls and obstacles.

The robot operated using its existing ultrasonic sensor and four-wheel drive system.

No remote directional control was used during autonomous operation.

### Test Configuration

```python
TEST_DURATION = 300

CRUISE_PWM = 30
CAUTION_PWM = 27

STOP_DISTANCE = 50.0
CLEAR_DISTANCE = 70.0
CRITICAL_DISTANCE = 30.0

CAUTION_TTC = 3.5
AVOID_TTC = 1.8
```

The system recorded navigation events, distance measurements, TTC estimates, motor-state changes, and recovery actions in a CSV file.

**Experiment log:**

`task8_7_20261016_210401.csv`

---

## 8. Experimental Results

### 8.1 Overall Performance

| Metric | Result |
|---|---|
| Requested experiment duration | 300 seconds |
| Actual experiment duration | 35.8 seconds |
| Obstacle/search events | 4 |
| Confirmed successful avoidance events | 3 |
| Predictive early avoidance events | 1 |
| Turning attempts | 4 |
| Direction switches | 0 |
| Sensor recoveries | 0 |
| Final state | `TOO_CLOSE` |

The robot successfully executed continuous forward movement and completed three obstacle-avoidance operations before terminating during the fourth search.

### 8.2 Successful Predictive Avoidance

A significant result was observed when the robot initiated obstacle avoidance at approximately 94.4 cm.

```text
OBSTACLE / EARLY AVOID
Distance = 94.4 cm
TTC = 1.52 s
```

This event occurred before the robot reached its normal 50 cm stopping threshold.

The result demonstrates that the TTC-based decision mechanism was able to trigger an early avoidance action.

However, the accuracy of the TTC estimate was not independently validated using measured vehicle velocity.

### 8.3 Successful Obstacle Recovery

During the first three search events, the robot successfully found candidate directions and verified their safety according to the configured ultrasonic clearance criteria.

Example:

```text
SEARCH 1/3 | LEFT

CONTINUOUS TURN: LEFT
TURN | 52.6 cm
TURN | 54.2 cm
TURN | 56.3 cm
TURN | 67.3 cm
TURN | 184.6 cm
TURN | 184.1 cm

TURN RESULT: CANDIDATE

VERIFY: SAFE | 154.0 cm

SEARCH RESULT: CLEAR
```

These observations indicate that continuous rotation with ultrasonic sensing can identify candidate travel directions without requiring a separate rotating ultrasonic platform.

The robot subsequently resumed forward movement.

### 8.4 Cruise and Caution Switching

A major limitation was observed in the motor speed control system.

The robot repeatedly switched between `CRUISE` and `CAUTION`.

Example:

```text
CAUTION | d=98.1 cm  | PWM=27
CRUISE  | d=241.0 cm | PWM=30
CAUTION | d=89.2 cm  | PWM=27
CRUISE  | d=119.2 cm | PWM=30
```

The experimental CSV contained 25 recorded cruise/caution transitions or state-setting events: 12 `CRUISE` and 13 `CAUTION`.

These frequent changes suggested that the controller lacked sufficient hysteresis and noise resistance.

As a result, the intended smooth speed regulation was not consistently achieved.

### 8.5 Final Recovery Failure

The fourth obstacle-avoidance event did not identify a confirmed clear path.

During the final turning sequence, measured distances remained approximately between 45 cm and 50 cm.

```text
TURN RESULT: NO_CANDIDATE
SEARCH RESULT: TOO_CLOSE
```

The final `TOO_CLOSE` condition occurred