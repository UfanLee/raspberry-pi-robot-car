# Task 09 — FPV Teleoperation and Xbox Controller Integration

**Project:** Raspberry Pi 4 Robot Car  
**Platform:** Raspberry Pi 4B · LOBOROBOT four-wheel mecanum chassis  
**Software:** Python · Flask · Legacy PiCamera · pygame-ce · HTTP/MJPEG  
**Status:** Tasks 9.1–9.3 demonstrated on the robot; Task 9.4 implementation prepared, full hardware validation pending  
**Development period:** October 2026 · Ongoing

## 1. Project Overview

Task 09 extends the earlier autonomous obstacle-avoidance and visual-tracking experiments into a **first-person-view (FPV) teleoperation platform**. Rather than relying solely on the robot's autonomous navigation logic, the operator can see its onboard camera feed on a Windows PC and drive it remotely over a local Wi-Fi network.

The development sequence is incremental:

| Task | Goal | Evidence / current outcome |
|---|---|---|
| **9.1** | Live camera streaming to Windows browser | **Demonstrated:** the user opened the stream successfully; a 180° image rotation corrected inverted video. |
| **9.2** | FPV with WASD keyboard control | **Demonstrated:** keyboard control worked; a subsequent operator-preferred version moved ultrasonic avoidance from enforced motion blocking to visual warnings. |
| **9.3** | Xbox gamepad teleoperation | **Demonstrated:** the user successfully drove the robot with a connected Xbox controller. |
| **9.4** | RT throttle, LT brake, pan/tilt, B pause and A resume | **Implemented in code:** scripts supplied; complete physical test outcome not yet documented. |

**Scope:** supervised local-network operation on a small experimental robot. This is not a certified autonomous vehicle or a collision-free driving system.

## 2. Existing Hardware and Reused Components

- **Raspberry Pi 4B:** onboard computer and HTTP server.
- **LOBOROBOT mecanum-wheel chassis:** four independently commanded DC motors, controlled through the existing `LOBOROBOT` Python interface.
- **Pi Camera on a pan/tilt mechanism:** video source; pan servo channel 10 and tilt servo channel 9 in the existing program.
- **Forward-facing ultrasonic sensor:** `TRIG = GPIO 20`, `ECHO = GPIO 21`; fixed to the chassis, **not** mechanically coupled to camera pan.
- **Windows computer:** remote display and control station.
- **Xbox controller:** connected to Windows by USB or Bluetooth; no direct connection to the Raspberry Pi is required.
- **Local Wi-Fi:** transports camera images and control commands.

The previous robot experiments provided the motor control routines, sensor integration, and practical knowledge of motor PWM behavior. In particular, PWM values below approximately 30 did not reliably move the robot in earlier ground tests. This is why Task 9.4 still uses a largely discrete motor output rather than claiming calibrated proportional vehicle speed.

## 3. System Architecture

```text
+--------------------------------------------------+
| Windows PC                                       |
|                                                  |
|  Xbox controller --> pygame-ce --> Python client  |
|                        |                         |
|                        | HTTP drive commands     |
|  Browser <-------------+---------------------+   |
|  (live MJPEG video and telemetry)            |   |
+----------------------------------------------|---+
                                               | Local Wi-Fi
+----------------------------------------------|---+
| Raspberry Pi 4B                              v   |
|  Flask HTTP server / session authorization       |
|  +--------------------------------------------+  |
|  | Control state: PAUSED / DRIVING             |  |
|  | Input validation & 0.35 s command watchdog |  |
|  +--------------------------------------------+  |
|      |                  |             |           |
|      v                  v             v           |
|  LOBOROBOT          Camera servos   Ultrasonic     |
|  DC motors          pan / tilt      warnings       |
|      ^                  ^                          |
|      +--------- Pi Camera --> MJPEG --> Browser    |
+--------------------------------------------------+
```

The key architectural decision is to **read the gamepad on Windows** and send normalized control values to the Raspberry Pi. This avoids Raspberry Pi Bluetooth-driver setup and keeps video display separate from the controller process.

## 4. Task 9.1 — Live FPV Video Streaming

### Objective

Make the robot's onboard camera view accessible from a Windows browser over the same local network.

### Environment discovery and compatibility

The installed system was identified as **Raspbian GNU/Linux 11 (Bullseye)**. The terminal contained `libcamera-hello` and `raspistill`, but `libcamera-hello --list-cameras` returned `No cameras available!`. Earlier Jupyter tests had successfully captured video using the **legacy `raspivid` interface**, so the working solution reused `picamera.PiCamera` instead of changing the camera stack.

The first Flask import failed due to a dependency mismatch: system Flask 1.1.2 imported `jinja2.escape`, which was absent from the newer Jinja2 in `/usr/local`. A separate `~/fpv-env` Python virtual environment was used for the FPV application to avoid disrupting the existing Jupyter robotics setup.

### Implementation

