"""
shadow_analyzer.py
──────────────────
Estimates roof pitch from cast shadows visible in the satellite image.

Algorithm
─────────
1. Detect roof boundary (passed in from roof_detector)
2. Find the shadow region adjacent to the roof
   - Convert to HSV, threshold for dark/low-saturation regions
   - Shadow must be connected to / adjacent to roof boundary
3. Measure shadow length in pixels (perpendicular to roof edge)
4. Calculate sun elevation at capture time using pvlib
5. pitch = arctan(roof_height / half_width)
   roof_height = shadow_length × tan(sun_elevation)

Edge cases
──────────
- No clear shadow → return None (caller uses fallback)
- Sun elevation < 15° → shadows too long/unreliable
- Shadow shorter than 5px → too short to measure reliably
"""

import cv2
import numpy as np
import math
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

try:
    import pvlib
    HAS_PVLIB = True
except ImportError:
    HAS_PVLIB = False


@dataclass
class ShadowAnalysisResult:
    pitch_degrees: float
    confidence: int          # 0-100
    shadow_length_px: float
    sun_elevation_degrees: float
    sun_azimuth_degrees: float
    method: str              # 'shadow_analysis' | 'pvlib' | 'fallback'


def get_sun_position(lat: float, lng: float, dt: Optional[datetime] = None):
    """
    Return (elevation_deg, azimuth_deg) for given lat/lng/time.
    Uses pvlib if available, otherwise falls back to pure-Python formula.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    if HAS_PVLIB:
        loc = pvlib.location.Location(lat, lng)
        times = pvlib.solarposition.get_solarposition(dt, lat, lng)
        elevation = float(times['apparent_elevation'].iloc[0])
        azimuth = float(times['azimuth'].iloc[0])
        return elevation, azimuth

    # Pure-Python fallback (USNO algorithm)
    rad = math.pi / 180
    day_of_year = dt.timetuple().tm_yday
    B = (360 / 365) * (day_of_year - 81) * rad
    EoT = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)
    declination = 23.45 * math.sin(B) * rad
    tz_offset = round(lng / 15)
    solar_noon = 12 - (lng - tz_offset * 15) / 15 - EoT / 60
    hour = dt.hour + dt.minute / 60 + dt.second / 3600
    hour_angle = (hour - solar_noon) * 15 * rad
    lat_r = lat * rad
    sin_elev = (math.sin(lat_r) * math.sin(declination)
                + math.cos(lat_r) * math.cos(declination) * math.cos(hour_angle))
    elevation = math.asin(max(-1, min(1, sin_elev))) / rad
    cos_az = ((math.sin(declination) - math.sin(lat_r) * sin_elev)
              / (math.cos(lat_r) * math.sqrt(1 - sin_elev ** 2) + 1e-9))
    azimuth = math.acos(max(-1, min(1, cos_az))) / rad
    if hour_angle > 0:
        azimuth = 360 - azimuth
    return elevation, azimuth


def detect_shadow_region(image: np.ndarray, roof_mask: np.ndarray) -> np.ndarray:
    """
    Find shadow pixels adjacent to the roof.
    Shadows are dark, low-saturation regions next to the bright roof.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # Shadow: low value (dark) + low saturation
    shadow_mask = cv2.inRange(hsv,
                              np.array([0, 0, 0]),
                              np.array([180, 60, 80]))

    # Dilate roof mask to find adjacent region
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    roof_dilated = cv2.dilate(roof_mask, kernel, iterations=2)

    # Shadow must be near the roof but not inside it
    near_roof = cv2.bitwise_and(roof_dilated, cv2.bitwise_not(roof_mask))
    candidate_shadow = cv2.bitwise_and(shadow_mask, near_roof)

    # Clean up
    kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    candidate_shadow = cv2.morphologyEx(candidate_shadow, cv2.MORPH_OPEN, kernel_small)

    return candidate_shadow


def measure_shadow_length(shadow_mask: np.ndarray, roof_mask: np.ndarray) -> Optional[float]:
    """
    Measure shadow length in pixels.
    Finds the bounding box of the shadow and returns its extent
    perpendicular to the dominant roof edge direction.
    """
    shadow_pixels = np.where(shadow_mask > 0)
    if len(shadow_pixels[0]) < 20:
        return None

    # Simple: use the longer dimension of the shadow bounding box
    min_r, max_r = shadow_pixels[0].min(), shadow_pixels[0].max()
    min_c, max_c = shadow_pixels[1].min(), shadow_pixels[1].max()
    h_extent = max_r - min_r
    w_extent = max_c - min_c
    shadow_length = max(h_extent, w_extent)

    if shadow_length < 5:
        return None

    return float(shadow_length)


def pitch_from_shadow(shadow_length_px: float, sun_elevation_deg: float,
                      image_width: int) -> tuple[float, int]:
    """
    Estimate roof pitch from shadow length.

    tan(pitch) = roof_height / (roof_width / 2)
    roof_height = shadow_length × tan(sun_elevation)

    Returns (pitch_degrees, confidence 0-100)
    """
    if sun_elevation_deg < 10:
        # Sun too low — shadows unreliable
        return 20.0, 25  # typical Indian roof fallback

    sun_elev_rad = math.radians(sun_elevation_deg)
    roof_height_px = shadow_length_px * math.tan(sun_elev_rad)

    # Estimate roof half-width as fraction of image width
    roof_half_width = image_width * 0.25  # rough assumption

    pitch_rad = math.atan2(roof_height_px, roof_half_width)
    pitch_deg = math.degrees(pitch_rad)

    # Clamp to realistic range
    pitch_deg = max(5.0, min(55.0, pitch_deg))

    # Confidence based on sun elevation
    if 25 <= sun_elevation_deg <= 55:
        confidence = 75
    elif 15 <= sun_elevation_deg < 25:
        confidence = 60
    else:
        confidence = 45

    # Reduce confidence if shadow is very short
    if shadow_length_px < 15:
        confidence -= 15

    return round(pitch_deg, 1), max(20, min(85, confidence))


def analyze_shadow(
    image: np.ndarray,
    roof_mask: np.ndarray,
    lat: float,
    lng: float,
    capture_time: Optional[datetime] = None,
) -> ShadowAnalysisResult:
    """
    Full shadow analysis pipeline.
    Falls back gracefully if no shadow is detected.
    """
    h, w = image.shape[:2]
    sun_elevation, sun_azimuth = get_sun_position(lat, lng, capture_time)

    # Try shadow detection
    shadow_mask = detect_shadow_region(image, roof_mask)
    shadow_length = measure_shadow_length(shadow_mask, roof_mask)

    if shadow_length is not None and sun_elevation > 5:
        pitch, confidence = pitch_from_shadow(shadow_length, sun_elevation, w)
        method = 'shadow_analysis' if HAS_PVLIB else 'shadow_analysis_approx'
    else:
        # No usable shadow — use typical regional pitch
        pitch = 20.0
        confidence = 35
        shadow_length = 0.0
        method = 'fallback_typical'

    return ShadowAnalysisResult(
        pitch_degrees=pitch,
        confidence=confidence,
        shadow_length_px=round(shadow_length, 1),
        sun_elevation_degrees=round(sun_elevation, 1),
        sun_azimuth_degrees=round(sun_azimuth, 1),
        method=method,
    )
