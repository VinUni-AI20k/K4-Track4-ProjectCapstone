"""
MEMBER 3 MODULE: TEMPORAL KALMAN & UNCERTAINTY TRACKER
Bộ lọc Kalman 3D làm mượt tọa độ và kiểm chứng bất định với Sim Ground Truth
"""

from collections import deque
import numpy as np

class KalmanFilter3D:
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
