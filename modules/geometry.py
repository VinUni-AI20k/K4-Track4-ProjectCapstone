import numpy as np

class GeometryCoordinateTransformer:
    """
    Member 2: 3D Camera Geometry & Coordinate Transformer
    Ánh xạ từ tâm pixel (u, v) sang không gian 3D thế giới trong Simulator.
    """
    def __init__(self, fx=550.0, fy=550.0, cx=320.0, cy=240.0, camera_height_m=0.35):
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy
        self.camera_height_m = camera_height_m  # Khoảng cách từ camera tới mặt bàn Sim

        # Giới hạn không gian làm việc của Robot (Workspace Limits mét)
        self.x_min, self.x_max = -0.25, 0.25
        self.y_min, self.y_max = 0.15, 0.50

    def pixel_to_world_3d(self, u, v):
        """Khôi phục tọa độ 3D mét từ điểm ảnh 2D và mô hình Pinhole Camera"""
        Z = self.camera_height_m
        X = ((u - self.cx) * Z) / self.fx
        Y = ((v - self.cy) * Z) / self.fy
        return [round(float(X), 3), round(float(Y), 3), round(float(Z), 3)]

    def is_reachable(self, world_pos):
        """Kiểm tra vật thể có nằm trong tầm với (Kinematic Reach) của cánh tay không"""
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
