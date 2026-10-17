# 📐 NHIỆM VỤ THÀNH VIÊN 2 (TRONG 4 BẠN): 3D CAMERA GEOMETRY & TỌA ĐỘ GẮP SIM

> **Dự án:** VinRobotics Waste Sorter Sim (Hệ thống Robot gắp phân loại phế liệu VinRobotics / VinFast)  
> **Thời gian:** 2 Giờ Build | 10 Phút Demo  
> **Nhánh Git phân công:** `feature/geometry-3d`  
> **Trụ cột Track 4 phụ trách:** **Trụ cột 2: HÌNH HỌC (Camera Geometry / 2D-to-3D World Transformation)**

---

## 1. Nhiệm vụ chính
1. **Trụ cột Hình học (Camera Geometry):**
   - Nhận tọa độ pixel $(u, v)$ từ **Thành viên 1** và thông số Camera ảo (Intrinsic matrix $K$, tiêu cự $f_x, f_y$, tâm quang học $c_x, c_y$, chiều cao camera) từ **Simulator của Leader**.
   - Dùng phép biến đổi **Nghịch đảo hình chiếu Pinhole (Inverse Camera Projection)** để tính tọa độ thế giới 3D thực tế $(X, Y, Z)_{\text{world}}$ của vật thể trong Simulator:
     $$X_{\text{world}} = \frac{(u - c_x) \times Z_{\text{depth}}}{f_x}, \quad Y_{\text{world}} = \frac{(v - c_y) \times Z_{\text{depth}}}{f_y}$$
2. **Tính toán điểm gắp tối ưu (Pick Point Pose):**
   - Xác định vector tiếp cận của tay gắp (End-Effector Orientation): Tính góc xoay $\theta$ hoặc offset z-clearance để cánh tay robot trong Simulator hạ xuống gắp an toàn không bị va chạm.
3. Chuyển tiếp tọa độ 3D cho **Thành viên 3** (Lọc Kalman & Bất định).

---

## 2. Giao kèo dữ liệu kết nối (Interface Contract)
File `modules/geometry.py` của bạn cung cấp class `GeometryCoordinateTransformer`:

```python
# Đầu ra gửi cho Thành viên 3:
geometric_items = [
    {
        "material_class": "Plastic",
        "confidence": 0.89,
        "pixel_center": (u, v),
        "target_world_3d": [0.048, 0.350, -0.098],  # Tọa độ 3D mét trong Simulator
        "pick_approach_vector": [0.0, 0.0, -1.0],   # Vector hướng gắp từ trên xuống
        "is_within_reach": True                     # Nằm trong tầm với của cánh tay robot
    }
]
```

---

## 3. Code mẫu khung sườn (`modules/geometry.py`)

```python
import numpy as np

class GeometryCoordinateTransformer:
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
```

---

## 4. Định dạng Console Log Trace
```text
[FRAME #0142] [GEOMETRY 3D] Pixel: (395, 185) -> Sim World Pose: X=0.048m, Y=0.350m, Z=-0.098m
              -> In Robot Reachable Workspace: TRUE | Approach: Top-Down (-Z)
```

---

## 5. Quy trình Git
```bash
git checkout -b feature/geometry-3d
git add modules/geometry.py
git commit -m "feat(geometry): implement pinhole inverse projection to leader simulator world frame"
git push origin feature/geometry-3d
```

---

## 6. Vai trò trong buổi thuyết trình 10 phút
* **Phút 02:00 - 03:00:** Báo cáo trụ cột **HÌNH HỌC**: *"Em đảm nhiệm việc ánh xạ từ không gian điểm ảnh 2D sang không gian tọa độ thế giới 3D của Simulator, cho phép cánh tay robot biết chính xác vị trí $(X, Y, Z)$ cần di chuyển tới để gắp vật thể."*
