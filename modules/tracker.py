"""
VinRobotics Waste Sorter Sim - Temporal Kalman & Uncertainty Evaluation
Trụ cột Track 4 phụ trách:
- Trụ cột 5: THỜI GIAN (Kalman Filter & Temporal Tracking)
- Trụ cột 3: BẤT ĐỊNH (Uncertainty Evaluation)

Vai trò:
- Triệt tiêu rung giật (jitter) tọa độ 3D nhận từ Thành viên 2 bằng bộ lọc Kalman 3D.
- Thiết lập cơ chế đồng thuận thời gian (Temporal Consensus: >= 4/5 frames).
- Đánh giá độ bất định định vị đối chiếu với Ground Truth của Simulator:
    Delta_E = sqrt((X_pred - X_gt)^2 + (Y_pred - Y_gt)^2)
    Nếu Delta_E > 25 mm hoặc Confidence < 0.65 -> Gán cờ UNCERTAIN / REJECTED và dừng gắp an toàn.
- Chuyển giao trạng thái an toàn (should_trigger_pick) cho Thành viên 4 (Actuator & HUD).
"""

from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class KalmanFilter3D:
    """
    Bộ lọc Kalman 3D làm mượt tọa độ thế giới (X, Y, Z) của phế liệu qua các frame liên tiếp.
    Triệt tiêu hiện tượng jitter của camera và ước lượng vị trí vật thể.
    """

    def __init__(self, q: float = 1e-3, r: float = 1e-2):
        """
        Khởi tạo KalmanFilter3D:
        :param q: Nhiễu quá trình (process noise covariance factor)
        :param r: Nhiễu đo lường từ camera/perception (measurement noise covariance factor)
        """
        self.q = float(q)
        self.r = float(r)
        self.x = np.zeros(3, dtype=float)
        self.p = np.eye(3, dtype=float)
        self.is_init = False

    def reset(self) -> None:
        """Đặt lại trạng thái bộ lọc khi đối tượng chuyển sang vật thể mới."""
        self.x = np.zeros(3, dtype=float)
        self.p = np.eye(3, dtype=float)
        self.is_init = False

    def predict(self) -> List[float]:
        """Bước dự đoán trạng thái (nếu frame bị drop hoặc vật thể trôi)."""
        if not self.is_init:
            return [0.0, 0.0, 0.0]
        self.p = self.p + np.eye(3, dtype=float) * self.q
        return [round(float(v), 3) for v in self.x]

    def update(self, measurement: Union[List[float], Tuple[float, ...], np.ndarray]) -> List[float]:
        """
        Cập nhật đo lường 3D từ hệ thống Perception.
        :param measurement: [X, Y, Z] tọa độ đo lường thô
        :return: [X, Y, Z] tọa độ 3D đã làm mượt (3 chữ số thập phân)
        """
        z = np.array(measurement, dtype=float)

        if not self.is_init:
            self.x = z
            self.p = np.eye(3, dtype=float)
            self.is_init = True
            return [round(float(v), 3) for v in self.x]

        # 1. Dự đoán (Predict)
        self.p = self.p + np.eye(3, dtype=float) * self.q

        # 2. Tính ma trận độ lợi Kalman (Kalman Gain)
        # S = P + R
        s = self.p + np.eye(3, dtype=float) * self.r
        k = self.p @ np.linalg.inv(s)

        # 3. Cập nhật trạng thái (Update State)
        self.x = self.x + k @ (z - self.x)

        # 4. Cập nhật ma trận hiệp phương sai sai số (Update Covariance)
        self.p = (np.eye(3, dtype=float) - k) @ self.p

        return [round(float(v), 3) for v in self.x]


