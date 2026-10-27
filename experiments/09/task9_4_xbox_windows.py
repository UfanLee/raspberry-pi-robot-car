"""Task 9.4 Windows Xbox controller; run with Python 3.14 + pygame-ce + requests.

First launch: guided axis calibration saved next to this script.
Vehicle boots PAUSED; press A with triggers/relevant stick neutral to drive.
B pauses without exiting. Ctrl+C stops the client. Trusted LAN only.
"""
import json
import math
import secrets
import time
from pathlib import Path

import pygame
import requests

PI_URL = 'http://192.168.4.44:5000'
SEND_PERIOD = 0.10
HTTP_TIMEOUT = 0.22
DEADZONE = 0.16
CALIBRATION_FILE = Path(__file__).with_name('task9_4_gamepad_calibration.json')


def clamp(v, low=0., high=1.):
    return max(low, min(high, v))


def stick(v):
    if abs(v) < DEADZONE:
        return 0.
    return math.copysign(clamp((abs(v) - DEADZONE) / (1 - DEADZONE)), v)


def samples_for_axis(pad, seconds=2.5):
    count = pad.get_numaxes()
    mins = [float('inf')] * count
    maxs = [float('-inf')] * count
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pygame.event.pump()
        for i in range(count):
            v = pad.get_axis(i)
            mins[i] = min(mins[i], v)
            maxs[i] = max(maxs[i], v)
        time.sleep(.02)
    return mins, maxs


def calibrate(pad):
    print('\n初次校准（车轮必须架空，控制命令尚未发送）。')
    print('按提示只操作一个控件。其他摇杆/扳机保持不动。')
    result = {}
    axes = [
        ('steering', '左摇杆左右移动几次'),
        ('throttle', '反复完整按下并放开 RT（右扳机）'),
        ('brake', '反复完整按下并放开 LT（左扳机）'),
        ('cam_x', '右摇杆左右移动几次'),
        ('cam_y', '右摇杆上下移动几次'),
    ]
    used = set()
    for name, prompt in axes:
        input(f'\n准备 {prompt}，按回车开始采样 2.5 秒...')
        pygame.event.pump()
        baseline = [pad.get_axis(i) for i in range(pad.get_numaxes())]
        print('现在操作！', flush=True)
        low, high = samples_for_axis(pad)
        candidates = sorted(range(len(low)), key=lambda i: high[i] - low[i], reverse=True)
        selected = next((i for i in candidates if i not in used and high[i] - low[i] > .35), None)
        if selected is None:
            raise RuntimeError(f'没有检测到 {name} 的明确轴变化；请重启并重新校准。')
        used.add(selected)
        result[name] = {
            'axis': selected,
            'baseline': round(baseline[selected], 4),
            'min': round(low[selected], 4),
            'max': round(high[selected], 4),
        }
        print(f'记录 {name}: axis {selected}, range=({low[selected]:+.2f}, {high[selected]:+.2f})')
    result['device'] = pad.get_name()
    print('\n校准完成：', result)
    CALIBRATION_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    return result


def raw_axis(pad, calibration, name):
    return pad.get_axis(calibration[name]['axis'])


def normalized_stick(pad, calibration, name, invert=False):
    info = calibration[name]
    raw = raw_axis(pad, calibration, name)
    # Typical centered stick is 0; subtract initial neutral baseline.
    v = clamp(raw - info['baseline'], -1., 1.)
    if invert:
        v = -v
    return stick(v)


def normalized_trigger(pad, calibration, name):
    info = calibration[name]
    raw = raw_axis(pad, calibration, name)
    base = info['baseline']
    amplitude = max(abs(info['max'] - base), abs(info['min'] - base))
    # Assumes trigger is released at calibration baseline.
    if amplitude < .35:
        return 0.
    return clamp(abs(raw - base) / amplitude)


