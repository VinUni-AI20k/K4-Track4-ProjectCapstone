"""Webcam -> hand landmarks -> controller -> PyBullet, with optional Three.js mirror."""

import argparse
from dataclasses import asdict, replace
import importlib
import time
import webbrowser

from config import Config, DEFAULT_CONFIG
from contracts import Event, RobotCommand, SimStatus
from control import Controller


def initial_status(simulation, result, config):
    if isinstance(result, SimStatus):
        return result
    return simulation.step(RobotCommand(config.home_xyz, False), 0.0)


def run(vision, simulation, metrics=None, config: Config = DEFAULT_CONFIG,
        duration_s=None, show_overlay=True, clock=time.monotonic, sleep=time.sleep,
        bridge=None):
    """Integrate injected modules; all simulation calls occur on this thread.

    Factories: Vision(config), Simulation(config), optional Metrics(config).
    initialize/reset may return SimStatus or None; step MUST return SimStatus.
    Optional vision.latest_overlay() returns a BGR image. Optional poll_key()
    returns p/r/c/q (pause/reset/confirm resume/quit), including in headless mode.
    Event payloads passed to metrics.record_event are plain JSON-safe dicts.
    Trial lifecycle/TrialRecord persistence remain the responsibility of TV4.
    """
    if config.control_mode == "arm":
        from arm_control import ArmController
        controller = ArmController(config)
    else:
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
        last_vision_error = None
        emit(Event(clock(), "session_started"))
        last_camera_overlay = None
        last_camera_publish = 0.0
        while duration_s is None or clock() - started < duration_s:
            tick = clock()
            # Cap after stalls: never let a delayed GUI advance a large physics step.
            dt = min(config.max_control_dt, max(0.0, tick - previous))
            previous = tick
            key = vision.poll_key() if hasattr(vision, "poll_key") else None
            if bridge is not None:
                key = bridge.poll_key() or key
            sample = vision.latest_sample()
            if (show_overlay or bridge is not None) and hasattr(vision, "latest_overlay"):
                overlay = vision.latest_overlay()
                if overlay is not None:
                    if cv2 is None:
                        cv2 = importlib.import_module("cv2")
                    frame = overlay.copy()
                    cv2.putText(frame, f"{controller.state.value}: {controller.message}",
                                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
                    cv2.putText(frame, f"candidate={status.candidate_box_id} held={status.held_box_id} "
                                f"placed={len(status.placed_box_ids)} | P pause C resume R reset Q quit",
                                (12, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                    if show_overlay:
                        cv2.imshow("Gesture robot", frame)
                        pressed = cv2.waitKey(1) & 0xFF
                        if pressed != 255:
                            key = chr(pressed).lower()
                    if (bridge is not None and overlay is not last_camera_overlay
                            and tick - last_camera_publish >= 1 / 15):
                        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
                        if ok:
                            bridge.publish_camera_frame(encoded.tobytes())
                            last_camera_overlay = overlay
                            last_camera_publish = tick
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
            elif key == "t" and config.control_mode == "pick" and metrics is not None and hasattr(metrics, "begin_trial"):
                metrics.begin_trial(tick)
            vision_error = getattr(vision, "error", None)
            if vision_error and vision_error != last_vision_error:
                print(f"Vision paused: {vision_error}")
                emit(Event(clock(), "vision_error", reason=vision_error))
            last_vision_error = vision_error
            # Read now AFTER the asynchronous producer's sample to avoid treating
            # a just-completed camera callback as a timestamp from the future.
            command = controller.update(sample, status, clock())
            status = simulation.step(command, dt)
            # The simulator moves in step; attachment is attempted after that step.
            # Its result is observed in the next SimStatus, never inferred from bool.
            if command.action.value == "ATTACH":
                if not simulation.try_attach(command.box_id):
                    reason = "grasp_point_outside_attach_distance"
                    controller.message = "Grasp missed: open hand, lower the tool and retry"
                    emit(Event(tick, "grasp_rejected", box_id=command.box_id,
                               controller_state=controller.state.value, reason=reason))
            elif command.action.value == "RELEASE":
                simulation.release()
            for event in controller.drain_events():
                emit(event)
            if metrics is not None and hasattr(metrics, "tick"):
                metrics.tick(clock())
            if bridge is not None:
                snapshot = simulation.snapshot()
                snapshot.update(controller_state=controller.state.value, message=controller.message,
                                source="synthetic" if getattr(vision, "is_synthetic", False) else "camera",
                                control_mode=config.control_mode,
                                vision_error=getattr(vision, "error", None))
                bridge.publish(snapshot)
            remaining = 1.0 / config.loop_hz - (clock() - tick)
            if remaining > 0:
                sleep(remaining)
        emit(Event(clock(), "session_ended", controller_state=controller.state.value))
        return status
    except Exception as exc:
        emit(Event(clock(), "session_failed", reason=str(exc)))
        raise
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
    parser.add_argument("--metrics-module", default="metrics", help="Module exporting Metrics(config)")
    parser.add_argument("--no-log", action="store_true")
    parser.add_argument("--source", default="0", help="Webcam index or video path")
    parser.add_argument("--hand", choices=["Right", "Left"], default="Right")
    parser.add_argument("--mode", choices=["pick", "arm"], default="arm", help="Full arm following with pinch grasp, or palm pick/place")
    parser.add_argument("--headless", action="store_true", help="PyBullet DIRECT (no native GUI)")
    web_group = parser.add_mutually_exclusive_group()
    web_group.add_argument("--web", dest="web", action="store_true", help="Serve Three.js mirror at localhost")
    web_group.add_argument("--no-web", dest="web", action="store_false", help="Do not open the 3D browser view")
    parser.set_defaults(web=True)
    parser.add_argument("--gui", action="store_true", help="Also show the native PyBullet window")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--demo", action="store_true", help="Synthetic hand input with REAL PyBullet physics")
    parser.add_argument("--operator", default="operator")
    parser.add_argument("--trial-box", choices=[box[0] for box in DEFAULT_CONFIG.boxes], default="green")
    parser.add_argument("--duration", type=float, help="Stop after N seconds")
    parser.add_argument("--no-overlay", action="store_true")
    args = parser.parse_args()
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration must be positive")
    config = replace(DEFAULT_CONFIG, camera_source=int(args.source) if args.source.isdigit() else args.source,
                     hand_side=args.hand, simulation_gui=args.gui or not args.headless, control_mode=args.mode)
    if args.mode == "arm" and args.vision_module == "vision":
        args.vision_module = "arm_vision"
    if args.demo or args.vision_module in ("dev.scripted_vision", "dev.scripted_arm"):
        args.demo = True
        args.vision_module = "dev.scripted_arm" if args.mode == "arm" else "dev.scripted_vision"
        args.duration = args.duration or 14
    try:
        vision_cls = getattr(importlib.import_module(args.vision_module), "Vision")
        sim_cls = getattr(importlib.import_module(args.simulation_module), "Simulation")
        metrics_cls = (getattr(importlib.import_module(args.metrics_module), "Metrics")
                       if not args.no_log else None)
    except (ImportError, AttributeError) as exc:
        parser.exit(2, f"Integration module unavailable: {exc}\n"
                    "Run ./setup-demo.ps1 and check the selected --vision-module/--simulation-module.\n")
    bridge = None
    try:
        if args.web:
            from simulation.serve import IntegrationBridge
            try:
                bridge = IntegrationBridge(args.port)
            except OSError as exc:
                if args.port == 0:
                    raise
                print(f"Port {args.port} is occupied ({exc}); using an available local port.")
                bridge = IntegrationBridge(0)
            url = f"http://127.0.0.1:{bridge.server.server_port}"
            print(f"Three.js physics mirror: {url}")
            webbrowser.open(url)
        if metrics_cls and args.metrics_module == "metrics":
            metrics = metrics_cls(config, directory="results/synthetic" if args.demo else "results/live",
                                  operator=args.operator, requested_box_id=args.trial_box,
                                  source="synthetic" if args.demo else "camera")
            print(f"Logs: {metrics.directory}")
        else:
            metrics = metrics_cls(config) if metrics_cls else None
        if args.demo:
            print("SYNTHETIC hand input; real PyBullet physics. Not a webcam evaluation.")
        run(vision_cls(config), sim_cls(config), metrics,
            config=config, duration_s=args.duration, show_overlay=not args.no_overlay, bridge=bridge)
    except KeyboardInterrupt:
        pass
    finally:
        if bridge is not None:
            bridge.close()


if __name__ == "__main__":
    main()