class WasteTemporalUncertaintyTracker:
    """
    Bộ theo dõi thời gian và lọc bất định cho hệ thống Robot gắp phân loại phế liệu VinRobotics.
    - Trụ cột Thời gian: Kalman 3D + Đồng thuận chuỗi thời gian (Temporal Consensus).
    - Trụ cột Bất định: Đánh giá sai số so với Ground Truth Simulator + Ngưỡng an toàn gắp.
    """

    def __init__(
        self,
        window_size: int = 5,
        min_consensus: int = 4,
        max_error_mm: float = 25.0,
        min_confidence: float = 0.65,
        reject_error_mm: float = 50.0,
        q: float = 1e-3,
        r: float = 1e-2,
    ):
        """
        :param window_size: Số frame trong cửa sổ đồng thuận (mặc định 5 frame)
        :param min_consensus: Số frame tối thiểu cần nhận diện cùng loại vật liệu (mặc định >= 4 frame)
        :param max_error_mm: Ngưỡng sai số định vị tối đa cho phép gắp (mặc định 25.0 mm)
        :param min_confidence: Ngưỡng độ tin cậy AI tối thiểu (mặc định 0.65)
        :param reject_error_mm: Ngưỡng sai số cực đại sẽ bị REJECTED (mặc định 50.0 mm)
        """
        self.kf = KalmanFilter3D(q=q, r=r)
        self.history = deque(maxlen=window_size)
        self.window_size = window_size
        self.min_consensus = min_consensus
        self.max_error_mm = max_error_mm
        self.min_confidence = min_confidence
        self.reject_error_mm = reject_error_mm

    def reset(self) -> None:
        """Đặt lại bộ lọc và lịch sử chuỗi thời gian."""
        self.kf.reset()
        self.history.clear()

    def update(
        self,
        geometric_items: Optional[List[Dict[str, Any]]],
        sim_ground_truth: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Nhận danh sách vật thể từ Thành viên 2 (Geometric items) và Ground Truth từ Sim Leader.
        Thực hiện lọc Kalman 3D, kiểm tra bất định và đồng thuận thời gian.

        :param geometric_items: Danh sách vật thể nhận diện kèm tọa độ 3D và độ với tới.
        :param sim_ground_truth: Ground truth thực tế từ Simulator (ví dụ: {'true_world_pos': [x, y, z]}).
        :return: tracked_state dict theo Interface Contract với Thành viên 4.
        """
        if not geometric_items:
            self.history.append("NONE")
            return {
                "target_object": None,
                "should_trigger_pick": False,
            }

        # Ưu tiên vật thể nằm trong tầm với của Robot (is_within_reach)
        reachable = [it for it in geometric_items if it.get("is_within_reach", False)]
        target = reachable[0] if reachable else geometric_items[0]

        # 1. Trụ cột Thời gian: Lọc mượt tọa độ 3D qua Kalman 3D
        raw_pos = target.get("target_world_3d") or target.get("world_pos_3d") or [0.0, 0.0, 0.0]
        smooth_pos = self.kf.update(raw_pos)

        # 2. Trụ cột Bất định: Đánh giá sai số định vị với Ground Truth từ Sim Leader
        error_mm = 0.0
        flag = "CONFIDENT"
        confidence = float(target.get("confidence", 1.0))

        if sim_ground_truth and ("true_world_pos" in sim_ground_truth or "gt_pos" in sim_ground_truth):
            gt_pos = sim_ground_truth.get("true_world_pos", sim_ground_truth.get("gt_pos"))
            # Delta_E = sqrt((X_pred - X_gt)^2 + (Y_pred - Y_gt)^2) (m) -> đổi sang mm (* 1000)
            dx = smooth_pos[0] - gt_pos[0]
            dy = smooth_pos[1] - gt_pos[1]
            error_mm = round(float(np.hypot(dx, dy) * 1000.0), 2)

            # Phân loại mức độ bất định
            if error_mm > self.reject_error_mm:
                flag = "REJECTED"
            elif error_mm > self.max_error_mm or confidence < self.min_confidence:
                flag = "UNCERTAIN"
            else:
                flag = "CONFIDENT"
        else:
            # Nếu không có Ground Truth, đánh giá dựa trên độ tự tin nhận diện
            if confidence < self.min_confidence:
                flag = "UNCERTAIN"
            else:
                flag = "CONFIDENT"

        # 3. Đồng thuận thời gian (Temporal Consensus)
        cls_name = target.get("material_class", "Unknown")
        self.history.append(cls_name)
        count = self.history.count(cls_name)
        ratio_str = f"{count}/{len(self.history)}"

        # Điều kiện an toàn để kích hoạt gắp:
        # - Đạt đồng thuận >= min_consensus (ví dụ 4/5 frame)
        # - Trạng thái đánh giá bất định là CONFIDENT (sai số <= 25mm và conf >= 0.65)
        # - Nằm trong tầm với gắp của Robot
        is_reachable = bool(target.get("is_within_reach", False))
        should_pick = (
            (count >= self.min_consensus)
            and (flag == "CONFIDENT")
            and is_reachable
        )

        return {
            "target_object": {
                "material_class": cls_name,
                "smooth_world_3d": smooth_pos,
                "localization_error_mm": error_mm,
                "uncertainty_flag": flag,
                "consensus_ratio": ratio_str,
            },
            "should_trigger_pick": should_pick,
        }

    def format_log(
        self,
        frame_id: int,
        raw_pos: List[float],
        tracked_state: Dict[str, Any],
        sim_ground_truth: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Định dạng Console Log Trace chuẩn theo yêu cầu hackathon:
        [FRAME #0142] [KALMAN 3D] Raw: [0.048, 0.350, -0.098]m -> Smooth: [0.049, 0.350, -0.099]m
        [FRAME #0142] [UNCERTAINTY] Sim Ground Truth: [0.050, 0.350, -0.100]m | Error: 2.14 mm (CONFIDENT)
        [FRAME #0142] [TEMPORAL CONSENSUS] Consensus: 5/5 frames 'Plastic' -> SAFETY STATUS: CLEAR_TO_PICK!
        """
        fid = f"{frame_id:04d}"
        target_obj = tracked_state.get("target_object")
        should_pick = tracked_state.get("should_trigger_pick", False)

        if not target_obj:
            return f"[FRAME #{fid}] [TRACKER] No target detected | SAFETY STATUS: IDLE"

        smooth_pos = target_obj["smooth_world_3d"]
        error_mm = target_obj["localization_error_mm"]
        flag = target_obj["uncertainty_flag"]
        ratio = target_obj["consensus_ratio"]
        cls_name = target_obj["material_class"]

        raw_str = f"[{raw_pos[0]:.3f}, {raw_pos[1]:.3f}, {raw_pos[2]:.3f}]m"
        smooth_str = f"[{smooth_pos[0]:.3f}, {smooth_pos[1]:.3f}, {smooth_pos[2]:.3f}]m"

        line1 = f"[FRAME #{fid}] [KALMAN 3D] Raw: {raw_str} -> Smooth: {smooth_str}"

        if sim_ground_truth and ("true_world_pos" in sim_ground_truth or "gt_pos" in sim_ground_truth):
            gt_pos = sim_ground_truth.get("true_world_pos", sim_ground_truth.get("gt_pos"))
            gt_str = f"[{gt_pos[0]:.3f}, {gt_pos[1]:.3f}, {gt_pos[2]:.3f}]m"
            line2 = f"[FRAME #{fid}] [UNCERTAINTY] Sim Ground Truth: {gt_str} | Error: {error_mm:.2f} mm ({flag})"
        else:
            line2 = f"[FRAME #{fid}] [UNCERTAINTY] Sim Ground Truth: N/A | Status: ({flag})"

        safety_status = "SAFETY STATUS: CLEAR_TO_PICK!" if should_pick else f"SAFETY STATUS: HOLD ({flag})"
        line3 = f"[FRAME #{fid}] [TEMPORAL CONSENSUS] Consensus: {ratio} frames '{cls_name}' -> {safety_status}"

        return f"{line1}\n{line2}\n{line3}"
