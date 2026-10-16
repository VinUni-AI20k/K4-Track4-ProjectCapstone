"""Một tiếng bíp khi có sự kiện mới; phát nền, không chặn camera.

Chạy thử loa: python -m src.alarm
"""

from __future__ import annotations

import sys
import threading
import time


class AlarmSound:
    def __init__(self, *, enabled: bool = True, cooldown_s: float = 3.0) -> None:
        self.enabled = enabled
        self.cooldown_s = cooldown_s
        self.error: str | None = None
        self._last_play = float("-inf")
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._closed = False

    def play(self) -> bool:
        """Xếp một bíp nếu không bận và đã qua thời gian nghỉ; không đợi loa."""
        with self._lock:
            now = time.monotonic()
            if (not self.enabled or self._closed or self.error is not None
                    or now - self._last_play < self.cooldown_s
                    or (self._thread is not None and self._thread.is_alive())):
                return False
            self._last_play = now
            self._thread = threading.Thread(target=self._beep, daemon=True, name="alert-sound")
            self._thread.start()
            return True

    def _beep(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd

            sample_rate = 44100
            samples = np.arange(round(sample_rate * 0.3)) / sample_rate
            tone = (0.25 * np.sin(2 * np.pi * 880 * samples)).astype(np.float32)
            # Fade đầu/cuối để tránh tiếng click.
            fade = round(sample_rate * 0.015)
            tone[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
            tone[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
            sd.play(tone, samplerate=sample_rate, blocking=True)
        except Exception as exc:
            # Camera và cảnh báo đỏ tiếp tục chạy nếu không có loa/thiết bị âm thanh.
            self.error = str(exc)
            print(f"Không phát được âm báo: {exc}. Cảnh báo trên hình vẫn hoạt động.", file=sys.stderr)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            thread = self._thread
        if thread is not None:
            thread.join(timeout=1.0)


if __name__ == "__main__":
    alarm = AlarmSound()
    alarm.play()
    alarm.close()
    if alarm.error:
        raise SystemExit(1)
    print("Đã gửi tiếng bíp tới loa mặc định. Kiểm tra âm lượng và thiết bị đầu ra nếu chưa nghe thấy.")
