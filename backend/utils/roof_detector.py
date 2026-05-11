"""
roof_detector.py  (v2 — GrabCut + center-bias)
───────────────────────────────────────────────
Detects the roof that the user aimed the map crosshair at.
The target roof is always near the image center.

Pipeline
────────
1.  GrabCut with a center rectangle seed
    → separates center-foreground (roof) from background
2.  Contour extraction from GrabCut mask
3.  Center-proximity scoring
    → pick the contour closest to image center, not the largest
4.  Shape filter
    → reject long thin shapes (roads), keep compact blobs (roofs)
5.  Solidity filter
    → roof contour area / convex hull area > 0.55
6.  Fallback: Watershed from center seed if GrabCut fails
7.  Polygon simplification + area → m²

Why GrabCut beats K-means for this task
─────────────────────────────────────────
K-means clusters ALL pixels by colour globally → road pixels (same
colour family as flat roof) get merged into the same cluster.

GrabCut uses a center rectangle as a "definitely foreground" seed
and iteratively refines the boundary using graph cuts. It naturally
separates the center object from surrounding context regardless of
similar colours elsewhere in the image.
"""

import cv2
import numpy as np
import math
from dataclasses import dataclass
from typing import Optional, Tuple


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class RoofDetectionResult:
    mask: np.ndarray             # binary mask uint8 0/255
    polygon: np.ndarray          # simplified contour Nx1x2
    area_pixels: float
    area_m2: float
    confidence: int              # 0-100
    annotated_image: np.ndarray
    method: str                  # 'grabcut' | 'watershed' | 'fallback'


# ── Scale conversion ──────────────────────────────────────────────────────────

def pixels_to_m2(pixel_area: float, lat: float, zoom: int) -> float:
    """
    Convert pixel area → m² using the Web Mercator scale formula.
    meters_per_pixel = 156543.03 × cos(lat) / 2^zoom
    The html2canvas snapshot is at CSS pixel resolution (not retina doubled),
    so we do NOT divide by 2 here.
    """
    mpp = 156_543.03 * math.cos(math.radians(lat)) / (2 ** zoom)
    return pixel_area * (mpp ** 2)


# ── Helper: center distance score ────────────────────────────────────────────

def center_score(contour: np.ndarray, h: int, w: int) -> float:
    """
    Score a contour by how close its centroid is to the image center.
    Returns 0-1 where 1 = centroid IS the image center.
    """
    M = cv2.moments(contour)
    if M["m00"] == 0:
        return 0.0
    cx = M["m10"] / M["m00"]
    cy = M["m01"] / M["m00"]
    dist = math.hypot(cx - w / 2, cy - h / 2)
    max_dist = math.hypot(w / 2, h / 2)
    return max(0.0, 1.0 - dist / max_dist)


def shape_score(contour: np.ndarray) -> float:
    """
    Score a contour by how 'roof-like' its shape is.
    Roofs: compact, roughly rectangular, solidity > 0.6
    Roads: long, thin, solidity can be low
    Returns 0-1.
    """
    area = cv2.contourArea(contour)
    if area < 100:
        return 0.0

    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area > 0 else 0

    # Aspect ratio — roof should not be extremely elongated
    _, (bw, bh), _ = cv2.minAreaRect(contour)
    if bw == 0 or bh == 0:
        return 0.0
    aspect = min(bw, bh) / max(bw, bh)   # 1 = square, 0 = line

    return float(solidity * 0.6 + aspect * 0.4)


# ── Method 1: GrabCut ────────────────────────────────────────────────────────

