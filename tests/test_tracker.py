"""
Unit tests for modules.tracker
Tests 3D Kalman Filter, Uncertainty Evaluation, Temporal Consensus, and Interface Contracts.
"""

import unittest
import numpy as np
from modules.tracker import KalmanFilter3D, WasteTemporalUncertaintyTracker


class TestKalmanFilter3D(unittest.TestCase):
    def setUp(self):
        self.kf = KalmanFilter3D(q=1e-3, r=1e-2)

    def test_initialization(self):
        first_meas = [0.1, 0.2, -0.3]
        out = self.kf.update(first_meas)
        self.assertEqual(out, [0.1, 0.2, -0.3])
        self.assertTrue(self.kf.is_init)

    def test_smoothing_jitter(self):
        # Vật thể đứng yên tại [0.050, 0.350, -0.100] nhưng có nhiễu Gaussian jitter
        true_pos = np.array([0.050, 0.350, -0.100])
        np.random.seed(42)

        smooth_pos = None
        for _ in range(20):
            noise = np.random.normal(0, 0.005, size=3)
            noisy_meas = true_pos + noise
            smooth_pos = self.kf.update(noisy_meas)

        # Sau 20 frame, tọa độ smoothed phải rất gần với true_pos (sai số < 2 mm)
        error_mm = np.linalg.norm(np.array(smooth_pos) - true_pos) * 1000.0
        self.assertLess(error_mm, 2.0)

    def test_reset(self):
        self.kf.update([1.0, 2.0, 3.0])
        self.assertTrue(self.kf.is_init)
        self.kf.reset()
        self.assertFalse(self.kf.is_init)
        self.assertEqual(self.kf.update([0.0, 0.0, 0.0]), [0.0, 0.0, 0.0])


class TestWasteTemporalUncertaintyTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = WasteTemporalUncertaintyTracker(
            window_size=5,
            min_consensus=4,
            max_error_mm=25.0,
            min_confidence=0.65,
        )

    def test_empty_geometric_items(self):
        result = self.tracker.update([])
        self.assertIsNone(result["target_object"])
        self.assertFalse(result["should_trigger_pick"])

    def test_consensus_and_pick_trigger(self):
        # 3 frame đầu: chưa đủ min_consensus (4) -> should_trigger_pick = False
        item = {
            "material_class": "Plastic",
            "target_world_3d": [0.049, 0.350, -0.099],
            "confidence": 0.95,
            "is_within_reach": True,
        }
        sim_gt = {"true_world_pos": [0.050, 0.350, -0.100]}

        for frame in range(1, 4):
            res = self.tracker.update([item], sim_gt)
            self.assertFalse(res["should_trigger_pick"])
            self.assertEqual(res["target_object"]["consensus_ratio"], f"{frame}/{frame}")
            self.assertEqual(res["target_object"]["uncertainty_flag"], "CONFIDENT")

        # Frame thứ 4: đạt 4/4 >= min_consensus (4) -> should_trigger_pick = True
        res4 = self.tracker.update([item], sim_gt)
        self.assertTrue(res4["should_trigger_pick"])
        self.assertEqual(res4["target_object"]["consensus_ratio"], "4/4")

        # Frame thứ 5: đạt 5/5 -> should_trigger_pick = True
        res5 = self.tracker.update([item], sim_gt)
        self.assertTrue(res5["should_trigger_pick"])
        self.assertEqual(res5["target_object"]["consensus_ratio"], "5/5")

    def test_reachability_gate(self):
        # Đạt consensus 5/5 và confident, nhưng vật thể NGOÀI tầm với -> should_trigger_pick = False
        item_unreachable = {
            "material_class": "Metal",
            "target_world_3d": [0.500, 0.850, -0.099],
            "confidence": 0.90,
            "is_within_reach": False,
        }
        sim_gt = {"true_world_pos": [0.500, 0.850, -0.100]}

        for _ in range(5):
            res = self.tracker.update([item_unreachable], sim_gt)

        self.assertEqual(res["target_object"]["consensus_ratio"], "5/5")
        self.assertEqual(res["target_object"]["uncertainty_flag"], "CONFIDENT")
        self.assertFalse(res["should_trigger_pick"])  # Blocked by reachability

    def test_uncertainty_due_to_high_localization_error(self):
        # Tọa độ đo lệch so với Ground Truth 30mm (> 25mm) -> UNCERTAIN -> không gắp
        item = {
            "material_class": "Cardboard",
            "target_world_3d": [0.080, 0.350, -0.099],  # Lệch 30mm theo trục X
            "confidence": 0.95,
            "is_within_reach": True,
        }
        sim_gt = {"true_world_pos": [0.050, 0.350, -0.100]}

        for _ in range(5):
            res = self.tracker.update([item], sim_gt)

        self.assertEqual(res["target_object"]["uncertainty_flag"], "UNCERTAIN")
        self.assertGreater(res["target_object"]["localization_error_mm"], 25.0)
        self.assertFalse(res["should_trigger_pick"])

    def test_uncertainty_due_to_low_confidence(self):
        # Confidence 0.50 (< 0.65) -> UNCERTAIN dù sai số định vị thấp
        item = {
            "material_class": "Glass",
            "target_world_3d": [0.050, 0.350, -0.100],
            "confidence": 0.50,
            "is_within_reach": True,
        }
        sim_gt = {"true_world_pos": [0.050, 0.350, -0.100]}

        for _ in range(5):
            res = self.tracker.update([item], sim_gt)

        self.assertEqual(res["target_object"]["uncertainty_flag"], "UNCERTAIN")
        self.assertFalse(res["should_trigger_pick"])

    def test_format_log_output(self):
        # Test định dạng Console Trace
        raw_pos = [0.048, 0.350, -0.098]
        tracked_state = {
            "target_object": {
                "material_class": "Plastic",
                "smooth_world_3d": [0.049, 0.350, -0.099],
                "localization_error_mm": 2.14,
                "uncertainty_flag": "CONFIDENT",
                "consensus_ratio": "5/5",
            },
            "should_trigger_pick": True,
        }
        sim_gt = {"true_world_pos": [0.050, 0.350, -0.100]}

        log_str = self.tracker.format_log(
            frame_id=142,
            raw_pos=raw_pos,
            tracked_state=tracked_state,
            sim_ground_truth=sim_gt,
        )

        expected_lines = [
            "[FRAME #0142] [KALMAN 3D] Raw: [0.048, 0.350, -0.098]m -> Smooth: [0.049, 0.350, -0.099]m",
            "[FRAME #0142] [UNCERTAINTY] Sim Ground Truth: [0.050, 0.350, -0.100]m | Error: 2.14 mm (CONFIDENT)",
            "[FRAME #0142] [TEMPORAL CONSENSUS] Consensus: 5/5 frames 'Plastic' -> SAFETY STATUS: CLEAR_TO_PICK!",
        ]
        for exp in expected_lines:
            self.assertIn(exp, log_str)


if __name__ == "__main__":
    unittest.main()
