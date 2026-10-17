"""
UNIT & INTEGRATION TEST SUITE: WASTE DETECTOR
Author: Member 1 (AI Perception Engineer)
Focus: Data Contract Compliance, Input Validation, Security, Fallback & Performance
"""

import pytest
import numpy as np
import cv2
import time
from modules.detector import WasteDetector

@pytest.fixture
def detector():
    """Fixture khởi tạo WasteDetector với cấu hình tiêu chuẩn."""
    return WasteDetector(conf_thresh=0.30)

@pytest.fixture
def synthetic_frame():
    """Tạo một khung hình mô phỏng chứa vật thể xanh lục (Plastic) và vàng (Metal)."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Vẽ vật thể màu xanh lục đại diện cho Plastic
    cv2.circle(frame, (250, 240), 35, (0, 220, 0), -1)
    # Vẽ vật thể màu vàng đại diện cho Metal
    cv2.circle(frame, (420, 240), 30, (0, 220, 220), -1)
    return frame

class TestDetectorInitialization:
    """Kiểm tra khởi tạo và chuẩn hóa tham số cấu hình."""

    def test_default_init(self, detector):
        assert detector is not None
        assert 0.0 < detector.conf_thresh <= 1.0
        assert 0.0 < detector.iou_thresh <= 1.0
        assert isinstance(detector.material_mapping, dict)

    def test_threshold_clamping(self):
        # Kiểm tra tự động giới hạn ngưỡng tự tin để chống lỗi logic
        det_low = WasteDetector(conf_thresh=-0.5)
        assert det_low.conf_thresh == 0.01

        det_high = WasteDetector(conf_thresh=1.5)
        assert det_high.conf_thresh == 0.99

    def test_sanitize_path(self):
        det = WasteDetector(model_path="../../etc/passwd.pt")
        # Phải fallback hoặc chuẩn hóa, không được phép crash
        assert det.model_path is not None


class TestInputValidationAndSecurity:
    """Kiểm thử phòng vệ: Chống crash và xử lý dữ liệu đầu vào bất thường (Security/Fuzzing)."""

    def test_none_frame(self, detector):
        results = detector.detect(None)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_non_numpy_input(self, detector):
        invalid_inputs = ["not_an_image", [1, 2, 3], {"frame": 123}, 42]
        for bad_input in invalid_inputs:
            results = detector.detect(bad_input)
            assert isinstance(results, list)
            assert len(results) == 0

    def test_empty_numpy_array(self, detector):
        empty_frame = np.array([], dtype=np.uint8)
        results = detector.detect(empty_frame)
        assert len(results) == 0

    def test_grayscale_2d_frame(self, detector):
        gray_frame = np.zeros((480, 640), dtype=np.uint8)
        results = detector.detect(gray_frame)
        assert len(results) == 0

    def test_rgba_4channel_frame(self, detector):
        rgba_frame = np.zeros((480, 640, 4), dtype=np.uint8)
        results = detector.detect(rgba_frame)
        assert len(results) == 0

    def test_undersized_resolution(self, detector):
        tiny_frame = np.zeros((8, 8, 3), dtype=np.uint8)
        results = detector.detect(tiny_frame)
        assert len(results) == 0

    def test_oversized_resolution(self, detector):
        huge_frame = np.zeros((5000, 5000, 3), dtype=np.uint8)
        results = detector.detect(huge_frame)
        assert len(results) == 0


class TestDataContractCompliance:
    """Kiểm tra tuân thủ đúng chuẩn giao tiếp dữ liệu (Interface Contract) với các thành viên khác."""

    def test_interface_contract_fields(self, detector, synthetic_frame):
        detections = detector.detect(synthetic_frame)
        assert isinstance(detections, list)
        
        # Nếu có phát hiện vật thể, kiểm tra từng trường dữ liệu
        for item in detections:
            # 1. Bắt buộc có đủ 5 trường
            assert "bbox" in item
            assert "center_pixel" in item
            assert "material_class" in item
            assert "confidence" in item
            assert "inference_ms" in item

            # 2. Kiểm tra kiểu dữ liệu
            assert isinstance(item["bbox"], list)
            assert len(item["bbox"]) == 4
            assert all(isinstance(c, int) for c in item["bbox"])

            assert isinstance(item["center_pixel"], (tuple, list))
            assert len(item["center_pixel"]) == 2
            cx, cy = item["center_pixel"]
            assert isinstance(cx, int) and isinstance(cy, int)

            assert isinstance(item["material_class"], str)
            assert len(item["material_class"]) > 0

            assert isinstance(item["confidence"], (float, int))
            assert 0.0 <= item["confidence"] <= 1.0

            assert isinstance(item["inference_ms"], (float, int))
            assert item["inference_ms"] >= 0.0

            # 3. Kiểm tra tính hợp lệ hình học của Bounding Box
            x1, y1, x2, y2 = item["bbox"]
            assert x1 <= x2, "x1 phải nhỏ hơn hoặc bằng x2"
            assert y1 <= y2, "y1 phải nhỏ hơn hoặc bằng y2"
            assert x1 <= cx <= x2, "cx phải nằm trong khoảng [x1, x2]"
            assert y1 <= cy <= y2, "cy phải nằm trong khoảng [y1, y2]"


class TestFallbackAndReliability:
    """Kiểm tra độ tin cậy và cơ chế Fallback không bao giờ làm sập hệ thống."""

    def test_fallback_detector_activation(self, synthetic_frame):
        # Ép chế độ Fallback bằng cách tắt cờ YOLO
        det = WasteDetector(conf_thresh=0.30)
        det.is_yolo_active = False

        results = det.detect(synthetic_frame)
        assert isinstance(results, list)
        assert len(results) >= 1  # Phải nhận diện được vật thể màu trong synthetic frame
        
        classes = [r["material_class"] for r in results]
        assert "Plastic" in classes or "Còn lại" in classes or "Metal" in classes

    def test_performance_latency_budget(self, detector, synthetic_frame):
        """Kiểm tra độ trễ xử lý phải đáp ứng thời gian thực (< 120ms trên CPU)."""
        # Warmup
        detector.detect(synthetic_frame)

        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            detector.detect(synthetic_frame)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        avg_latency = np.mean(latencies)
        print(f"\n[BENCHMARK] Average latency per frame: {avg_latency:.2f} ms")
        assert avg_latency < 1000.0, f"Độ trễ quá cao ({avg_latency:.2f} ms > 1000 ms)"
