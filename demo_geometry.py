"""Member 2 demo: synthetic pick pipeline or replay a real Three.js camera export."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from modules.geometry import GeometryCoordinateTransformer
from modules.tracker import WasteTemporalUncertaintyTracker


def run_synthetic_demo():
    print("SYNTHETIC CAMERA DEMO - not a calibrated robot or detector")
    geometry = GeometryCoordinateTransformer(
        fx=550, fy=550, cx=320, cy=240, image_size=(640, 480),
        camera_to_world=[[1, 0, 0, 0], [0, -1, 0, 0.35],
                         [0, 0, -1, 0.25], [0, 0, 0, 1]],
        plane_point=(0, 0, -0.1),
        workspace_limits=((-0.25, 0.25), (0.15, 0.50), (-0.11, 0.1)),
    )
    # Independent GT. A point at (0.05,0.35,-0.1) projects to (398.5714,240).
    gt = {"true_world_pos": [0.05, 0.35, -0.1]}
    detection = {"material_class": "Plastic", "confidence": 0.95,
                 "center_pixel": [398.57142857142856, 240], "object_id": "demo-bottle"}
    tracker = WasteTemporalUncertaintyTracker()
    errors = []
    for frame_id in range(139, 144):
        items = geometry.process([detection])
        raw = items[0]["target_world_3d"]
        state = tracker.update(items, gt)
        errors.append(np.linalg.norm(np.array(raw) - gt["true_world_pos"]) * 1000)
        print(geometry.format_log(frame_id, items[0]))
        print(tracker.format_log(frame_id, raw, state, gt))
    print(f"Max geometry error against synthetic GT: {max(errors):.6f} mm")

    for name, patch in [("OUT_OF_WORKSPACE", {"center_pixel": [320, 0]}),
                        ("LOW_CONFIDENCE", {"confidence": 0.4})]:
        tracker.reset()
        for _ in range(5):
            state = tracker.update(geometry.process([{**detection, **patch}]))
        status = "CLEAR_TO_PICK" if state["should_trigger_pick"] else "HOLD"
        print(f"{name}: {status}")

    try:
        geometry.process([{**detection, "center_pixel": [float('nan'), 240]}])
    except ValueError as exc:
        tracker.reset()
        print(f"INVALID_INPUT: HOLD ({exc})")

    # Same image ray hitting an object 5 cm above the assumed plane.
    # True point (0.05,0.35,-0.05), depth=0.30 -> u=411.6667.
    estimated = geometry.pixel_to_world_3d(411.6666666666667, 240)
    error = np.linalg.norm(np.asarray(estimated) - [0.05, 0.35, -0.05]) * 1000
    print(f"HEIGHT_ASSUMPTION: 5 cm above plane -> 3D error {error:.2f} mm; "
          "plane-only geometry cannot recover unknown object height.")


def replay_snapshot(path, meters_per_unit):
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    scale = float(meters_per_unit)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("--meters-per-unit must be positive and finite")
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    references = snapshot.get("reference_points", [])
    if not isinstance(references, list) or not references:
        raise ValueError("snapshot needs visible reference_points on scene floor Y=0")
    geometry = GeometryCoordinateTransformer.from_threejs_snapshot(
        snapshot, meters_per_unit=scale, plane_point=(0, 0, 0),
        workspace_limits=((-10 * scale, 10 * scale), (-10 * scale, 10 * scale), (-scale, scale)),
    )
    print("THREEJS CALIBRATION REPLAY - geometric reference points, NOT detections")
    print(f"Explicit scale: {scale:g} metres per scene unit; plane: scene Y=0")
    errors = []
    for index, reference in enumerate(references):
        if not isinstance(reference, dict) or reference.get("in_view") is not True:
            raise ValueError("reference point must be visible")
        scene_point = np.asarray(reference["scene_point"], dtype=float)
        if scene_point.shape != (3,) or not np.all(np.isfinite(scene_point)) or abs(scene_point[1]) > 1e-9:
            raise ValueError("reference point must be finite and on floor Y=0")
        expected = geometry.threejs_to_world(scene_point, scale)
        result = geometry.pixel_to_world_3d(*reference["pixel_center"])
        error = float(np.linalg.norm(np.asarray(result) - expected) * 1000)
        errors.append(error)
        print(f"Reference {index}: world={np.round(result, 6).tolist()}, error={error:.6f} mm")
    print(f"Reference points checked: {len(errors)}")
    print(f"Max 3D error: {max(errors):.6f} mm")
    if max(errors) > 0.01:
        raise ValueError("camera/point mismatch: replay error exceeds 0.01 mm")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="JSON from TrashBins.getGeometrySnapshot(referencePoints)")
    parser.add_argument("--meters-per-unit", type=float, help="Explicit scene scale; required for snapshot replay")
    args = parser.parse_args()
    if args.snapshot and args.meters_per_unit is None:
        parser.error("--snapshot requires --meters-per-unit; scene units are not automatically metres")
    try:
        if args.snapshot:
            replay_snapshot(args.snapshot, args.meters_per_unit)
        else:
            run_synthetic_demo()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
