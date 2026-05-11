"""
orientation_detector.py
───────────────────────
Detects roof orientation (compass azimuth) from satellite image.

Since satellite images are always North-up, the roof ridge line angle
directly gives us the compass orientation.

Algorithm
─────────
1. Extract roof region (using mask)
2. Detect edges inside roof (Canny)
3. Detect lines using Hough Transform
4. Cluster line angles to find dominant ridge direction
5. Convert ridge angle → roof face azimuth
   - A ridge running E-W means roof faces N or S
   - A ridge running N-S means roof faces E or W
6. Use sun position to disambiguate N vs S, E vs W
   (the sun-facing side is the side with the shadow)
"""

import cv2
import numpy as np
import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class OrientationResult:
    azimuth_degrees: float       # 0–360, clockwise from North
    direction_label: str         # 'South', 'North-East', etc.
    ridge_angle_degrees: float   # angle of ridge line (0–180)
    confidence: int              # 0–100
    num_lines_detected: int
    segments: List[dict]         # per-face data


DIRECTION_LABELS = [
    (22.5,  'North'),      (67.5,  'North-East'),
    (112.5, 'East'),       (157.5, 'South-East'),
    (202.5, 'South'),      (247.5, 'South-West'),
    (292.5, 'West'),       (337.5, 'North-West'),
    (360.1, 'North'),
]

def azimuth_to_direction(deg: float) -> str:
    d = deg % 360
    for threshold, label in DIRECTION_LABELS:
        if d < threshold:
            return label
    return 'North'


def detect_ridge_lines(image: np.ndarray, mask: np.ndarray) -> List[float]:
    """
    Find dominant line angles within the roof region using Hough lines.
    Returns list of angles in degrees (0–180).
    """
    # Apply mask to focus on roof only
    masked = cv2.bitwise_and(image, image, mask=mask)
    gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Hough line detection
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=60)
    if lines is None:
        return []

    angles = []
    for line in lines:
        rho, theta = line[0]
        angle_deg = math.degrees(theta)
        angles.append(angle_deg)

    return angles


def cluster_angles(angles: List[float], tolerance: float = 15.0) -> Optional[float]:
    """
    Find the dominant angle cluster in a list of angles.
    Returns the mean angle of the largest cluster.
    """
    if not angles:
        return None

    angles_arr = np.array(angles)

    # Simple clustering: bin into 12 buckets of 15°
    hist, bin_edges = np.histogram(angles_arr, bins=12, range=(0, 180))
    dominant_bin = np.argmax(hist)
    dominant_center = (bin_edges[dominant_bin] + bin_edges[dominant_bin + 1]) / 2

    # Mean of angles near dominant bin
    in_cluster = angles_arr[np.abs(angles_arr - dominant_center) < tolerance]
    if len(in_cluster) == 0:
        return dominant_center

    return float(np.mean(in_cluster))


def ridge_angle_to_azimuths(ridge_angle: float, sun_azimuth: float) -> tuple[float, float]:
    """
    Convert ridge line angle to the two roof face azimuths.

    A ridge at angle θ from North creates two faces:
        face1_azimuth = θ + 90°   (one side)
        face2_azimuth = θ - 90°   (other side)

    We pick the face closer to the sun direction as the primary (more sunlit) face.
    """
    face1 = (ridge_angle + 90) % 360
    face2 = (ridge_angle - 90) % 360

    # Choose the face closer to sun azimuth as primary
    diff1 = abs(((face1 - sun_azimuth) + 180) % 360 - 180)
    diff2 = abs(((face2 - sun_azimuth) + 180) % 360 - 180)

    if diff1 <= diff2:
        primary, secondary = face1, face2
    else:
        primary, secondary = face2, face1

    return round(primary, 1), round(secondary, 1)


def estimate_segment_areas(mask: np.ndarray, ridge_angle: float) -> tuple[float, float]:
    """
    Estimate area split between two roof faces using the ridge line.
    Rotates the mask to align ridge with vertical, then splits left/right.
    """
    h, w = mask.shape
    total_pixels = mask.sum() / 255

    # Rotate mask so ridge is vertical
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, ridge_angle, 1.0)
    rotated = cv2.warpAffine(mask, M, (w, h))

    left_half = rotated[:, :w // 2].sum() / 255
    right_half = rotated[:, w // 2:].sum() / 255

    if total_pixels > 0:
        left_frac = left_half / total_pixels
        right_frac = right_half / total_pixels
    else:
        left_frac = right_frac = 0.5

    return left_frac, right_frac


def detect_orientation(
    image: np.ndarray,
    roof_mask: np.ndarray,
    roof_area_m2: float,
    sun_azimuth: float = 180.0,
) -> OrientationResult:
    """
    Full orientation detection pipeline.
    """
    angles = detect_ridge_lines(image, roof_mask)
    ridge_angle = cluster_angles(angles)
    num_lines = len(angles)

    if ridge_angle is None:
        # No lines detected — assume south-facing (most common in India)
        ridge_angle = 90.0  # E-W ridge → N/S facing
        confidence = 40
    else:
        # Confidence based on how many lines we found and their consistency
        if num_lines >= 20:
            confidence = 88
        elif num_lines >= 10:
            confidence = 78
        elif num_lines >= 5:
            confidence = 65
        else:
            confidence = 50

    primary_az, secondary_az = ridge_angle_to_azimuths(ridge_angle, sun_azimuth)

    # Split area between segments
    left_frac, right_frac = estimate_segment_areas(roof_mask, ridge_angle)
    area1 = round(roof_area_m2 * left_frac, 1)
    area2 = round(roof_area_m2 * right_frac, 1)

    segments = [
        {
            'label': f'{azimuth_to_direction(primary_az)} face',
            'orientation': primary_az,
            'pitch': 0.0,    # filled in by main.py after shadow analysis
            'area': area1,
        },
        {
            'label': f'{azimuth_to_direction(secondary_az)} face',
            'orientation': secondary_az,
            'pitch': 0.0,
            'area': area2,
        },
    ]

    return OrientationResult(
        azimuth_degrees=primary_az,
        direction_label=azimuth_to_direction(primary_az),
        ridge_angle_degrees=round(ridge_angle, 1),
        confidence=confidence,
        num_lines_detected=num_lines,
        segments=segments,
    )
