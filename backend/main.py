"""
main.py  —  Solar Roof Analysis Backend v3
──────────────────────────────────────────
FastAPI server with complete pipeline:
  1. Roof detection (GrabCut + center-bias)
  2. Pixel polygon → lat/lon coordinates (Web Mercator inverse)
  3. Accurate area in m² (UTM projection via pyproj)
  4. Shadow-adjusted usable area
  5. Solar panel count
  6. Centroid (lat, lon)
  7. Extended metrics: energy, CO2, cost, payback
  8. CSV storage (thread-safe, appended per analysis)
  9. Full JSON response

Endpoints
─────────
POST /analyze          — main analysis (image upload)
POST /analyze/polygon  — analysis from raw lat/lon polygon
GET  /results          — list all stored CSV records
GET  /results/download — download results.csv
GET  /health           — health check
"""

import io
import base64
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from utils.roof_detector       import detect_roof
from utils.shadow_analyzer     import analyze_shadow
from utils.orientation_detector import detect_orientation
from utils.polygon_utils       import (
    pixels_to_latlon,
    polygon_area_m2,
    polygon_centroid,
    usable_area,
    estimate_panels,
    efficiency_score,
)
from utils.extended_calculator import calculate_extended
from utils.csv_store           import append_result, read_all, get_csv_path


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Solar Roof Analysis API v3",
    description=(
        "Complete rooftop solar analysis: polygon extraction, "
        "accurate area (pyproj UTM), energy generation, CO2 savings, "
        "installation cost, CSV storage."
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class SegmentOut(BaseModel):
    label:       str
    orientation: float
    pitch:       float
    area_m2:     float

class PolygonAnalysisRequest(BaseModel):
    """For /analyze/polygon — accepts raw lat/lon polygon."""
    polygon:          List[List[float]] = Field(..., description="[[lat,lon], ...]")
    lat:              float
    lng:              float
    shadow_fraction:  float = Field(0.0, ge=0.0, le=1.0)
    pitch_degrees:    float = Field(20.0, ge=0.0, le=60.0)
    azimuth_degrees:  float = Field(180.0, ge=0.0, le=360.0)
    address:          str   = ""

class AnalysisResponse(BaseModel):
    # Record
    record_id:              str
    capture_utc:            str

    # Polygon & geometry
    polygon_latlon:         List[List[float]]   # [[lat, lon], ...]
    centroid_lat:           float
    centroid_lon:           float
    total_area_m2:          float
    usable_area_m2:         float
    shadow_fraction:        float

    # Pitch & orientation
    pitch_degrees:          float
    pitch_confidence:       int
    orientation_degrees:    float
    orientation_label:      str
    orientation_confidence: int
    efficiency_score:       float

    # Panels
    panels_count:           int
    panel_area_m2:          float
    panel_capacity_w:       int
    system_capacity_kwp:    float

    # Energy
    annual_energy_kwh:      int
    peak_sun_hours:         int
    tilt_factor:            float
    orientation_factor:     float

    # CO2
    co2_saved_kg_year:      float
    co2_saved_tons_year:    float
    trees_equivalent:       int

    # Cost
    gross_cost_inr:         int
    subsidy_inr:            int
    net_cost_inr:           int
    cost_category:          str
    annual_savings_inr:     int
    payback_years:          float
    lifetime_savings_inr:   int

    # Roof segments
    segments:               List[SegmentOut]

    # Debug
    detection_method:       str
    analysis_method:        str
    shadow_length_px:       float
    sun_elevation_degrees:  float

    # Processed image
    processed_image_url:    Optional[str]

    # Warnings
    warnings:               List[str]

    # CSV
    csv_path:               str


# ── Image helpers ─────────────────────────────────────────────────────────────

def decode_image(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Cannot decode image. Upload JPEG or PNG.")
    return img

def encode_b64(img: np.ndarray, quality: int = 88) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


# ── Warning builder ───────────────────────────────────────────────────────────

def build_warnings(
    detection_method: str,
    shadow_method:    str,
    pitch_conf:       int,
    orient_conf:      int,
    shadow_frac:      float,
) -> List[str]:
    w: List[str] = []

    if detection_method == "fallback":
        w.append("Roof boundary not detected — using center crop. Zoom in closer.")
    elif detection_method == "watershed":
        w.append("Fallback detection used. Accuracy may be lower.")

    if shadow_method == "fallback_typical":
        w.append("No shadow found — pitch defaulted to 20° (regional typical).")
    elif pitch_conf < 60:
        w.append(f"Low pitch confidence ({pitch_conf}%). Capture between 10am–3pm for clearer shadows.")

    if orient_conf < 60:
        w.append(f"Low orientation confidence ({orient_conf}%). Few ridge lines detected.")

    if shadow_frac > 0.40:
        w.append(f"High shadow coverage ({shadow_frac*100:.0f}%) — usable area significantly reduced.")

    return w


# ── Core pipeline (shared by both endpoints) ──────────────────────────────────

def run_full_pipeline(
    img:              Optional[np.ndarray],
    lat:              float,
    lng:              float,
    zoom:             int,
    shadow_fraction:  float,
    capture_time:     datetime,
    address:          str,
    # Optional overrides (used by /analyze/polygon)
    polygon_latlon_override: Optional[List] = None,
    pitch_override:   Optional[float] = None,
    azimuth_override: Optional[float] = None,
) -> AnalysisResponse:

    PANEL_AREA_M2    = 1.6
    PANEL_CAPACITY_W = 400
    EFF_FACTOR       = 0.75

    # ── Step 1: Roof detection ────────────────────────────────────────────────
    if img is not None:
        roof = detect_roof(img, lat=lat, zoom=zoom)
        h, w_img = img.shape[:2]

        # Extract pixel polygon vertices
        pixel_pts = [(int(pt[0][0]), int(pt[0][1])) for pt in roof.polygon]

        # Convert to lat/lon
        polygon_latlon = pixels_to_latlon(
            pixel_pts, w_img, h, lat, lng, zoom
        )

        detection_method = roof.method
        annotated_b64    = encode_b64(roof.annotated_image)

    else:
        # Polygon provided directly — skip image detection
        polygon_latlon   = polygon_latlon_override or []
        detection_method = "polygon_input"
        annotated_b64    = None

    # ── Step 2: Accurate area via UTM projection ──────────────────────────────
    total_area = polygon_area_m2(polygon_latlon)

    # Fallback: if polygon too small (detection failed) use pixel area
    if img is not None and total_area < 1.0:
        total_area = roof.area_m2

    # ── Step 3: Centroid ──────────────────────────────────────────────────────
    centroid = polygon_centroid(polygon_latlon) if polygon_latlon else (lat, lng)
    centroid_lat, centroid_lon = centroid

    # ── Step 4: Shadow-adjusted usable area ───────────────────────────────────
    usable = usable_area(total_area, shadow_fraction)

    # ── Step 5: Shadow analysis → pitch (if image available) ─────────────────
    if img is not None and pitch_override is None:
        shadow_res = analyze_shadow(
            img, roof.mask, lat=lat, lng=lng, capture_time=capture_time
        )
        pitch_deg    = shadow_res.pitch_degrees
        pitch_conf   = shadow_res.confidence
        shadow_len   = shadow_res.shadow_length_px
        sun_elev     = shadow_res.sun_elevation_degrees
        analysis_method = shadow_res.method
    else:
        pitch_deg    = pitch_override or 20.0
        pitch_conf   = 100 if pitch_override else 50
        shadow_len   = 0.0
        sun_elev     = 0.0
        analysis_method = "manual_input" if pitch_override else "fallback_typical"

    # ── Step 6: Orientation (if image available) ──────────────────────────────
    if img is not None and azimuth_override is None:
        from utils.shadow_analyzer import get_sun_position
        _, sun_az = get_sun_position(lat, lng, capture_time)
        orient_res       = detect_orientation(img, roof.mask, total_area, sun_az)
        azimuth_deg      = orient_res.azimuth_degrees
        orient_conf      = orient_res.confidence
        orient_label     = orient_res.direction_label
        segments_raw     = orient_res.segments
    else:
        azimuth_deg  = azimuth_override or 180.0
        orient_conf  = 100 if azimuth_override else 50
        from utils.polygon_utils import efficiency_score as _ef
        orient_label = _direction_label(azimuth_deg)
        segments_raw = []

    # Inject pitch into segments
    for seg in segments_raw:
        seg["pitch"] = pitch_deg

    # ── Step 7: Panel count ───────────────────────────────────────────────────
    panels = estimate_panels(usable, PANEL_AREA_M2, EFF_FACTOR)

    # ── Step 8: Efficiency score ──────────────────────────────────────────────
    eff_score = efficiency_score(pitch_deg, azimuth_deg, shadow_fraction, lat)

    # ── Step 9: Extended metrics ──────────────────────────────────────────────
    ext = calculate_extended(
        panels       = panels,
        pitch_deg    = pitch_deg,
        azimuth_deg  = azimuth_deg,
        lat          = lat,
        panel_capacity_w = PANEL_CAPACITY_W,
    )

    # ── Step 10: Build warnings ───────────────────────────────────────────────
    warnings = build_warnings(
        detection_method, analysis_method, pitch_conf, orient_conf, shadow_fraction
    )

    # ── Step 11: CSV storage ──────────────────────────────────────────────────
    record_id = append_result(
        centroid_lat          = centroid_lat,
        centroid_lon          = centroid_lon,
        polygon               = polygon_latlon,
        total_area_m2         = total_area,
        usable_area_m2        = usable,
        shadow_fraction       = shadow_fraction,
        panels_count          = panels,
        panel_capacity_w      = PANEL_CAPACITY_W,
        system_capacity_kwp   = ext.system_capacity_kwp,
        efficiency_score      = eff_score,
        pitch_degrees         = pitch_deg,
        orientation_degrees   = azimuth_deg,
        orientation_label     = orient_label,
        pitch_confidence      = pitch_conf,
        orientation_confidence= orient_conf,
        detection_method      = detection_method,
        analysis_method       = analysis_method,
        annual_energy_kwh     = ext.annual_energy_kwh,
        co2_saved_kg_year     = ext.co2_saved_kg_year,
        co2_saved_tons_year   = ext.co2_saved_tons_year,
        trees_equivalent      = ext.trees_equivalent,
        gross_cost_inr        = ext.gross_cost_inr,
        subsidy_inr           = ext.subsidy_inr,
        net_cost_inr          = ext.net_cost_inr,
        annual_savings_inr    = ext.annual_savings_inr,
        payback_years         = ext.payback_years,
        lifetime_savings_inr  = ext.lifetime_savings_inr,
        cost_category         = ext.cost_category,
        peak_sun_hours        = ext.peak_sun_hours,
        tilt_factor           = ext.tilt_factor,
        orientation_factor    = ext.orientation_factor,
        address               = address,
    )

    # ── Step 12: Build response ───────────────────────────────────────────────
    return AnalysisResponse(
        record_id              = record_id,
        capture_utc            = capture_time.isoformat(),
        polygon_latlon         = [[lat, lon] for (lat, lon) in polygon_latlon],
        centroid_lat           = centroid_lat,
        centroid_lon           = centroid_lon,
        total_area_m2          = total_area,
        usable_area_m2         = usable,
        shadow_fraction        = shadow_fraction,
        pitch_degrees          = pitch_deg,
        pitch_confidence       = pitch_conf,
        orientation_degrees    = azimuth_deg,
        orientation_label      = orient_label,
        orientation_confidence = orient_conf,
        efficiency_score       = eff_score,
        panels_count           = panels,
        panel_area_m2          = PANEL_AREA_M2,
        panel_capacity_w       = PANEL_CAPACITY_W,
        system_capacity_kwp    = ext.system_capacity_kwp,
        annual_energy_kwh      = ext.annual_energy_kwh,
        peak_sun_hours         = ext.peak_sun_hours,
        tilt_factor            = ext.tilt_factor,
        orientation_factor     = ext.orientation_factor,
        co2_saved_kg_year      = ext.co2_saved_kg_year,
        co2_saved_tons_year    = ext.co2_saved_tons_year,
        trees_equivalent       = ext.trees_equivalent,
        gross_cost_inr         = ext.gross_cost_inr,
        subsidy_inr            = ext.subsidy_inr,
        net_cost_inr           = ext.net_cost_inr,
        cost_category          = ext.cost_category,
        annual_savings_inr     = ext.annual_savings_inr,
        payback_years          = ext.payback_years,
        lifetime_savings_inr   = ext.lifetime_savings_inr,
        segments               = [SegmentOut(
                                    label       = s["label"],
                                    orientation = s["orientation"],
                                    pitch       = s["pitch"],
                                    area_m2     = s["area"],
                                  ) for s in segments_raw],
        detection_method       = detection_method,
        analysis_method        = analysis_method,
        shadow_length_px       = shadow_len,
        sun_elevation_degrees  = sun_elev,
        processed_image_url    = annotated_b64 if annotated_b64 else None,
        warnings               = warnings,
        csv_path               = get_csv_path(),
    )


def _direction_label(deg: float) -> str:
    DIRS = [
        (22.5,"North"),(67.5,"North-East"),(112.5,"East"),(157.5,"South-East"),
        (202.5,"South"),(247.5,"South-West"),(292.5,"West"),(337.5,"North-West"),(360.1,"North"),
    ]
    d = deg % 360
    for thr, lbl in DIRS:
        if d < thr:
            return lbl
    return "North"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=AnalysisResponse, summary="Analyze from satellite image")
async def analyze_from_image(
    image:           UploadFile = File(..., description="Satellite/aerial roof JPEG or PNG"),
    lat:             float      = Form(..., description="Latitude of building center"),
    lng:             float      = Form(..., description="Longitude of building center"),
    zoom:            int        = Form(19,  description="Leaflet zoom level (17-21)"),
    shadow_fraction: float      = Form(0.0, description="Shadow coverage 0.0-1.0"),
    address:         str        = Form("",  description="Human-readable address"),
):
    """
    Main analysis endpoint.
    Accepts satellite image + coordinates from Leaflet map capture.

    Pipeline:
      Image → roof detection → lat/lon polygon → accurate area (UTM)
      → shadow usable area → panels → energy → CO2 → cost → CSV
    """
    capture_time = datetime.now(timezone.utc)

    # Validate
    if not (-90 <= lat <= 90):
        raise HTTPException(400, "Invalid latitude.")
    if not (-180 <= lng <= 180):
        raise HTTPException(400, "Invalid longitude.")
    if image.content_type not in ("image/jpeg", "image/jpg", "image/png", "image/webp"):
        raise HTTPException(400, "Unsupported image type. Use JPEG or PNG.")
    shadow_fraction = max(0.0, min(1.0, shadow_fraction))

    raw = await image.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 25 MB).")

    img = decode_image(raw)

    return run_full_pipeline(
        img             = img,
        lat             = lat,
        lng             = lng,
        zoom            = zoom,
        shadow_fraction = shadow_fraction,
        capture_time    = capture_time,
        address         = address,
    )


