"""
VIN PERCEPTION HACKATHON — AI PERCEPTION & 3D SIMULATOR BRIDGE
Tích hợp Module Perception (Member 1) với 3D Trash Bin Simulator (Leader huy20)

Luồng hoạt động:
1. Đọc webcam / camera theo thời gian thực (hoặc video backup).
2. Chạy WasteDetector (YOLOv8) nhận diện: Plastic, Metal, Paper, Organic.
3. Vẽ Bounding Box, nhãn vật liệu, độ tự tin lên khung hình.
4. Stream MJPEG về trình duyệt qua route '/video_feed'.
5. Bắn tín hiệu Server-Sent Events (SSE) qua route '/api/events' để tự động mở nắp 3D tương ứng trong simulator.html!
"""

import cv2
import time
import json
import os
import sys
import threading
from typing import Generator
from flask import Flask, Response, send_file, jsonify

# Đảm bảo import được module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.detector import WasteDetector

app = Flask(__name__)

# Khởi tạo detector của Member 1
detector = WasteDetector(conf_thresh=0.35)

# Trạng thái chia sẻ giữa luồng Camera và luồng SSE
class PerceptionState:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_frame = None
        self.latest_annotated = None
        self.latest_detection = None
        self.event_queue = []
        self.fps = 0.0
        self.latency_ms = 0.0

state = PerceptionState()

# Ánh xạ từ nhãn detector sang key của Simulator (plastic, other)
MATERIAL_TO_SIM_KEY = {
    "Plastic": "plastic",
    "Còn lại": "other",
    "Other": "other",
    "Waste": "other"
}

