# Experiment 04 — Infrared Obstacle Avoidance

## Objective

Implement a basic autonomous obstacle avoidance system on a Raspberry Pi 4 robot car using two infrared sensors and four-wheel motor control.

## Hardware

- Raspberry Pi 4
- Four-wheel robot chassis
- Two infrared obstacle detection sensors
- Motor driver board
- Battery power supply

## GPIO Configuration

| Component | BCM GPIO | Purpose |
|---|---|---|
| Left infrared sensor | GPIO12 | Detect left-side obstacles |
| Right infrared sensor | GPIO16 | Detect right-side obstacles |

## Working Principle

The infrared sensors provide digital signals to the Raspberry Pi. Based on the sensor readings, the robot selects a movement command.

For the tested sensor configuration:

- `1` = No obstacle detected
- `0` = Obstacle detected

### Decision Table

| Left | Right | Action |
|---|---|---|
| 1 | 1 | FORWARD |
| 0 | 1 | TURN_RIGHT |
| 1 | 0 | TURN_LEFT |
| 0 | 0 | STOP |

## Implementation

The control system consists of three main components:

1. **Sensor Input:** Read GPIO12 and GPIO16.
2. **Decision Logic:** Convert sensor readings into movement commands.
3. **Motor Control:** Execute the selected command using the `LOBOROBOT` library.

The initial autonomous test used:

- Motor speed: 25
- Action duration: 0.2 seconds
- Total test duration: approximately 10 seconds

A `try/finally` block was used to issue a motor stop command after the test.

## Troubleshooting

### Right Infrared Sensor Always Returned LOW

During the initial experiment, the right sensor continuously returned `0`, even without an obstacle.

The left sensor responded normally.

**Solution:** Adjusted the right sensor's sensitivity potentiometer.

After calibration, both sensors produced the expected digital signals.

### Frequent Movement Switching

The autonomous test showed repeated switching between `FORWARD` and `TURN_RIGHT`.

Potential contributing factors include sensor threshold fluctuations, obstacle positioning, and changes in detection angle during movement.

Future improvements may include signal filtering, debouncing, and state-based motor control.

## Experimental Results

| Test | Result |
|---|---|
| Left sensor input | Passed |
| Right sensor input | Passed after calibration |
| Forward movement | Passed |
| Left turn | Passed |
| Right turn | Passed |
| Dual-obstacle STOP decision | Pending final verification |
| Motor stop response | Pending final verification |
| Timed autonomous control loop | Completed |

The robot successfully demonstrated basic reactive obstacle avoidance during the initial test.

## Key Learnings

- Reading and interpreting infrared sensor signals
- Calibrating infrared detection sensitivity
- Combining GPIO input with motor control
- Implementing conditional movement decisions
- Using bounded execution and cleanup for safer testing
- Understanding the limitations of reactive obstacle avoidance

## Future Improvements

- Implement sensor debouncing
- Reduce unnecessary motor stopping and restarting
- Add a finite-state machine
- Improve obstacle avoidance in narrow environments
- Investigate additional distance sensors for more reliable navigation