def grabcut_detect(image: np.ndarray, h: int, w: int) -> Optional[np.ndarray]:
    """
    Run GrabCut with the center 50% of the image as the seed rectangle.
    Returns binary mask (0/255) or None if it fails.
    """
    # Seed rectangle = center 50% of image (where the roof should be)
    margin_x = int(w * 0.25)
    margin_y = int(h * 0.25)
    rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

    gc_mask  = np.zeros((h, w), dtype=np.uint8)
    bgd_model = np.zeros((1, 65), dtype=np.float64)
    fgd_model = np.zeros((1, 65), dtype=np.float64)

    try:
        cv2.grabCut(image, gc_mask, rect, bgd_model, fgd_model,
                    iterCount=5, mode=cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None

    # Pixels marked as definite/probable foreground
    fg_mask = np.where(
        (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD),
        255, 0
    ).astype(np.uint8)

    if fg_mask.sum() < 100 * 255:   # too little foreground
        return None

    # Morphological clean-up
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, k, iterations=2)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN,  k, iterations=1)

    return fg_mask


# ── Method 2: Watershed from center seed ────────────────────────────────────

def watershed_detect(image: np.ndarray, h: int, w: int) -> Optional[np.ndarray]:
    """
    Watershed segmentation seeded from the image center.
    Used as fallback when GrabCut fails.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Distance transform
    dist = cv2.distanceTransform(thresh, cv2.DIST_L2, 5)
    cv2.normalize(dist, dist, 0, 1.0, cv2.NORM_MINMAX)

    # Sure foreground: center 30%
    sure_fg = np.zeros((h, w), dtype=np.uint8)
    cy, cx = h // 2, w // 2
    r = min(h, w) // 6
    cv2.circle(sure_fg, (cx, cy), r, 255, -1)

    # Sure background
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    sure_bg = cv2.dilate(thresh, kernel, iterations=3)

    unknown = cv2.subtract(sure_bg, sure_fg)
    _, markers = cv2.connectedComponents(sure_fg)
    markers += 1
    markers[unknown == 255] = 0
    markers = markers.astype(np.int32)

    try:
        cv2.watershed(image, markers)
    except cv2.error:
        return None

    fg_mask = np.where(markers == 2, 255, 0).astype(np.uint8)

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, k, iterations=2)

    return fg_mask if fg_mask.sum() > 100 * 255 else None


# ── Contour selection ────────────────────────────────────────────────────────

def select_best_contour(
    mask: np.ndarray, h: int, w: int,
    min_area_frac: float = 0.02,
    max_area_frac: float = 0.85,
) -> Optional[np.ndarray]:
    """
    From all contours in mask, pick the one that:
    1. Has area between min_area_frac and max_area_frac of image
    2. Scores highest on: center_proximity × shape_quality
    """
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    img_area = h * w
    min_area = img_area * min_area_frac
    max_area = img_area * max_area_frac

    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area or area > max_area:
            continue
        cs = center_score(c, h, w)
        ss = shape_score(c)
        # Combined score: weight center proximity heavily
        score = cs * 0.65 + ss * 0.35
        candidates.append((score, c))

    if not candidates:
        # Relax size filter and just pick closest to center
        for c in contours:
            area = cv2.contourArea(c)
            if area < 50:
                continue
            cs = center_score(c, h, w)
            candidates.append((cs, c))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ── Confidence calculation ────────────────────────────────────────────────────

def calc_confidence(contour: np.ndarray, h: int, w: int, method: str) -> int:
    cs = center_score(contour, h, w)
    ss = shape_score(contour)
    area_frac = cv2.contourArea(contour) / (h * w)

    # Good coverage: 5–60% of image
    if 0.05 <= area_frac <= 0.60:
        cov = 1.0
    elif area_frac < 0.05:
        cov = area_frac / 0.05
    else:
        cov = max(0, 1 - (area_frac - 0.60) / 0.40)

    raw = cs * 0.4 + ss * 0.3 + cov * 0.3
    conf = int(raw * 100)

    # Method bonus
    if method == 'grabcut':
        conf = min(95, conf + 5)
    elif method == 'fallback':
        conf = max(20, conf - 15)

    return max(20, min(95, conf))


# ── Annotation ────────────────────────────────────────────────────────────────

def annotate(image: np.ndarray, polygon: np.ndarray, area_m2: float) -> np.ndarray:
    out = image.copy()
    overlay = image.copy()

    # Semi-transparent fill — amber/solar colour
    cv2.drawContours(overlay, [polygon], -1, (36, 191, 251), -1)   # BGR = solar amber
    cv2.addWeighted(overlay, 0.30, out, 0.70, 0, out)

    # Border
    cv2.drawContours(out, [polygon], -1, (36, 191, 251), 3)

    # Vertices
    for pt in polygon:
        cv2.circle(out, tuple(pt[0]), 6, (255, 255, 255), -1)
        cv2.circle(out, tuple(pt[0]), 6, (36, 191, 251), 2)

    # Area label at centroid
    M = cv2.moments(polygon)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    else:
        cx, cy = image.shape[1] // 2, image.shape[0] // 2

    label = f"{area_m2} m2"
    (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
    cv2.rectangle(out, (cx - lw // 2 - 6, cy - lh - 8),
                  (cx + lw // 2 + 6, cy + 6), (0, 0, 0), -1)
    cv2.putText(out, label, (cx - lw // 2, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

    return out


# ── Main entry point ──────────────────────────────────────────────────────────

def detect_roof(
    image: np.ndarray,
    lat: float = 20.0,
    zoom: int = 19,
) -> RoofDetectionResult:
    """
    Detect the roof near the center of the image.

    Tries three methods in order:
      1. GrabCut (best, center-seeded)
      2. Watershed (fallback)
      3. Center crop (last resort)
    """
    h, w = image.shape[:2]
    method = 'grabcut'

    # ── Method 1: GrabCut ────────────────────────────────────────────────────
    mask = grabcut_detect(image, h, w)
    best_contour = select_best_contour(mask, h, w) if mask is not None else None

    # ── Method 2: Watershed ───────────────────────────────────────────────────
    if best_contour is None:
        method = 'watershed'
        mask = watershed_detect(image, h, w)
        best_contour = select_best_contour(mask, h, w) if mask is not None else None

    # ── Method 3: Center crop fallback ────────────────────────────────────────
    if best_contour is None:
        method = 'fallback'
        mask, best_contour = _center_crop_fallback(h, w)

    # ── Recreate clean mask from chosen contour ───────────────────────────────
    clean_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(clean_mask, [best_contour], -1, 255, -1)

    # ── Polygon simplification ────────────────────────────────────────────────
    perimeter = cv2.arcLength(best_contour, True)
    epsilon = 0.015 * perimeter
    polygon = cv2.approxPolyDP(best_contour, epsilon, True)

    # ── Area ─────────────────────────────────────────────────────────────────
    area_px = cv2.contourArea(best_contour)
    area_m2 = round(pixels_to_m2(area_px, lat, zoom), 1)

    # ── Confidence ───────────────────────────────────────────────────────────
    confidence = calc_confidence(best_contour, h, w, method)

    # ── Annotate ─────────────────────────────────────────────────────────────
    annotated = annotate(image, polygon, area_m2)

    return RoofDetectionResult(
        mask=clean_mask,
        polygon=polygon,
        area_pixels=float(area_px),
        area_m2=area_m2,
        confidence=confidence,
        annotated_image=annotated,
        method=method,
    )


def _center_crop_fallback(h: int, w: int) -> Tuple[np.ndarray, np.ndarray]:
    """40% center crop as absolute last resort."""
    mask = np.zeros((h, w), dtype=np.uint8)
    y1, y2 = int(h * 0.30), int(h * 0.70)
    x1, x2 = int(w * 0.30), int(w * 0.70)
    mask[y1:y2, x1:x2] = 255
    contour = np.array(
        [[[x1, y1]], [[x2, y1]], [[x2, y2]], [[x1, y2]]], dtype=np.int32
    )
    return mask, contour
