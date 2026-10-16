"""
MEMBER 4 MODULE: CLOSED-LOOP ROBOT CONTROLLER
Cầu nối gửi lệnh điều khiển từ Perception sang Simulator của Leader
"""

import time

class ClosedLoopController:
    def __init__(self, cooldown_seconds=2.0):
        self.last_action_time = 0
        self.cooldown_seconds = cooldown_seconds
        self.current_action_state = "IDLE"

    def dispatch_action(self, sim, tracked_state):
        now = time.time()
        
        # Nếu chưa đủ điều kiện an toàn gắp từ TV3
        if not tracked_state.get("should_trigger_pick", False):
            if now - self.last_action_time > 1.5:
                self.current_action_state = "SCANNING"
            return self.current_action_state

        # Cơ chế chống gửi lệnh dồn dập (Debouncing / Cooldown)
        if now - self.last_action_time < self.cooldown_seconds:
            return "BUSY_EXECUTING"

        target = tracked_state.get("target_object")
        if not target:
            return "IDLE"

        action_cmd = {
            "action": f"SORT_{target['material_class'].upper()}",
            "target_pos": target["smooth_world_3d"],
            "material": target["material_class"]
        }

        # Gọi hàm execute_action trong Simulator của Leader!
        sim.execute_action(action_cmd)
        self.last_action_time = now
        self.current_action_state = f"TRIGGERED_{action_cmd['action']}"
        return self.current_action_state
