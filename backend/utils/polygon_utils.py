"""
polygon_utils.py
────────────────
Converts pixel-space roof polygons into geospatial coordinates (lat/lon)
and calculates accurate area in m² using pyproj UTM projection.

WHY LAT/LON AREA CALCULATION FAILS
────────────────────────────────────
If you compute area directly from lat/lon coordinates using Shapely:
    polygon = Polygon([(lon1,lat1), (lon2,lat2), ...])
    area = polygon.area   ← WRONG: gives degrees², NOT metres²

At latitude 18° (Pune):
    1° latitude  ≈ 111,000 m
    1° longitude ≈ 105,000 m   (shrinks with cos(lat))
    → 1 deg² ≈ 11.655 billion m²  (not a fixed conversion)

CORRECT APPROACH: Project lat/lon → UTM (metres) → compute area
    UTM is a local Cartesian projection where 1 unit = 1 metre.
    Use the UTM zone that contains the polygon centroid.

COMMON MISTAKES IN PANEL ESTIMATION
─────────────────────────────────────
1. Using total roof area instead of usable area
   Fix: apply efficiency_factor (0.75) for spacing/tilt
2. Using panel power (Wp) instead of panel physical size
   Fix: use panel_area_m2 = 1.6 m² (standard 60-cell panel)
3. Not accounting for roof pitch
   Fix: actual surface area = projected area / cos(pitch)
4. Integer truncation vs rounding
   Fix: always use int(floor(...)) — you can't install half a panel
"""

import math
from typing import List, Tuple, Optional

import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import transform
import pyproj


# ── Types ─────────────────────────────────────────────────────────────────────
LatLon   = Tuple[float, float]          # (lat, lon)
PixelPt  = Tuple[int, int]              # (x, y)
Polygon2D = List[Tuple[float, float]]   # list of (x,y) or (lat,lon)


# ── Coordinate conversion ──────────────────────────────────────────────────────

def pixels_to_latlon(
    pixel_points: List[PixelPt],
    image_width:  int,
    image_height: int,
    center_lat:   float,
    center_lon:   float,
    zoom:         int,
) -> List[LatLon]:
    """
    Convert pixel coordinates (from OpenCV polygon) to (lat, lon).

    Uses the Web Mercator inverse tile formula:
        lat = 2*atan(exp(π - 2π*y_merc/2^zoom)) - π/2
        lon = 360 * x_merc / 2^zoom - 180

    Parameters
    ----------
    pixel_points  : list of (x, y) from OpenCV contour
    image_width   : captured image width in pixels
    image_height  : captured image height in pixels
    center_lat    : latitude of image center (where crosshair was)
    center_lon    : longitude of image center
    zoom          : Leaflet zoom level

    Returns
    -------
    List of (lat, lon) tuples
    """
    n = 2 ** zoom  # number of tiles at this zoom

    # Tile coordinates of image center
    center_tile_x = (center_lon + 180) / 360 * n
    center_tile_y = (1 - math.log(
        math.tan(math.radians(center_lat)) +
        1 / math.cos(math.radians(center_lat))
    ) / math.pi) / 2 * n

    # Meters per pixel at this zoom (Web Mercator)
    # Each tile is 256×256 pixels
    mpp = 156_543.03 * math.cos(math.radians(center_lat)) / n
    tile_size = 256  # standard Web Mercator tile

    results: List[LatLon] = []
    for (px, py) in pixel_points:
        # Offset from image center in pixels
        dx = px - image_width  / 2
        dy = py - image_height / 2

        # Convert pixel offset → tile offset
        tile_dx = dx / tile_size
        tile_dy = dy / tile_size

        # Absolute tile coordinates
        tile_x = center_tile_x + tile_dx
        tile_y = center_tile_y + tile_dy

        # Tile coords → lat/lon
        lon = tile_x / n * 360 - 180
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
        lat = math.degrees(lat_rad)

        results.append((round(lat, 7), round(lon, 7)))

    return results


# ── UTM zone selection ────────────────────────────────────────────────────────

def get_utm_crs(lat: float, lon: float) -> str:
    """
    Return the EPSG code for the UTM zone containing (lat, lon).
    Example: lat=18.5, lon=73.8 → 'EPSG:32643'  (WGS84 / UTM zone 43N)
    """
    zone = int((lon + 180) / 6) + 1
    if lat >= 0:
        return f"EPSG:{32600 + zone}"   # Northern hemisphere
    else:
        return f"EPSG:{32700 + zone}"   # Southern hemisphere


# ── Accurate area calculation ─────────────────────────────────────────────────

