"""Hợp đồng chung đã chốt; không phụ thuộc OpenCV hoặc MediaPipe.

Hai nhánh import từ đây, không tạo bản sao riêng của các kiểu dữ liệu.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DriverState(str, Enum):
    CALIBRATING = "CALIBRATING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    ALERT = "ALERT"
    UNKNOWN = "UNKNOWN"


# Tọa độ pixel (x, y), gốc ở góc trên trái của khung hình gốc.
Point = tuple[float, float]


@dataclass(frozen=True)
class EyeObservation:
    """Đầu ra detector. Mất mặt/nhiều mặt/mốc lỗi: valid=False, EAR=None.

eye_points chứa các mốc quanh hai mắt để overlay; không phải toàn bộ mặt.
Nếu valid=True, cả ba EAR phải có giá trị hữu hạn; không hợp lệ trả tuple rỗng.
"""

    valid: bool = False
    ear_left: float | None = None
    ear_right: float | None = None
    ear: float | None = None
    eye_points: tuple[Point, ...] = ()


@dataclass(frozen=True)
class StateDecision:
    """Đầu ra bộ trạng thái, không chứa logic vẽ hoặc ghi log.

CALIBRATING và UNKNOWN có thể chưa có ngưỡng. alert_event chỉ True
trên mẫu đầu tiên phát cảnh báo của một chuỗi mắt đóng.
"""

    state: DriverState
    closed_duration_s: float = 0.0
    close_threshold: float | None = None
    open_threshold: float | None = None
    alert_event: bool = False


@dataclass(frozen=True)
class FrameResult:
    """Quý ghép kết quả; Tuyên dùng cùng đối tượng cho overlay và CSV.

timestamp_s: giây tương đối từ đầu lượt chạy, tăng dần.
processing_ms: thời gian xử lý phần mềm trước overlay/logger.
"""

    frame_id: int
    timestamp_s: float
    observation: EyeObservation
    decision: StateDecision
    processing_ms: float


CSV_FIELDS = (
    "frame_id", "timestamp_s", "ear_left", "ear_right", "ear", "valid",
    "state", "closed_duration_s", "alert_event", "processing_ms",
)
