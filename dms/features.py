"""Turn 478 face landmarks into the few numbers the monitor reasons about.

Representation pillar: a face becomes eye openness (EAR), mouth openness (MAR)
and head orientation (yaw, pitch). Geometry pillar: head pose comes from
solvePnP between a generic 3D face model and the 2D landmarks.
"""
from dataclasses import dataclass

import cv2
import numpy as np

# MediaPipe Face Mesh indices, ordered p1..p6 as in Soukupova & Cech (2016):
# p1/p4 are the eye corners, (p2, p6) and (p3, p5) are upper/lower lid pairs.
RIGHT_EYE = (33, 160, 158, 133, 153, 144)  # subject's right eye, image left
LEFT_EYE = (362, 385, 387, 263, 373, 380)
MOUTH = (78, 308, 13, 14)  # left corner, right corner, upper inner lip, lower inner lip

# 2D landmarks paired with a generic 3D face model (millimetre-ish units,
# nose tip at origin, x to image right, y up, z toward the camera).
POSE_IDX = (1, 152, 33, 263, 61, 291)
POSE_MODEL = np.array([
    (0.0, 0.0, 0.0),          # nose tip
    (0.0, -330.0, -65.0),     # chin
    (-225.0, 170.0, -135.0),  # right eye outer corner (image left)
    (225.0, 170.0, -135.0),   # left eye outer corner (image right)
    (-150.0, -150.0, -125.0), # right mouth corner
    (150.0, -150.0, -125.0),  # left mouth corner
], dtype=np.float64)


@dataclass
class Observation:
    ear: float      # mean of both eyes
    ear_l: float
    ear_r: float
    mar: float
    yaw: float      # degrees, raw (the monitor subtracts the driver's baseline)
    pitch: float


def to_pixels(landmarks, w, h):
    """Normalized landmarks -> (N, 2) pixel array. EAR needs real aspect ratio."""
    return np.array([(p.x * w, p.y * h) for p in landmarks], dtype=np.float64)


def eye_aspect_ratio(pts, idx):
    p1, p2, p3, p4, p5, p6 = (pts[i] for i in idx)
    width = np.linalg.norm(p1 - p4)
    if width < 1e-6:
        return 0.0
    return (np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)) / (2.0 * width)


def mouth_aspect_ratio(pts, idx=MOUTH):
    left, right, top, bottom = (pts[i] for i in idx)
    width = np.linalg.norm(left - right)
    if width < 1e-6:
        return 0.0
    return np.linalg.norm(top - bottom) / width


def camera_matrix(w, h):
    """Uncalibrated webcam guess: focal length ~ image width, principal point at centre.

    A proper intrinsic calibration (checkerboard / ArUco) would replace this;
    because the monitor only uses angles relative to the calibrated baseline,
    the error in f mostly cancels out.
    """
    f = float(w)
    return np.array([[f, 0, w / 2.0], [0, f, h / 2.0], [0, 0, 1]], dtype=np.float64)


# The model has y up and z out of the face; the camera has y down and z into
# the scene. A face looking straight at the camera is this 180° turn about x.
FACING_CAMERA = np.diag([1.0, -1.0, -1.0])


def head_pose(pts, w, h):
    """Return (yaw, pitch) in degrees from solvePnP, or (nan, nan) if it fails.

    Angles come from where the nose points (the head's z axis), not from an
    Euler decomposition: RQ decomposition near a 180° base rotation can return
    the mirrored solution and lose the sign of yaw.
    Positive yaw: nose toward image right. Positive pitch: head tipped down.
    """
    image_pts = np.array([pts[i] for i in POSE_IDX], dtype=np.float64)
    K = camera_matrix(w, h)
    # PnP with six roughly coplanar points has a mirrored second solution, and
    # an unguided solve flips between the two from frame to frame. Start from
    # "face looking at the camera" at the distance implied by the eye spacing,
    # which a driver's pose is always closer to than to its mirror.
    f, cx, cy = K[0, 0], K[0, 2], K[1, 2]
    eye_px = np.linalg.norm(image_pts[2] - image_pts[3])
    z = f * np.linalg.norm(POSE_MODEL[2] - POSE_MODEL[3]) / max(eye_px, 1.0)
    rvec0 = cv2.Rodrigues(FACING_CAMERA)[0]
    tvec0 = np.array([[(image_pts[0, 0] - cx) * z / f], [(image_pts[0, 1] - cy) * z / f], [z]])
    ok, rvec, _ = cv2.solvePnP(POSE_MODEL, image_pts, K, np.zeros(4), rvec0, tvec0,
                               useExtrinsicGuess=True, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        return float("nan"), float("nan")
    rot, _ = cv2.Rodrigues(rvec)
    nose = (FACING_CAMERA @ rot)[:, 2]
    yaw = np.degrees(np.arctan2(nose[0], nose[2]))
    pitch = np.degrees(np.arctan2(-nose[1], np.hypot(nose[0], nose[2])))
    return float(yaw), float(pitch)


def pick_driver(faces, w, h):
    """Index of the largest face: the one nearest the camera is the driver.

    With one face requested the landmarker returns whichever it is most sure of,
    which can be a passenger or someone in the back seat.
    """
    def area(lms):
        xs = [p.x * w for p in lms]
        ys = [p.y * h for p in lms]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    return max(range(len(faces)), key=lambda i: area(faces[i]))


def observe(landmarks, w, h):
    pts = to_pixels(landmarks, w, h)
    ear_r = eye_aspect_ratio(pts, RIGHT_EYE)
    ear_l = eye_aspect_ratio(pts, LEFT_EYE)
    yaw, pitch = head_pose(pts, w, h)
    return Observation(ear=(ear_l + ear_r) / 2.0, ear_l=ear_l, ear_r=ear_r,
                       mar=mouth_aspect_ratio(pts), yaw=yaw, pitch=pitch), pts
