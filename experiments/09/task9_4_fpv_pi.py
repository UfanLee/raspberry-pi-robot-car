"""Task 9.4: Raspberry Pi server for supervised FPV Xbox driving.

Legacy PiCamera / Bullseye; Flask from ~/fpv-env; LOBOROBOT via PYTHONPATH.
Keep robot wheels raised during initial commissioning.
"""
import io
import math
import secrets
import threading
import time

import RPi.GPIO as GPIO
from flask import Flask, Response, jsonify, request
from picamera import PiCamera
from LOBOROBOT import LOBOROBOT

HOST, PORT = '0.0.0.0', 5000
TRIG, ECHO = 20, 21
LEFT_MOTORS, RIGHT_MOTORS = (0, 2), (1, 3)
CAMERA_ROTATION = 180
COMMAND_TIMEOUT = 0.35
MAX_PWM = 30
MOTOR_DEADZONE = 0.20
PAN_HOME, TILT_HOME = 90, 5
# Conservative *starting* servo travel limits; verify hardware clearance manually.
PAN_MIN, PAN_MAX = 70, 110
TILT_MIN, TILT_MAX = 5, 25
SERVO_MAX_STEP_DEG = 2  # maximum one update per accepted control tick

app = Flask(__name__)
robot = LOBOROBOT()
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ECHO, GPIO.IN)
access_pin = secrets.token_hex(3)
lock = threading.RLock()
video_lock = threading.Lock()
camera = None

controller_session = None
last_seq = -1
last_message_time = time.monotonic()
paused = True                    # Starting/reconnecting always requires explicit A
reason = 'START_PAUSED'
motor_state = [(None, 0)] * 4
pan_angle, tilt_angle = PAN_HOME, TILT_HOME
distance_cm, sensor_time = None, 0.0


def motor_stop():
    global motor_state
    for i in range(4):
        robot.MotorStop(i)
    motor_state = [(None, 0)] * 4


def one_motor(index, value):
    global motor_state
    if abs(value) < MOTOR_DEADZONE:
        target = (None, 0)
    else:
        direction = 'forward' if value > 0 else 'backward'
        # Chassis was verified near PWM 30; do not assume lower commands move it.
        target = (direction, MAX_PWM)
    previous = motor_state[index]
    if previous == target:
        return
    if previous[0] is not None:
        robot.MotorStop(index)
    if target[0] is not None:
        robot.MotorRun(index, target[0], target[1])
    motor_state[index] = target


def sonar_read(timeout=0.03):
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(.002)
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(.00001)
    GPIO.output(TRIG, GPIO.LOW)
    start = time.monotonic()
    while GPIO.input(ECHO) == GPIO.LOW:
        if time.monotonic() - start >= timeout:
            return None
    pulse_start = time.monotonic()
    while GPIO.input(ECHO) == GPIO.HIGH:
        if time.monotonic() - pulse_start >= timeout:
            return None
    d = (time.monotonic() - pulse_start) * 34300 / 2
    return round(d, 1) if 2 <= d <= 400 else None


def sonar_worker():
    global distance_cm, sensor_time
    while True:
        try:
            d = sonar_read()
        except Exception as exc:
            print('Sonar:', repr(exc), flush=True)
            d = None
        with lock:
            distance_cm = d
            sensor_time = time.monotonic()
        time.sleep(.09)


def watchdog_worker():
    global controller_session, paused, reason
    while True:
        time.sleep(.04)
        with lock:
            if controller_session is not None and time.monotonic() - last_message_time > COMMAND_TIMEOUT:
                motor_stop()
                paused = True
                controller_session = None
                reason = 'SIGNAL_LOST_PAUSED'


def check_pin(pin):
    return isinstance(pin, str) and secrets.compare_digest(pin, access_pin)


def info():
    d = distance_cm if time.monotonic() - sensor_time < .6 else None
    if d is None:
        warning = '超声波读数不可用：需目视驾驶'
    elif d < 30:
        warning = '前方极近！'
    elif d < 50:
        warning = '前方障碍物较近'
    else:
        warning = '前方暂无距离警告（侧后方未知）'
    return dict(paused=paused, reason=reason,
                gamepad_active=controller_session is not None,
                distance_cm=d, warning=warning, pan=pan_angle, tilt=tilt_angle)


