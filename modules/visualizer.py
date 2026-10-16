"""
MEMBER 4 MODULE: HUD VISUALIZER & TRACE LOGGING
Dựng HUD trực quan trên OpenCV và xuất Log CSV kiểm chứng
"""

import cv2
import csv
import os
import time

class WasteVisualizer:
    def __init__(self, log_path="logs/sim_trace.csv"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        if not os.path.exists(self.log_path):
            with open(self.log_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "frame_id", "material", "smooth_x", "smooth_y", "smooth_z",
                    "error_mm", "uncertainty_flag", "action_state", "latency_ms"
                ])

    def log_trace(self, frame_id, target, action_state, latency_ms):
        with open(self.log_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            pos = target["smooth_world_3d"] if target else [0, 0, 0]
            writer.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S"),
                frame_id,
                target["material_class"] if target else "None",
                pos[0], pos[1], pos[2],
                target["localization_error_mm"] if target else 0.0,
                target["uncertainty_flag"] if target else "None",
                action_state,
                round(latency_ms, 2)
            ])

    def draw(self, frame, tracked_state, action_state, frame_id, fps, latency_ms):
        canvas = frame.copy()
        h, w = canvas.shape[:2]
        target = tracked_state.get("target_object")

        # 1. Vẽ HUD thông tin trên góc màn hình
        cv2.rectangle(canvas, (10, 10), (330, 85), (25, 25, 25), -1)
        cv2.rectangle(canvas, (10, 10), (330, 85), (100, 100, 100), 1)
        cv2.putText(canvas, f"FPS: {fps:.1f} | Latency: {latency_ms:.1f} ms", (18, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 255), 1)
        
        act_color = (0, 255, 0) if "TRIGGERED" in action_state else (200, 200, 200)
        cv2.putText(canvas, f"Action: {action_state}", (18, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, act_color, 2)
        cv2.putText(canvas, f"Status: Closed-Loop Active", (18, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (150, 150, 255), 1)

        # 2. Vẽ thông số 3D của mục tiêu
        if target:
            pos = target["smooth_world_3d"]
            err = target["localization_error_mm"]
            flag = target["uncertainty_flag"]
            color = (0, 255, 0) if flag == "CONFIDENT" else (0, 165, 255)
            
            info_str = f"Target 3D: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]m | Error: {err:.1f}mm [{flag}]"
            cv2.putText(canvas, info_str, (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        self.log_trace(frame_id, target, action_state, latency_ms)
        return canvas
