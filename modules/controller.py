import time
from typing import Any, Dict, Optional

class ClosedLoopController:
    """
    Closed-Loop Robot Actuator Bridge
    Phụ trách nhận tín hiệu kích hoạt và tọa độ 3D từ Member 3 (Temporal & Uncertainty Tracker),
    chuyển tiếp lệnh điều khiển gắp/thả (Pick & Place) trực tiếp tới Simulator của Leader.
    Tích hợp cơ chế cooldown nhằm chống nghẽn lệnh (command flooding).
    """

    def __init__(self, cooldown_seconds: float = 2.0):
        self.last_action_time: float = 0.0
        self.cooldown_seconds: float = cooldown_seconds
        self.last_dispatched_command: Optional[Dict[str, Any]] = None

    def dispatch_action(self, sim: Any, tracked_state: Dict[str, Any], frame_id: Optional[int] = None) -> str:
        """
        Gửi lệnh hành động tới Simulator nếu thỏa mãn điều kiện an toàn và cooldown.

        Args:
            sim: Đối tượng Simulator của Leader (cung cấp phương thức execute_action(cmd)).
            tracked_state: Trạng thái theo dõi từ Member 3 bao gồm target_object và should_trigger_pick.
            frame_id: (Tùy chọn) Mã frame hiện tại để ghi log console chuẩn format.

        Returns:
            str: Trạng thái hành động ('IDLE', 'EXECUTING_PREVIOUS', 'TRIGGERED_SORT_...')
        """
        now = time.time()
        
        # 1. Kiểm tra cờ kích hoạt an toàn từ Member 3
        if not tracked_state or not tracked_state.get("should_trigger_pick", False):
            return "IDLE"

        # 2. Kiểm tra cooldown chống gửi dồn lệnh làm nghẽn simulator
        elapsed = now - self.last_action_time
        if elapsed < self.cooldown_seconds:
            return "EXECUTING_PREVIOUS"

        target = tracked_state.get("target_object")
        if not target or "smooth_world_3d" not in target:
            return "IDLE"

        material = target.get("material_class", "Plastic")
        action_name = f"SORT_{material.upper()}"
        target_pos = target["smooth_world_3d"]

        # 3. Tạo cấu trúc lệnh theo chuẩn Interface Contract
        cmd = {
            "action": action_name,
            "target_pos": target_pos,
            "material": material
        }

        # 4. Gửi trực tiếp tới Simulator của Leader
        if hasattr(sim, "execute_action") and callable(sim.execute_action):
            sim.execute_action(cmd)
        elif hasattr(sim, "step") and callable(sim.step):
            # Fallback nếu simulator dùng chuẩn gym step
            sim.step(cmd)

        self.last_action_time = now
        self.last_dispatched_command = cmd

        # 5. In log console chuẩn format của dự án
        frame_str = f"[FRAME #{frame_id:04d}] " if frame_id is not None else ""
        print(f"{frame_str}[CLOSED-LOOP] Actuator Bridge Sent: '{action_name}' at {target_pos}m to Leader Sim!")

        return f"TRIGGERED_{action_name}"

    def reset_cooldown(self) -> None:
        """Đặt lại thời gian cooldown (dùng cho unit test hoặc reset cảnh)."""
        self.last_action_time = 0.0