def main():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        raise RuntimeError('没有检测到手柄；请先在 Windows 连接 Xbox 手柄。')
    pad = pygame.joystick.Joystick(0)
    pad.init()
    print('Xbox:', pad.get_name(), '| axes:', pad.get_numaxes(), '| buttons:', pad.get_numbuttons())
    print('注意：Xbox 手柄不同驱动的轴映射不同，首轮必须校准。')
    calibration = None
    if CALIBRATION_FILE.exists():
        candidate = json.loads(CALIBRATION_FILE.read_text(encoding='utf-8'))
        if candidate.get('device') == pad.get_name() and all(
            candidate[k]['axis'] < pad.get_numaxes()
            for k in ('steering', 'throttle', 'brake', 'cam_x', 'cam_y')
        ):
            calibration = candidate
            ans = input('发现以前的轴校准。使用它吗？[Y/n]: ').strip().lower()
            if ans == 'n':
                calibration = None
    if calibration is None:
        calibration = calibrate(pad)

    # B=1 and A=0 are usual Xbox button indices in pygame, but verify.
    A_BUTTON = 0
    B_BUTTON = 1
    X_BUTTON = 2
    print('\n按钮编号默认 A=0, B=1, X=2。若错误，先架空轮子检查。')
    pin = input('输入树莓派服务器显示的 CONTROL CODE: ').strip()
    session = secrets.token_hex(12)
    seq = 0
    net = requests.Session()
    paused = True
    prev_a = prev_b = prev_x = False
    center_requested = False
    last_status = ''

    def request(path, payload, timeout=HTTP_TIMEOUT):
        r = net.post(PI_URL + path, json=dict(pin=pin, session=session, **payload), timeout=timeout)
        r.raise_for_status()
        return r.json()

    try:
        r = net.get(PI_URL + '/status', params={'pin': pin}, timeout=3)
        r.raise_for_status()
        print('\n连接成功。初始 PAUSED；松开 RT/LT 并回中摇杆后按 A 解锁。')
        print('RT 油门、LT 刹车、左摇杆左右转向、右摇杆云台、X 云台回中、B 暂停、A 恢复。')
        while True:
            pygame.event.pump()
            if pygame.joystick.get_count() == 0:
                print('\n手柄断开，退出；车端自动超时暂停。')
                break
            # Recompute every loop; keyboard never shares driving ownership.
            steer = normalized_stick(pad, calibration, 'steering')
            throttle = normalized_trigger(pad, calibration, 'throttle')
            brake = normalized_trigger(pad, calibration, 'brake')
            cam_x = normalized_stick(pad, calibration, 'cam_x')
            cam_y = normalized_stick(pad, calibration, 'cam_y', invert=False)

            a = bool(pad.get_button(A_BUTTON)) if pad.get_numbuttons() > A_BUTTON else False
            b = bool(pad.get_button(B_BUTTON)) if pad.get_numbuttons() > B_BUTTON else False
            x = bool(pad.get_button(X_BUTTON)) if pad.get_numbuttons() > X_BUTTON else False

            if b and not prev_b:
                result = request('/pause', {})
                paused = True
                print('\nB: PAUSED — 电机停止；A 可恢复')
            if a and not prev_a and not b:
                if throttle > .08 or brake > .10 or abs(steer) > .12:
                    print('\n恢复失败：先松开 RT/LT，左摇杆回中，再按 A。')
                else:
                    result = request('/resume', dict(throttle=throttle, brake=brake, steering=steer))
                    paused = bool(result['paused'])
                    print('\nA: ' + ('仍然 PAUSED' if paused else 'DRIVING — 可以驾驶'))
            if x and not prev_x:
                center_requested = True
            prev_a, prev_b, prev_x = a, b, x

            seq += 1
            result = request('/drive', dict(
                seq=seq,
                throttle=0. if paused else throttle,
                brake=brake,
                steering=steer,
                cam_x=cam_x,
                cam_y=cam_y,
                center_camera=center_requested,
            ))
            center_requested = False
            paused = bool(result['paused'])
            state = f"{'PAUSED' if paused else 'DRIVING'} | RT={throttle:.2f} LT={brake:.2f} STEER={steer:+.2f} CAM=({result['pan']},{result['tilt']})"
            if state != last_status:
                print('\r' + state + '     ', end='', flush=True)
                last_status = state
            time.sleep(SEND_PERIOD)
    except KeyboardInterrupt:
        print('\nCtrl+C：退出 Windows 控制端。')
    except requests.RequestException as exc:
        print('\n连接异常:', exc, '\n车端将在 0.35 秒左右进入 PAUSED。')
    finally:
        try:
            request('/stop', {}, timeout=.35)
        except requests.RequestException:
            pass
        net.close()
        pygame.quit()
        print('\n手柄客户端已结束。')


if __name__ == '__main__':
    main()
