"""VinFast driver monitoring demo: webcam -> face landmarks -> driver state -> alert.

    python run_dms.py                 # live webcam
    python run_dms.py --protocol      # live, then the scripted eyes-closed test
    python run_dms.py --source clip.mp4 --headless   # process a recorded video

Keys: q / Esc quit, c recalibrate, p start the protocol.
Every session is logged to logs/ and can be replayed with evaluate.py.
"""
import argparse
import csv
import math
import os
import sys
import threading
import time
import urllib.request
from collections import deque
from datetime import datetime

import cv2
import numpy as np

from dms.evaluation import GT_CLOSED, GT_NONE, LOG_FIELDS, Protocol, read_log, replay, score, timing
from dms.features import LEFT_EYE, RIGHT_EYE, observe
from dms.monitor import (CALIBRATING, DISTRACTED, LEVEL_ALARM, LEVEL_WARN, MICROSLEEP, NO_FACE,
                         PERCLOS_HIGH, UNCERTAIN, YAWNING, Monitor)

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")
MODEL_SIZE = 3758596

ALERT_TEXT = {
    MICROSLEEP: "NGỦ GẬT! Mắt nhắm quá lâu",
    DISTRACTED: "MẤT TẬP TRUNG: không nhìn đường",
    NO_FACE: "KHÔNG THẤY MẶT TÀI XẾ",
    PERCLOS_HIGH: "Dấu hiệu buồn ngủ: PERCLOS cao",
    YAWNING: "Ngáp nhiều lần: nên dừng nghỉ",
}

RED, ORANGE, GREEN, WHITE, GREY, CYAN = (40, 40, 220), (0, 150, 255), (80, 200, 80), (240, 240, 240), (150, 150, 150), (220, 200, 60)


# ---- model ------------------------------------------------------------------
def ensure_model(path):
    """Download the face landmarker, resuming after dropped connections."""
    if os.path.exists(path) and os.path.getsize(path) == MODEL_SIZE:
        return path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    part = path + ".part"
    for attempt in range(10):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have >= MODEL_SIZE:
            break
        try:
            req = urllib.request.Request(MODEL_URL, headers={"Range": f"bytes={have}-"})
            with urllib.request.urlopen(req, timeout=30) as r, open(part, "ab") as f:
                while chunk := r.read(1 << 16):
                    f.write(chunk)
        except OSError as e:
            print(f"download attempt {attempt + 1} failed: {e}", file=sys.stderr)
    if not os.path.exists(part) or os.path.getsize(part) != MODEL_SIZE:
        sys.exit(f"Could not download the model. Fetch it manually from {MODEL_URL} into {path}")
    os.replace(part, path)
    return path


def make_landmarker(model_path):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision
    opts = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp, vision.FaceLandmarker.create_from_options(opts)


# ---- sound ------------------------------------------------------------------
class Beeper:
    def __init__(self, enabled=True):
        try:
            import winsound
            self._beep = winsound.Beep if enabled else None
        except ImportError:
            self._beep = None
        self._busy = False

    def beep(self, freq, ms):
        if self._beep is None or self._busy:
            return
        self._busy = True

        def run():
            try:
                self._beep(freq, ms)
            finally:
                self._busy = False
        threading.Thread(target=run, daemon=True).start()


# ---- drawing ----------------------------------------------------------------
class TextLayer:
    """Unicode text via Pillow (cv2.putText cannot draw Vietnamese diacritics)."""

    def __init__(self):
        self.fonts = {}
        self.items = []
        try:
            from PIL import ImageFont
            self._font_cls = ImageFont
            for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
                try:
                    ImageFont.truetype(name, 16)
                    self.font_name = name
                    break
                except OSError:
                    continue
            else:
                self._font_cls = None
        except ImportError:
            self._font_cls = None

    def add(self, text, xy, size=18, color=WHITE):
        self.items.append((text, xy, size, color))

    def render(self, frame):
        if not self.items:
            return frame
        if self._font_cls is None:
            for text, (x, y), size, color in self.items:
                ascii_text = text.encode("ascii", "replace").decode()
                cv2.putText(frame, ascii_text, (x, y + size), cv2.FONT_HERSHEY_SIMPLEX, size / 32, color, 1, cv2.LINE_AA)
        else:
            from PIL import Image, ImageDraw
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img)
            for text, xy, size, color in self.items:
                if size not in self.fonts:
                    self.fonts[size] = self._font_cls.truetype(self.font_name, size)
                draw.text(xy, text, font=self.fonts[size], fill=color[::-1])
            frame = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        self.items = []
        return frame


