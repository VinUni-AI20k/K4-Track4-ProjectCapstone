"""Dữ liệu GIẢ để phát triển overlay/logger, không phải bằng chứng đánh giá.

Chạy tại gốc repo: python -m scripts.mock_results
"""

from dataclasses import asdict
import json

from src.contracts import DriverState, EyeObservation, FrameResult, StateDecision


def mock_results() -> list[FrameResult]:
    """Trả một chuỗi mẫu có đủ trạng thái, không mô phỏng model thực."""
    samples = [
        (0.0, 0.30, DriverState.CALIBRATING, 0.0, False),
        (0.5, 0.30, DriverState.OPEN, 0.0, False),
        (1.0, 0.10, DriverState.CLOSING, 0.0, False),
        (2.5, 0.10, DriverState.ALERT, 1.5, True),
        (2.6, 0.10, DriverState.ALERT, 1.6, False),
        (2.7, None, DriverState.UNKNOWN, 0.0, False),
        (3.0, 0.30, DriverState.OPEN, 0.0, False),
    ]
    results = []
    for frame_id, (timestamp, ear, state, duration, event) in enumerate(samples):
        calibrated = state != DriverState.CALIBRATING
        results.append(FrameResult(
            frame_id=frame_id,
            timestamp_s=timestamp,
            observation=EyeObservation(
                valid=ear is not None, ear_left=ear, ear_right=ear, ear=ear,
                eye_points=((100.0, 100.0), (120.0, 100.0)) if ear is not None else (),
            ),
            decision=StateDecision(
                state=state, closed_duration_s=duration,
                close_threshold=0.20 if calibrated else None,
                open_threshold=0.23 if calibrated else None,
                alert_event=event,
            ),
            processing_ms=10.0,
        ))
    return results


if __name__ == "__main__":
    print("DỮ LIỆU GIẢ — chỉ dùng phát triển, không dùng báo cáo kết quả.")
    for result in mock_results():
        print(json.dumps(asdict(result), ensure_ascii=False))