def camera_perception_loop():
    """Luồng chạy ngầm đọc camera và suy luận YOLO liên tục."""
    cap = None
    cam_name = "None"
    
    # 1. Quét tìm webcam thật trên Windows (Ưu tiên DirectShow cv2.CAP_DSHOW)
    for idx in [0, 1]:
        test_cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if test_cap.isOpened():
            ret, test_frame = test_cap.read()
            if ret and test_frame is not None and test_frame.size > 0:
                cap = test_cap
                cam_name = f"Webcam #{idx} (DirectShow)"
                break
            test_cap.release()

    # 2. Thử tiếp backend mặc định nếu DirectShow chưa được
    if cap is None:
        for idx in [0, 1]:
            test_cap = cv2.VideoCapture(idx)
            if test_cap.isOpened():
                ret, test_frame = test_cap.read()
                if ret and test_frame is not None and test_frame.size > 0:
                    cap = test_cap
                    cam_name = f"Webcam #{idx} (Default)"
                    break
                test_cap.release()

    using_synthetic = (cap is None)
    if not using_synthetic:
        # Cấu hình độ phân giải chuẩn
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print(f"[CAMERA] >>> KẾT NỐI THÀNH CÔNG: {cam_name}")
        print("[CAMERA] >>> ĐANG ĐỌC VIDEO THẬT TỪ WEBCAM! Hãy giơ chai nước hoặc lon nước trước camera.")
    else:
        print("[CAMERA] [CẢNH BÁO] Không tìm thấy webcam vật lý nào. Chuyển sang Synthetic Animation.")

    frame_id = 0
    prev_time = time.time()
    synthetic_cycle = 0

    while True:
        frame_id += 1
        t_start = time.perf_counter()

        if not using_synthetic:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.03)
                continue
            frame = cv2.resize(frame, (640, 480))
        else:
            # Tạo synthetic frame chuyển động mô phỏng vật thể rác đưa vào camera
            frame = np_synthetic_frame(synthetic_cycle)
            synthetic_cycle += 1
            time.sleep(0.04)

        # 1. Chạy AI Perception của Member 1
        detections = detector.detect(frame)
        latency = (time.perf_counter() - t_start) * 1000.0

        # Tính FPS
        now = time.time()
        fps = 1.0 / max(1e-5, (now - prev_time))
        prev_time = now

        # 2. Vẽ đồ họa HUD và Bounding Box
        annotated = frame.copy()
        detected_event = None

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            cls_name = det["material_class"]
            conf = det["confidence"]

            # Màu theo loại vật liệu: Xanh ngọc cho Plastic, Vàng cam cho Còn lại, Xám nhạt cho Person
            if cls_name == "Plastic":
                color = (69, 214, 196)  # Xanh ngọc
            elif cls_name == "Còn lại":
                color = (100, 185, 240)  # Vàng cam
            else:
                color = (180, 180, 180)  # Xám cho Person / vật thể khác

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{cls_name} {conf:.2f}"
            cv2.putText(annotated, label, (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            sim_key = MATERIAL_TO_SIM_KEY.get(cls_name)
            if sim_key and conf >= 0.40:
                detected_event = {
                    "label": cls_name,
                    "conf": conf,
                    "state": {sim_key: 1}
                }

        # Vẽ thanh HUD FPS & Latency
        cv2.rectangle(annotated, (10, 10), (280, 50), (20, 20, 20), -1)
        cv2.putText(annotated, f"FPS: {fps:.1f} | Latency: {latency:.1f}ms", (18, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)

        # Cập nhật state an toàn luồng
        with state.lock:
            state.latest_annotated = annotated
            state.fps = fps
            state.latency_ms = latency
            if detected_event:
                state.latest_detection = detected_event
                state.event_queue.append(detected_event)
                # Giới hạn hàng đợi sự kiện
                if len(state.event_queue) > 10:
                    state.event_queue.pop(0)

def np_synthetic_frame(cycle):
    """Tạo frame giả lập đổi luân phiên các loại rác để test khi không có webcam."""
    import numpy as np
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(canvas, (40, 40), (600, 440), (25, 30, 40), -1)
    cv2.putText(canvas, "[ SYNTHETIC WEBCAM FEED ]", (50, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)
    
    # Chu kỳ 80 frame đổi loại rác 1 lần (Plastic <-> Còn lại)
    mode = (cycle // 80) % 2
    if mode == 0:
        cv2.circle(canvas, (320, 240), 50, (69, 214, 196), -1)
        cv2.putText(canvas, "Simulated Plastic Bottle", (220, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    else:
        cv2.circle(canvas, (320, 240), 45, (100, 185, 240), -1)
        cv2.putText(canvas, "Simulated Waste Item (Con lai)", (190, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return canvas

@app.route("/")
def index():
    """Phục vụ file 3D Trash Bin Simulator của Leader (Three.js WebGL)."""
    sim_path = os.path.join(os.path.dirname(__file__), "Trash Bin Simulator 3D.html")
    return send_file(sim_path)

@app.route("/video_feed")
def video_feed():
    """Stream MJPEG hình ảnh annotated trực tiếp về trình duyệt."""
    def generate():
        while True:
            with state.lock:
                frame = state.latest_annotated
            if frame is None:
                time.sleep(0.04)
                continue
            ret, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
            time.sleep(0.033) # ~30 FPS

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/events")
def events_stream():
    """Stream sự kiện nhận diện qua Server-Sent Events (SSE)."""
    def event_generator():
        last_sent_time = 0
        while True:
            evt = None
            with state.lock:
                if state.event_queue:
                    evt = state.event_queue.pop(0)

            if evt:
                now = time.time()
                # Cooldown 2 giây giữa các lần kích hoạt nắp
                if now - last_sent_time > 2.0:
                    last_sent_time = now
                    yield f"data: {json.dumps(evt)}\n\n"
            time.sleep(0.1)

    return Response(event_generator(), mimetype="text/event-stream")

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "fps": round(state.fps, 1),
        "latency_ms": round(state.latency_ms, 1),
        "yolo_active": detector.is_yolo_active
    })

if __name__ == "__main__":
    # Khởi động luồng đọc camera
    cam_thread = threading.Thread(target=camera_perception_loop, daemon=True)
    cam_thread.start()

    port = 5000
    print("=" * 65)
    print(f" 🚀 AI PERCEPTION & 3D SIMULATOR BRIDGE ĐANG CHẠY!")
    print(f" Mở trình duyệt tại: http://localhost:{port}")
    print("=" * 65)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
