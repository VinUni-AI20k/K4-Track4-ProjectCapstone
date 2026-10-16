"""
LEADER MODULE: SIMULATOR & DIGITAL TWIN
Môi trường mô phỏng cánh tay robot và băng chuyền phân loại VinRobotics
"""

import numpy as np
import cv2
import time

class WasteRobotSimulator:
    def __init__(self):
        self.width = 640
        self.height = 480
        
        # Camera Intrinsic ảo
        self.fx = 550.0
        self.fy = 550.0
        self.cx = 320.0
        self.cy = 240.0
        
        # Vật thể trong thế giới Sim (Tọa độ thật: mét)
        self.sim_objects = [
            {"id": 1, "class": "Plastic", "world_pos": np.array([0.05, 0.35, -0.10]), "color": (0, 220, 0)},
            {"id": 2, "class": "Metal", "world_pos": np.array([-0.12, 0.40, -0.10]), "color": (0, 220, 220)}
        ]
        
        self.robot_state = "IDLE"
        self.current_action = "IDLE"
        self.target_pos = None

    def get_frame(self):
        """Render ảnh ảo mô phỏng góc nhìn camera nhìn xuống bàn thao tác"""
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Nền băng chuyền / bàn mô phỏng
        cv2.rectangle(canvas, (60, 50), (580, 430), (45, 45, 45), -1)
        cv2.rectangle(canvas, (60, 50), (580, 430), (80, 80, 80), 2)
        cv2.putText(canvas, "[ VINROBOTICS CLOSED-LOOP SIMULATOR ]", (80, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

        gt_data = None
        for obj in self.sim_objects:
            X, Y, Z = obj["world_pos"]
            # Chiếu Pinhole Projection: u, v pixel
            u = int(self.fx * X / Y + self.cx)
            v = int(self.fy * Z / Y + self.cy)
            radius = int(22.0 / Y)

            cv2.circle(canvas, (u, v), radius, obj["color"], -1)
            cv2.putText(canvas, obj["class"], (u - 25, max(20, v - radius - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

            if gt_data is None:
                gt_data = {
                    "true_world_pos": [round(float(X), 3), round(float(Y), 3), round(float(Z), 3)],
                    "true_class": obj["class"],
                    "true_pixel": [u, v]
                }

        # Vẽ cơ cấu cánh tay robot
        arm_color = (0, 255, 0) if "SORT" in self.current_action else (180, 180, 180)
        cv2.putText(canvas, f"ROBOT ACTUATOR: [{self.robot_state}] - Action: {self.current_action}", 
                    (80, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.50, arm_color, 2)
        
        return canvas, gt_data

    def execute_action(self, action_cmd):
        """Nhận lệnh điều khiển từ TV4 để kích hoạt chuyển động gắp trong Sim"""
        self.current_action = action_cmd.get("action", "IDLE")
        self.target_pos = action_cmd.get("target_pos")
        self.robot_state = "PICKING_AND_SORTING"
        print(f"[SIMULATOR] Robot thực thi lệnh: {self.current_action} tại vị trí {self.target_pos}")

    def step(self):
        """Cập nhật 1 bước thời gian vật lý trong Sim"""
        time.sleep(0.005)