- The Pi Camera captures JPEG frames using `capture_continuous(..., format='jpeg', use_video_port=True)`.
- Flask exposes an MJPEG stream via `/video` and a browser page via `/`.
- The server listens on the Raspberry Pi's local network interface, port **5000**.
- `camera.rotation = 180` corrects the upside-down physical camera orientation.

During the experiment, the device's LAN address was **`192.168.4.44`**. This address is environment-specific and may change when reconnecting to Wi-Fi.

### Result

**Passed in practical use:** the Windows browser displayed the live robot camera feed. The orientation issue was resolved using software rotation.

**Not yet measured:** end-to-end latency, dropped-frame rate, sustained frame rate, or multi-client stability. The working MJPEG architecture is an initial implementation, not a low-latency performance benchmark.

## 5. Task 9.2 — FPV Keyboard Teleoperation

### Objective

Control the four-wheel robot through the same FPV interface using the Windows keyboard.

### Implementation

The initial keyboard version mapped directional keys to the existing LOBOROBOT motor commands, and displayed ultrasonic sensor information in the web interface.

| Input | Action |
|---|---|
| `W` | Forward |
| `A` | Turn left |
| `D` | Turn right |
| `S` | Reverse in the later manual-driving variant |
| `Space` | Stop |
| Key released / commands expire | Stop motors |

An early version automatically blocked some movements based on ultrasonic measurements and disabled reversing because the robot had no rear-facing range sensor. Based on hands-on driving feedback, a subsequent **manual-warning mode** changed the ultrasonic function to *operator information*, rather than automatic obstacle-triggered intervention.

### Design trade-off

Manual-warning mode gives the operator more freedom to maneuver but **does not provide collision prevention**. Forward-only ultrasonic readings cannot guarantee clearance at the sides or rear. The operator must maintain direct supervision, and command-timeout stopping remains mandatory.

### Result

**Passed in practical use:** browser-based manual driving worked, and the operator requested a less restrictive manual mode after testing it.

## 6. Task 9.3 — Xbox Gamepad Teleoperation

### Objective

Replace discrete keyboard control with a more natural handheld driving interface while continuing to use the browser for FPV video.

### Software and compatibility

The Xbox controller was paired with the Windows PC. The client used `pygame` APIs to read controller input and `requests` to send HTTP control messages to the Pi.

The Windows environment initially used **Python 3.14**. Installation of the original `pygame` failed while attempting to build a wheel, leaving the `pygame` module unavailable. Installing **`pygame-ce`** supplied the compatible `pygame` import interface and resolved this blocker.

### Controller mapping implemented in Task 9.3

- Left stick vertical: forward/reverse intent.
- Left stick horizontal: steering/rotation intent.
- Diagonal left-stick movement: simultaneous travel and steering mix.
- B button: stop and exit the controller client in this initial version.

The operator confirmed that the Xbox-control test succeeded. However, pressing **B** exited the Windows client, requiring it to be relaunched to resume control. This usability issue motivated Task 9.4.

### Result

**Passed in practical use:** the Xbox controller successfully sent driving input to the Raspberry Pi robot.

**Not yet measured:** controller-to-motor latency or command-drop rate.

## 7. Task 9.4 — Expanded Xbox Controls and Safe Pause/Resume

### Objective

Extend the gamepad interface while separating a temporary **PAUSED** state from exiting the application.

### Proposed / implemented control scheme

| Controller input | Intended behavior |
|---|---|
| **RT** | Forward throttle intent |
| **LT** | Brake / suppress forward drive |
| **Left stick X** | Steering |
| **Right stick X/Y** | Camera pan and tilt |
| **A** | Resume from `PAUSED` after neutral-input checks |
| **B** | Immediately stop motors and enter `PAUSED` without quitting |
| **X** | Center the camera |
| Client exit / loss of control messages | Stop and return to `PAUSED` |

The supplied Raspberry Pi script is `task9_4_fpv_pi.py`, and the Windows client is `task9_4_xbox_windows.py`.

### Neutral-input resume safeguard

The Raspberry Pi starts in `PAUSED`. Pressing A is accepted only when throttle, brake, and steering are released or near neutral. The **server checks these conditions**, instead of relying entirely on the Windows client. This helps avoid sudden movement on unpausing.

### Communication watchdog

The Raspberry Pi checks the age of accepted control messages and stops motors if no recent command arrives for approximately **0.35 seconds**. A communication timeout also clears control ownership and returns the server to `PAUSED`, requiring explicit reconnection and resumption.

This is a software watchdog, **not** a safety-rated emergency stop or a replacement for a physical power disconnect.

### Camera and ultrasonic behavior

- Camera image orientation: **180° rotation**.
- Camera pan software limits: **70°–110°**, starting at **90°**.
- Camera tilt software limits: **5°–25°**, starting at **5°**.
- Maximum servo change per accepted update: **2°**.
- Ultrasonic readings generate forward-distance warnings in the FPV interface; **the warning does not override manual motor commands**.

The servo range is a conservative software starting point and still requires mechanical clearance checks on the real camera bracket.

### Drive behavior and remaining limits

