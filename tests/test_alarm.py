"""Kiểm tra tiếng bíp không mở loa thật trong bộ test."""

import threading
import unittest
from unittest.mock import patch

from src.alarm import AlarmSound


class AlarmTests(unittest.TestCase):
    def test_disabled_alarm_never_starts_audio(self):
        alarm = AlarmSound(enabled=False)
        with patch.object(alarm, "_beep") as beep:
            self.assertFalse(alarm.play())
            alarm.close()
            beep.assert_not_called()

    def test_play_returns_while_worker_busy_and_does_not_queue_duplicates(self):
        alarm = AlarmSound(cooldown_s=0)
        entered = threading.Event()
        release = threading.Event()
        def beep():
            entered.set()
            release.wait(timeout=2)
        with patch.object(alarm, "_beep", side_effect=beep):
            try:
                self.assertTrue(alarm.play())
                self.assertTrue(entered.wait(timeout=1))
                self.assertFalse(alarm.play())
            finally:
                release.set()
                alarm.close()

    def test_cooldown_and_close_suppress_repeated_sounds(self):
        alarm = AlarmSound(cooldown_s=3)
        with patch.object(alarm, "_beep") as beep, patch("src.alarm.time.monotonic", side_effect=[10, 11, 14, 20]):
            self.assertTrue(alarm.play())
            alarm._thread.join(timeout=1)
            self.assertFalse(alarm.play())
            self.assertTrue(alarm.play())
            alarm.close()
            self.assertFalse(alarm.play())
            self.assertEqual(beep.call_count, 2)

    def test_audio_failure_does_not_escape_worker(self):
        import sys
        from unittest.mock import MagicMock
        import io
        from contextlib import redirect_stderr
        sd = MagicMock()
        sd.play.side_effect = RuntimeError("No output device")
        alarm = AlarmSound()
        with patch.dict(sys.modules, {"sounddevice": sd}), redirect_stderr(io.StringIO()):
            alarm.play()
            alarm.close()
        self.assertIn("No output device", alarm.error)
        self.assertFalse(alarm.play())


if __name__ == "__main__":
    unittest.main()
