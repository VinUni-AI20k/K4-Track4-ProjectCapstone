"""Hiệu chỉnh cá nhân, hysteresis và cảnh báo theo thời gian quan sát.

Không phụ thuộc camera, MediaPipe hoặc tốc độ phát video.
"""

from __future__ import annotations

import math
from statistics import median

from src.contracts import DriverState, EyeObservation, StateDecision


class DriverStateMachine:
    def __init__(
        self, *, alert_after_s: float = 1.5, calibration_samples: int = 60,
        close_ratio: float = 0.65, open_ratio: float = 0.75,
        max_gap_s: float = 0.5,
    ) -> None:
        if not math.isfinite(alert_after_s) or alert_after_s < 0:
            raise ValueError("alert_after_s phải hữu hạn và >= 0")
        if isinstance(calibration_samples, bool) or not isinstance(calibration_samples, int) or calibration_samples < 1:
            raise ValueError("calibration_samples phải là số nguyên >= 1")
        if not (0 < close_ratio < open_ratio < 1):
            raise ValueError("Cần 0 < close_ratio < open_ratio < 1")
        if not math.isfinite(max_gap_s) or max_gap_s <= 0:
            raise ValueError("max_gap_s phải hữu hạn và > 0")
        self.alert_after_s = alert_after_s
        self.calibration_samples = calibration_samples
        self.close_ratio = close_ratio
        self.open_ratio = open_ratio
        self.max_gap_s = max_gap_s
        self.reset()

    def reset(self) -> None:
        self._samples: list[float] = []
        self._reference: float | None = None
        self._last_time: float | None = None
        self._closed_since: float | None = None
        self._alerted = False

    @property
    def calibration_count(self) -> int:
        return len(self._samples)

    @property
    def reference_ear(self) -> float | None:
        return self._reference

    def _clear_closure(self) -> None:
        self._closed_since = None
        self._alerted = False

    def _decision(self, state: DriverState, duration: float = 0.0,
                  event: bool = False) -> StateDecision:
        reference = self._reference
        return StateDecision(
            state=state, closed_duration_s=duration,
            close_threshold=None if reference is None else reference * self.close_ratio,
            open_threshold=None if reference is None else reference * self.open_ratio,
            alert_event=event,
        )

    def update(self, observation: EyeObservation, timestamp_s: float) -> StateDecision:
        if not math.isfinite(timestamp_s) or timestamp_s < 0:
            raise ValueError("timestamp_s phải hữu hạn và >= 0")
        if self._last_time is not None and timestamp_s <= self._last_time:
            raise ValueError("timestamp_s phải tăng nghiêm ngặt; reset khi đổi nguồn")
        gap = self._last_time is not None and timestamp_s - self._last_time > self.max_gap_s
        self._last_time = timestamp_s
        ears = (observation.ear_left, observation.ear_right, observation.ear)
        valid = observation.valid and all(
            value is not None and math.isfinite(value) and value >= 0 for value in ears
        )
        if gap or not valid:
            self._clear_closure()
            if self._reference is None:
                self._samples.clear()
            return self._decision(DriverState.UNKNOWN)

        ear = observation.ear
        assert ear is not None
        if self._reference is None:
            # Mẫu mắt đóng hoàn toàn không thể làm tham chiếu mắt mở.
            if ear <= 0:
                self._samples.clear()
                return self._decision(DriverState.CALIBRATING)
            self._samples.append(ear)
            if len(self._samples) < self.calibration_samples:
                return self._decision(DriverState.CALIBRATING)
            self._reference = median(self._samples)
            # Mẫu cuối của hiệu chỉnh chưa được dùng để phát cảnh báo.
            return self._decision(DriverState.OPEN)

        close_threshold = self._reference * self.close_ratio
        open_threshold = self._reference * self.open_ratio
        if self._closed_since is None:
            if ear >= close_threshold:
                return self._decision(DriverState.OPEN)
            self._closed_since = timestamp_s
        elif ear >= open_threshold:
            self._clear_closure()
            return self._decision(DriverState.OPEN)

        duration = timestamp_s - self._closed_since
        if duration + 1e-9 < self.alert_after_s:
            return self._decision(DriverState.CLOSING, duration)
        new_event = not self._alerted
        self._alerted = True
        return self._decision(DriverState.ALERT, duration, new_event)