def polygon_area_m2(latlon_polygon: List[LatLon]) -> float:
    """
    Calculate polygon area in m² using UTM projection.

    Steps:
    1. Build Shapely Polygon from (lat, lon) pairs → note (lon, lat) order for WKT
    2. Reproject from WGS84 (EPSG:4326) to local UTM zone
    3. Compute area in m² (UTM units are metres)

    Parameters
    ----------
    latlon_polygon : list of (lat, lon) tuples (at least 3 points)

    Returns
    -------
    area in square metres (float)
    """
    if len(latlon_polygon) < 3:
        return 0.0

    # Shapely uses (lon, lat) order — (x, y) convention
    lonlat_pts = [(lon, lat) for (lat, lon) in latlon_polygon]
    poly_wgs84 = Polygon(lonlat_pts)

    if not poly_wgs84.is_valid:
        poly_wgs84 = poly_wgs84.buffer(0)   # auto-fix self-intersections

    # Choose UTM CRS from centroid
    centroid = poly_wgs84.centroid
    utm_crs = get_utm_crs(centroid.y, centroid.x)

    # Project WGS84 → UTM
    wgs84  = pyproj.CRS("EPSG:4326")
    utm    = pyproj.CRS(utm_crs)
    project = pyproj.Transformer.from_crs(
        wgs84, utm, always_xy=True
    ).transform

    poly_utm = transform(project, poly_wgs84)
    return round(float(poly_utm.area), 2)


# ── Centroid calculation ──────────────────────────────────────────────────────

def polygon_centroid(latlon_polygon: List[LatLon]) -> LatLon:
    """
    Compute centroid of a lat/lon polygon.
    Returns (centroid_lat, centroid_lon).

    Uses Shapely for geometric centroid (NOT simple average of coordinates,
    which is wrong for non-convex or irregular polygons).
    """
    if not latlon_polygon:
        return (0.0, 0.0)

    lonlat_pts = [(lon, lat) for (lat, lon) in latlon_polygon]
    poly = Polygon(lonlat_pts)
    if not poly.is_valid:
        poly = poly.buffer(0)

    c = poly.centroid
    return (round(c.y, 7), round(c.x, 7))   # return as (lat, lon)


# ── Shadow-adjusted usable area ───────────────────────────────────────────────

def usable_area(total_area_m2: float, shadow_fraction: float = 0.0) -> float:
    """
    Reduce total roof area by shadow coverage.

    Parameters
    ----------
    total_area_m2   : full detected roof area
    shadow_fraction : 0.0–1.0 (0 = no shadow, 1 = fully shaded)

    Returns
    -------
    usable area in m²
    """
    shadow_fraction = max(0.0, min(1.0, shadow_fraction))
    return round(total_area_m2 * (1 - shadow_fraction), 2)


# ── Panel count ───────────────────────────────────────────────────────────────

def estimate_panels(
    usable_area_m2: float,
    panel_area_m2:  float = 1.6,
    efficiency_factor: float = 0.75,
) -> int:
    """
    Calculate number of solar panels that fit on the usable roof area.

    Formula:
        panels = floor( usable_area * efficiency_factor / panel_area )

    Parameters
    ----------
    usable_area_m2    : area after shadow deduction
    panel_area_m2     : physical size of one panel (default 1.6 m²)
    efficiency_factor : packing efficiency 0.7–0.8 (spacing, tilt, edges)
                        default 0.75

    Returns
    -------
    integer panel count (floor, never round up)

    COMMON MISTAKES
    ───────────────
    ✗ panels = usable_area / panel_area          # ignores spacing
    ✗ panels = round(usable_area * eff / panel)  # rounding up is wrong
    ✓ panels = int(usable_area * eff / panel)    # floor division
    """
    if usable_area_m2 <= 0 or panel_area_m2 <= 0:
        return 0
    efficiency_factor = max(0.5, min(0.95, efficiency_factor))
    return int(usable_area_m2 * efficiency_factor / panel_area_m2)


# ── Efficiency score ──────────────────────────────────────────────────────────

def efficiency_score(
    pitch_deg:    float,
    azimuth_deg:  float,
    shadow_frac:  float = 0.0,
    lat:          float = 20.0,
) -> float:
    """
    Composite efficiency score 0–100 for the rooftop.

    Components:
        orientation_score : south-facing (180°) = 1.0, north = 0.5
        tilt_score        : optimal tilt ≈ latitude, 0° (flat) = 0.85
        shadow_score      : 0% shadow = 1.0, 100% shadow = 0.0

    Returns weighted average × 100.
    """
    # Orientation (south = 180° = best for northern hemisphere)
    az_diff = abs(((azimuth_deg - 180) + 180 + 360) % 360 - 180)
    orient  = max(0.0, 1.0 - az_diff / 180) * 0.5 + 0.5   # clamp min 0.5

    # Tilt (optimal ≈ latitude for India 8–35°)
    opt_tilt  = abs(lat)
    tilt_diff = abs(pitch_deg - opt_tilt)
    tilt      = max(0.5, 1.0 - tilt_diff / 60)

    # Shadow
    shadow = 1.0 - shadow_frac

    # Weighted composite
    score = orient * 0.40 + tilt * 0.35 + shadow * 0.25
    return round(score * 100, 1)
