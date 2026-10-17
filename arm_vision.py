"""TV2 Holistic pose+hands on the integrated latest-frame worker lifecycle."""
from math import dist, isfinite
import time

from contracts import ArmSample
from vision import Vision as HandVision

HAND_EDGES = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
              (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15), (15, 16),
              (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17))
ARM_IDX = {"R": (12, 14, 16), "L": (11, 13, 15)}


def pinch_ratio_from_hand(hand_landmarks, width, height):
    if hand_landmarks is None or len(hand_landmarks) < 21 or width <= 0 or height <= 0:
        return None
    points = [(p.x * width, p.y * height) for p in hand_landmarks]
    if not all(isfinite(value) for point in points for value in point):
        return None
    palm_size = dist(points[0], points[9])
    if palm_size < 15:
        return None
    return dist(points[4], points[8]) / palm_size


def sample_from_pose(landmarks, world, side, frame_id, captured_at, processed_at,
                     visibility=.65, hand_landmarks=None, width=0, height=0):
    invalid = ArmSample(frame_id, captured_at, processed_at, False)
    if landmarks is None or world is None or len(landmarks) < 33 or len(world) < 33:
        return invalid
    indices = (12, 14, 16) if side == "Right" else (11, 13, 15)
    for i in indices:
        point = landmarks[i]
        if (not all(isfinite(x) for x in (point.x, point.y, point.visibility))
                or point.visibility < visibility or not (0 <= point.x <= 1 and 0 <= point.y <= 1)):
            return invalid
    points = [tuple(getattr(world[i], axis) for axis in ("x", "y", "z")) for i in indices]
    if not all(isfinite(x) for point in points for x in point):
        return invalid
    if not all(.06 <= dist(a, b) <= .65 for a,b in zip(points, points[1:])):
        return invalid
    pinch_ratio = pinch_ratio_from_hand(hand_landmarks, width, height)
    if pinch_ratio is None:
        return invalid
    return ArmSample(frame_id, captured_at, processed_at, True, *points,
                     pinch_ratio=pinch_ratio, pinch_valid=True)


class Vision(HandVision):
    def _invalid_sample(self, frame_id, now):
        return ArmSample(frame_id, now, now, False)

    def _create_model(self):
        import mediapipe as mp
        return mp.solutions.holistic.Holistic(model_complexity=0, smooth_landmarks=True,
                                              min_detection_confidence=.6, min_tracking_confidence=.6)

    def _infer(self, frame, frame_id, captured, timestamp):
        import cv2
        import numpy as np
        result = self._model.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        landmarks = result.pose_landmarks.landmark if result.pose_landmarks else None
        world = result.pose_world_landmarks.landmark if result.pose_world_landmarks else None
        h, w = frame.shape[:2]
        hand = result.right_hand_landmarks if self.config.hand_side == "Right" else result.left_hand_landmarks
        sample = sample_from_pose(landmarks, world, self.config.hand_side, frame_id,
                                  captured, time.monotonic(), self.config.arm_visibility,
                                  hand.landmark if hand else None, w, h)
        overlay = frame.copy()
        # Draw both visible arms; exactly the selected side controls the robot.
        if landmarks:
            for side, indices in ARM_IDX.items():
                selected = (side == "R") == (self.config.hand_side == "Right")
                color = (0, 255, 255) if selected else (130, 130, 130)
                if min(landmarks[i].visibility for i in indices) < self.config.arm_visibility:
                    continue
                pixels = [(int(landmarks[i].x*w), int(landmarks[i].y*h)) for i in indices]
                for a,b in zip(pixels, pixels[1:]):
                    cv2.line(overlay, a, b, color, 4)
                for point, name in zip(pixels, ("shoulder", "elbow", "wrist")):
                    cv2.circle(overlay, point, 7, color, -1)
                    if selected:
                        cv2.putText(overlay, name, (point[0]+8, point[1]), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
        if hand:
            hand_pixels = [(int(p.x*w), int(p.y*h)) for p in hand.landmark]
            for a, b in HAND_EDGES:
                cv2.line(overlay, hand_pixels[a], hand_pixels[b], (60, 230, 120), 2)
            for point in hand_pixels:
                cv2.circle(overlay, point, 3, (0, 80, 255), -1)
        if sample.valid:
            text = f"{self.config.hand_side} ARM | pinch={sample.pinch_ratio:.2f} | C calibrate P pause"
        else:
            text = "SHOW FULL ARM AND HAND"
        cv2.putText(overlay, text, (12,h-16), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,255,255), 2)
        return sample, overlay
