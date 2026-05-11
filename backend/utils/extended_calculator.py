"""
extended_calculator.py
──────────────────────
Calculates extended solar metrics:
  • Annual energy generation (kWh/year)
  • CO2 savings (kg/year and tons/year)
  • Installation cost estimate (INR)
  • Payback period (years)
  • 25-year lifetime savings (INR)

FORMULAS EXPLAINED
──────────────────

1. Annual Energy (kWh/year)
   ─────────────────────────
   E = P_system × PSH × PR × tilt_factor × orientation_factor

   Where:
     P_system          = panels × panel_capacity_Wp / 1000   [kWp]
     PSH               = Peak Sun Hours per year at location  [h/yr]
     PR                = Performance Ratio (default 0.75)
                         accounts for: wiring losses, inverter efficiency,
                         soiling, temperature coefficient, mismatch
     tilt_factor       = correction for non-optimal pitch (vs optimal = lat°)
     orientation_factor= correction for non-south facing (south=1.0)

   Example: 20 panels × 400W = 8 kWp × 1820h × 0.75 × 0.97 × 0.99
          = 10,552 kWh/year

2. CO2 Savings (kg/year)
   ──────────────────────
   CO2_saved = E × grid_emission_factor

   India grid emission factor (CEA 2023): 0.82 kg CO2 per kWh
   (varies by state: coal-heavy states ~0.95, renewable-heavy ~0.65)

   CO2_saved = 10,552 × 0.82 = 8,653 kg/year = 8.65 tons/year

3. Installation Cost (INR)
   ──────────────────────────
   Cost = panels × cost_per_panel + inverter_cost + installation_labour
        + mounting_structure + wiring + net_metering_fees

   Simplified: Cost ≈ system_kWp × cost_per_kWp

   India 2024 benchmark costs:
     Residential (1–10 kWp) : ₹50,000 – ₹65,000 per kWp
     Commercial (10–100 kWp): ₹42,000 – ₹55,000 per kWp
     Industrial (>100 kWp)  : ₹35,000 – ₹45,000 per kWp

   Subsidy (PM Surya Ghar Yojana 2024):
     First 2 kWp : ₹30,000/kWp subsidy
     2–3 kWp     : ₹18,000/kWp subsidy
     >3 kWp      : no additional subsidy

4. Payback Period
   ───────────────
   Payback = Net_Cost / Annual_Savings

   Annual_Savings = E × electricity_rate_per_kWh
   India avg retail rate: ₹7–9/kWh (varies by state + slab)

5. Lifetime Savings (25 years)
   ─────────────────────────────
   Panel degradation: ~0.5% per year (Tier-1 panels)
   Year_n energy = E × (1 - 0.005)^n

   Total savings = Σ(year 1 to 25) [E_n × rate] - Net_Cost
"""

import math
from dataclasses import dataclass
from typing import Optional


# ── Constants ─────────────────────────────────────────────────────────────────

# India CEA grid emission factor 2023 (kg CO2 per kWh)
INDIA_GRID_EMISSION_KG_PER_KWH = 0.82

# Panel specs
DEFAULT_PANEL_CAPACITY_W = 400     # Wp per panel
DEFAULT_PANEL_AREA_M2    = 1.6     # m² per panel
PANEL_DEGRADATION_RATE   = 0.005   # 0.5% per year

# Performance ratio components
PERFORMANCE_RATIO = 0.75

# Installation cost benchmarks (INR per kWp, 2024)
COST_PER_KWP = {
    "residential": 57_000,   # ≤10 kWp
    "commercial":  48_000,   # 10–100 kWp
    "industrial":  40_000,   # >100 kWp
}

# PM Surya Ghar Yojana subsidy (INR per kWp, 2024)
SUBSIDY_SLAB = [
    (2.0, 30_000),    # first 2 kWp at ₹30k/kWp
    (1.0, 18_000),    # next 1 kWp at ₹18k/kWp
]

# Average electricity tariff (INR per kWh)
ELECTRICITY_RATE_INR = 8.0

# Lifetime analysis years
PANEL_LIFETIME_YEARS = 25


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class ExtendedResult:
    # Energy
    annual_energy_kwh:    int
    peak_sun_hours:       int
    performance_ratio:    float
    tilt_factor:          float
    orientation_factor:   float

    # CO2
    co2_saved_kg_year:    float
    co2_saved_tons_year:  float
    trees_equivalent:     int       # 1 tree ≈ 21 kg CO2/year

    # Cost
    system_capacity_kwp:  float
    gross_cost_inr:       int
    subsidy_inr:          int
    net_cost_inr:         int
    cost_category:        str       # residential | commercial | industrial

    # Returns
    annual_savings_inr:   int
    payback_years:        float
    lifetime_savings_inr: int       # 25-year net savings


# ── Peak sun hours by latitude (India-specific) ───────────────────────────────

def peak_sun_hours(lat: float) -> int:
    """Annual peak sun hours based on latitude band (India)."""
    bands = [
        (8,  14, 1950),   # Kerala, Tamil Nadu — high solar
        (14, 20, 1880),   # Karnataka, AP, South Maharashtra
        (20, 25, 1830),   # North Maharashtra, MP, Gujarat
        (25, 30, 1790),   # Rajasthan, UP, Bihar
        (30, 38, 1710),   # Punjab, HP, J&K
    ]
    for lo, hi, hrs in bands:
        if lo <= abs(lat) < hi:
            return hrs
    return 1800


