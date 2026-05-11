import { useEffect, useRef, useState, useCallback } from 'react'
import { Camera, Layers, ZoomIn, ZoomOut, Crosshair } from 'lucide-react'
import { TILE_PROVIDERS } from '../utils/geoUtils'

// Leaflet is loaded via CDN in index.html — access via window.L
// This avoids SSR issues and import conflicts with React-Leaflet

export default function LeafletMap({ coords, onMapClick, onSnapshot, disabled }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const markerRef = useRef(null)
  const [tileProvider, setTileProvider] = useState('esri')
  const [isCapturing, setIsCapturing] = useState(false)
  const [zoom, setZoom] = useState(19)

  // ── Initialize Leaflet map ───────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const L = window.L
    if (!L) { console.error('Leaflet not loaded'); return }

    const map = L.map(containerRef.current, {
      center: [20.5937, 78.9629], // center of India
      zoom: 5,
      zoomControl: false,
    })

    // Add satellite tiles
    L.tileLayer(TILE_PROVIDERS.esri.url, {
      attribution: TILE_PROVIDERS.esri.attribution,
      maxZoom: TILE_PROVIDERS.esri.maxZoom,
    }).addTo(map)

    // Click handler
    map.on('click', (e) => {
      if (onMapClick) onMapClick(e.latlng.lat, e.latlng.lng)
    })

    map.on('zoomend', () => setZoom(map.getZoom()))

    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  // ── Fly to coords when they change ─────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || !coords) return
    const L = window.L
    mapRef.current.flyTo([coords.lat, coords.lng], 19, { duration: 1.5 })

    // Update/add marker
    if (markerRef.current) markerRef.current.remove()
    const icon = L.divIcon({
      className: '',
      html: `<div style="
        width:20px;height:20px;
        background:rgba(251,191,36,0.9);
        border:2px solid white;
        border-radius:50%;
        box-shadow:0 0 8px rgba(251,191,36,0.6);
      "></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    })
    markerRef.current = L.marker([coords.lat, coords.lng], { icon }).addTo(mapRef.current)
  }, [coords])

  // ── Switch tile layer ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current) return
    const L = window.L
    // Remove all tile layers
    mapRef.current.eachLayer(layer => {
      if (layer instanceof L.TileLayer) layer.remove()
    })
    const provider = TILE_PROVIDERS[tileProvider]
    L.tileLayer(provider.url, {
      attribution: provider.attribution,
      maxZoom: provider.maxZoom,
    }).addTo(mapRef.current)
  }, [tileProvider])

  // ── Capture snapshot using html2canvas ─────────────────────────────────────
  const handleCapture = useCallback(async () => {
    if (!containerRef.current || !coords) return
    setIsCapturing(true)
    try {
      // Wait for tiles to fully render
      await new Promise(r => setTimeout(r, 800))

      const canvas = await window.html2canvas(containerRef.current, {
        useCORS: true,
        allowTaint: true,
        scale: 2,
        logging: false,
        imageTimeout: 10000,
      })

      const blob = await new Promise(resolve =>
        canvas.toBlob(resolve, 'image/jpeg', 0.92)
      )
      const url = URL.createObjectURL(blob)
      onSnapshot(blob, url)
    } catch (err) {
      console.error('Snapshot failed:', err)
      // Fallback: fetch tile image directly
      alert('Snapshot failed. Please try switching tile provider or try again.')
    } finally {
      setIsCapturing(false)
    }
  }, [coords, onSnapshot])

  const handleZoom = (delta) => {
    if (!mapRef.current) return
    mapRef.current.setZoom(mapRef.current.getZoom() + delta)
  }

  const centerOnMarker = () => {
    if (!mapRef.current || !coords) return
    mapRef.current.flyTo([coords.lat, coords.lng], 19)
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Map container */}
      <div className="relative rounded-2xl overflow-hidden border border-white/10" style={{ height: '420px' }}>
        <div ref={containerRef} className="w-full h-full" />

        {/* Overlay controls */}
        <div className="absolute top-3 left-3 flex flex-col gap-1 z-[1000]">
          {/* Tile switcher */}
          <div className="flex gap-1 p-1 bg-slate-950/80 backdrop-blur-sm border border-white/10 rounded-lg">
            {Object.entries(TILE_PROVIDERS).map(([key, p]) => (
              <button
                key={key}
                onClick={() => setTileProvider(key)}
                className={`px-2 py-1 rounded text-xs font-display transition-all ${
                  tileProvider === key
                    ? 'bg-solar-400 text-slate-950'
                    : 'text-slate-400 hover:text-white'
                }`}
                style={{ fontWeight: tileProvider === key ? 700 : 500 }}
                title={p.name}
              >
                {key === 'esri' ? 'Esri' : key === 'osm' ? 'OSM' : 'Goog'}
              </button>
            ))}
          </div>
        </div>

        {/* Zoom + center controls */}
        <div className="absolute top-3 right-3 flex flex-col gap-1 z-[1000]">
          {[
            { icon: ZoomIn, action: () => handleZoom(1), title: 'Zoom in' },
            { icon: ZoomOut, action: () => handleZoom(-1), title: 'Zoom out' },
            { icon: Crosshair, action: centerOnMarker, title: 'Center on marker', disabled: !coords },
          ].map(({ icon: Icon, action, title, disabled: btnDisabled }) => (
            <button
              key={title}
              onClick={action}
              disabled={btnDisabled}
              title={title}
              className="w-8 h-8 bg-slate-950/80 backdrop-blur-sm border border-white/15 rounded-lg flex items-center justify-center text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <Icon size={14} />
            </button>
          ))}
        </div>

        {/* Crosshair center */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[999]">
          <div className="relative opacity-40">
            <div className="w-8 h-px bg-solar-400" />
            <div className="w-px h-8 bg-solar-400 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
        </div>

        {/* Zoom badge */}
        <div className="absolute bottom-3 left-3 z-[1000] px-2 py-1 bg-slate-950/70 backdrop-blur-sm border border-white/10 rounded-lg">
          <span className="font-mono text-xs text-slate-400">z{zoom}</span>
        </div>

        {/* Instruction overlay when no coords */}
        {!coords && (
          <div className="absolute inset-0 flex items-center justify-center z-[998] pointer-events-none">
            <div className="bg-slate-950/70 backdrop-blur-sm border border-white/10 rounded-xl px-4 py-3 text-center">
              <p className="font-display text-sm text-white" style={{ fontWeight: 600 }}>
                Search an address or click the map
              </p>
              <p className="font-body text-xs text-slate-400 mt-1">
                to place the analysis marker
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Capture button */}
      <button
        onClick={handleCapture}
        disabled={!coords || isCapturing || disabled}
        className={`flex items-center justify-center gap-2.5 py-3.5 rounded-xl font-display text-sm transition-all duration-200
          ${coords && !isCapturing && !disabled
            ? 'bg-solar-400 hover:bg-solar-300 text-slate-950 hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-solar-400/20'
            : 'bg-white/5 text-slate-600 cursor-not-allowed border border-white/10'
          }`}
        style={{ fontWeight: 700 }}
      >
        <Camera size={17} className={isCapturing ? 'animate-pulse' : ''} />
        {isCapturing ? 'Capturing map...' : coords ? 'Capture & Analyze Roof' : 'Search an address first'}
      </button>

      <p className="text-xs font-body text-slate-600 text-center">
        Zoom in until the roof clearly fills the frame, then capture
      </p>
    </div>
  )
}
