import unittest
from dataclasses import replace
from math import dist

from config import DEFAULT_CONFIG as C
from contracts import Action, ControllerState as State, HandSample, RobotCommand, SimStatus
from control import Controller
from dev.run_control import Harness, LocalSimulation
from main import run


class ControlTests(unittest.TestCase):
    def test_complete_cycle_once_and_rate_limit(self):
        h = Harness()
        h.pick()
        self.assertEqual(h.sim.held, "green")
        h.place()
        self.assertEqual(h.sim.placed, {"green"})
        self.assertEqual(h.sim.attach_calls, 1)
        self.assertEqual(h.sim.release_calls, 1)
        self.assertTrue(all(not command.gripper_closed for command in h.commands
                            if command.action == Action.RELEASE))
        self.assertEqual(sum(e.event_type == "placed" for e in h.events), 1)
        for a, b in zip(h.commands, h.commands[1:]):
            self.assertLessEqual(dist(a.target_xyz, b.target_xyz), C.max_speed / 60 + 1e-9)

    def test_startup_closed_hand_cannot_pick(self):
        h = Harness()
        h.frames(180, v=0.752, ratio=0.1)
        self.assertEqual(h.sim.attach_calls, 0)
        self.assertEqual(h.controller.state, State.READY)

    def test_short_pinch_and_middle_band_do_not_trigger_pick(self):
        h = Harness()
        h.frames(120, v=0.752)
        for _ in range(20):
            h.frames(4, v=0.752, ratio=0.1)
            h.frames(4, v=0.752, ratio=0.4)
        self.assertEqual(h.sim.attach_calls, 0)
        self.assertEqual(h.controller.state, State.READY)

    def test_no_candidate_does_not_attach(self):
        h = Harness()
        h.frames(100)
        h.frames(100, ratio=0.1)
        self.assertEqual(h.sim.attach_calls, 0)
        self.assertTrue(any(e.event_type == "pick_rejected" for e in h.events))

    def test_attach_failure_recovers_and_requires_new_gesture(self):
        h = Harness(attach_ok=False)
        h.pick()
        h.frames(180, v=0.752, ratio=0.1)
        self.assertEqual(h.sim.attach_calls, 1)
        self.assertIsNone(h.sim.held)
        self.assertEqual(h.controller.state, State.READY)
        self.assertAlmostEqual(h.sim.xyz[2], C.transport_z)
        self.assertTrue(any(e.event_type == "pick_failed" for e in h.events))

    def test_open_outside_bin_keeps_box(self):
        h = Harness()
        h.pick()
        h.frames(100, v=0.752, ratio=0.8)
        self.assertEqual(h.sim.held, "green")
        self.assertEqual(h.sim.release_calls, 0)
        self.assertTrue(any(e.event_type == "place_rejected" for e in h.events))

    def test_tracking_loss_holds_actual_pose_and_resume_is_explicit(self):
        h = Harness()
        h.pick()
        actual = (0.49, -0.17, 0.30)
        h.sim.xyz = actual
        command = h.tick(valid=False)
        self.assertEqual(command.target_xyz, actual)
        self.assertTrue(command.gripper_closed)
        h.frames(60, v=0.248)
        self.assertEqual(h.controller.state, State.PAUSED)
        self.assertEqual(h.sim.xyz, actual)
        self.assertEqual(h.sim.held, "green")
        h.controller.request_resume()
        h.tick(v=0.248)
        self.assertEqual(h.controller.state, State.LIFTING)
        self.assertEqual(h.sim.xyz[:2], actual[:2])
        h.frames(120, v=0.248)
        self.assertEqual(h.controller.state, State.CARRYING)
        self.assertEqual(h.sim.release_calls, 0)

    def test_resume_closed_hand_stays_paused(self):
        h = Harness()
        h.tick(valid=False)
        h.controller.request_resume()
        h.frames(100, ratio=0.1)
        self.assertEqual(h.controller.state, State.PAUSED)

    def test_cached_and_stale_samples_do_not_arm(self):
        controller = Controller()
        status = SimStatus(C.home_xyz, True, "green")
        sample = HandSample(1, 0, 0, True)
        for now in (0, 0.1, 0.2):
            controller.update(sample, status, now)
        self.assertFalse(controller._armed)
        command = controller.update(sample, status, 0.3)
        self.assertEqual(controller.state, State.PAUSED)
        self.assertEqual(command.action, Action.NONE)

    def test_bad_samples_pause(self):
        status = SimStatus(C.home_xyz, True)
        sample = HandSample(1, 1, 1, True)
        for bad in (None, replace(sample, u=float("nan")), replace(sample, v=2),
                    replace(sample, pinch_ratio=-1), replace(sample, processed_at=2),
                    replace(sample, captured_at=2), replace(sample, valid=False)):
            controller = Controller()
            controller.update(bad, status, 1)
            self.assertEqual(controller.state, State.PAUSED)

    def test_mapping_direction_and_bounds(self):
        h = Harness()
        h.frames(180, u=0, v=0)
        self.assertAlmostEqual(h.sim.xyz[0], C.workspace_x[0], places=5)
        self.assertAlmostEqual(h.sim.xyz[1], C.workspace_y[1], places=5)
        h.frames(180, u=1, v=1)
        self.assertAlmostEqual(h.sim.xyz[0], C.workspace_x[1], places=5)
        self.assertAlmostEqual(h.sim.xyz[1], C.workspace_y[0], places=5)

    def test_setpoint_alone_does_not_confirm_motion_or_attach(self):
        h = Harness()
        h.frames(120, v=0.752)
        # Freeze physical feedback above the box while commands keep advancing.
        frozen = h.sim.status()
        for _ in range(150):
            h.now += 1 / 60
            h.frame += 1
            sample = HandSample(h.frame, h.now, h.now, True, 0.5, 0.752, 0.1)
            command = h.controller.update(sample, frozen, h.now)
            self.assertEqual(command.action, Action.NONE)
        self.assertEqual(h.controller.state, State.LOWERING_PICK)

    def test_no_feedback_cannot_confirm_pick(self):
        h = Harness(attach_ok=False)
        h.pick()
        self.assertFalse(any(e.event_type == "picked" for e in h.events))

    def test_failed_placement_is_not_counted(self):
        h = Harness(placement_ok=False)
        h.pick()
        h.place()
        self.assertEqual(h.sim.placed, set())
        self.assertFalse(any(e.event_type == "placed" for e in h.events))
        self.assertTrue(any(e.event_type == "place_failed" for e in h.events))

    def test_reset_mid_cycle_clears_hold_and_gesture(self):
        h = Harness()
        h.pick()
        h.sim.reset()
        h.controller.reset()
        h.frames(180, v=0.752, ratio=0.1)
        self.assertIsNone(h.sim.held)
        self.assertEqual(h.sim.placed, set())
        self.assertEqual(h.controller.state, State.READY)
        self.assertEqual(h.sim.attach_calls, 1)

    def test_motion_timeout(self):
        h = Harness()
        h.frames(120, v=0.752)
        status = h.sim.status()
        for _ in range(600):
            h.now += 1 / 60
            h.frame += 1
            h.controller.update(HandSample(h.frame, h.now, h.now, True, 0.5, 0.752, 0.1), status, h.now)
        self.assertEqual(h.controller.state, State.PAUSED)


