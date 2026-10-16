"""Geometry contracts: calibrated rays, world axes and Member 3 compatibility."""

import copy
import json
import unittest

import numpy as np

from modules.tracker import WasteTemporalUncertaintyTracker


from modules.geometry import GeometryCoordinateTransformer


def transformer(**overrides):
    options = dict(
        fx=550.0, fy=550.0, cx=320.0, cy=240.0,
        image_size=(640, 480),
        camera_to_world=[[1, 0, 0, 0], [0, -1, 0, 0.35],
                         [0, 0, -1, 0.25], [0, 0, 0, 1]],
        plane_point=(0, 0, -0.1), plane_normal=(0, 0, 1),
        workspace_limits=((-0.25, 0.25), (0.15, 0.50), (-0.11, 0.1)),
        clearance_m=0.05,
    )
    options.update(overrides)
    return GeometryCoordinateTransformer(**options)


def three_snapshot():
    # GL camera at (0, 1, 0), looking down -Y. Arrays are column-major.
    # Independent simple perspective fixture: fx=fy=240 at 640x480.
    return {
        "schema_version": 1,
        "source": "threejs",
        "image_size": [640, 480],
        "projection_matrix": [0.75, 0, 0, 0, 0, 1, 0, 0,
                              0, 0, -1.0033389, -1, 0, 0, -0.2003339, 0],
        "camera_matrix_world": [1, 0, 0, 0, 0, 0, -1, 0,
                                0, 1, 0, 0, 0, 1, 0, 1],
    }


