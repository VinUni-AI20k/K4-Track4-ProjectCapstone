# ⏱️ NHIỆM VỤ THÀNH VIÊN 3 (TRONG 4 BẠN): TEMPORAL KALMAN & LỌC BẤT ĐỊNH

> **Dự án:** VinRobotics Waste Sorter Sim (Hệ thống Robot gắp phân loại phế liệu VinRobotics / VinFast)  
> **Thời gian:** 2 Giờ Build | 10 Phút Demo  
> **Nhánh Git phân công:** `feature/temporal-uncertainty`  
> **Trụ cột Track 4 phụ trách:** **Trụ cột 5: THỜI GIAN (Kalman Filter & Temporal Tracking)** + **Trụ cột 3: BẤT ĐỊNH (Uncertainty Evaluation)**

---

## 1. Nhiệm vụ chính
1. **Trụ cột Thời gian (3D Kalman Filter):**
   - Làm mượt chuỗi tọa độ 3D $(X, Y, Z)$ nhận từ Thành viên 2 qua các khung hình liên tiếp.
   - Triệt tiêu hiện tượng rung giật BBox (jitter), dự đoán vị trí nếu vật thể trôi trên băng chuyền ảo của Simulator.
2. **Cơ chế Đồng thuận thời gian (Temporal Consensus):**
   - Chỉ cho phép gửi lệnh gắp khi vật thể được nhận diện ổn định trong $\ge 4/5$ frame liên tiếp.
3. **Trụ cột Bất định (Uncertainty Filter):**
   - Kiểm tra **Ground Truth** do Simulator của Leader cung cấp: Tính sai số định vị thực tế:
     $$\Delta E = \sqrt{(X_{\text{pred}} - X_{\text{gt}})^2 + (Y_{\text{pred}} - Y_{\text{gt}})^2}$$
   - Nếu sai số $\Delta E > 25\text{ mm}$ hoặc độ tự tin $Conf < 0.65$ $\rightarrow$ Gán cờ `UNCERTAIN` và yêu cầu robot dừng gắp để tránh va chạm.
4. Chuyển trạng thái an toàn cho **Thành viên 4** (Closed-Loop Actuator & HUD).

---

## 2. Giao kèo dữ liệu kết nối (Interface Contract)
File `modules/tracker.py` cung cấp class `WasteTemporalUncertaintyTracker`:

```python
# Đầu ra gửi cho Thành viên 4:
tracked_state = {
    "target_object": {
        "material_class": "Plastic",
        "smooth_world_3d": [0.049, 0.350, -0.099],   # Tọa độ 3D sau khi lọc Kalman mượt
        "localization_error_mm": 2.1,                # Sai số so với Ground Truth của Sim
        "uncertainty_flag": "CONFIDENT",             # "CONFIDENT" | "UNCERTAIN" | "REJECTED"
        "consensus_ratio": "5/5"
    },
    "should_trigger_pick": True                      # True nếu đủ điều kiện an toàn để gắp
}
```

---

## 3. Code mẫu khung sườn (`modules/tracker.py`)

```python
from collections import deque
import numpy as np

class KalmanFilter3D:
    """Bộ lọc Kalman 3D làm mượt tọa độ thế giới (X, Y, Z) của vật thể"""
    def __init__(self, q=1e-3, r=1e-2):
        self.q = q
        self.r = r
        self.x = np.zeros(3)
        self.p = np.eye(3)
        self.is_init = False

    def update(self, measurement):
        z = np.array(measurement, dtype=float)
        if not self.is_init:
            self.x = z
            self.is_init = True
            return self.x.tolist()

        # Predict
        self.p = self.p + np.eye(3) * self.q
        # Update
        k = self.p / (self.p + np.eye(3) * self.r)
        self.x = self.x + k @ (z - self.x)
        self.p = (np.eye(3) - k) @ self.p
        return [round(float(v), 3) for v in self.x]

class WasteTemporalUncertaintyTracker:
    def __init__(self, window_size=5, min_consensus=4):
        self.kf = KalmanFilter3D()
        self.history = deque(maxlen=window_size)
        self.min_consensus = min_consensus

    def update(self, geometric_items, sim_ground_truth=None):
        if not geometric_items:
            self.history.append("NONE")
            return {"target_object": None, "should_trigger_pick": False}

        # Ưu tiên vật thể nằm trong tầm với của Robot
        reachable = [it for it in geometric_items if it.get("is_within_reach", False)]
        target = reachable[0] if reachable else geometric_items[0]

        # 1. Lọc mượt tọa độ qua Kalman 3D
        raw_pos = target["target_world_3d"]
        smooth_pos = self.kf.update(raw_pos)

        # 2. Đánh giá sai số định vị với Ground Truth từ Sim của Leader
        error_mm = 0.0
        flag = "CONFIDENT"
        if sim_ground_truth and "true_world_pos" in sim_ground_truth:
            gt_pos = sim_ground_truth["true_world_pos"]
            dx = smooth_pos[0] - gt_pos[0]
            dy = smooth_pos[1] - gt_pos[1]
            error_mm = round(float(np.sqrt(dx**2 + dy**2) * 1000.0), 2)
            
            # Nếu sai số > 20mm hoặc conf thấp -> UNCERTAIN
            if error_mm > 20.0 or target["confidence"] < 0.65:
                flag = "UNCERTAIN"

        # 3. Đồng thuận thời gian (Temporal Consensus)
        cls_name = target["material_class"]
        self.history.append(cls_name)
        count = self.history.count(cls_name)
        ratio_str = f"{count}/{len(self.history)}"

        should_pick = (count >= self.min_consensus) and (flag == "CONFIDENT") and target.get("is_within_reach", False)

        return {
            "target_object": {
                "material_class": cls_name,
                "smooth_world_3d": smooth_pos,
                "localization_error_mm": error_mm,
                "uncertainty_flag": flag,
                "consensus_ratio": ratio_str
            },
            "should_trigger_pick": should_pick
        }
```

---

## 4. Định dạng Console Log Trace
```text
[FRAME #0142] [KALMAN 3D] Raw: [0.048, 0.350, -0.098]m -> Smooth: [0.049, 0.350, -0.099]m
[FRAME #0142] [UNCERTAINTY] Sim Ground Truth: [0.050, 0.350, -0.100]m | Error: 2.14 mm (CONFIDENT)
[FRAME #0142] [TEMPORAL CONSENSUS] Consensus: 5/5 frames 'Plastic' -> SAFETY STATUS: CLEAR_TO_PICK!
```

---

## 5. Quy trình Git
```bash
git checkout -b feature/temporal-uncertainty
git add modules/tracker.py
git commit -m "feat(temporal): implement 3d kalman filtering and uncertainty verification with sim gt"
git push origin feature/temporal-uncertainty
```

---

## 6. Vai trò trong buổi thuyết trình 10 phút
* **Phút 03:00 - 04:00:** Báo cáo trụ cột **THỜI GIAN** và **BẤT ĐỊNH**: *"Em phụ trách bộ lọc Kalman 3D để triệt tiêu nhiễu dao động của camera, đồng thời kết nối trực tiếp với Ground Truth của Simulator để đánh giá độ bất định trước khi cho phép robot thực hiện gắp."*
