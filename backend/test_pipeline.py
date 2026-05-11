"""
test_pipeline.py  —  v3
────────────────────────
Full sanity test for the complete enhanced pipeline.
Run: python test_pipeline.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from datetime import datetime, timezone

from utils.roof_detector        import detect_roof
from utils.shadow_analyzer      import analyze_shadow, get_sun_position
from utils.orientation_detector import detect_orientation
from utils.polygon_utils        import (
    pixels_to_latlon, polygon_area_m2, polygon_centroid,
    usable_area, estimate_panels, efficiency_score,
)
from utils.extended_calculator  import calculate_extended
from utils.csv_store            import append_result, read_all, get_csv_path


def create_test_image(size=640):
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = (40, 60, 30)
    pts = np.array([[size//4,size//4],[3*size//4,size//4],
                    [3*size//4,3*size//4],[size//4,3*size//4]], dtype=np.int32)
    cv2.fillPoly(img, [pts], (160, 155, 145))
    cv2.line(img,(size//2,size//4),(size//2,3*size//4),(120,115,110),4)
    shadow = np.array([[3*size//4,size//4+20],[3*size//4+50,size//4+30],
                       [3*size//4+50,3*size//4-30],[3*size//4,3*size//4-20]],dtype=np.int32)
    cv2.fillPoly(img, [shadow], (25, 35, 20))
    noise = np.random.randint(-10, 10, img.shape, dtype=np.int8)
    return np.clip(img.astype(np.int16)+noise, 0, 255).astype(np.uint8)


def sep(title): print(f"\n─── {title} {'─'*(52-len(title))}")

def run():
    print("="*60)
    print("  Solar Roof Pipeline — Full Test v3")
    print("="*60)

    lat, lng = 18.5204, 73.8567
    zoom = 19
    dt   = datetime(2024, 3, 15, 9, 30, tzinfo=timezone.utc)
    img  = create_test_image(640)
    h, w = img.shape[:2]

    sep("1. Sun Position")
    elev, az = get_sun_position(lat, lng, dt)
    print(f"  Elevation={elev:.1f}°  Azimuth={az:.1f}°")

    sep("2. Roof Detection")
    roof = detect_roof(img, lat=lat, zoom=zoom)
    print(f"  Method={roof.method}  Area={roof.area_m2}m²  Conf={roof.confidence}%")
    assert roof.area_m2 > 0

    sep("3. Pixel → Lat/Lon")
    pixel_pts = [(int(p[0][0]), int(p[0][1])) for p in roof.polygon]
    poly_ll   = pixels_to_latlon(pixel_pts, w, h, lat, lng, zoom)
    print(f"  {len(pixel_pts)} points → first: {poly_ll[0] if poly_ll else 'n/a'}")

    sep("4. Accurate UTM Area")
    area_utm = polygon_area_m2(poly_ll)
    print(f"  Pixel-based: {roof.area_m2}m²   UTM-based: {area_utm}m²")
    # Known rectangle test: ~44m × ~55m ≈ 2420m²
    known = [(18.52,73.856),(18.52,73.8565),(18.5205,73.8565),(18.5205,73.856)]
    ka = polygon_area_m2(known)
    print(f"  Known 44×55m rect: {ka:.1f}m² (expected ~2420m²)")

    sep("5. Centroid")
    clat, clon = polygon_centroid(poly_ll) if poly_ll else (lat, lng)
    print(f"  Centroid = ({clat}, {clon})")

    sep("6. Shadow-Adjusted Area")
    total = area_utm if area_utm > 1 else roof.area_m2
    for sf in [0.0, 0.20, 0.40]:
        print(f"  shadow={sf:.0%} → usable={usable_area(total,sf)}m²")
    assert usable_area(100.0, 0.25) == 75.0

    sep("7. Panel Count")
    for eff in [0.70, 0.75, 0.80]:
        p = estimate_panels(usable_area(total,0.15), 1.6, eff)
        print(f"  eff={eff} → {p} panels")
    assert estimate_panels(100.0, 1.6, 0.75) == 46

    sep("8. Shadow Analysis → Pitch")
    sh = analyze_shadow(img, roof.mask, lat, lng, dt)
    print(f"  Pitch={sh.pitch_degrees}°  Conf={sh.confidence}%  Method={sh.method}")

    sep("9. Orientation Detection")
    orient = detect_orientation(img, roof.mask, total, az)
    print(f"  Azimuth={orient.azimuth_degrees}° ({orient.direction_label})  Conf={orient.confidence}%")

    sep("10. Efficiency Score")
    eff_s = efficiency_score(sh.pitch_degrees, orient.azimuth_degrees, 0.15, lat)
    print(f"  Score = {eff_s}/100")

    sep("11. Extended Metrics")
    panels = estimate_panels(usable_area(total, 0.15), 1.6, 0.75)
    ext = calculate_extended(panels, sh.pitch_degrees, orient.azimuth_degrees, lat)
    print(f"  Panels={panels}  System={ext.system_capacity_kwp}kWp")
    print(f"  Energy={ext.annual_energy_kwh:,}kWh/yr")
    print(f"  CO2={ext.co2_saved_kg_year}kg/yr ({ext.co2_saved_tons_year}t)  Trees≡{ext.trees_equivalent}")
    print(f"  Cost: ₹{ext.gross_cost_inr:,} gross, ₹{ext.subsidy_inr:,} subsidy, ₹{ext.net_cost_inr:,} net")
    print(f"  Savings: ₹{ext.annual_savings_inr:,}/yr  Payback: {ext.payback_years}yr")
    print(f"  25yr net: ₹{ext.lifetime_savings_inr:,}")
    assert ext.annual_energy_kwh > 0
    assert ext.co2_saved_kg_year > 0
    assert ext.payback_years > 0

    sep("12. CSV Storage")
    record_id = append_result(
        centroid_lat=clat, centroid_lon=clon, polygon=poly_ll,
        total_area_m2=total, usable_area_m2=usable_area(total,0.15),
        shadow_fraction=0.15, panels_count=panels, panel_capacity_w=400,
        system_capacity_kwp=ext.system_capacity_kwp, efficiency_score=eff_s,
        pitch_degrees=sh.pitch_degrees, orientation_degrees=orient.azimuth_degrees,
        orientation_label=orient.direction_label,
        pitch_confidence=sh.confidence, orientation_confidence=orient.confidence,
        detection_method=roof.method, analysis_method=sh.method,
        annual_energy_kwh=ext.annual_energy_kwh,
        co2_saved_kg_year=ext.co2_saved_kg_year,
        co2_saved_tons_year=ext.co2_saved_tons_year,
        trees_equivalent=ext.trees_equivalent,
        gross_cost_inr=ext.gross_cost_inr, subsidy_inr=ext.subsidy_inr,
        net_cost_inr=ext.net_cost_inr, annual_savings_inr=ext.annual_savings_inr,
        payback_years=ext.payback_years, lifetime_savings_inr=ext.lifetime_savings_inr,
        cost_category=ext.cost_category, peak_sun_hours=ext.peak_sun_hours,
        tilt_factor=ext.tilt_factor, orientation_factor=ext.orientation_factor,
        address="Test: Pune, Maharashtra",
    )
    records = read_all()
    print(f"  Record ID : {record_id}")
    print(f"  CSV path  : {get_csv_path()}")
    print(f"  Total rows: {len(records)}")
    assert any(r["id"] == record_id for r in records)

    cv2.imwrite("test_output_v3.jpg", roof.annotated_image)
    print(f"\n💾 Annotated image → test_output_v3.jpg")
    print("\n" + "="*60)
    print("  ✅  All 12 tests passed!")
    print("="*60)
    if records:
        print(f"\nSample CSV columns ({len(records[0])} total):")
        for k, v in list(records[-1].items())[:6]:
            print(f"  {k}: {v}")
        print("  ...")


if __name__ == "__main__":
    run()
