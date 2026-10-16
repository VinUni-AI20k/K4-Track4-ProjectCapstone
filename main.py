"""Single-owner integration loop. Real vision/simulation modules are supplied by TV2/TV3."""

import argparse
from dataclasses import asdict
import importlib
import time

from config import Config, DEFAULT_CONFIG
from contracts import Event, RobotCommand, SimStatus
from control import Controller


def initial_status(simulation, result, config):
    if isinstance(result, SimStatus):
        return result
    return simulation.step(RobotCommand(config.home_xyz, False), 0.0)


def run(vision, simulation, metrics=None, config: Config = DEFAULT_CONFIG,
        duration_s=None, show_overlay=True, clock=time.monotonic, sleep=time.sleep):
    """Integrate injected modules; all simulation calls occur on this thread.

    Factories: Vision(config), Simulation(config), optional Metrics(config).
    initialize/reset may return SimStatus or None; step MUST return SimStatus.
    Optional vision.latest_overlay() returns a BGR image. Optional poll_key()
    returns p/r/c/q (pause/reset/confirm resume/quit), including in headless mode.
    Event payloads passed to metrics.record_event are plain JSON-safe dicts.
    Trial lifecycle/TrialRecord persistence remain the responsibility of TV4.
    """
    controller = Controller(config)
    cv2 = None

    def emit(event):
        if metrics is not None:
            metrics.record_event(asdict(event))

    try:
        status = initial_status(simulation, simulation.initialize(), config)
        vision.start()
        started = clock()
        previous = started
        emit(Event(clock(), "session_started"))
        while duration_s is None or clock() - started < duration_s:
            tick = clock()
            # Cap after stalls: never let a delayed GUI advance a large physics step.
            dt = min(config.max_control_dt, max(0.0, tick - previous))
            previous = tick
            key = vision.poll_key() if hasattr(vision, "poll_key") else None
            if show_overlay and hasattr(vision, "latest_overlay"):
                frame = vision.latest_overlay()
                if frame is not None:
                    if cv2 is None:
                        cv2 = importlib.import_module("cv2")
                    frame = frame.copy()
                    cv2.putText(frame, f"{controller.state.value}: {controller.message}",
                                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
                    cv2.putText(frame, f"candidate={status.candidate_box_id} held={status.held_box_id} "
                                f"placed={len(status.placed_box_ids)} | P pause C resume R reset Q quit",
                                (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                    cv2.imshow("Gesture robot", frame)
                    pressed = cv2.waitKey(1) & 0xFF
                    if pressed != 255:
                        key = chr(pressed).lower()
            if key in ("q", "\x1b"):
                break
            if key == "r":
                status = initial_status(simulation, simulation.reset(), config)
                controller.reset()
                emit(Event(tick, "reset", controller_state=controller.state.value))
            elif key == "p":
                controller.pause(status, tick)
            elif key == "c":
                controller.request_resume()
            sample = vision.latest_sample()
            # Read now AFTER the asynchronous producer's sample to avoid treating
            # a just-completed camera callback as a timestamp from the future.
            command = controller.update(sample, status, clock())
            status = simulation.step(command, dt)
            # The simulator moves in step; attachment is attempted after that step.
            # Its result is observed in the next SimStatus, never inferred from bool.
            if command.action.value == "ATTACH":
                simulation.try_attach(command.box_id)
            elif command.action.value == "RELEASE":
                simulation.release()
            for event in controller.drain_events():
                emit(event)
            remaining = 1.0 / config.loop_hz - (clock() - tick)
            if remaining > 0:
                sleep(remaining)
        emit(Event(clock(), "session_ended", controller_state=controller.state.value))
        return status
    finally:
        # All resources get a cleanup attempt even if one close raises.
        try:
            vision.close()
        finally:
            try:
                simulation.close()
            finally:
                try:
                    if metrics is not None and hasattr(metrics, "close"):
                        metrics.close()
                finally:
                    if cv2 is not None:
                        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vision-module", default="vision")
    parser.add_argument("--simulation-module", default="simulation")
    parser.add_argument("--metrics-module", help="Optional module exporting Metrics(config)")
    parser.add_argument("--duration", type=float, help="Stop after N seconds")
    parser.add_argument("--no-overlay", action="store_true")
    args = parser.parse_args()
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration must be positive")
    try:
        vision_cls = getattr(importlib.import_module(args.vision_module), "Vision")
        sim_cls = getattr(importlib.import_module(args.simulation_module), "Simulation")
        metrics_cls = (getattr(importlib.import_module(args.metrics_module), "Metrics")
                       if args.metrics_module else None)
    except (ImportError, AttributeError) as exc:
        parser.exit(2, f"Integration module unavailable: {exc}\n"
                    "TV2/TV3 must supply Vision(config)/Simulation(config). "
                    "Run python -m dev.run_control for the independent TV1 demo.\n")
    try:
        run(vision_cls(DEFAULT_CONFIG), sim_cls(DEFAULT_CONFIG),
            metrics_cls(DEFAULT_CONFIG) if metrics_cls else None,
            duration_s=args.duration, show_overlay=not args.no_overlay)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
