import math
import os
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dms.evaluation import GT_NONE, Protocol, replay, score
from dms.features import (LEFT_EYE, POSE_IDX, POSE_MODEL, Observation, camera_matrix,
                          eye_aspect_ratio, head_pose)
from dms.monitor import DISTRACTED, MICROSLEEP, NO_FACE, OK, UNCERTAIN, Config, Monitor

FPS = 30.0
OPEN, SHUT = 0.30, 0.08


def obs(ear=OPEN, yaw=0.0, pitch=0.0, mar=0.1):
    return Observation(ear, ear, ear, mar, yaw, pitch)


def calibrated_monitor(cfg=None):
    mon = Monitor(cfg or Config())
    t = 0.0
    while not mon.calibrated:
        mon.update(t, obs())
        t += 1 / FPS
    return mon, t


def run(mon, t, seconds, o):
    rep = None
    for _ in range(int(round(seconds * FPS))):
        rep = mon.update(t, o)
        t += 1 / FPS
    return rep, t


class Features(unittest.TestCase):
    def test_ear_of_known_eye(self):
        pts = np.zeros((478, 2))
        # corners 10 apart, lids 3 apart -> EAR = (3 + 3) / (2 * 10)
        for i, p in zip(LEFT_EYE, [(0, 0), (3, -1.5), (7, -1.5), (10, 0), (7, 1.5), (3, 1.5)]):
            pts[i] = p
        self.assertAlmostEqual(eye_aspect_ratio(pts, LEFT_EYE), 0.3)

    def test_head_pose_recovers_relative_yaw(self):
        w, h = 960, 540
        K = camera_matrix(w, h)

        def project(yaw_deg, pitch_deg=0.0):
            # facing the camera (model y up -> image y down), then turned about the neck
            flip, _ = cv2.Rodrigues(np.array([math.pi, 0.0, 0.0]))
            turn, _ = cv2.Rodrigues(np.array([0.0, math.radians(yaw_deg), 0.0]))
            nod, _ = cv2.Rodrigues(np.array([math.radians(pitch_deg), 0.0, 0.0]))
            rvec, _ = cv2.Rodrigues(flip @ turn @ nod)
            img, _ = cv2.projectPoints(POSE_MODEL, rvec, np.array([0.0, 0.0, 1500.0]), K, np.zeros(4))
            pts = np.zeros((478, 2))
            for i, p in zip(POSE_IDX, img.reshape(-1, 2)):
                pts[i] = p
            return head_pose(pts, w, h)

        for yaw, pitch in [(0, 0), (30, 0), (-30, 0), (0, 20), (0, -20), (25, 15), (-25, -15)]:
            got_yaw, got_pitch = project(yaw, pitch)
            self.assertAlmostEqual(got_yaw, yaw, delta=1, msg=(yaw, pitch))
            self.assertAlmostEqual(got_pitch, pitch, delta=1, msg=(yaw, pitch))


class DriverSelection(unittest.TestCase):
    def test_largest_face_is_the_driver(self):
        from types import SimpleNamespace as P

        def face(cx, cy, r):
            return [P(x=cx + dx * r, y=cy + dy * r) for dx, dy in ((-1, -1), (1, 1), (0, 0))]
        faces = [face(0.7, 0.4, 0.05), face(0.2, 0.5, 0.2), face(0.5, 0.3, 0.08)]
        from dms.features import pick_driver
        self.assertEqual(pick_driver(faces, 640, 480), 1)

    def test_frames_are_scaled_without_stretching(self):
        from run_dms import fit
        out = fit(np.zeros((480, 640, 3), np.uint8), 960, 540)  # 4:3 webcam into a 16:9 box
        self.assertEqual(out.shape[:2], (540, 720))
        out = fit(np.zeros((1080, 1920, 3), np.uint8), 960, 540)
        self.assertEqual(out.shape[:2], (540, 960))


