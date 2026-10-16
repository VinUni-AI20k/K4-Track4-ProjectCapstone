"""Kiểm thử quyết định cảnh báo bằng chuỗi theo thời gian, không dùng webcam."""

import unittest

from src.contracts import DriverState, EyeObservation
from src.state_machine import DriverStateMachine


def observed(ear=0.3):
    return EyeObservation(valid=True, ear_left=ear, ear_right=ear, ear=ear)


class StateMachineTests(unittest.TestCase):
    def ready(self, **kwargs):
        machine = DriverStateMachine(calibration_samples=1, **kwargs)
        self.assertEqual(machine.update(observed(), 0).state, DriverState.OPEN)
        return machine

    def test_calibration_uses_median_and_requires_enough_samples(self):
        machine = DriverStateMachine(calibration_samples=3)
        self.assertEqual(machine.update(observed(0.3), 0).state, DriverState.CALIBRATING)
        self.assertEqual(machine.update(observed(0.9), 0.1).state, DriverState.CALIBRATING)
        result = machine.update(observed(0.31), 0.2)
        self.assertEqual(result.state, DriverState.OPEN)
        self.assertAlmostEqual(result.close_threshold, 0.31 * 0.65)
        self.assertAlmostEqual(result.open_threshold, 0.31 * 0.75)

    def test_invalid_sample_clears_partial_calibration(self):
        machine = DriverStateMachine(calibration_samples=2)
        machine.update(observed(), 0)
        self.assertEqual(machine.update(EyeObservation(), 0.1).state, DriverState.UNKNOWN)
        self.assertEqual(machine.calibration_count, 0)
        self.assertEqual(machine.update(observed(), 0.2).state, DriverState.CALIBRATING)

    def test_zero_reference_never_finishes_calibration(self):
        machine = DriverStateMachine(calibration_samples=1)
        self.assertEqual(machine.update(observed(0), 0).state, DriverState.CALIBRATING)
        self.assertIsNone(machine.reference_ear)

    def test_short_blink_does_not_alert(self):
        machine = self.ready()
        self.assertEqual(machine.update(observed(0.1), 0.1).state, DriverState.CLOSING)
        self.assertFalse(machine.update(observed(0.1), 0.2).alert_event)
        self.assertEqual(machine.update(observed(), 0.3).state, DriverState.OPEN)

    def test_alert_at_duration_and_once_until_reopened(self):
        machine = self.ready(alert_after_s=0.5)
        machine.update(observed(0.1), 0.1)
        self.assertFalse(machine.update(observed(0.1), 0.59).alert_event)
        result = machine.update(observed(0.1), 0.6)
        self.assertEqual(result.state, DriverState.ALERT)
        self.assertAlmostEqual(result.closed_duration_s, 0.5)
        self.assertTrue(result.alert_event)
        self.assertFalse(machine.update(observed(0.1), 0.7).alert_event)
        machine.update(observed(), 0.8)
        machine.update(observed(0.1), 0.9)
        machine.update(observed(0.1), 1.3)
        self.assertTrue(machine.update(observed(0.1), 1.4).alert_event)

    def test_hysteresis_avoids_reset_near_close_threshold(self):
        machine = self.ready(alert_after_s=0.2)
        machine.update(observed(0.1), 0.1)
        result = machine.update(observed(0.21), 0.3)
        self.assertTrue(result.alert_event)
        self.assertEqual(machine.update(observed(0.23), 0.4).state, DriverState.OPEN)

    def test_hysteresis_does_not_start_closure_in_middle_band(self):
        machine = self.ready()
        self.assertEqual(machine.update(observed(0.21), 0.1).state, DriverState.OPEN)

    def test_missing_face_discards_elapsed_time(self):
        machine = self.ready(alert_after_s=0.5)
        machine.update(observed(0.1), 0.1)
        self.assertEqual(machine.update(EyeObservation(), 0.5).state, DriverState.UNKNOWN)
        result = machine.update(observed(0.1), 0.6)
        self.assertEqual(result.closed_duration_s, 0)
        self.assertFalse(result.alert_event)

    def test_processing_gap_discards_elapsed_time(self):
        machine = self.ready(alert_after_s=0.5)
        machine.update(observed(0.1), 0.1)
        result = machine.update(observed(0.1), 2)
        self.assertEqual(result.state, DriverState.UNKNOWN)
        self.assertEqual(result.closed_duration_s, 0)
        self.assertFalse(machine.update(observed(0.1), 2.1).alert_event)

    def test_gap_discards_partial_calibration(self):
        machine = DriverStateMachine(calibration_samples=2)
        machine.update(observed(), 0)
        self.assertEqual(machine.update(observed(), 1).state, DriverState.UNKNOWN)
        self.assertEqual(machine.calibration_count, 0)

    def test_nonfinite_or_missing_ear_is_unknown(self):
        for value in (None, float("nan"), float("inf"), -0.1):
            with self.subTest(value=value):
                machine = self.ready()
                result = machine.update(observed(value), 0.1)
                self.assertEqual(result.state, DriverState.UNKNOWN)

    def test_invalid_left_eye_rejects_even_if_average_present(self):
        machine = self.ready()
        sample = EyeObservation(valid=True, ear_left=None, ear_right=0.3, ear=0.3)
        self.assertEqual(machine.update(sample, 0.1).state, DriverState.UNKNOWN)

    def test_reset_removes_calibration_and_accepts_new_timebase(self):
        machine = self.ready()
        machine.update(observed(0.1), 0.1)
        machine.reset()
        self.assertIsNone(machine.reference_ear)
        self.assertEqual(machine.calibration_count, 0)
        self.assertEqual(machine.update(observed(), 0).state, DriverState.OPEN)

    def test_zero_duration_supports_frame_baseline(self):
        machine = self.ready(alert_after_s=0)
        result = machine.update(observed(0.1), 0.1)
        self.assertTrue(result.alert_event)
        self.assertEqual(result.closed_duration_s, 0)

    def test_time_based_alert_is_consistent_across_fps(self):
        for fps in (10, 25, 60):
            with self.subTest(fps=fps):
                machine = self.ready(alert_after_s=1.5)
                events = []
                first_closed = 1 / fps
                for index in range(1, fps * 2 + 1):
                    timestamp = index / fps
                    if machine.update(observed(0.1), timestamp).alert_event:
                        events.append(timestamp)
                self.assertEqual(len(events), 1)
                self.assertLessEqual(abs(events[0] - first_closed - 1.5), 1 / fps + 1e-8)

    def test_time_must_increase_and_be_finite(self):
        for timestamp in (0, -1, float("nan"), float("inf")):
            with self.subTest(timestamp=timestamp):
                machine = self.ready()
                with self.assertRaises(ValueError):
                    machine.update(observed(), timestamp)

    def test_invalid_configuration_rejected(self):
        for kwargs in (
            {"alert_after_s": -1}, {"alert_after_s": float("nan")},
            {"calibration_samples": 0}, {"calibration_samples": 1.5},
            {"close_ratio": 0.8, "open_ratio": 0.7},
            {"open_ratio": 1}, {"max_gap_s": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                DriverStateMachine(**kwargs)


if __name__ == "__main__":
    unittest.main()