@app.post("/analyze/polygon", response_model=AnalysisResponse,
          summary="Analyze from lat/lon polygon (no image)")
async def analyze_from_polygon(req: PolygonAnalysisRequest):
    """
    Accepts raw lat/lon polygon instead of image.
    Useful when polygon comes from another source (GIS tool, manual drawing, etc.)

    Example request body:
    {
      "polygon": [[18.520, 73.856], [18.521, 73.857], [18.519, 73.858]],
      "lat": 18.520,
      "lng": 73.856,
      "shadow_fraction": 0.15,
      "pitch_degrees": 22.0,
      "azimuth_degrees": 175.0,
      "address": "Infosys Campus, Pune"
    }
    """
    capture_time = datetime.now(timezone.utc)
    polygon_latlon = [(pt[0], pt[1]) for pt in req.polygon]

    return run_full_pipeline(
        img                     = None,
        lat                     = req.lat,
        lng                     = req.lng,
        zoom                    = 19,
        shadow_fraction         = req.shadow_fraction,
        capture_time            = capture_time,
        address                 = req.address,
        polygon_latlon_override = polygon_latlon,
        pitch_override          = req.pitch_degrees,
        azimuth_override        = req.azimuth_degrees,
    )


@app.get("/results", summary="List all stored analysis results")
async def list_results():
    """Return all records stored in results.csv as JSON."""
    records = read_all()
    return {
        "count":   len(records),
        "csv":     get_csv_path(),
        "records": records,
    }


@app.get("/results/download", summary="Download results.csv")
async def download_csv():
    """Download the results CSV file directly."""
    path = Path(get_csv_path())
    if not path.exists():
        raise HTTPException(404, "No results yet. Run /analyze first.")
    return FileResponse(
        path        = str(path),
        filename    = "solar_roof_results.csv",
        media_type  = "text/csv",
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/")
async def root():
    return {
        "service":   "Solar Roof Analysis API v3",
        "endpoints": {
            "analyze_image":   "POST /analyze",
            "analyze_polygon": "POST /analyze/polygon",
            "list_results":    "GET  /results",
            "download_csv":    "GET  /results/download",
            "swagger_ui":      "GET  /docs",
            "health":          "GET  /health",
        }
    }