The server currently uses a maximum PWM command of **30**, a normalized deadzone of **0.20**, and simple left/right motor mixing. The effective output is not yet a calibrated continuous speed controller. The Task 9.4 server also intentionally **does not implement reverse movement**, despite reverse being available in earlier keyboard/gamepad experiments.

This is a conscious limitation of the supplied Task 9.4 implementation and must not be described as a completed feature.

### Validation status

The scripts were prepared and syntax-checked, but there is **no documented completed hardware acceptance test** for Task 9.4 yet. The operator still needs to verify: correct trigger and stick axis calibration, A/B state transitions, camera direction, servo clearances, timeout stopping, and motor response under load.

## 8. Engineering Problems Encountered and Solutions

| Problem | Observation | Resolution |
|---|---|---|
| Camera command mismatch | `rpicam-hello` missing on Bullseye | Investigated OS version and camera commands. |
| No cameras in libcamera | `libcamera-hello --list-cameras` found none | Reused the previously working legacy PiCamera stack. |
| Flask / Jinja2 mismatch | `ImportError: cannot import name 'escape'` | Isolated the web application in `~/fpv-env`. |
| LOBOROBOT import failure | Motor driver in `/home/makerobo/code/LOBOROBOT.py` | Added its **parent directory** to `PYTHONPATH`. |
| Video image upside down | Camera view inverted | Configured 180° camera rotation. |
| `pygame` build failure | Windows Python 3.14 build error | Switched to `pygame-ce`. |
| B ended driving session | Could not resume without restarting client | Added separate `PAUSED` and `DRIVING` behavior in Task 9.4. |
| Overrestrictive manual control | Automatic obstacle locks inhibited operator | Introduced warning-only ultrasonic feedback, while retaining communication safety stops. |

## 9. Safety and Testing Protocol

This is a **supervised research platform**. Software safeguards are not guarantees against collision or unintended motor movement.

1. Raise the wheels off the ground before testing new mappings or startup behavior.
2. Check the physical direction of each wheel, especially after changing left/right mixing.
3. Confirm RT/LT neutral positions and test B pause before applying propulsion.
4. Verify A does not resume when throttle or steering is held.
5. Verify client shutdown / network disconnect stops motors promptly.
6. Check pan/tilt motion for cable snagging and mechanical end-stop contact.
7. Conduct initial ground tests in a clear, flat, controlled area with immediate access to motor-power disconnection.
8. Do not expose the development Flask server or access PIN to the public Internet.

The front sensor has no reliable knowledge of rear or lateral obstacles. Sensor warnings must not be mistaken for autonomous collision avoidance.

## 10. Current Outcomes and Lessons Learned

The experimentally confirmed outcomes are: **working browser FPV video, working keyboard remote control, and working Xbox controller remote driving**. These three results demonstrate successful integration across camera capture, network communication, human input, and motor actuation.

Task 9.4 extends the design toward a more usable cockpit-style controller, but its full feature list remains **pending real-world validation**. Its B-to-pause and A-to-resume architecture is a meaningful safety and usability improvement over terminating the client on B.

The main engineering lesson is that system integration often requires reconciling real device constraints: legacy camera software, Python dependency mismatches, module search paths, input-device axes, mechanical servo limits, and communication loss handling. These are as important to robot reliability as the navigation algorithm itself.

## 11. Next Steps

- Complete and document the Task 9.4 physical acceptance checklist, including pause/resume and servo limits.
- Calibrate motor PWM against observed ground speed and explore genuinely proportional low-speed control.
- Measure video latency and control-loop round-trip time; evaluate lower-latency H.264/WebRTC streaming if needed.
- Add a clear on-screen `PAUSED / DRIVING / SIGNAL LOST` status indicator and optionally record run-level telemetry.
- Preserve operator control as a separate mode from autonomous exploration and future shared autonomy.

## 12. Repository Organization

Suggested files under `experiments/09/`:

```text
experiments/
└── 09/
    ├── Task09_FPV_Teleoperation_and_Xbox_Control.md
    ├── task9_3_fpv_gamepad_pi.py
    ├── task9_3_xbox_windows.py
    ├── task9_4_fpv_pi.py
    ├── task9_4_xbox_windows.py
    └── media/
        ├── fpv_browser_screenshot.png      # add when captured
        └── xbox_driving_demo.mp4           # add when recorded
```

The `media/` entries are **recommended placeholders**, not claimed existing experiment artifacts.

## Conclusion

Task 09 establishes a practical FPV teleoperation layer for the Raspberry Pi robot. The robot can stream live video to a Windows browser and receive live keyboard or Xbox gamepad driving commands through Wi-Fi. Initial hands-on tests confirmed the core FPV and control workflow. Task 9.4 further introduces throttle/brake intent, camera pan/tilt, and resumable pause states, with full hardware verification still to be recorded.

This platform provides a reusable basis for later experiments in **human-in-the-loop robotics**, **shared autonomy**, and eventually an **autonomous follow-me camping cargo rover**.
