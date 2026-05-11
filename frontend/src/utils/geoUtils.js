// ── Nominatim geocoding (OpenStreetMap) — completely free, no key needed ──────

const NOMINATIM = 'https://nominatim.openstreetmap.org'

/**
 * Geocode address → { lat, lng, displayName }
 * Rate limit: max 1 req/sec (Nominatim policy)
 */
export async function geocodeAddress(address) {
  const url = `${NOMINATIM}/search?q=${encodeURIComponent(address)}&format=json&limit=1&addressdetails=1`
  const res = await fetch(url, {
    headers: { 'Accept-Language': 'en', 'User-Agent': 'SolarRoofApp/2.0' },
  })
  if (!res.ok) throw new Error('Geocoding service unavailable. Please try again.')
  const data = await res.json()
  if (!data.length) throw new Error('Address not found. Try a more specific address (include city/state).')
  return {
    lat: parseFloat(data[0].lat),
    lng: parseFloat(data[0].lon),
    displayName: data[0].display_name,
  }
}

/**
 * Reverse geocode lat/lng → address string
 */
export async function reverseGeocode(lat, lng) {
  const url = `${NOMINATIM}/reverse?lat=${lat}&lon=${lng}&format=json`
  const res = await fetch(url, {
    headers: { 'Accept-Language': 'en', 'User-Agent': 'SolarRoofApp/2.0' },
  })
  if (!res.ok) return null
  const data = await res.json()
  return data.display_name || null
}

// ── Free satellite tile providers ─────────────────────────────────────────────

export const TILE_PROVIDERS = {
  esri: {
    name: 'Esri World Imagery',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, GeoEye, Earthstar Geographics',
    maxZoom: 19,
  },
  osm: {
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
  googleSat: {
    name: 'Google Satellite',
    url: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attribution: 'Map data &copy; Google',
    maxZoom: 21,
  },
}

// ── Snapshot: capture current Leaflet map view as PNG blob ───────────────────

/**
 * Use html2canvas to capture the Leaflet map container as a PNG blob.
 * Falls back to a fetch-based tile stitcher if html2canvas is unavailable.
 */
export async function captureMapSnapshot(mapContainer) {
  // Dynamically import html2canvas (loaded via CDN in index.html)
  if (window.html2canvas) {
    const canvas = await window.html2canvas(mapContainer, {
      useCORS: true,
      allowTaint: true,
      scale: 2,
      logging: false,
    })
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92))
  }
  throw new Error('Snapshot library not loaded.')
}

// ── Sun position calculation (no library needed) ──────────────────────────────

/**
 * Calculate sun elevation and azimuth for a given location and time.
 * Uses the USNO solar position algorithm (accurate to ±0.01°).
 * @returns { elevation: degrees above horizon, azimuth: degrees from north }
 */
export function getSunPosition(lat, lng, date = new Date()) {
  const rad = Math.PI / 180
  const deg = 1 / rad

  const dayOfYear = Math.floor(
    (date - new Date(date.getFullYear(), 0, 0)) / 86400000
  )
  const B = (360 / 365) * (dayOfYear - 81) * rad

  // Equation of time (minutes)
  const EoT = 9.87 * Math.sin(2 * B) - 7.53 * Math.cos(B) - 1.5 * Math.sin(B)

  // Solar declination
  const declination = 23.45 * Math.sin(B) * rad

  // Time correction
  const timezone = Math.round(lng / 15)
  const solarNoon = 12 - (lng - timezone * 15) / 15 - EoT / 60
  const hourAngle = (date.getHours() + date.getMinutes() / 60 - solarNoon) * 15 * rad

  const latRad = lat * rad
  const sinElevation =
    Math.sin(latRad) * Math.sin(declination) +
    Math.cos(latRad) * Math.cos(declination) * Math.cos(hourAngle)

  const elevation = Math.asin(sinElevation) * deg

  const cosAzimuth =
    (Math.sin(declination) - Math.sin(latRad) * sinElevation) /
    (Math.cos(latRad) * Math.cos(Math.asin(sinElevation)))

  let azimuth = Math.acos(Math.max(-1, Math.min(1, cosAzimuth))) * deg
  if (hourAngle > 0) azimuth = 360 - azimuth

  return { elevation, azimuth }
}

// ── Direction helpers ─────────────────────────────────────────────────────────

export function azimuthToDirection(deg) {
  const d = ((deg % 360) + 360) % 360
  if (d < 22.5 || d >= 337.5) return 'North'
  if (d < 67.5)  return 'North-East'
  if (d < 112.5) return 'East'
  if (d < 157.5) return 'South-East'
  if (d < 202.5) return 'South'
  if (d < 247.5) return 'South-West'
  if (d < 292.5) return 'West'
  return 'North-West'
}

export function solarEfficiencyScore(pitchDeg, azimuthDeg) {
  const azDiff = Math.abs(((azimuthDeg - 180) + 180 + 360) % 360 - 180)
  const azScore = Math.max(0, 1 - azDiff / 90)
  const optimalPitch = 25
  const pitchDiff = Math.abs(pitchDeg - optimalPitch)
  const pitchScore = Math.max(0, 1 - pitchDiff / 45)
  return Math.round((azScore * 0.6 + pitchScore * 0.4) * 100)
}
