"""End-to-end checks for the Member 2 command-line demo and real camera fixture."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

import numpy as np

from modules.geometry import GeometryCoordinateTransformer

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "threejs_camera_snapshot.json"


class TestGeometryDemo(unittest.TestCase):
    def run_demo(self, *args):
        self.assertTrue((ROOT / "demo_geometry.py").exists(), "Member 2 CLI demo must exist")
        return subprocess.run([sys.executable, str(ROOT / "demo_geometry.py"), *args],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)

    def test_cli_synthetic_demo_runs_real_tracker_and_reports_hold_case(self):
        result = self.run_demo()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SYNTHETIC", result.stdout)
        self.assertIn("CLEAR_TO_PICK", result.stdout)
        self.assertIn("OUT_OF_WORKSPACE: HOLD", result.stdout)
        self.assertIn("LOW_CONFIDENCE: HOLD", result.stdout)
        self.assertIn("HEIGHT_ASSUMPTION", result.stdout)
        self.assertIn("INVALID_INPUT: HOLD", result.stdout)

    def test_live_threejs_camera_fixture_recovers_independent_scene_points(self):
        snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        geometry = GeometryCoordinateTransformer.from_threejs_snapshot(
            snapshot, meters_per_unit=1, plane_point=(0, 0, 0),
            workspace_limits=((-1, 1), (-1, 1), (0, 1)))
        expected = [[0, 0, 0], [0.1, -0.2, 0], [-0.2, 0.1, 0]]
        for point, want in zip(snapshot["reference_points"], expected):
            np.testing.assert_allclose(geometry.pixel_to_world_3d(*point["pixel_center"]), want, atol=1e-12)

    def test_cli_replays_exported_snapshot_with_explicit_scale(self):
        result = self.run_demo("--snapshot", str(FIXTURE), "--meters-per-unit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("THREEJS CALIBRATION REPLAY", result.stdout)
        self.assertIn("Reference points checked: 3", result.stdout)
        self.assertIn("Max 3D error: 0.000000 mm", result.stdout)

    def test_cli_requires_scale_instead_of_guessing_scene_metres(self):
        result = self.run_demo("--snapshot", str(FIXTURE))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--meters-per-unit", result.stderr)

    def test_cli_reports_missing_file_as_failure(self):
        result = self.run_demo("--snapshot", str(ROOT / "missing_snapshot.json"), "--meters-per-unit", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HOLD", result.stderr)


if __name__ == "__main__":
    unittest.main()
