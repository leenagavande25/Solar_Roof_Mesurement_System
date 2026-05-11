"""
energy_calculator.py
────────────────────
Calculates solar panel count and yearly energy production
from roof area, pitch, orientation, and location.

Uses the standard formula:
    E = P_system × H_sun × PR

where:
    P_system  = total panel capacity (kWp)
    H_sun     = peak sun hours per year at location
    PR        = performance ratio (default 0.75)
"""

import math
from dataclasses import dataclass


@dataclass
class EnergyResult:
    max_panels: int
    panel_capacity_w: int
    system_capacity_kw: float
    yearly_energy_kwh: int
    sunshine_hours: int
    tilt_factor: float          # correction for non-optimal pitch
    orientation_factor: float   # correction for non-south orientation
    usable_area_m2: float


# Standard panel dimensions (metres)
PANEL_WIDTH_M  = 1.0
PANEL_HEIGHT_M = 1.65
PANEL_AREA_M2  = PANEL_WIDTH_M * PANEL_HEIGHT_M   # 1.65 m²
PANEL_CAPACITY_W = 400

# Area utilisation factor (spacing, edges, obstructions)
AREA_UTILISATION = 0.75

# Performance ratio (wiring losses, temperature, soiling)
PERFORMANCE_RATIO = 0.75

# Average peak sun hours for major Indian cities (hours/year)
INDIA_SUNSHINE = {
    # lat_min, lat_max, sunshine_hours
    (8,  14):  1900,   # Kerala, Tamil Nadu
    (14, 20):  1850,   # Karnataka, Andhra Pradesh, Maharashtra (south)
    (20, 25):  1820,   # Maharashtra (north), Madhya Pradesh, Gujarat
    (25, 30):  1780,   # Rajasthan, Uttar Pradesh, Bihar
    (30, 38):  1700,   # Punjab, Himachal Pradesh, J&K
}

def get_sunshine_hours(lat: float) -> int:
    """Estimate annual peak sun hours based on latitude (India)."""
    for (lat_min, lat_max), hours in INDIA_SUNSHINE.items():
        if lat_min <= abs(lat) < lat_max:
            return hours
    return 1800  # global default


def tilt_factor(pitch_deg: float, lat: float) -> float:
    """
    Correction factor for roof tilt vs optimal tilt angle.
    Optimal tilt ≈ latitude for fixed panels.
    Based on simplified PVGIS formula.
    """
    optimal = abs(lat)
    diff = abs(pitch_deg - optimal)
    # Penalty: ~0.5% per degree deviation
    return max(0.7, 1.0 - diff * 0.005)


def orientation_factor(azimuth_deg: float) -> float:
    """
    Correction factor for roof orientation.
    South-facing (180°) = 1.0 (northern hemisphere)
    North-facing (0°/360°) = 0.6
    """
    # Deviation from south
    south = 180.0
    diff = abs(((azimuth_deg - south) + 180) % 360 - 180)
    # Cosine taper: 0° diff → 1.0, 90° diff → 0.7, 180° diff → 0.6
    return round(0.6 + 0.4 * math.cos(math.radians(diff * 0.9)), 3)


def calculate_energy(
    roof_area_m2: float,
    pitch_degrees: float,
    orientation_degrees: float,
    lat: float = 20.0,
    panel_capacity_w: int = PANEL_CAPACITY_W,
) -> EnergyResult:
    """
    Calculate panel count and energy production.
    """
    # Usable area after spacing/edge margins
    usable_area = roof_area_m2 * AREA_UTILISATION

    # Number of panels that fit
    max_panels = max(0, int(usable_area / PANEL_AREA_M2))

    # System capacity
    system_kw = round(max_panels * panel_capacity_w / 1000, 2)

    # Sunshine hours for location
    sunshine_hours = get_sunshine_hours(lat)

    # Correction factors
    t_factor = tilt_factor(pitch_degrees, lat)
    o_factor = orientation_factor(orientation_degrees)

    # Energy: E = P × H × PR × tilt_factor × orientation_factor
    yearly_kwh = int(system_kw * sunshine_hours * PERFORMANCE_RATIO * t_factor * o_factor)

    return EnergyResult(
        max_panels=max_panels,
        panel_capacity_w=panel_capacity_w,
        system_capacity_kw=system_kw,
        yearly_energy_kwh=yearly_kwh,
        sunshine_hours=sunshine_hours,
        tilt_factor=round(t_factor, 3),
        orientation_factor=round(o_factor, 3),
        usable_area_m2=round(usable_area, 1),
    )
