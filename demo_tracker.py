"""
VinRobotics Waste Sorter Sim - Demo Stream for Temporal Kalman & Uncertainty Evaluation
Run this script to demonstrate Member 3's pipeline during the 10-minute presentation!
"""

import time
import numpy as np
from modules.tracker import WasteTemporalUncertaintyTracker


def run_demo():
    print("=" * 80)
    print("  VINROBOTICS WASTE SORTER SIM - MEMBER 3 PIPELINE DEMO")
    print("  Track 4 Pillars: Pillar 5 (Temporal Kalman) & Pillar 3 (Uncertainty Filter)")
    print("=" * 80)

    tracker = WasteTemporalUncertaintyTracker(
        window_size=5,
        min_consensus=4,
        max_error_mm=25.0,
        min_confidence=0.65,
    )

    # Vị trí vật lý thực tế của phế liệu trên băng chuyền ảo (Ground Truth)
    sim_gt = {"true_world_pos": [0.050, 0.350, -0.100]}
    base_pos = np.array(sim_gt["true_world_pos"])

    # Kịch bản mô phỏng 10 frame:
    # - Frames 1-3: Tích lũy đồng thuận thời gian (Consensus building 1/1 -> 3/3)
    # - Frames 4-6: Đạt đồng thuận >= 4/5 và CONFIDENT -> Kích hoạt lệnh gắp CLEAR_TO_PICK!
    # - Frame 7: Nhiễu đột biến lớn (camera jitter > 30mm) -> UNCERTAIN, robot lập tức dừng gắp!
    # - Frames 8-10: Ổn định trở lại -> CLEAR_TO_PICK!
    scenarios = [
        # (frame_no, noise_scale, confidence, is_reach, description)
        (139, 0.003, 0.95, True, "Khởi động nhận diện phế liệu Plastic"),
        (140, 0.004, 0.94, True, "Chuỗi frame tiếp tục nhận diện ổn định"),
        (141, 0.003, 0.96, True, "Tích lũy đồng thuận 3/3 frames"),
        (142, 0.002, 0.98, True, "Đạt ngưỡng an toàn 4/4 frames -> CLEAR_TO_PICK!"),
        (143, 0.002, 0.97, True, "Đạt 5/5 frames hoàn hảo -> Sẵn sàng gắp"),
        (144, 0.003, 0.99, True, "Duy trì trạng thái CONFIDENT"),
        (145, 0.090, 0.90, True, "CẢNH BÁO: Nhiễu rung cực lớn (>80mm) -> Kích hoạt UNCERTAIN dừng robot!"),
        (146, 0.002, 0.96, True, "Bộ lọc Kalman kéo mượt lại vị trí chuẩn"),
        (147, 0.002, 0.97, True, "Hồi phục trạng thái an toàn"),
        (148, 0.001, 0.98, True, "Robot hoàn thành chu trình gắp"),
    ]

    np.random.seed(42)

    for frame_id, noise_scale, conf, reach, desc in scenarios:
        # Giả lập nhiễu từ camera perception của Thành viên 2
        noise = np.random.normal(0, noise_scale, size=3)
        raw_pos = [round(float(v), 3) for v in (base_pos + noise)]

        geometric_items = [
            {
                "material_class": "Plastic",
                "target_world_3d": raw_pos,
                "confidence": conf,
                "is_within_reach": reach,
            }
        ]

        tracked_state = tracker.update(geometric_items, sim_gt)
        log_trace = tracker.format_log(frame_id, raw_pos, tracked_state, sim_gt)

        print(f"\n--- [Tình huống: {desc}] ---")
        print(log_trace)
        time.sleep(0.05)

    print("\n" + "=" * 80)
    print("  DEMO HOÀN TẤT: KALMAN 3D VÀ BỘ LỌC BẤT ĐỊNH HOẠT ĐỘNG CHUẨN XÁC!")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
