"""Member 2: calibrated image rays -> metric robot-world coordinates.

Camera coordinates use the OpenCV convention: +X right, +Y down, +Z forward.
Robot world is right-handed, Z-up. Calibration, plane and workspace are explicit:
there is deliberately no guessed camera pose or physical scale.
"""

from collections.abc import Mapping

import numpy as np


def _array(value, shape, name):
    try:
        result = np.array(value, dtype=float, copy=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must have shape {shape} and finite values")
    return result


def _positive(value, name):
    result = float(_array(value, (), name))
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _image_size(value):
    size = _array(value, (2,), "image_size")
    if np.any(size <= 0) or np.any(size != np.floor(size)):
        raise ValueError("image_size must contain positive integer width and height")
    return tuple(int(v) for v in size)


def _pose(value):
    matrix = _array(value, (4, 4), "camera_to_world")
    rotation = matrix[:3, :3]
    if (not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-8, rtol=0)
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-6, rtol=0)):
        raise ValueError("camera_to_world must be a rigid right-handed transform")
    return matrix


# Right-handed rotation: Three.js (X,Y,Z) -> robot (X,-Z,Y).
_SCENE_TO_WORLD = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])


class GeometryCoordinateTransformer:
    """Intersect calibrated rays with a known picking plane, in metres.

    Pixel coordinates must belong to the calibrated image, not a letterboxed
    or resized detector input. The plane is a geometric assumption, not depth
    inferred from a bounding box. Workspace checks are AABB checks, NOT IK or
    collision avoidance. The caller must stop/hold on ValueError.
    """

    def __init__(self, fx, fy, cx, cy, *, image_size, camera_to_world,
                 plane_point, workspace_limits, plane_normal=(0, 0, 1),
                 clearance_m=0.05):
        self.fx = _positive(fx, "fx")
        self.fy = _positive(fy, "fy")
        self.cx = float(_array(cx, (), "cx"))
        self.cy = float(_array(cy, (), "cy"))
        self.image_size = _image_size(image_size)
        self.camera_to_world = _pose(camera_to_world)
        self.plane_point = _array(plane_point, (3,), "plane_point")
        normal = _array(plane_normal, (3,), "plane_normal")
        length = np.linalg.norm(normal)
        if not np.isfinite(length) or length < 1e-12:
            raise ValueError("plane_normal must be nonzero")
        self.plane_normal = normal / length
        self.workspace_limits = _array(workspace_limits, (3, 2), "workspace_limits")
        if np.any(self.workspace_limits[:, 0] > self.workspace_limits[:, 1]):
            raise ValueError("workspace minimum must not exceed maximum")
        self.clearance_m = float(_array(clearance_m, (), "clearance_m"))
        if self.clearance_m < 0:
            raise ValueError("clearance_m must be nonnegative")

    def pixel_to_world_3d(self, u, v):
        """Return the forward ray/plane intersection; never round geometry."""
        u, v = _array([u, v], (2,), "pixel")
        width, height = self.image_size
        if not (0 <= u < width and 0 <= v < height):
            raise ValueError("pixel is outside the calibrated image")
        direction_camera = np.array([(u - self.cx) / self.fx,
                                     (v - self.cy) / self.fy, 1.0])
        direction = self.camera_to_world[:3, :3] @ direction_camera
        origin = self.camera_to_world[:3, 3]
        denominator = float(self.plane_normal @ direction)
        if abs(denominator) / np.linalg.norm(direction) < 1e-9:
            raise ValueError("camera ray is parallel or too close to parallel to the plane")
        distance = float(self.plane_normal @ (self.plane_point - origin)) / denominator
        if not np.isfinite(distance) or distance <= 0:
            raise ValueError("plane intersection is at or behind the camera")
        point = origin + distance * direction
        if not np.all(np.isfinite(point)):
            raise ValueError("plane intersection is not finite")
        return point.tolist()

    def is_reachable(self, world_pos):
        """Inclusive 3-axis workspace bound check, not a kinematics guarantee."""
        point = _array(world_pos, (3,), "world_pos")
        return bool(np.all(point >= self.workspace_limits[:, 0])
                    and np.all(point <= self.workspace_limits[:, 1]))

    def process(self, detections):
        """Preserve detection metadata and add Member 3-compatible geometry.

        Accept center_pixel (Member 1) or pixel_center (written contract).
        A malformed item rejects the batch rather than inventing a pick target.
        """
        items = []
        for index, det in enumerate(detections):
            if not isinstance(det, Mapping):
                raise ValueError(f"detection {index} must be a mapping")
            material = det.get("material_class")
            if not isinstance(material, str) or not material.strip():
                raise ValueError(f"detection {index} requires material_class")
            confidence = float(_array(det.get("confidence"), (), "confidence"))
            if not 0 <= confidence <= 1:
                raise ValueError("confidence must be between 0 and 1")
            pixel = _array(det.get("center_pixel", det.get("pixel_center")), (2,), "center_pixel")
            if "center_pixel" in det and "pixel_center" in det:
                alias = _array(det["pixel_center"], (2,), "pixel_center")
                if not np.array_equal(pixel, alias):
                    raise ValueError("center_pixel and pixel_center disagree")
            world = self.pixel_to_world_3d(*pixel)
            pre_pick = np.asarray(world) + self.plane_normal * self.clearance_m
            item = dict(det)
            item.update({
                "confidence": confidence,
                "center_pixel": pixel.tolist(),
                "pixel_center": pixel.tolist(),
                "target_world_3d": world,
                "pre_pick_world_3d": pre_pick.tolist(),
                "pick_approach_vector": (-self.plane_normal).tolist(),
                "is_within_reach": self.is_reachable(world) and self.is_reachable(pre_pick),
                "coordinate_frame": "robot_world_z_up",
            })
            items.append(item)
        return items

    @staticmethod
    def threejs_to_world(point, meters_per_unit):
        """Convert scene units and Y-up axes without reflecting handedness."""
        scale = _positive(meters_per_unit, "meters_per_unit")
        return (_SCENE_TO_WORLD @ _array(point, (3,), "scene_point") * scale).tolist()

    @classmethod
    def from_threejs_snapshot(cls, snapshot, *, meters_per_unit, plane_point,
                              workspace_limits, clearance_m=0.05):
        """Read live camera matrices from TrashBins.getGeometrySnapshot().

        Three.js arrays are column-major. GL camera axes (+Y up, -Z forward)
        are converted to CV axes before applying the scene-to-robot rotation.
        Scale is supplied by the caller; the renderer does not define metres.
        Plane and workspace arguments are already in robot-world metres.
        """
        if not isinstance(snapshot, Mapping) or snapshot.get("schema_version") != 1:
            raise ValueError("unsupported camera snapshot schema")
        if snapshot.get("source") != "threejs":
            raise ValueError("snapshot must come from the Three.js simulator")
        width, height = _image_size(snapshot.get("image_size"))
        projection = _array(snapshot.get("projection_matrix"), (16,), "projection_matrix").reshape(4, 4, order="F")
        pose_gl = _pose(_array(snapshot.get("camera_matrix_world"), (16,), "camera_matrix_world").reshape(4, 4, order="F"))
        if (not np.allclose(projection[3], [0, 0, -1, 0], atol=1e-8, rtol=0)
                or not np.allclose(projection[[0, 0, 1, 1, 2, 2], [1, 3, 0, 3, 0, 1]], 0)):
            raise ValueError("only unskewed perspective camera projections are supported")
        scale = _positive(meters_per_unit, "meters_per_unit")
        pose_cv = np.eye(4)
        pose_cv[:3, :3] = _SCENE_TO_WORLD @ pose_gl[:3, :3] @ np.diag([1., -1., -1.])
        pose_cv[:3, 3] = _SCENE_TO_WORLD @ pose_gl[:3, 3] * scale
        return cls(
            fx=projection[0, 0] * width / 2,
            fy=projection[1, 1] * height / 2,
            cx=(1 - projection[0, 2]) * width / 2,
            cy=(1 + projection[1, 2]) * height / 2,
            image_size=(width, height), camera_to_world=pose_cv,
            plane_point=plane_point, workspace_limits=workspace_limits,
            clearance_m=clearance_m,
        )

    @staticmethod
    def format_log(frame_id, item):
        u, v = item["pixel_center"]
        x, y, z = item["target_world_3d"]
        reachable = str(item["is_within_reach"]).upper()
        return (f"[FRAME #{frame_id:04d}] [GEOMETRY 3D] Pixel: ({u:g}, {v:g}) -> "
                f"World Pose: X={x:.3f}m, Y={y:.3f}m, Z={z:.3f}m\n"
                f"              -> In Workspace: {reachable} | "
                f"Approach: {item['pick_approach_vector']} | Frame: robot_world_z_up")