def shade(frame, x0, y0, x1, y1, alpha=0.55):
    roi = frame[y0:y1, x0:x1]
    roi[:] = (roi * (1 - alpha)).astype(np.uint8)


def fmt(x, spec=".2f", none="—"):
    return none if x is None or (isinstance(x, float) and math.isnan(x)) else format(x, spec)


def draw(frame, text, rep, pts, history, proto_info, fps, proc_ms):
    h, w = frame.shape[:2]

    # eye contours, red when the monitor considers the eyes closed
    if pts is not None:
        col = RED if rep["closed"] else GREEN
        for idx in (LEFT_EYE, RIGHT_EYE):
            poly = np.array([pts[i] for i in idx], dtype=np.int32)
            cv2.polylines(frame, [poly], True, col, 1, cv2.LINE_AA)

    # status panel
    shade(frame, 0, 0, 270, 196)
    state = rep["state"]
    state_col = {CALIBRATING: CYAN, UNCERTAIN: ORANGE}.get(state, GREEN)
    text.add(f"Trạng thái: {state}", (10, 6), 18, state_col)
    text.add(f"EAR {fmt(rep['ear'], '.3f')}  ngưỡng {fmt(rep['close_thr'], '.3f')}", (10, 32), 16)
    cov = rep["perclos_coverage"]
    text.add(f"PERCLOS {fmt(rep['perclos'] * 100 if rep['perclos'] == rep['perclos'] else math.nan, '.0f')}%"
             f"  (phủ {fmt(cov * 100, '.0f')}% cửa sổ)", (10, 54), 16)
    text.add(f"Chớp mắt/phút {rep['blinks_per_min']}   Ngáp {rep['yawns']}", (10, 76), 16)
    text.add(f"Đầu: yaw {fmt(rep['dyaw'], '+.0f')}°  pitch {fmt(rep['dpitch'], '+.0f')}°", (10, 98), 16)
    text.add(f"{fmt(fps, '.0f')} FPS   xử lý {fmt(proc_ms, '.0f')} ms/khung", (10, 120), 16, GREY)
    text.add("q thoát · c hiệu chuẩn · p kịch bản đo", (10, 168), 14, GREY)

    if state == CALIBRATING:
        left = rep["calib_left"]
        msg = "Hiệu chuẩn: nhìn thẳng, mở mắt bình thường"
        msg += f" ({fmt(max(left, 0), '.1f')} s)" if left == left else " (chưa thấy mặt)"
        shade(frame, 0, h // 2 - 24, w, h // 2 + 24)
        text.add(msg, (20, h // 2 - 14), 22, CYAN)

    # alert banner
    if rep["level"] >= LEVEL_WARN:
        col = RED if rep["level"] == LEVEL_ALARM else ORANGE
        cv2.rectangle(frame, (280, 0), (w, 48), col, -1)
        msg = " · ".join(ALERT_TEXT[a] for a in rep["alerts"])
        text.add(msg, (292, 10), 22, WHITE)
        if rep["level"] == LEVEL_ALARM:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), col, 6)

    # protocol cue
    if proto_info:
        cue, sub = proto_info
        shade(frame, w - 300, 56, w, 120)
        text.add(cue, (w - 290, 60), 26, RED if "NHẮM" in cue else WHITE)
        text.add(sub, (w - 290, 94), 14, GREY)

    # EAR over the last 10 s, with thresholds and ground-truth windows
    gh, gy = 90, h - 90
    shade(frame, 0, gy, w, h)
    if history and rep["close_thr"] == rep["close_thr"]:
        t_now = history[-1][0]
        top = max(0.45, rep["open_thr"] * 1.6)

        def xy(t, v):
            return int(w * (1 - (t_now - t) / 10.0)), int(gy + gh - 6 - (gh - 12) * min(v, top) / top)
        for t, _, gt in history:
            if gt == GT_CLOSED:
                x = xy(t, 0)[0]
                cv2.line(frame, (x, gy), (x, h), (60, 60, 120), 2)
        for thr, col in ((rep["close_thr"], RED), (rep["open_thr"], ORANGE)):
            y = xy(t_now, thr)[1]
            cv2.line(frame, (0, y), (w, y), col, 1)
        line = np.array([xy(t, e) for t, e, _ in history if e == e], dtype=np.int32)
        if len(line) > 1:
            cv2.polylines(frame, [line], False, GREEN, 2, cv2.LINE_AA)
        text.add("EAR 10 s (đỏ: ngưỡng nhắm, cam: ngưỡng mở)", (8, gy + 2), 13, GREY)
    return text.render(frame)


def open_source(source, is_cam, width=640, height=480):
    if not is_cam:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            sys.exit(f"Cannot open video {source!r}")
        return cap
    backends = ([cv2.CAP_DSHOW] if sys.platform == "win32" else []) + [cv2.CAP_ANY]
    for be in backends:
        cap = cv2.VideoCapture(int(source), be)
        if cap.isOpened():
            # Nếu muốn chỉnh độ phân giải thì PHẢI chỉnh TRƯỚC khi gọi cap.read() lần đầu
            # Hoặc tốt nhất để mặc định của webcam rồi dùng cv2.resize sau
            ok, _ = cap.read()
            if ok:
                return cap
        cap.release()
    sys.exit(
        f"Cannot open camera {source}. Check that:\n"
        "  - the webcam is connected and enabled (laptop camera key / privacy shutter, Device Manager)\n"
        "  - no other app (Zoom, Teams, Camera) is using it\n"
        "  - another index works: python run_dms.py --source 1\n"
        "Or run on a recorded clip: python run_dms.py --source clip.mp4")


# ---- main loop ----------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default="0", help="camera index or video file")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--height", type=int, default=540)
    ap.add_argument("--model", default=os.path.join("models", "face_landmarker.task"))
    ap.add_argument("--log-dir", default="logs")
    ap.add_argument("--protocol", action="store_true", help="start the scripted test after calibration")
    ap.add_argument("--trials", type=int, default=8)
    ap.add_argument("--no-mirror", action="store_true")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--headless", action="store_true", help="no window (for video files)")
    ap.add_argument("--max-seconds", type=float, default=0, help="stop after this long (0 = no limit)")
    args = ap.parse_args()

    mp, landmarker = make_landmarker(ensure_model(args.model))
    is_cam = args.source.isdigit()
    cap = open_source(args.source, is_cam)
    # XÓA HOẶC COMMENT 3 DÒNG cap.set NÀY ĐI VÌ NÓ LÀM HỎNG BUFFER CỦA DIRECTSHOW:
    # if is_cam:
    #     cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    #     cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    os.makedirs(args.log_dir, exist_ok=True)
    log_path = os.path.join(args.log_dir, datetime.now().strftime("session-%Y%m%d-%H%M%S.csv"))
    log_file = open(log_path, "w", newline="", encoding="utf-8")
    log = csv.writer(log_file)
    log.writerow(LOG_FIELDS)

    monitor = Monitor()
    beeper = Beeper(enabled=not args.no_sound)
    text = TextLayer()
    history = deque()
    protocol, proto_start, want_protocol = None, None, args.protocol
    last_gt, last_alarm_beep = GT_NONE, 0.0
    frame_times = deque(maxlen=30)
    recalib = False
    t0, frame_idx, last_ts = time.perf_counter(), 0, -1

    try:
        while True:
            ok, frame = cap.read()
            t_cap = time.perf_counter()
            if not ok:
                break
            if is_cam:
                frame = cv2.resize(frame, (args.width, args.height)) # Resize bằng phần mềm an toàn 100%
            if is_cam and not args.no_mirror:
                frame = cv2.flip(frame, 1)
            t = (t_cap - t0) if is_cam else frame_idx / video_fps
            frame_idx += 1
            if args.max_seconds and t > args.max_seconds:
                break

            h, w = frame.shape[:2]
            ts = max(int(t * 1000), last_ts + 1)  # landmarker wants strictly increasing ms
            last_ts = ts
            result = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), ts)
            obs, pts = (observe(result.face_landmarks[0], w, h) if result.face_landmarks else (None, None))

            if recalib:
                monitor.reset()
            rep = monitor.update(t, obs)

            # protocol starts once calibration is done
            if want_protocol and monitor.calibrated and protocol is None:
                protocol, proto_start = Protocol(trials=args.trials), t
            gt, proto_info = GT_NONE, None
            if protocol is not None:
                el = t - proto_start
                gt = protocol.gt_at(el)
                if gt == GT_NONE:
                    print("Protocol finished.")
                    protocol, want_protocol = None, False
                else:
                    done = sum(1 for s, _, g in protocol.segments if g == GT_CLOSED and s < el)
                    proto_info = (("NHẮM MẮT", f"đến tiếng bíp trầm · lần {done}/{protocol.trials}")
                                  if gt == GT_CLOSED else
                                  ("Mở mắt, nhìn đường", f"chớp mắt bình thường · xong {done}/{protocol.trials}"))
                    if gt != last_gt:
                        beeper.beep(1500 if gt == GT_CLOSED else 600, 150)
            last_gt = gt

            if rep["level"] == LEVEL_ALARM and t - last_alarm_beep > 0.6 and gt == GT_NONE:
                beeper.beep(1000, 200)
                last_alarm_beep = t

            proc_ms = (time.perf_counter() - t_cap) * 1000
            frame_times.append(t)
            fps = (len(frame_times) - 1) / (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 and frame_times[-1] > frame_times[0] else math.nan

            log.writerow([f"{t:.4f}", int(obs is not None),
                          *(f"{v:.5f}" for v in ((obs.ear, obs.ear_l, obs.ear_r, obs.mar, obs.yaw, obs.pitch)
                                                if obs else (math.nan,) * 6)),
                          f"{proc_ms:.2f}", gt, int(recalib), rep["level"], "|".join(rep["alerts"])])
            recalib = False

            history.append((t, rep["ear"], gt))
            while history and history[0][0] < t - 10:
                history.popleft()

            if not args.headless:
                frame = draw(frame, text, rep, pts, history, proto_info, fps, proc_ms)
                cv2.imshow("VinFast DMS demo", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("c"):
                    recalib = True
                if key == ord("p") and protocol is None:
                    want_protocol = True
    finally:
        cap.release()
        log_file.close()
        landmarker.close()
        cv2.destroyAllWindows()

    print(f"Log: {log_path}")
    rows = read_log(log_path)
    if rows:
        tm = timing(rows)
        print(f"{tm['fps']:.1f} FPS, processing p50 {tm['proc_ms_p50']:.1f} ms / p95 {tm['proc_ms_p95']:.1f} ms, "
              f"face found in {tm['face_found']:.0%} of frames")
        mon, reps = replay(rows)
        s = score(rows, mon, reps)
        if s:
            print(f"Protocol: {s['hits']}/{s['trials']} closures alarmed, "
                  f"{s['false_alarms']} false alarms, mean latency {s['latency_mean_s']:.2f} s. "
                  f"Run: python evaluate.py {log_path}")


if __name__ == "__main__":
    main()
