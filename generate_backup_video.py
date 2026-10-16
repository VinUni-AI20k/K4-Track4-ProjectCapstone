import os
import cv2
import numpy as np
from modules.controller import ClosedLoopController
from modules.visualizer import WasteVisualizer

class MockSim:
    def __init__(self):
        self.last_action = None
    def execute_action(self, cmd):
        self.last_action = cmd

def generate_video(output_path="backup_demo/backup_video.mp4", duration_sec=10, fps=30):
    """
    Tạo video backup mô phỏng chu trình phân loại phế liệu công nghiệp với HUD Dashboard.
    Bao gồm các pha:
    - Pha 1 (0s - 4s): Phân loại Chai nhựa (Plastic) -> Kích hoạt gắp an toàn.
    - Pha 2 (4s - 7s): Phân loại Lon kim loại (Metal) -> Kích hoạt gắp an toàn.
    - Pha 3 (7s - 10s): Ca lỗi trượt quán tính / che khuất -> Báo UNCERTAIN & Dừng an toàn (Safe Idle).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    width, height = 640, 480
    total_frames = duration_sec * fps

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    sim = MockSim()
    controller = ClosedLoopController(cooldown_seconds=2.0)
    visualizer = WasteVisualizer(log_path="logs/sim_trace.csv")

    for i in range(total_frames):
        t = i / fps
        frame = np.full((height, width, 3), 42, dtype=np.uint8)

        # 1. Vẽ băng chuyền ảo
        cv2.rectangle(frame, (80, 140), (560, 400), (68, 68, 72), -1)
        cv2.line(frame, (80, 270), (560, 270), (100, 100, 105), 2)
        # Vạch kẻ băng tải di chuyển
        offset = int((i * 4) % 60)
        for x in range(80 + offset, 560, 60):
            cv2.line(frame, (x, 140), (x, 400), (80, 80, 85), 1)

        # 2. Tạo chuyển động vật thể theo từng kịch bản
        if t < 4.0:
            # Pha 1: Plastic di chuyển từ trái sang phải
            obj_x = int(120 + (t / 4.0) * 320)
            obj_y = 270
            cv2.circle(frame, (obj_x, obj_y), 22, (230, 175, 45), -1)
            cv2.putText(frame, "Plastic Bottle", (obj_x - 38, obj_y - 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (230, 175, 45), 1)

            should_pick = (t >= 1.5)
            tracked_state = {
                "target_object": {
                    "material_class": "Plastic",
                    "smooth_world_3d": [round(float((obj_x - 320)/600.0), 3), 0.350, -0.099],
                    "localization_error_mm": 2.14,
                    "uncertainty_flag": "CONFIDENT",
                    "consensus_ratio": "5/5"
                },
                "should_trigger_pick": should_pick
            }
        elif t < 7.0:
            # Pha 2: Metal di chuyển
            rel_t = t - 4.0
            obj_x = int(120 + (rel_t / 3.0) * 320)
            obj_y = 265
            cv2.rectangle(frame, (obj_x - 18, obj_y - 18), (obj_x + 18, obj_y + 18), (170, 170, 190), -1)
            cv2.putText(frame, "Metal Scrap", (obj_x - 35, obj_y - 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (170, 170, 190), 1)

            should_pick = (rel_t >= 1.0)
            tracked_state = {
                "target_object": {
                    "material_class": "Metal",
                    "smooth_world_3d": [round(float((obj_x - 320)/600.0), 3), 0.365, -0.098],
                    "localization_error_mm": 2.31,
                    "uncertainty_flag": "CONFIDENT",
                    "consensus_ratio": "5/5"
                },
                "should_trigger_pick": should_pick
            }
        else:
            # Pha 3: Ca lỗi thực nghiệm (Trượt nhanh / Bất định cao)
            rel_t = t - 7.0
            obj_x = int(100 + (rel_t / 3.0) * 440)
            obj_y = 280
            # Vẽ vật thể méo mó bị che khuất
            pts = np.array([[obj_x - 20, obj_y - 10], [obj_x + 15, obj_y - 15], [obj_x + 10, obj_y + 20], [obj_x - 25, obj_y + 10]], np.int32)
            cv2.fillPoly(frame, [pts], (140, 140, 160))
            cv2.putText(frame, "Occluded / High Speed", (obj_x - 55, obj_y - 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 140, 255), 1)

            tracked_state = {
                "target_object": {
                    "material_class": "Metal",
                    "smooth_world_3d": [-0.121, 0.398, -0.101],
                    "localization_error_mm": 24.80,
                    "uncertainty_flag": "UNCERTAIN",
                    "consensus_ratio": "2/5"
                },
                "should_trigger_pick": False  # Từ chối gắp
            }

        action_state = controller.dispatch_action(sim, tracked_state, frame_id=i+1)
        annotated = visualizer.draw(frame, tracked_state, action_state, frame_id=i+1, fps=31.5, latency_ms=22.4)

        out.write(annotated)

    out.release()
    print(f"-> Tạo video backup thành công tại: {output_path} ({duration_sec}s, {total_frames} frames, {fps} FPS)")

if __name__ == "__main__":
    generate_video(duration_sec=10, fps=30)