# ── Tilt and orientation correction ──────────────────────────────────────────

def tilt_correction(pitch_deg: float, lat: float) -> float:
    """Correction factor for roof tilt vs optimal tilt ≈ latitude."""
    optimal = abs(lat)
    diff = abs(pitch_deg - optimal)
    return round(max(0.70, 1.0 - diff * 0.005), 4)


def orientation_correction(azimuth_deg: float) -> float:
    """Correction factor for roof orientation (south=1.0, north=0.60)."""
    diff = abs(((azimuth_deg - 180) + 180 + 360) % 360 - 180)
    return round(0.60 + 0.40 * math.cos(math.radians(diff * 0.9)), 4)


# ── Subsidy calculation ───────────────────────────────────────────────────────

def calculate_subsidy(system_kwp: float) -> int:
    """
    PM Surya Ghar Yojana 2024 subsidy calculation.
    Only applicable to residential rooftop (≤10 kWp).
    """
    if system_kwp > 10:
        return 0   # commercial systems not eligible

    subsidy = 0.0
    remaining = system_kwp
    for (slab_kwp, rate_per_kwp) in SUBSIDY_SLAB:
        if remaining <= 0:
            break
        allocated = min(remaining, slab_kwp)
        subsidy += allocated * rate_per_kwp
        remaining -= allocated

    return int(subsidy)


# ── 25-year lifetime savings ──────────────────────────────────────────────────

def lifetime_savings(
    annual_energy_kwh: int,
    net_cost_inr: int,
    electricity_rate: float = ELECTRICITY_RATE_INR,
    years: int = PANEL_LIFETIME_YEARS,
) -> int:
    """
    Calculate net savings over panel lifetime accounting for degradation.

    Year n energy = annual × (1 - degradation)^n
    Total revenue = Σ year_n_energy × electricity_rate
    Net savings   = Total revenue - Net installation cost
    """
    total_revenue = 0.0
    for year in range(1, years + 1):
        year_energy = annual_energy_kwh * ((1 - PANEL_DEGRADATION_RATE) ** year)
        total_revenue += year_energy * electricity_rate

    return int(total_revenue - net_cost_inr)


# ── Main calculation ──────────────────────────────────────────────────────────

def calculate_extended(
    panels:          int,
    pitch_deg:       float,
    azimuth_deg:     float,
    lat:             float,
    panel_capacity_w: int   = DEFAULT_PANEL_CAPACITY_W,
    electricity_rate: float = ELECTRICITY_RATE_INR,
) -> ExtendedResult:
    """
    Full extended calculation: energy + CO2 + cost + returns.

    Parameters
    ----------
    panels           : number of solar panels fitted
    pitch_deg        : roof pitch in degrees
    azimuth_deg      : roof orientation (0=N, 90=E, 180=S, 270=W)
    lat              : building latitude
    panel_capacity_w : Wp per panel (default 400)
    electricity_rate : local tariff in INR/kWh

    Returns
    -------
    ExtendedResult dataclass
    """
    # ── System capacity ───────────────────────────────────────────────────────
    system_kwp = round(panels * panel_capacity_w / 1000, 2)

    # ── Peak sun hours + correction factors ───────────────────────────────────
    psh    = peak_sun_hours(lat)
    t_corr = tilt_correction(pitch_deg, lat)
    o_corr = orientation_correction(azimuth_deg)

    # ── Annual energy ─────────────────────────────────────────────────────────
    annual_kwh = int(
        system_kwp * psh * PERFORMANCE_RATIO * t_corr * o_corr
    )

    # ── CO2 savings ───────────────────────────────────────────────────────────
    co2_kg   = round(annual_kwh * INDIA_GRID_EMISSION_KG_PER_KWH, 1)
    co2_tons = round(co2_kg / 1000, 2)
    trees    = int(co2_kg / 21)   # 1 tree absorbs ~21 kg CO2/year

    # ── Installation cost ─────────────────────────────────────────────────────
    if system_kwp <= 10:
        cost_cat = "residential"
    elif system_kwp <= 100:
        cost_cat = "commercial"
    else:
        cost_cat = "industrial"

    gross_cost = int(system_kwp * COST_PER_KWP[cost_cat])
    subsidy    = calculate_subsidy(system_kwp)
    net_cost   = max(0, gross_cost - subsidy)

    # ── Financial returns ─────────────────────────────────────────────────────
    annual_savings = int(annual_kwh * electricity_rate)
    payback        = round(net_cost / annual_savings, 1) if annual_savings > 0 else 0.0
    lt_savings     = lifetime_savings(annual_kwh, net_cost, electricity_rate)

    return ExtendedResult(
        annual_energy_kwh    = annual_kwh,
        peak_sun_hours       = psh,
        performance_ratio    = PERFORMANCE_RATIO,
        tilt_factor          = t_corr,
        orientation_factor   = o_corr,
        co2_saved_kg_year    = co2_kg,
        co2_saved_tons_year  = co2_tons,
        trees_equivalent     = trees,
        system_capacity_kwp  = system_kwp,
        gross_cost_inr       = gross_cost,
        subsidy_inr          = subsidy,
        net_cost_inr         = net_cost,
        cost_category        = cost_cat,
        annual_savings_inr   = annual_savings,
        payback_years        = payback,
        lifetime_savings_inr = lt_savings,
    )
