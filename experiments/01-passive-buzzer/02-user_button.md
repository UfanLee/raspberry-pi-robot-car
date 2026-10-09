# Experiment #02 — User Button

**Date:** 2026-10-10  
**Platform:** Raspberry Pi 4  
**Language:** Python  
**Library:** `RPi.GPIO`  
**Input:** User Button  
**GPIO Mode:** `GPIO.BCM`  
**Button Pin:** GPIO19

---

## Objective

The goal of this experiment was to learn how the Raspberry Pi reads a digital input from a physical button.

The experiment focused on:

- Configuring a GPIO pin as an input
- Reading `HIGH` and `LOW` states
- Determining the actual button logic through testing
- Monitoring the button using polling
- Limiting the experiment to a fixed duration
- Cleaning up GPIO resources after execution

---

# Step 1 — Configure the Button Input

GPIO19 was configured as a digital input:

```python
import RPi.GPIO as GPIO

BUTTON_PIN = 19

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(
    BUTTON_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP
)
```

Unlike the previous passive buzzer experiment, which used `GPIO.BOARD`, this experiment uses:

```python
GPIO.setmode(GPIO.BCM)
```

Therefore:

```text
BUTTON_PIN = 19
```

means **BCM GPIO19**, not physical pin 19.

The first test simply read the current GPIO state:

```python
print(GPIO.input(BUTTON_PIN))
```

The initial result was:

```text
0
```

---

# Step 2 — Determine the Actual Button Logic

Instead of assuming the electrical behaviour of the button, its state was measured experimentally.

Without pressing the button:

```python
print("Button state:", GPIO.input(BUTTON_PIN))
```

Result:

```text
Button state: 0
```

The same test was then performed while holding the button down.

Result:

```text
Button state: 1
```

Therefore, the actual behaviour observed on this robot car was:

```text
Button RELEASED → LOW  → 0
Button PRESSED  → HIGH → 1
```

This means the button state can be interpreted as:

```python
if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
    print("Button PRESSED")
else:
    print("Button RELEASED")
```

## Important Observation

The hardware behaviour was verified experimentally rather than assumed from the tutorial code.

This is important when working with embedded systems because the actual hardware configuration should always be tested.

---

# Step 3 — Five-Second Button Polling Test

After confirming the button logic, the next goal was to continuously monitor the button.

Instead of using an infinite:

```python
while True:
```

the experiment was limited to **5 seconds**, making it more suitable for testing inside Jupyter Notebook.

```python
import RPi.GPIO as GPIO
import time

BUTTON_PIN = 19

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(
    BUTTON_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP
)

start_time = time.time()

try:

    while time.time() - start_time < 5:

        state = GPIO.input(BUTTON_PIN)

        if state == GPIO.HIGH:
            print("Button PRESSED")
        else:
            print("Button RELEASED")

        time.sleep(0.2)

finally:

    GPIO.cleanup()
    print("5-second test finished.")
```

During the test, the Raspberry Pi successfully detected the transition between released and pressed states.

Example output:

```text
Button RELEASED
Button RELEASED
Button RELEASED
Button PRESSED
Button PRESSED
Button PRESSED
Button PRESSED
Button RELEASED
Button RELEASED
...
5-second test finished.
```

The experiment therefore successfully demonstrated real-time digital input monitoring.

---

# How Polling Works

The current implementation uses **polling**.

The Raspberry Pi repeatedly checks GPIO19:

```text
Start
  │
  ▼
Read GPIO19
  │
  ├── LOW  → RELEASED
  │
  └── HIGH → PRESSED
  │
  ▼
Wait 0.2 seconds
  │
  └───────────────→ Read GPIO19 again
```

With:

```python
time.sleep(0.2)
```

the button is checked approximately:

```text
1 / 0.2 = 5 times per second
```

During a five-second experiment, approximately:

```text
5 × 5 = 25 readings
```

are performed.

---

# GPIO Resource Management

The experiment uses:

```python
try:
    ...
finally:
    GPIO.cleanup()
```

The `finally` block ensures that GPIO resources are released when the experiment finishes.

This is especially useful in Jupyter Notebook because the Python kernel remains active after a cell has finished executing.

Proper GPIO cleanup reduces the chance of hardware resources from one experiment interfering with later experiments.

---

# Experiment Summary

The development process for this experiment was:

```text
Configure GPIO19
      ↓
Read raw GPIO value
      ↓
Test button released
      ↓
0 (LOW)
      ↓
Test button pressed
      ↓
1 (HIGH)
      ↓
Determine real button behaviour
      ↓
Implement 5-second polling
      ↓
Detect PRESSED / RELEASED
      ↓
GPIO cleanup
```

## What I Learned

This experiment introduced several important embedded-system concepts:

- Digital GPIO input
- `GPIO.BCM` pin numbering
- `GPIO.HIGH` and `GPIO.LOW`
- Pull-up configuration
- Physical button state detection
- Hardware verification through experimentation
- Polling
- Timing using `time.time()`
- Sampling intervals using `time.sleep()`
- `try/finally`
- GPIO resource cleanup

Most importantly, this experiment moved the robot car from only producing an **output** to receiving a physical **input** from the real world.

```text
Experiment #01

Raspberry Pi
     │
     ▼
   Buzzer

OUTPUT


Experiment #02

   Button
     │
     ▼
Raspberry Pi

INPUT
```

This is an important step toward an interactive robot system.

---

# Next Step

The current implementation checks the button every `0.2` seconds using polling.

The next stage will investigate:

**Button Debouncing**

and then:

**GPIO Event Detection + Callback**

Instead of continuously asking:

```text
"Is the button pressed?"
"Is the button pressed?"
"Is the button pressed?"
```

the goal is to eventually allow the program to respond automatically when a button event occurs.

This will make the button suitable for controlling future robot functions such as:

```text
Start robot
Stop robot
Change mode
Trigger autonomous driving
Emergency stop
```

---

## Status

**Experiment #02 — Basic User Button Input: SUCCESS**