class MonitorLogic(unittest.TestCase):
    def test_calibration_sets_per_driver_threshold(self):
        mon, _ = calibrated_monitor()
        self.assertAlmostEqual(mon.ear0, OPEN)
        self.assertAlmostEqual(mon.close_thr, 0.7 * OPEN)

    def test_blink_is_not_microsleep(self):
        mon, t = calibrated_monitor()
        _, t = run(mon, t, 0.2, obs(SHUT))
        rep, t = run(mon, t, 1.0, obs())
        self.assertEqual(rep["blinks_per_min"], 1)
        self.assertNotIn(MICROSLEEP, [e.kind for e in mon.events])

    def test_long_closure_raises_microsleep_after_threshold(self):
        mon, t = calibrated_monitor()
        start = t
        rep, t = run(mon, t, 1.5, obs(SHUT))
        self.assertIn(MICROSLEEP, rep["alerts"])
        ev = mon.events[0]
        self.assertAlmostEqual(ev.alarm - start, 1.0, delta=1.5 / FPS)
        rep, t = run(mon, t, 0.2, obs())
        self.assertNotIn(MICROSLEEP, rep["alerts"])

    def test_hysteresis_ignores_flicker_near_threshold(self):
        mon, t = calibrated_monitor()
        # dips just under the close threshold, recovers only to between thresholds
        for i in range(60):
            mon.update(t, obs(0.20 if i % 2 else 0.225))
            t += 1 / FPS
        self.assertTrue(mon.closed)  # stayed closed: 0.225 < open threshold 0.24

    def test_turned_head_is_uncertain_not_asleep(self):
        mon, t = calibrated_monitor()
        rep, t = run(mon, t, 1.0, obs(SHUT, yaw=40))
        self.assertEqual(rep["state"], UNCERTAIN)
        self.assertNotIn(MICROSLEEP, rep["alerts"])
        rep, t = run(mon, t, 1.5, obs(SHUT, yaw=40))
        self.assertIn(DISTRACTED, rep["alerts"])
        rep, t = run(mon, t, 0.1, obs())
        self.assertEqual(rep["state"], OK)
        self.assertEqual(rep["alerts"], [])

    def test_missing_face(self):
        mon, t = calibrated_monitor()
        rep, t = run(mon, t, 2.5, None)
        self.assertIn(NO_FACE, rep["alerts"])

    def test_perclos_needs_coverage(self):
        mon, t = calibrated_monitor()
        rep, t = run(mon, t, 5.0, obs(SHUT))
        self.assertGreater(rep["perclos"], 0.9)
        self.assertNotIn("PERCLOS_HIGH", rep["alerts"])  # only 5 s of a 30 s window seen
        rep, t = run(mon, t, 12.0, obs(SHUT))
        self.assertIn("PERCLOS_HIGH", rep["alerts"])

    def test_perclos_alert_clears_when_face_is_lost(self):
        mon, t = calibrated_monitor()
        rep, t = run(mon, t, 20.0, obs(SHUT))
        self.assertIn("PERCLOS_HIGH", rep["alerts"])
        rep, t = run(mon, t, 20.0, None)  # camera sees no face; old samples must age out
        self.assertNotIn("PERCLOS_HIGH", rep["alerts"])
        self.assertLess(rep["perclos_coverage"], 0.5)


class ProtocolScoring(unittest.TestCase):
    def synthetic_log(self, reaction=0.3, false_closure_at=None):
        proto = Protocol(trials=4)
        rows, t = [], 0.0
        calib_until = 6.0
        while t < calib_until + proto.duration:
            el = t - calib_until
            gt = proto.gt_at(el) if el >= 0 else GT_NONE
            # the actor closes `reaction` s after the cue and opens `reaction` s after the end cue
            shut = el >= 0 and proto.gt_at(el - reaction) == 1
            if false_closure_at is not None and false_closure_at <= t < false_closure_at + 1.5:
                shut = True
            ear = SHUT if shut else OPEN
            rows.append({"t": t, "face": True, "ear": ear, "ear_l": ear, "ear_r": ear, "mar": 0.1,
                         "yaw": 0.0, "pitch": 0.0, "proc_ms": 10.0, "gt": gt, "recalib": False})
            t += 1 / FPS
        return rows

    def test_perfect_actor_scores_full_recall(self):
        rows = self.synthetic_log()
        mon, reps = replay(rows)
        s = score(rows, mon, reps)
        self.assertEqual((s["hits"], s["trials"], s["false_alarms"]), (4, 4, 0))
        self.assertAlmostEqual(s["latency_mean_s"], 1.3, delta=0.1)  # reaction + 1.0 s rule
        self.assertAlmostEqual(s["frame_accuracy"], 1.0)

    def test_closure_outside_cue_is_false_alarm(self):
        rows = self.synthetic_log(false_closure_at=8.0)
        mon, reps = replay(rows)
        s = score(rows, mon, reps)
        self.assertEqual(s["false_alarms"], 1)


if __name__ == "__main__":
    unittest.main()
