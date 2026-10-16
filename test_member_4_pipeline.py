import os
import time
import numpy as np
import cv2
from modules.controller import ClosedLoopController
from modules.visualizer import WasteVisualizer

class MockLeaderSimulator:
    """Giả lập môi trường Simulator của Leader để kiểm thử khép kín vòng lặp."""
    def __init__(self):
        self.action_history = []

    def execute_action(self, cmd):
        self.action_history.append((time.time(), cmd))
        print(f"[SIMULATOR CORE] Nhận lệnh từ Actuator Bridge: {cmd['action']} tại {cmd['target_pos']} -> Đang thực thi cử động gắp!")

def run_test():
    print("=================================================================")
    print("KIỂM THỬ KHÉP KÍN VÒNG LẶP MEMBER 4: ACTUATOR BRIDGE & HUD TRACE")
    print("=================================================================")

    sim = MockLeaderSimulator()
    controller = ClosedLoopController(cooldown_seconds=1.5)
    visualizer = WasteVisualizer(log_path="logs/sim_trace.csv")

    os.makedirs("backup_demo", exist_ok=True)

    # Tạo frame nền giả lập 640x480 (màu xám công nghiệp)
    base_frame = np.full((480, 640, 3), 45, dtype=np.uint8)
    # Vẽ băng chuyền ảo
    cv2.rectangle(base_frame, (100, 120), (540, 420), (70, 70, 75), -1)
    cv2.line(base_frame, (100, 270), (540, 270), (120, 120, 130), 2)

    # 1. Ca kiểm thử 1: Vật thể Plastic hợp lệ, kích hoạt gắp thành công
    print("\n--- 1. Kiểm thử Ca Thành Công: Phân loại Plastic (Confident) ---")
    tracked_state_plastic = {
        "target_object": {
            "material_class": "Plastic",
            "smooth_world_3d": [0.049, 0.350, -0.099],
            "localization_error_mm": 2.14,
            "uncertainty_flag": "CONFIDENT",
            "consensus_ratio": "5/5"
        },
        "should_trigger_pick": True
    }
    action_1 = controller.dispatch_action(sim, tracked_state_plastic, frame_id=142)
    assert action_1 == "TRIGGERED_SORT_PLASTIC", f"Kỳ vọng TRIGGERED_SORT_PLASTIC nhưng nhận {action_1}"

    frame_plastic = base_frame.copy()
    # Vẽ vật thể chai nhựa
    cv2.circle(frame_plastic, (320, 240), 25, (220, 180, 50), -1)
    annotated_1 = visualizer.draw(frame_plastic, tracked_state_plastic, action_1, frame_id=142, fps=31.8, latency_ms=22.4)
    cv2.imwrite("backup_demo/hud_sample_plastic_triggered.png", annotated_1)
    print("-> Đã lưu ảnh HUD mẫu: backup_demo/hud_sample_plastic_triggered.png")

    # 2. Ca kiểm thử 2: Frame tiếp theo ngay lập tức (Cooldown chống nghẽn lệnh)
    print("\n--- 2. Kiểm thử Ca Cooldown (Chống nghẽn lệnh Actuator Bridge) ---")
    action_2 = controller.dispatch_action(sim, tracked_state_plastic, frame_id=143)
    assert action_2 == "EXECUTING_PREVIOUS", f"Kỳ vọng EXECUTING_PREVIOUS nhưng nhận {action_2}"
    annotated_2 = visualizer.draw(frame_plastic, tracked_state_plastic, action_2, frame_id=143, fps=32.1, latency_ms=22.0)

    # 3. Ca kiểm thử 3: Ca lỗi thực nghiệm (Trượt quán tính / Che khuất -> UNCERTAIN)
    print("\n--- 3. Kiểm thử Ca Lỗi Thực Nghiệm: Sai số cao -> Báo UNCERTAIN & Từ chối gắp ---")
    # Reset cooldown để kiểm tra xem robot có từ chối gắp dù cooldown đã hết
    controller.reset_cooldown()
    tracked_state_uncertain = {
        "target_object": {
            "material_class": "Metal",
            "smooth_world_3d": [-0.121, 0.398, -0.101],
            "localization_error_mm": 24.80,  # Vượt ngưỡng 20mm
            "uncertainty_flag": "UNCERTAIN",
            "consensus_ratio": "2/5"
        },
        "should_trigger_pick": False  # Member 3 từ chối gắp do bất định
    }
    action_3 = controller.dispatch_action(sim, tracked_state_uncertain, frame_id=210)
    assert action_3 == "IDLE", f"Kỳ vọng IDLE để an toàn nhưng nhận {action_3}"

    frame_metal_err = base_frame.copy()
    # Vẽ phôi kim loại bị lệch/che khuất
    cv2.rectangle(frame_metal_err, (200, 180), (280, 260), (160, 160, 180), -1)
    annotated_3 = visualizer.draw(frame_metal_err, tracked_state_uncertain, action_3, frame_id=210, fps=30.5, latency_ms=24.8)
    cv2.imwrite("backup_demo/hud_sample_uncertain_safestop.png", annotated_3)
    print("-> Đã lưu ảnh HUD mẫu ca lỗi: backup_demo/hud_sample_uncertain_safestop.png")

    print("\n=================================================================")
    print("TẤT CẢ CÁC CA KIỂM THỬ ĐÃ THÀNH CÔNG VÀ KHỚP VỚI HƯỚNG DẪN CAPSTONE!")
    print(f"Tổng số lệnh Sim đã thực thi: {len(sim.action_history)}")
    print("Log CSV đã được cập nhật thành công tại: logs/sim_trace.csv")
    print("=================================================================")

if __name__ == "__main__":
    run_test()
