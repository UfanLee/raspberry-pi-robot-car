"""LightNav-0 client for the Task 9 Raspberry Pi chassis."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import ExitStack
import io
import json
import math
from pathlib import Path
import signal
import sys
import threading
import time

from websockets.sync.client import connect


RESPONSE_TIMEOUT = 3.0
PULSE_SECONDS = 0.12
STOP_DISTANCE_CM = 15
VISUAL_COMMAND_LEASE = 2.0


def exchange(ws, action, data):
    ws.send(json.dumps({"action": action, "data": data}))
    reply = json.loads(ws.recv(timeout=RESPONSE_TIMEOUT))
    if not isinstance(reply, dict) or reply.get("action") != action:
        raise ValueError("Unexpected LightNav response")
    result = reply.get("data")
    if not isinstance(result, dict) or type(result.get("rc")) is not int or result["rc"] != 0:
        raise ValueError("LightNav rejected " + action)
    return result


def first_waypoint(result, seq):
    if type(result.get("seq")) is not int or result["seq"] != seq:
        raise ValueError("LightNav sequence mismatch")
    if result.get("stop") is True:
        return None
    if result.get("stop") is not False:
        raise ValueError("Missing LightNav stop flag")
    chunk = result.get("actions")
    rows = chunk.get("actions") if isinstance(chunk, dict) else None
    waypoint = rows[0] if isinstance(rows, list) and rows else None
    if not isinstance(waypoint, list) or len(waypoint) != 3 or any(
        type(value) not in (int, float) or not math.isfinite(value)
        for value in waypoint
    ):
        raise ValueError("Invalid first waypoint")
    return waypoint


def wheel_command(waypoint, rolling=False):
    forward, left, yaw = waypoint
    # No lateral or reverse drive. Rotate first, then replan from a new image.
    bearing = math.atan2(left, forward) if math.hypot(forward, left) >= 0.04 else 0.0
    turn = bearing if abs(bearing) >= 0.20 else yaw
    if rolling and forward >= 0.04:
        if turn >= 0.20:
            return (0, 1)
        if turn <= -0.20:
            return (1, 0)
        return (1, 1)
    if abs(turn) >= 0.20 or (forward < 0.04 and abs(turn) >= 0.12):
        return (-1, 1) if turn > 0 else (1, -1)
    return (1, 1) if forward >= 0.04 else (0, 0)


def check_clear(chassis):
    distance = chassis.sonar_read()
    for _ in range(2):
        if distance is not None:
            break
        time.sleep(0.09)
        distance = chassis.sonar_read()
    if distance is None or distance <= STOP_DISTANCE_CM:
        raise RuntimeError("Stop: blocked or invalid sonar reading (%s cm)" % distance)


def set_wheels(chassis, wheels):
    for indices, value in zip((chassis.LEFT_MOTORS, chassis.RIGHT_MOTORS), wheels):
        for index in indices:
            chassis.one_motor(index, value)


def drive_pulse(chassis, wheels, deadline):
    check_clear(chassis)
    if time.monotonic() + PULSE_SECONDS >= deadline:
        return
    if wheels == (0, 0):
        return
    pulse_end = time.monotonic() + PULSE_SECONDS
    try:
        set_wheels(chassis, wheels)
        time.sleep(max(0, pulse_end - time.monotonic()))
    finally:
        chassis.motor_stop()


def capture_frame(camera):
    with io.BytesIO() as stream:
        camera.capture(stream, format="jpeg", use_video_port=True)
        return stream.getvalue()


class LatestFrame:
    """Capture JPEGs continuously and retain only the newest complete frame."""

    def __init__(self, camera):
        self.camera = camera
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.frame = None
        self.error = None
        self.thread = threading.Thread(target=self.capture, daemon=True)
        self.thread.start()

    def capture(self):
        try:
            with io.BytesIO() as stream:
                for _ in self.camera.capture_continuous(stream, format="jpeg", use_video_port=True):
                    if self.stop.is_set():
                        return
                    self.frame = (stream.getvalue(), time.monotonic())
                    self.ready.set()
                    stream.seek(0)
                    stream.truncate()
        except Exception as exc:
            self.error = exc
        finally:
            self.ready.set()

    def latest(self):
        self.ready.wait(timeout=1.0)
        if self.error is not None:
            raise RuntimeError("Continuous camera capture failed") from self.error
        frame = self.frame
        if frame is None or time.monotonic() - frame[1] > 0.75:
            raise RuntimeError("Continuous camera capture stopped producing frames")
        return frame

    def close(self):
        self.stop.set()
        self.thread.join(timeout=1.0)


def forward_lookahead(result, first, wheels):
    """Use a few compatible cumulative points without driving through a turn."""
    distance = first[0]
    if distance < 0.10:
        return distance
    for waypoint in result["actions"]["actions"][1:3]:
        if not isinstance(waypoint, list) or len(waypoint) != 3 or any(
            type(value) not in (int, float) or not math.isfinite(value) for value in waypoint
        ):
            break
        if waypoint[0] <= distance or wheel_command(waypoint, rolling=True) != wheels:
            break
        distance = waypoint[0]
    return distance


def request_waypoint(ws, camera, jpeg_path, seq, instruction, frames=None):
    if frames is not None:
        jpeg, captured_at = frames.latest()
    else:
        captured_at = time.monotonic()
        jpeg = jpeg_path.read_bytes() if camera is None else capture_frame(camera)
    result = exchange(ws, "next", {
        "seq": seq,
        "image": base64.b64encode(jpeg).decode("ascii"),
        "instruction": instruction if seq else None,
    })
    return result, jpeg, captured_at


def run(args):
    with ExitStack() as stack:
        events = None
        if args.record:
            args.record.mkdir(parents=True, exist_ok=False)
            events = stack.enter_context((args.record / "events.jsonl").open("w", encoding="utf-8"))
        chassis = camera = frames = None
        if args.jpeg is None:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "09"))
            import task9_4_fpv_pi as chassis

            stack.callback(chassis.motor_stop)
            chassis.motor_stop()
            chassis.camera_update(0, 0, center=True)
            camera = stack.enter_context(chassis.PiCamera())
            camera.resolution = (640, 480)
            camera.framerate = 15
            camera.rotation = chassis.CAMERA_ROTATION
            time.sleep(1)
            if args.smooth:
                frames = LatestFrame(camera)
                stack.callback(frames.close)

        ws = stack.enter_context(connect(args.server, open_timeout=5, close_timeout=1))
        exchange(ws, "login", {"clientId": "pi4-vln"})
        exchange(ws, "reset", {})

        worker = stack.enter_context(ThreadPoolExecutor(max_workers=1)) if args.vision_only else None
        if worker is not None:
            stack.callback(chassis.motor_stop)
        lease_end = 0.0
        motion_started = 0.0
        previous_wheels = (0, 0)
        deadline = time.monotonic() + args.duration if args.duration else math.inf
        for seq in range(args.steps):
            if time.monotonic() >= deadline:
                print("Stopped: time limit reached", flush=True)
                return
            frame_time = time.monotonic()
            request = (ws, camera, args.jpeg, seq, args.instruction, frames)
            if worker is None:
                result, jpeg, captured_at = request_waypoint(*request)
            else:
                pending = worker.submit(request_waypoint, *request)
                try:
                    result, jpeg, captured_at = pending.result(timeout=max(0, lease_end - time.monotonic()))
                except FutureTimeout:
                    chassis.motor_stop()
                    result, jpeg, captured_at = pending.result()
            if events is not None:
                frame_name = "frame-%04d.jpg" % seq
                (args.record / frame_name).write_bytes(jpeg)
                events.write(json.dumps({
                    "seq": seq, "frame": frame_name,
                    "instruction": args.instruction if seq else None,
                    "round_trip_s": time.monotonic() - frame_time,
                    "frame_age_s": time.monotonic() - captured_at,
                    "response": result,
                }) + "\n")
                events.flush()
            if seq == 0:
                if type(result.get("seq")) is not int or result["seq"] != seq:
                    raise ValueError("LightNav sequence mismatch")
                continue
            waypoint = first_waypoint(result, seq)
            visible = result.get("visible")
            searching = args.search and visible is False
            if args.search and type(visible) is not bool:
                raise ValueError("Search requires a model response with a visibility flag")
            age = time.monotonic() - captured_at
            wheels = (0, 0) if waypoint is None else wheel_command(waypoint, rolling=args.vision_only)
            if searching and wheels == (0, 0):
                # The model sometimes asks to stop while the target is out of view.
                # Rotate briefly to show the model a different view.
                wheels = (-1, 1)
            print("seq=%d age=%.3fs visible=%s waypoint=%s wheels=%s stop=%s" %
                  (seq, age, visible, waypoint, wheels, result["stop"]), flush=True)
            if waypoint is None and not searching:
                print("Stopped: model stop", flush=True)
                return
            if args.vision_only:
                if time.monotonic() >= deadline:
                    print("Stopped: time limit reached", flush=True)
                    return
                now = time.monotonic()
                lease = VISUAL_COMMAND_LEASE
                if args.smooth:
                    lease = 0.28
                    if waypoint is not None and min(wheels) >= 0 and any(wheels):
                        distance = forward_lookahead(result, waypoint, wheels)
                        if min(previous_wheels) >= 0 and any(previous_wheels):
                            distance -= args.speed_mps * max(
                                0.0, min(now, lease_end) - max(captured_at, motion_started)
                            )
                        lease = max(0.0, min(VISUAL_COMMAND_LEASE, distance / args.speed_mps))
                    if not any(wheels) or lease < 0.08:
                        wheels = (0, 0)
                        lease = 0.0
                elif args.search:
                    lease = 0.28
                    if waypoint is not None and min(wheels) >= 0:
                        lease = max(0.12, min(0.65, max(0.0, waypoint[0]) * 3.0))
                motion_started = now
                lease_end = min(deadline, now + lease)
                previous_wheels = wheels
                set_wheels(chassis, wheels)
                if events is not None:
                    events.write(json.dumps({
                        "seq": seq, "wheels_commanded": wheels,
                        "motion_budget_s": max(0.0, lease_end - now),
                    }) + "\n")
                    events.flush()
                if args.search and not args.smooth:
                    # Stop before capture so the model sees a sharp view.
                    time.sleep(max(0.0, lease_end - time.monotonic()))
                    chassis.motor_stop()
                    time.sleep(0.15)
                continue
            if args.drive:
                if time.monotonic() + PULSE_SECONDS >= deadline:
                    print("Stopped: time limit reached", flush=True)
                    return
                drive_pulse(chassis, wheels, deadline)

            # Leave time for the chassis to settle and for sonar echoes to decay.
            time.sleep(0.10)
        print("Stopped: step limit reached", flush=True)


def interrupt(_signum, _frame):
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="ws://127.0.0.1:8050")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--duration", type=float, help="Time limit for navigation, in seconds")
    parser.add_argument("--record", type=Path, help="Save the model inputs and responses in a new directory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--jpeg", type=Path, help="Repeat a saved JPEG without Pi hardware")
    mode.add_argument("--drive", action="store_true", help="Enable motor pulses on the Pi")
    mode.add_argument("--vision-only", action="store_true", help="Drive continuously from visual waypoints without sonar")
    parser.add_argument("--search", action="store_true",
                        help="Explore while the LightNav target is out of view")
    parser.add_argument("--smooth", action="store_true",
                        help="Sample a continuous camera stream and overlap motion with inference")
    parser.add_argument("--speed-mps", type=float, default=0.28,
                        help="Estimated chassis speed at FPV PWM, used by --smooth")
    args = parser.parse_args()
    if args.smooth and not args.vision_only:
        parser.error("--smooth requires --vision-only")
    if not math.isfinite(args.speed_mps) or args.speed_mps <= 0:
        parser.error("--speed-mps must be positive and finite")
    if args.search and not args.vision_only:
        parser.error("--search requires --vision-only")
    if args.steps is None:
        args.steps = 120 if args.vision_only else 30
    if args.steps < 2 or not args.instruction.strip():
        parser.error("Specify at least two frames and a nonempty instruction")
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0):
        parser.error("Duration must be positive and finite")
    if args.vision_only and args.duration is None:
        args.duration = 60
    if args.jpeg and not args.jpeg.is_file():
        parser.error("JPEG file does not exist")
    signal.signal(signal.SIGTERM, interrupt)
    try:
        run(args)
    except KeyboardInterrupt:
        print("Stopped by operator", flush=True)
        return 130
    except Exception as exc:
        print("Stopped: %s" % exc, file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
