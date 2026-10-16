"""
MEMBER 2 MODULE: 3D CAMERA GEOMETRY & COORDINATES
Chuyển đổi từ tọa độ ảnh (u, v) sang tọa độ thế giới 3D robot (X, Y, Z)
"""

import numpy as np

class GeometryCoordinateTransformer:
    def __init__(self, fx=550.0, fy=550.0, cx=320.0, cy=240.0, camera_height_m=0.35):
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy
        self.camera_height_m = camera_height_m

        # Vùng không gian làm việc an toàn của robot (Workspace mét)
        self.x_min, self.x_max = -0.25, 0.25
        self.y_min, self.y_max = 0.15, 0.50

    def pixel_to_world_3d(self, u, v):
        """Khôi phục tọa độ 3D mét từ điểm ảnh 2D theo mô hình Pinhole Camera"""
        Z = self.camera_height_m
        X = ((u - self.cx) * Z) / self.fx
        Y = ((v - self.cy) * Z) / self.fy
        return [round(float(X), 3), round(float(Y), 3), round(float(Z), 3)]

    def is_reachable(self, world_pos):
        x, y, _ = world_pos
        return (self.x_min <= x <= self.x_max) and (self.y_min <= y <= self.y_max)

    def process(self, detections):
        geometric_items = []
        for det in detections:
            u, v = det["center_pixel"]
            world_3d = self.pixel_to_world_3d(u, v)
            reachable = self.is_reachable(world_3d)

            item = dict(det)
            item.update({
                "target_world_3d": world_3d,
                "pick_approach_vector": [0.0, 0.0, -1.0],
                "is_within_reach": reachable
            })
            geometric_items.append(item)

        return geometric_items
