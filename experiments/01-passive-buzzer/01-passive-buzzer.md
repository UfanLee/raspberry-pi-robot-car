# Experiment #01 — Passive Buzzer

**Platform:** Raspberry Pi 4  
**Language:** Python  
**Library:** `RPi.GPIO`  
**Hardware:** Passive Buzzer  
**GPIO Mode:** `GPIO.BOARD`  
**Buzzer Pin:** Physical Pin 11

---

## Objective

The goal of this experiment was to understand how a Raspberry Pi can control a passive buzzer using GPIO and PWM.

The experiment started with a basic buzzer test and was gradually improved into reusable Python functions that can later be integrated into the robot car as a sound notification system.

---

# Step 1 — Basic 0.5 Second Buzzer Test

The first goal was simply to verify that the Raspberry Pi could successfully control the buzzer.

```python
import RPi.GPIO as GPIO
import time

BUZZER = 11

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUZZER, GPIO.OUT)

buzzer = GPIO.PWM(BUZZER, 440)

buzzer.start(50)

time.sleep(0.5)

buzzer.stop()
GPIO.cleanup()
```

### Result

The buzzer successfully produced a sound for approximately **0.5 seconds**.

This confirmed that:

- the buzzer hardware was working;
- Physical Pin 11 was correctly configured;
- Python could control the GPIO output;
- PWM could successfully drive the passive buzzer.

### What I Learned

A passive buzzer requires a changing electrical signal rather than simply remaining HIGH.

```python
GPIO.PWM(BUZZER, 440)
```

creates a PWM signal with a frequency of **440 Hz**.

```python
buzzer.start(50)
```

starts the PWM with a **50% duty cycle**.

The duration of the sound is controlled by:

```python
time.sleep(0.5)
```

Therefore, the basic relationship is:

```text
GPIO Pin
   ↓
PWM Signal
   ↓
Frequency → Pitch
   ↓
Duration → How long the sound plays
```

---

# Step 2 — Three Short Beeps

After confirming that the buzzer worked, the next experiment was to create a simple repeating notification sound.

```python
import RPi.GPIO as GPIO
import time

BUZZER = 11

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUZZER, GPIO.OUT)

buzzer = GPIO.PWM(BUZZER, 440)

for i in range(3):

    buzzer.start(50)
    time.sleep(0.1)

    buzzer.stop()
    time.sleep(0.1)

GPIO.cleanup()
```

The expected pattern was:

```text
BEEP → silence → BEEP → silence → BEEP
```

### Result

The Raspberry Pi successfully generated three short buzzer sounds.

This experiment introduced repetition using:

```python
for i in range(3):
```

Instead of manually writing the same instructions three times, the program can repeat the same hardware operation automatically.

---

# Step 3 — Refactoring into Reusable Functions

The original experimental code worked, but repeatedly starting and stopping PWM is not ideal for a larger robotics project.

The next version therefore keeps PWM active and controls whether the buzzer produces sound using its **duty cycle**.

```python
import RPi.GPIO as GPIO
import time

BUZZER = 11

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUZZER, GPIO.OUT)

buzzer = GPIO.PWM(BUZZER, 440)

# Start PWM silently
buzzer.start(0)
```

A reusable `beep()` function was then created:

```python
def beep(
    times=1,
    frequency=440,
    duration=0.1,
    interval=0.1
):
    """
    Generate one or more buzzer beeps.

    Parameters
    ----------
    times : int
        Number of beeps.

    frequency : int
        Buzzer frequency in Hz.

    duration : float
        Duration of each beep in seconds.

    interval : float
        Silence between beeps in seconds.
    """

    buzzer.ChangeFrequency(frequency)

    for _ in range(times):

        # Sound ON
        buzzer.ChangeDutyCycle(50)
        time.sleep(duration)

        # Sound OFF
        buzzer.ChangeDutyCycle(0)
        time.sleep(interval)
```

Now the previous three-beep experiment can simply be written as:

```python
beep(3)
```

The function can also generate different notification patterns.

### Low-frequency beep

```python
beep(
    times=3,
    frequency=200,
    duration=0.1
)
```

### High-frequency beep

```python
beep(
    times=3,
    frequency=1000,
    duration=0.1
)
```

### Fast warning sound

```python
beep(
    times=5,
    frequency=800,
    duration=0.05,
    interval=0.05
)
```

After the experiment, GPIO resources should be released:

```python
buzzer.stop()
GPIO.cleanup()
```

---

# Refactoring the Original Song Player

The original example stored the notes and beats in separate lists and accessed them using an index.

For example:

```python
for i in range(1, len(song)):
    buzzer.ChangeFrequency(song[i])
    time.sleep(beats[i] * 0.5)
```

Starting the loop at `1` skips the first element because Python lists are zero-indexed.

Instead of manually managing indexes, `zip()` can associate each frequency with its corresponding beat:

```python
def play_song(buzzer, song, beats, beat_duration=0.5):

    if len(song) != len(beats):
        raise ValueError(
            "song and beats must have the same length"
        )

    for frequency, beat in zip(song, beats):

        buzzer.ChangeFrequency(frequency)
        buzzer.ChangeDutyCycle(50)

        time.sleep(beat * beat_duration)

        buzzer.ChangeDutyCycle(0)
```

This version provides several improvements:

- The first note is no longer skipped.
- Manual index handling is removed.
- Song playback becomes reusable.
- Song and beat lengths are validated.
- PWM does not need to be repeatedly created.
- The code is easier to integrate into a larger robot project.

The original cleanup function was also named:

```python
def destory():
```

This was replaced with the clearer:

```python
def cleanup(buzzer):

    buzzer.stop()
    GPIO.cleanup()
```

The use of a global PWM object can also be avoided by returning the object from the setup function:

```python
def setup():

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BUZZER, GPIO.OUT)

    buzzer = GPIO.PWM(BUZZER, 440)
    buzzer.start(0)

    return buzzer
```

Then:

```python
buzzer = setup()
```

---

# Experiment Summary

This experiment started as a simple hardware verification:

```text
Raspberry Pi
     ↓
GPIO
     ↓
PWM
     ↓
Passive Buzzer
```

and gradually evolved into a reusable software component:

```text
Raw GPIO control
       ↓
0.5 second buzzer test
       ↓
Repeated beep pattern
       ↓
PWM duty-cycle control
       ↓
beep()
       ↓
play_song()
       ↓
Reusable Robot Sound Module
```

The most important concepts learned in this experiment were:

- GPIO pin configuration
- `GPIO.BOARD` numbering
- PWM
- Frequency
- Duty cycle
- Timing with `time.sleep()`
- Python loops
- Functions
- Default function parameters
- `zip()`
- Basic input validation
- Hardware resource cleanup
- Code abstraction and reuse

The project has therefore moved from simply reproducing a Raspberry Pi tutorial to restructuring the code into components that can later become part of the robot car's software architecture.

## Next

The buzzer module can later be used to represent different robot states such as:

```text
Startup
Success
Warning
Error
Obstacle detected
Mission complete
```

The next stage of the project will continue integrating Raspberry Pi hardware into reusable robot modules.