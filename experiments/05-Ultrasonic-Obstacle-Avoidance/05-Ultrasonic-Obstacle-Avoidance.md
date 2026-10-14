# Experiment 05 — Ultrasonic Obstacle Avoidance

## 1. Objective

Develop a basic ultrasonic obstacle avoidance system for a Raspberry Pi robot car.

The experiment focuses on measuring obstacle distance, making movement decisions based on a predefined threshold, and controlling the robot's motors.

## 2. Hardware and Software

**Hardware**
- Raspberry Pi 4
- Four-wheel robot car chassis
- Ultrasonic distance sensor
- Motor driver and PCA9685 PWM controller
- Battery power supply

**Software**
- Python 3
- `RPi.GPIO`
- `LOBOROBOT`
- Jupyter Notebook
- Python `time` and `statistics` modules

## 3. GPIO Configuration

| Component | BCM GPIO | Function |
|---|---|---|
| Ultrasonic TRIG | GPIO20 | Output |
| Ultrasonic ECHO | GPIO21 | Input |

The TRIG pin generates a short ultrasonic trigger pulse. The ECHO pin is used to measure the duration of the returned signal.

The ECHO signal must be electrically compatible with the Raspberry Pi's 3.3V GPIO inputs.

## 4. Working Principle

The ultrasonic sensor estimates the distance to an obstacle by measuring the round-trip travel time of a sound wave.

The distance is calculated using:

\[
d = \frac{v \times t}{2}
\]

Where:
- \(d\) is the distance to the obstacle.
- \(v\) is the speed of sound, approximately 343 m/s.
- \(t\) is the measured echo duration.

The result is divided by two because the sound travels to the obstacle and returns to the sensor.

## 5. Implementation

### 5.1 Ultrasonic Distance Measurement

A Python function was implemented to:

1. Generate a 10-microsecond trigger pulse.
2. Wait for the ECHO signal to become HIGH.
3. Measure the HIGH pulse duration.
4. Convert the pulse duration into distance.
5. Return `None` when the measurement times out.

Timeout handling was added to prevent the program from waiting indefinitely for a sensor response.

### 5.2 Distance-Based Decision Making

A threshold of 40 cm was used.

| Condition | Action |
|---|---|
| Distance ≥ 40 cm | FORWARD |
| Distance < 40 cm | AVOID |
| Invalid measurement (`None`) | STOP |

An earlier conservative test used `STOP` instead of `AVOID` when an obstacle was detected.

### 5.3 Median Filtering

A median filter was implemented using three distance samples.

The filter was designed to reduce the influence of occasional unusual measurements.

Ten filtered measurements were recorded:

`56.6, 36.9, 70.2, 63.2, None, 16.9, 12.6, 10.5, 9.5, 12.3 cm`

Nine measurements returned numeric values, while one returned `None`.

Although the filtering code executed successfully, further controlled testing is needed to determine whether it improves accuracy and stability.

### 5.4 Active Obstacle Avoidance

The final test program implemented the following behavior:

**Clear path**
- Move forward for 0.2 seconds.
- Stop.

**Obstacle detected**
- Stop.
- Reverse for 0.3 seconds.
- Stop.
- Turn right for 0.4 seconds.
- Stop.

**Sensor timeout**
- Stop the motors.

The motor speed parameter was set to 25.

The test was limited to five iterations, with motor-stop commands and GPIO cleanup included.

## 6. Experimental Results

### 6.1 Initial Distance Measurements

The initial distance test produced 15 numeric readings, ranging from 5.6 cm to 35.8 cm.

The readings changed as obstacles were moved in front of the sensor.

### 6.2 Threshold Control

A separate test confirmed that the software selected:

- `FORWARD` for distances above the threshold.
- `STOP` for distances below the threshold.
- `STOP` for invalid measurements.

Several intermittent `None` readings were observed.

### 6.3 Active Avoidance Test

The final five-iteration test produced:

| Trial | Distance | Decision |
|---|---:|---|
| 1 | 35.4 cm | AVOID |
| 2 | 6.5 cm | AVOID |
| 3 | 14.7 cm | AVOID |
| 4 | 35.5 cm | AVOID |
| 5 | 35.5 cm | AVOID |

All five readings were below the 40 cm threshold.

The program entered the `AVOID` branch in all five trials and finished without a Python exception.

**Physical verification:** The actual reverse-then-right-turn wheel movement remains to be explicitly confirmed.

## 7. Troubleshooting

### Issue 1 — `NameError: robot is not defined`

**Cause:** The `LOBOROBOT` object had not been initialized in the active Jupyter session.

**Resolution:** Imported the `LOBOROBOT` class and created a robot instance.

### Issue 2 — GPIO Channel Not Configured as OUTPUT

The ultrasonic measurement function initially failed because the TRIG pin had not been configured as an output.

Later, a motor control operation failed because a motor-direction GPIO channel was no longer configured as an output.

**Cause:** GPIO cleanup and reinitialization were not consistently managed across notebook cells.

**Resolution:**
- Initialize the robot motor controller.
- Configure the ultrasonic sensor GPIO pins.
- Run the experiment.
- Stop all motors.
- Perform GPIO cleanup at the end.

### Issue 3 — Intermittent Sensor Timeouts

Some distance measurements returned `None`.

**Possible contributing factors:**
- Weak or missing ultrasonic reflections
- Object angle and surface material
- Electrical noise
- Measurement timing

**Resolution:** Added timeout handling and a fail-safe STOP decision.

## 8. Key Learnings

This experiment introduced:

- Ultrasonic time-of-flight distance measurement
- GPIO input and output configuration
- Distance-based movement decisions
- Motor control integration
- Timeout handling
- Median filtering
- Exception handling and hardware cleanup
- Debugging stateful Jupyter Notebook hardware experiments

## 9. Limitations

The current implementation has several limitations:

- The ultrasonic sensor may produce inconsistent readings.
- The robot has no rear obstacle detection.
- The avoidance strategy always turns right.
- The robot does not build a map of its environment.
- Median filtering may introduce additional response latency.
- Physical avoidance performance requires further validation.

## 10. Next Experiment

**Experiment 06 — Ultrasonic and Infrared Obstacle Avoidance**

The next experiment combines ultrasonic distance measurement with two infrared obstacle sensors.

The objective is to improve obstacle detection and select movement actions using multiple sensor inputs.
