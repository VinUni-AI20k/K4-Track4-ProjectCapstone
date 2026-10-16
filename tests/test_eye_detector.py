"""Hình học và lọc quan sát, không cần MediaPipe hoặc dữ liệu khuôn mặt."""

import math
from types import SimpleNamespace
import unittest

from src.eye_detector import LEFT_EYE, RIGHT_EYE, eye_aspect_ratio, observation_from_landmarks


EYE = ((0, 0), (5, -3), (15, -3), (20, 0), (15, 3), (5, 3))


class EyeGeometryTests(unittest.TestCase):
    def test_ear_has_expected_value(self):
        self.assertAlmostEqual(eye_aspect_ratio(EYE), 0.3)

    def test_ear_preserved_under_translation_scale_and_rotation(self):
        for angle in (0, 0.4, 1.5):
            points = tuple((2 * (x * math.cos(angle) - y * math.sin(angle)) + 50,
                            2 * (x * math.sin(angle) + y * math.cos(angle)) + 80)
                           for x, y in EYE)
            self.assertAlmostEqual(eye_aspect_ratio(points), 0.3)

    def test_tiny_collapsed_or_nonfinite_eyes_rejected(self):
        for points in ((), ((0, 0),) * 6, tuple((x / 20, y / 20) for x, y in EYE),
                       ((float("nan"), 0),) + EYE[1:]):
            self.assertIsNone(eye_aspect_ratio(points))

    def landmarks(self):
        landmarks = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
        for indices, shift in ((LEFT_EYE, 100), (RIGHT_EYE, 200)):
            for index, (x, y) in zip(indices, EYE):
                landmarks[index] = SimpleNamespace(x=(x + shift) / 640, y=(y + 100) / 480)
        return landmarks

    def test_normalized_landmarks_are_converted_to_pixel_on_nonsquare_frame(self):
        result = observation_from_landmarks([self.landmarks()], 640, 480)
        self.assertTrue(result.valid)
        self.assertAlmostEqual(result.ear, 0.3)
        self.assertEqual(len(result.eye_points), 12)
        self.assertEqual(result.eye_points[0], (100, 100))

    def test_zero_or_multiple_faces_rejected(self):
        self.assertFalse(observation_from_landmarks([], 640, 480).valid)
        face = self.landmarks()
        self.assertFalse(observation_from_landmarks([face, face], 640, 480).valid)

    def test_out_of_frame_and_incomplete_face_rejected(self):
        self.assertFalse(observation_from_landmarks([[SimpleNamespace(x=0, y=0)]], 640, 480).valid)
        face = self.landmarks()
        face[LEFT_EYE[0]].x = 1.2
        self.assertFalse(observation_from_landmarks([face], 640, 480).valid)


if __name__ == "__main__":
    unittest.main()