class LoopTests(unittest.TestCase):
    def test_complete_cycle_through_main_loop(self):
        class Clock:
            now = 0.0
            def __call__(self):
                return self.now
            def sleep(self, duration):
                self.now += duration

        clock = Clock()

        class Vision:
            frame = 0
            def start(self):
                pass
            def latest_sample(self):
                self.frame += 1
                return HandSample(self.frame, clock.now, clock.now, True, 0.5,
                                  0.752 if clock.now < 5 else 0.248,
                                  0.8 if clock.now < 2 or clock.now >= 8 else 0.1)
            def close(self):
                pass

        class Metrics:
            def __init__(self):
                self.events = []
            def record_event(self, event):
                self.events.append(event)

        sim, metrics = LocalSimulation(), Metrics()
        result = run(Vision(), sim, metrics, duration_s=12, show_overlay=False,
                     clock=clock, sleep=clock.sleep)
        self.assertEqual(result.placed_box_ids, frozenset({"green"}))
        self.assertEqual(sim.attach_calls, 1)
        self.assertEqual(sim.release_calls, 1)
        self.assertEqual(sum(e["event_type"] == "picked" for e in metrics.events), 1)
        self.assertEqual(sum(e["event_type"] == "placed" for e in metrics.events), 1)

    def test_injected_loop_reset_pause_resume_and_cleanup(self):
        class Clock:
            now = 0.0
            def __call__(self):
                return self.now
            def sleep(self, duration):
                self.now += duration

        clock = Clock()

        class Vision:
            closed = False
            frame = 0
            def start(self):
                pass
            def latest_sample(self):
                self.frame += 1
                return HandSample(self.frame, clock.now, clock.now, True)
            def poll_key(self):
                return {5: "p", 40: "c", 70: "r", 100: "q"}.get(self.frame)
            def close(self):
                self.closed = True

        class Metrics:
            def __init__(self):
                self.events = []
            def record_event(self, event):
                self.events.append(event)

        vision, sim, metrics = Vision(), LocalSimulation(), Metrics()
        run(vision, sim, metrics, clock=clock, sleep=clock.sleep, show_overlay=False)
        self.assertTrue(vision.closed and sim.closed)
        self.assertEqual(sum(e["event_type"] == "reset" for e in metrics.events), 1)
        self.assertTrue(any(e["event_type"] == "paused" for e in metrics.events))
        self.assertEqual(metrics.events[-1]["event_type"], "session_ended")

    def test_cleanup_on_vision_failure(self):
        class Vision:
            closed = False
            def start(self):
                raise RuntimeError("camera unavailable")
            def close(self):
                self.closed = True
        vision, sim = Vision(), LocalSimulation()
        with self.assertRaisesRegex(RuntimeError, "camera unavailable"):
            run(vision, sim, show_overlay=False)
        self.assertTrue(vision.closed and sim.closed)


if __name__ == "__main__":
    unittest.main()