class TestGeometry(unittest.TestCase):
    def test_pixel_center_maps_to_table_not_camera_depth(self):
        np.testing.assert_allclose(transformer().pixel_to_world_3d(320, 240), [0, 0.35, -0.1])

    def test_off_center_pixel_has_correct_world_signs_and_precision(self):
        result = transformer().pixel_to_world_3d(395, 185)
        np.testing.assert_allclose(result, [0.04772727272727273, 0.385, -0.1], atol=1e-12)
        self.assertNotEqual(result[0], round(result[0], 3))

    def test_tilted_camera_intersects_plane(self):
        # Camera at (0,0,1), 45 degrees around X, looking towards +Y and -Z.
        a = np.sqrt(0.5)
        geometry = transformer(camera_to_world=[[1, 0, 0, 0], [0, -a, a, 0],
                                                [0, -a, -a, 1], [0, 0, 0, 1]],
                               plane_point=(0, 0, 0))
        np.testing.assert_allclose(geometry.pixel_to_world_3d(320, 240), [0, 1, 0], atol=1e-12)

    def test_parallel_and_backward_rays_are_rejected(self):
        cases = [dict(plane_normal=(1, 0, 0)), dict(plane_point=(0, 0, 1))]
        for options in cases:
            with self.subTest(options=options), self.assertRaises(ValueError):
                transformer(**options).pixel_to_world_3d(320, 240)

    def test_workspace_checks_all_axes_and_boundaries(self):
        geometry = transformer()
        for point, expected in [([-0.25, 0.15, -0.11], True), ([0.25, 0.50, 0.1], True),
                                ([0.251, 0.35, 0], False), ([0, 0.149, 0], False),
                                ([0, 0.35, 0.101], False)]:
            with self.subTest(point=point):
                self.assertIs(geometry.is_reachable(point), expected)

    def test_invalid_camera_configuration_fails_early(self):
        for options in [dict(fx=0), dict(fy=float('nan')), dict(image_size=(0, 480)),
                        dict(image_size=(640.5, 480)), dict(plane_normal=(0, 0, 0)),
                        dict(clearance_m=-0.1), dict(camera_to_world=np.zeros((4, 4))),
                        dict(camera_to_world=np.diag([1, 1, -1, 1])),
                        dict(workspace_limits=((1, -1), (0, 1), (0, 1)))]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                transformer(**options)

    def test_invalid_pixels_and_positions_never_reach_tracker(self):
        geometry = transformer()
        for u, v in [(float('nan'), 10), (10, float('inf')), (-1, 0), (640, 0), (0, 480)]:
            with self.subTest(pixel=(u, v)), self.assertRaises(ValueError):
                geometry.pixel_to_world_3d(u, v)
        with self.assertRaises(ValueError):
            geometry.is_reachable([0, float('nan'), 0])

    def test_process_preserves_input_and_emits_serializable_pick_metadata(self):
        detection = {"material_class": "Plastic", "confidence": 0.89,
                     "center_pixel": (320, 240), "object_id": "bottle-1"}
        before = copy.deepcopy(detection)
        item = transformer().process([detection])[0]
        self.assertEqual(detection, before)
        self.assertEqual(item["object_id"], "bottle-1")
        self.assertEqual(item["pixel_center"], [320.0, 240.0])
        np.testing.assert_allclose(item["target_world_3d"], [0, 0.35, -0.1])
        np.testing.assert_allclose(item["pre_pick_world_3d"], [0, 0.35, -0.05])
        self.assertEqual(item["pick_approach_vector"], [0, 0, -1])
        self.assertIs(item["is_within_reach"], True)
        self.assertEqual(item["coordinate_frame"], "robot_world_z_up")
        json.dumps(item, allow_nan=False)
        self.assertEqual(transformer().process([]), [])

    def test_pixel_center_alias_is_supported_but_conflicts_are_rejected(self):
        detection = {"material_class": "Metal", "confidence": 0.9, "pixel_center": [320, 240]}
        self.assertEqual(len(transformer().process([detection])), 1)
        detection["center_pixel"] = [100, 200]
        with self.assertRaises(ValueError):
            transformer().process([detection])

    def test_missing_or_invalid_detection_does_not_default_to_valid_pick(self):
        valid = {"material_class": "Plastic", "confidence": 0.9, "center_pixel": [320, 240]}
        for bad in [{}, {**valid, "confidence": float('nan')}, {**valid, "confidence": 1.1},
                    {**valid, "material_class": ""}, {**valid, "center_pixel": [320]}]:
            with self.subTest(detection=bad), self.assertRaises(ValueError):
                transformer().process([bad])

    def test_clearance_outside_workspace_blocks_pick(self):
        geometry = transformer(clearance_m=0.3)
        self.assertTrue(geometry.is_reachable([0, 0.35, -0.1]))
        item = geometry.process([{"material_class": "Plastic", "confidence": 0.9,
                                  "center_pixel": [320, 240]}])[0]
        self.assertFalse(item["is_within_reach"])

    def test_actual_tracker_accepts_output_and_blocks_unreachable(self):
        geometry = transformer()
        tracker = WasteTemporalUncertaintyTracker()
        items = geometry.process([{"material_class": "Plastic", "confidence": 0.95,
                                   "center_pixel": [320, 240]}])
        gt = {"true_world_pos": [0, 0.35, -0.1]}
        for frame in range(4):
            state = tracker.update(items, gt)
            self.assertEqual(state["should_trigger_pick"], frame == 3)
        self.assertEqual(state["target_object"]["localization_error_mm"], 0)
        tracker.reset()
        items = geometry.process([{"material_class": "Plastic", "confidence": 0.95,
                                   "center_pixel": [320, 0]}])
        for _ in range(5):
            state = tracker.update(items)
        self.assertFalse(state["should_trigger_pick"])

    def test_log_reports_world_position_without_changing_precision(self):
        item = transformer().process([{"material_class": "Plastic", "confidence": 0.9,
                                       "center_pixel": [395, 185]}])[0]
        log = transformer().format_log(142, item)
        self.assertIn("[FRAME #0142]", log)
        self.assertIn("X=0.048m", log)
        self.assertIn("Y=0.385m", log)
        self.assertIn("Z=-0.100m", log)

    def test_threejs_snapshot_converts_handedness_units_and_intrinsics(self):
        geometry = GeometryCoordinateTransformer.from_threejs_snapshot(
            three_snapshot(), meters_per_unit=0.5, plane_point=(0, 0, 0),
            workspace_limits=((-1, 1), (-1, 1), (0, 1)))
        # Pixel displacement 24,48 with depth 0.5: x=0.05, y=-0.1 in Z-up.
        np.testing.assert_allclose(geometry.pixel_to_world_3d(344, 288), [0.05, -0.1, 0], atol=1e-12)
        self.assertAlmostEqual(geometry.fx, 240)
        self.assertAlmostEqual(geometry.fy, 240)
        point = GeometryCoordinateTransformer.threejs_to_world([0.1, 0, 0.2], 0.5)
        np.testing.assert_allclose(point, [0.05, -0.1, 0])

    def test_threejs_snapshot_rejects_unsupported_or_invalid_metadata(self):
        for updates in [{"schema_version": 2}, {"source": "css"},
                        {"projection_matrix": [0] * 16}, {"image_size": [640, 0]}]:
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                GeometryCoordinateTransformer.from_threejs_snapshot(
                    {**three_snapshot(), **updates}, meters_per_unit=1,
                    plane_point=(0, 0, 0), workspace_limits=((-1, 1), (-1, 1), (0, 1)))
        with self.assertRaises(ValueError):
            GeometryCoordinateTransformer.threejs_to_world([0, 1, 0], 0)


if __name__ == "__main__":
    unittest.main()