def authenticate(data):
    global controller_session, last_seq, last_message_time
    if not check_pin(data.get('pin')):
        return 'wrong PIN', 403
    session = data.get('session')
    if not isinstance(session, str) or not (8 <= len(session) <= 64):
        return 'invalid session', 400
    if controller_session is not None and controller_session != session:
        return 'controller in use', 409
    if controller_session is None:
        controller_session = session
        last_seq = -1
        # paused is deliberately NOT reset here: timeout makes it True.
    last_message_time = time.monotonic()
    return None


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) and -1 <= value <= 1 else None


def camera_update(x, y, center=False):
    global pan_angle, tilt_angle
    if center:
        pan_angle, tilt_angle = PAN_HOME, TILT_HOME
    else:
        pan_angle = max(PAN_MIN, min(PAN_MAX, pan_angle + int(round(x * SERVO_MAX_STEP_DEG))))
        tilt_angle = max(TILT_MIN, min(TILT_MAX, tilt_angle - int(round(y * SERVO_MAX_STEP_DEG))))
    robot.set_servo_angle(10, pan_angle)
    robot.set_servo_angle(9, tilt_angle)


@app.route('/')
def home():
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Task 9.4 Xbox FPV</title>
<style>body{background:#111827;color:#f9fafb;font:16px Arial;text-align:center;margin:16px}
main{max-width:850px;margin:auto}img{width:100%;max-width:820px;border-radius:12px;background:#000}
input,button{font-size:16px;padding:10px;border-radius:7px}button{background:#0d9488;border:0;color:white}
#warning{color:#fbbf24;font-weight:bold;margin:12px}</style></head><body><main>
<h2>Task 9.4 — Xbox FPV</h2>
<input type="password" id="pin" placeholder="控制码"><button onclick="connect()">查看图传</button>
<p><img id="feed" alt="Camera feed"></p><p id="state">未连接</p><p id="warning">超声波仅提示，不自动刹车</p>
<p>RT 油门 · LT 刹车 · 左摇杆转向 · 右摇杆云台 · B 暂停 · 摇杆/油门归零后 A 恢复 · X 云台回中</p>
<p style="color:#9ca3af">本页只显示图传；Windows Xbox 客户端驱动。仅限可信局域网，人在车旁可断电。</p>
<script>let pin='';async function connect(){let p=document.getElementById('pin').value.trim();let r=await fetch('/status?pin='+encodeURIComponent(p));
if(!r.ok){document.getElementById('state').textContent='控制码错误';return}pin=p;
document.getElementById('feed').src='/video?pin='+encodeURIComponent(pin);}
setInterval(async()=>{if(!pin)return;try{let r=await fetch('/status?pin='+encodeURIComponent(pin));
if(!r.ok)return;let s=await r.json();document.getElementById('state').textContent=(s.paused?'PAUSED · 已停车':'DRIVING')+
' | 手柄 '+(s.gamepad_active?'在线':'离线')+' | '+s.reason+' | 云台 '+s.pan+'°/'+s.tilt+'°';
document.getElementById('warning').textContent=(s.distance_cm===null?'距离未知':s.distance_cm+' cm')+' | '+s.warning;
document.getElementById('warning').style.color=(s.distance_cm!==null && s.distance_cm<50)?'#f87171':'#fbbf24';}catch(e){}},350);
</script></main></body></html>'''


@app.route('/status')
def status():
    if not check_pin(request.args.get('pin')):
        return jsonify(error='wrong PIN'), 403
    with lock:
        return jsonify(info())


@app.route('/drive', methods=['POST'])
def drive():
    global last_seq, reason
    data = request.get_json(silent=True) or {}
    # Validate all values before acquiring / refreshing the control session.
    seq = data.get('seq')
    values = [number(data.get(k)) for k in ('throttle', 'brake', 'steering', 'cam_x', 'cam_y')]
    if not isinstance(seq, int) or isinstance(seq, bool) or any(v is None for v in values):
        return jsonify(error='invalid drive data'), 400
    throttle, brake, steering, cam_x, cam_y = values
    if throttle < 0 or brake < 0:
        return jsonify(error='throttle/brake must be 0..1'), 400
    with lock:
        error = authenticate(data)
        if error:
            return jsonify(error=error[0]), error[1]
        if seq <= last_seq:
            return jsonify(info())
        last_seq = seq
        if not paused:
            # Brake overrides throttle; forward only for first supervised version.
            movement = throttle * (1 - brake)
            if brake >= .1:
                movement = 0.
            # Steering only moves chassis when accelerator pressed.
            steering *= movement
            left, right = movement + steering, movement - steering
            norm = max(1., abs(left), abs(right))
            for index in LEFT_MOTORS:
                one_motor(index, left / norm)
            for index in RIGHT_MOTORS:
                one_motor(index, right / norm)
            reason = 'DRIVING' if movement >= MOTOR_DEADZONE else 'NEUTRAL'
        else:
            motor_stop()
            reason = 'PAUSED'
        # Camera is usable in PAUSED too; deliberately bounded in software.
        if bool(data.get('center_camera')):
            camera_update(0, 0, center=True)
        elif abs(cam_x) > .20 or abs(cam_y) > .20:
            camera_update(cam_x, cam_y)
        return jsonify(info())


@app.route('/pause', methods=['POST'])
def pause():
    global paused, reason
    data = request.get_json(silent=True) or {}
    with lock:
        error = authenticate(data)
        if error:
            return jsonify(error=error[0]), error[1]
        motor_stop()
        paused = True
        reason = 'B_PAUSED'
        return jsonify(info())


@app.route('/resume', methods=['POST'])
def resume():
    global paused, reason
    data = request.get_json(silent=True) or {}
    with lock:
        error = authenticate(data)
        if error:
            return jsonify(error=error[0]), error[1]
        # Server must also enforce neutral before resuming, not only Windows.
        throttle = number(data.get('throttle'))
        brake = number(data.get('brake'))
        steering = number(data.get('steering'))
        if throttle is None or brake is None or steering is None:
            return jsonify(error='invalid neutral inputs'), 400
        if throttle > .08 or abs(steering) > .12 or brake > .10:
            return jsonify(error='release throttle, brake and steering before A'), 409
        motor_stop()
        paused = False
        reason = 'A_RESUMED'
        return jsonify(info())


@app.route('/stop', methods=['POST'])
def stop():
    global paused, reason, controller_session
    data = request.get_json(silent=True) or {}
    with lock:
        if not check_pin(data.get('pin')):
            return jsonify(error='wrong PIN'), 403
        if controller_session is not None and controller_session != data.get('session'):
            return jsonify(error='not owner'), 409
        motor_stop()
        paused = True
        controller_session = None
        reason = 'CLIENT_STOPPED'
        return jsonify(info())


def frames():
    if not video_lock.acquire(blocking=False):
        return
    stream = io.BytesIO()
    try:
        for _ in camera.capture_continuous(stream, format='jpeg', use_video_port=True):
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + stream.getvalue() + b'\r\n'
            stream.seek(0)
            stream.truncate()
    finally:
        video_lock.release()


@app.route('/video')
def video():
    if not check_pin(request.args.get('pin')):
        return 'Access denied', 403
    return Response(frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    try:
        motor_stop()
        camera_update(0, 0, center=True)
        camera = PiCamera()
        camera.resolution = (640, 480)
        camera.framerate = 15
        camera.rotation = CAMERA_ROTATION
        threading.Thread(target=sonar_worker, daemon=True).start()
        threading.Thread(target=watchdog_worker, daemon=True).start()
        print('Task 9.4 Xbox FPV | CONTROL CODE:', access_pin, flush=True)
        print('Open http://192.168.4.44:5000', flush=True)
        print('Initially PAUSED. Press A only after releasing all inputs.', flush=True)
        app.run(host=HOST, port=PORT, threaded=True, debug=False)
    finally:
        motor_stop()
        if camera is not None:
            camera.close()
