"""MediaPipe Tasks Face Landmarker → mốc mắt pixel → EAR.

IMAGE mode giữ đúng API detect(frame), không cần timestamp MediaPipe.
num_faces=2 để từ chối khung hình có nhiều người; không nhận dạng danh tính.
"""

from __future__ import annotations

import math
from pathlib import Path

from src.contracts import EyeObservation, Point


# Sáu điểm theo vòng mắt: hai khóe, hai cặp mí trên/dưới.
LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_EYE = (33, 160, 158, 133, 153, 144)


def eye_aspect_ratio(points: tuple[Point, ...]) -> float | None:
    """EAR bất biến với tịnh tiến, scale đồng đều và xoay trong mặt phẳng.

Điểm phải có cùng đơn vị pixel; không dùng trực tiếp x/y chuẩn hóa trên ảnh
khác tỉ lệ. Chiều rộng dưới 3 pixel bị loại vì không đủ phân giải.
"""
    if len(points) != 6 or not all(math.isfinite(v) for point in points for v in point):
        return None
    width = math.dist(points[0], points[3])
    if width < 3.0:
        return None
    return (math.dist(points[1], points[5]) + math.dist(points[2], points[4])) / (2 * width)


def observation_from_landmarks(faces, width: int, height: int) -> EyeObservation:
    """Chuyển đầu ra Tasks; tách khỏi inference để kiểm thử hình học."""
    if len(faces) != 1 or width <= 0 or height <= 0:
        return EyeObservation()
    landmarks = faces[0]
    if len(landmarks) <= max(LEFT_EYE + RIGHT_EYE):
        return EyeObservation()
    points = []
    for index in LEFT_EYE + RIGHT_EYE:
        landmark = landmarks[index]
        if not (math.isfinite(landmark.x) and math.isfinite(landmark.y)
                and 0 <= landmark.x < 1 and 0 <= landmark.y < 1):
            return EyeObservation()
        points.append((landmark.x * width, landmark.y * height))
    left = eye_aspect_ratio(tuple(points[:6]))
    right = eye_aspect_ratio(tuple(points[6:]))
    if left is None or right is None:
        return EyeObservation()
    return EyeObservation(
        valid=True, ear_left=left, ear_right=right,
        ear=(left + right) / 2, eye_points=tuple(points),
    )


class EyeDetector:
    def __init__(self, model_path: str) -> None:
        if not Path(model_path).is_file():
            raise FileNotFoundError(
                f"Không thấy model: {model_path}. Chạy python -m scripts.download_model"
            )
        import cv2
        import mediapipe as mp
        import numpy as np

        self._cv2, self._mp, self._np = cv2, mp, np
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(
                model_asset_path=str(model_path), delegate=mp.tasks.BaseOptions.Delegate.CPU,
            ),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=2,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def detect(self, frame) -> EyeObservation:
        if self._landmarker is None:
            raise RuntimeError("Detector đã đóng")
        if (not isinstance(frame, self._np.ndarray) or frame.dtype != self._np.uint8
                or frame.ndim != 3 or frame.shape[2] != 3 or frame.size == 0):
            raise ValueError("frame phải là ảnh BGR uint8 có 3 kênh")
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(image)
        return observation_from_landmarks(result.face_landmarks, frame.shape[1], frame.shape[0])

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
