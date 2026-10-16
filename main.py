"""
VIN PERCEPTION HACKATHON — CAPSTONE PROJECT
Team: TeamFanMU (5 Thành viên)
Đề tài: VinRobotics Closed-Loop Waste Sorter (Real2Sim & Robot Actuation)
Pillars: Simulation (Leader), Learning (TV1), Geometry (TV2), Temporal (TV3), Data & Evidence (TV4)
"""

import cv2
import time
import os
import sys

# Đảm bảo import được các module trong thư mục modules/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.simulator import WasteRobotSimulator
from modules.detector import WasteDetector
from modules.geometry import GeometryCoordinateTransformer
from modules.tracker import WasteTemporalUncertaintyTracker
from modules.controller import ClosedLoopController
from modules.visualizer import WasteVisualizer

def main():
    print("=" * 70)
    print(" VIN PERCEPTION HACKATHON — VINROBOTICS CLOSED-LOOP WASTE SORTER")
    print(" Hệ thống Robot gắp phân loại phế liệu khép kín trong Môi trường Mô phỏng")
    print("=" * 70)

    # 1. Khởi tạo Simulator của Leader và 4 Module của 4 thành viên
    sim = WasteRobotSimulator()
    detector = WasteDetector()
    geometry_proc = GeometryCoordinateTransformer()
    tracker = WasteTemporalUncertaintyTracker(window_size=5, min_consensus=4)
    controller = ClosedLoopController(cooldown_seconds=2.0)
    visualizer = WasteVisualizer(log_path="logs/sim_trace.csv")

    frame_id = 0
    prev_time = time.time()

    print("[SYSTEM] Bắt đầu vòng lặp điều khiển khép kín (Closed-Loop). Nhấn 'q' để dừng.")

    while True:
        frame_id += 1
        start_pipeline = time.time()

        # === 0. LEADER: SIMULATOR RENDER CAMERA ẢO & GROUND TRUTH ===
        frame, sim_gt = sim.get_frame()

        # === 1. THÀNH VIÊN 1: PERCEPTION (YOLO MATERIAL DETECTION) ===
        detections = detector.detect(frame)

        # === 2. THÀNH VIÊN 2: 3D CAMERA GEOMETRY & TỌA ĐỘ GẮP ===
        geometric_items = geometry_proc.process(detections)

        # === 3. THÀNH VIÊN 3: TEMPORAL KALMAN & ĐÁNH GIÁ BẤT ĐỊNH ===
        tracked_state = tracker.update(geometric_items, sim_ground_truth=sim_gt)

        # === 4. THÀNH VIÊN 4: CLOSED-LOOP ACTUATOR BRIDGE & GỬI LỆNH VỀ CHO SIM ===
        action_state = controller.dispatch_action(sim, tracked_state)

        # Cập nhật 1 bước thời gian vật lý của Sim
        sim.step()

        # Đo đạc thời gian và FPS
        now = time.time()
        latency_ms = (now - start_pipeline) * 1000
        fps = 1.0 / max(1e-5, (now - prev_time))
        prev_time = now

        # === 5. THÀNH VIÊN 4: HUD DASHBOARD & CSV LOG TRACE ===
        annotated_frame = visualizer.draw(
            frame=frame,
            tracked_state=tracked_state,
            action_state=action_state,
            frame_id=frame_id,
            fps=fps,
            latency_ms=latency_ms
        )

        # In log trace chu kỳ ngắn ra terminal
        if frame_id % 30 == 0:
            target = tracked_state.get("target_object")
            mat = target["material_class"] if target else "None"
            err = f"{target['localization_error_mm']:.2f}mm" if target else "N/A"
            flag = target["uncertainty_flag"] if target else "SCANNING"
            print(f"[STEP #{frame_id:04d}] Mat: {mat:<7} | Error: {err:<7} | Flag: {flag:<9} | "
                  f"Action: {action_state:<18} | Latency: {latency_ms:4.1f}ms | FPS: {fps:4.1f}")

        cv2.imshow("VinRobotics Closed-Loop Waste Sorter - Sim & Control", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    print("[SYSTEM] Dừng hệ thống. Toàn bộ log trace đã được lưu tại 'logs/sim_trace.csv'.")

if __name__ == "__main__":
    main()
