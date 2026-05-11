"""
csv_store.py
────────────
Thread-safe CSV storage for rooftop analysis results.

Each call to append_result() creates or appends one row to results.csv.
Uses file locking (threading.Lock) to prevent concurrent write corruption.

CSV Schema
──────────
id                   : UUID (auto-generated)
timestamp            : ISO-8601 UTC
address              : reverse-geocoded address or lat/lng string
centroid_lat         : float
centroid_lon         : float
polygon_points       : JSON string of [(lat,lon), ...]
total_area_m2        : float  — full detected roof area
usable_area_m2       : float  — after shadow deduction
shadow_fraction      : float  — 0.0–1.0
panels_count         : int
panel_capacity_w     : int    — Wp per panel
system_capacity_kwp  : float
efficiency_score     : float  — 0–100
pitch_degrees        : float
orientation_degrees  : float
orientation_label    : str    — 'South', 'North-East', etc.
pitch_confidence     : int
orientation_confidence: int
detection_method     : str    — grabcut | watershed | fallback
annual_energy_kwh    : int
co2_saved_kg_year    : float
co2_saved_tons_year  : float
trees_equivalent     : int
gross_cost_inr       : int
subsidy_inr          : int
net_cost_inr         : int
annual_savings_inr   : int
payback_years        : float
lifetime_savings_inr : int
cost_category        : str
peak_sun_hours       : int
tilt_factor          : float
orientation_factor   : float
analysis_method      : str    — shadow_analysis | fallback_typical
"""

import csv
import json
import threading
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from utils.polygon_utils import LatLon


# ── Config ────────────────────────────────────────────────────────────────────

CSV_PATH = Path(os.getenv("CSV_PATH", "results.csv"))

CSV_COLUMNS = [
    "id",
    "timestamp",
    "address",
    "centroid_lat",
    "centroid_lon",
    "polygon_points",
    "total_area_m2",
    "usable_area_m2",
    "shadow_fraction",
    "panels_count",
    "panel_capacity_w",
    "system_capacity_kwp",
    "efficiency_score",
    "pitch_degrees",
    "orientation_degrees",
    "orientation_label",
    "pitch_confidence",
    "orientation_confidence",
    "detection_method",
    "annual_energy_kwh",
    "co2_saved_kg_year",
    "co2_saved_tons_year",
    "trees_equivalent",
    "gross_cost_inr",
    "subsidy_inr",
    "net_cost_inr",
    "annual_savings_inr",
    "payback_years",
    "lifetime_savings_inr",
    "cost_category",
    "peak_sun_hours",
    "tilt_factor",
    "orientation_factor",
    "analysis_method",
]

# Thread lock to prevent concurrent write corruption
_write_lock = threading.Lock()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ensure_header():
    """Create CSV file with header row if it doesn't exist."""
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()


def _serialize_polygon(polygon: Optional[List[LatLon]]) -> str:
    """Serialize polygon points to JSON string for CSV storage."""
    if not polygon:
        return "[]"
    return json.dumps([[round(lat, 6), round(lon, 6)] for (lat, lon) in polygon])


# ── Public API ────────────────────────────────────────────────────────────────

def append_result(
    # Geometry
    centroid_lat:          float,
    centroid_lon:          float,
    polygon:               Optional[List[LatLon]],
    total_area_m2:         float,
    usable_area_m2:        float,
    shadow_fraction:       float,

    # Panels
    panels_count:          int,
    panel_capacity_w:      int,
    system_capacity_kwp:   float,
    efficiency_score:      float,

    # Orientation & pitch
    pitch_degrees:         float,
    orientation_degrees:   float,
    orientation_label:     str,
    pitch_confidence:      int,
    orientation_confidence: int,
    detection_method:      str,
    analysis_method:       str,

    # Extended metrics
    annual_energy_kwh:     int,
    co2_saved_kg_year:     float,
    co2_saved_tons_year:   float,
    trees_equivalent:      int,
    gross_cost_inr:        int,
    subsidy_inr:           int,
    net_cost_inr:          int,
    annual_savings_inr:    int,
    payback_years:         float,
    lifetime_savings_inr:  int,
    cost_category:         str,
    peak_sun_hours:        int,
    tilt_factor:           float,
    orientation_factor:    float,

    # Optional
    address:               str = "",
) -> str:
    """
    Append one rooftop analysis result to the CSV file.

    Thread-safe: uses a threading.Lock to prevent concurrent writes.

    Returns
    -------
    str : the UUID assigned to this record
    """
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    row = {
        "id":                    record_id,
        "timestamp":             timestamp,
        "address":               address,
        "centroid_lat":          round(centroid_lat, 7),
        "centroid_lon":          round(centroid_lon, 7),
        "polygon_points":        _serialize_polygon(polygon),
        "total_area_m2":         total_area_m2,
        "usable_area_m2":        usable_area_m2,
        "shadow_fraction":       round(shadow_fraction, 3),
        "panels_count":          panels_count,
        "panel_capacity_w":      panel_capacity_w,
        "system_capacity_kwp":   system_capacity_kwp,
        "efficiency_score":      efficiency_score,
        "pitch_degrees":         pitch_degrees,
        "orientation_degrees":   orientation_degrees,
        "orientation_label":     orientation_label,
        "pitch_confidence":      pitch_confidence,
        "orientation_confidence": orientation_confidence,
        "detection_method":      detection_method,
        "annual_energy_kwh":     annual_energy_kwh,
        "co2_saved_kg_year":     co2_saved_kg_year,
        "co2_saved_tons_year":   co2_saved_tons_year,
        "trees_equivalent":      trees_equivalent,
        "gross_cost_inr":        gross_cost_inr,
        "subsidy_inr":           subsidy_inr,
        "net_cost_inr":          net_cost_inr,
        "annual_savings_inr":    annual_savings_inr,
        "payback_years":         payback_years,
        "lifetime_savings_inr":  lifetime_savings_inr,
        "cost_category":         cost_category,
        "peak_sun_hours":        peak_sun_hours,
        "tilt_factor":           tilt_factor,
        "orientation_factor":    orientation_factor,
        "analysis_method":       analysis_method,
    }

    with _write_lock:
        _ensure_header()
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row)

    return record_id


def read_all() -> List[dict]:
    """Read all records from the CSV as a list of dicts."""
    if not CSV_PATH.exists():
        return []
    with _write_lock:
        with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)


def get_csv_path() -> str:
    """Return absolute path to the CSV file."""
    return str(CSV_PATH.resolve())
