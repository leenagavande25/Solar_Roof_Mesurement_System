import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, MapPin, Info, CheckCircle2, ArrowRight, RefreshCw } from 'lucide-react'
import { useRoofAnalysis } from '../hooks/useRoofAnalysis'
import LeafletMap from '../components/LeafletMap'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'
import PageHeader from '../components/PageHeader'

const EXAMPLES = [
  'Infosys Campus, Pune, Maharashtra, India',
  'IIT Bombay, Powai, Mumbai, India',
  'Hawa Mahal, Jaipur, Rajasthan, India',
  'Lalbagh Botanical Garden, Bangalore, India',
]

const TIPS = [
  'Zoom to level 18–20 for best roof detail',
  'Make sure the full roof fits in frame',
  'Use Esri tiles for sharpest imagery',
  'Click anywhere on the map to move marker',
]

export default function AnalyzePage() {
  const navigate = useNavigate()
  const [inputValue, setInputValue] = useState('')
  const [snapshotPreview, setSnapshotPreview] = useState(null)

  const {
    address,
    coords,
    results,
    isGeocoding,
    isAnalyzing,
    loadingMsg,
    error, setError,
    handleGeocode,
    handleMapClick,
    analyzeRoof,
    reset,
  } = useRoofAnalysis()

  const handleSearch = (e) => {
    e.preventDefault()
    if (inputValue.trim()) handleGeocode(inputValue)
  }

  const handleSnapshot = useCallback((blob, url) => {
    setSnapshotPreview(url)
    analyzeRoof(blob, url).then(() => {
      // auto navigate once done
    })
  }, [analyzeRoof])

  const handleReset = () => {
    reset()
    setInputValue('')
    setSnapshotPreview(null)
  }

  // Navigate to results when done
  if (results && !isAnalyzing) {
    navigate('/results')
  }

  return (
    <div className="relative min-h-screen">
      <div className="fixed top-1/4 right-0 w-[400px] h-[400px] bg-solar-400/4 rounded-full blur-3xl pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-16">
        <PageHeader
          badge={{ text: '100% Free · No API Key', icon: null }}
          title="Find &amp; Analyze"
          highlight="Any Roof"
          description="Search any address using free OpenStreetMap data. Zoom in on the satellite view, then capture and analyze the roof."
        />

        {isAnalyzing ? (
          <div className="mt-12 card max-w-lg mx-auto p-10">
            <LoadingSpinner
              message={loadingMsg || 'Analyzing roof...'}
              subMessage="Running AI detection, shadow analysis, and orientation calculation"
            />
          </div>
        ) : (
          <div className="mt-10 grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Main: search + map */}
            <div className="lg:col-span-2 flex flex-col gap-4">

              {/* Search bar */}
              <form onSubmit={handleSearch} className="flex gap-2">
                <div className="relative flex-1">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none">
                    {isGeocoding
                      ? <Loader2 size={16} className="text-solar-400 animate-spin" />
                      : <Search size={16} className="text-slate-500" />
                    }
                  </div>
                  <input
                    type="text"
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value)}
                    placeholder="Search address, landmark, or city..."
                    disabled={isGeocoding}
                    className="w-full bg-white/5 border border-white/15 rounded-xl pl-11 pr-4 py-3 text-white placeholder-slate-500
                      focus:outline-none focus:border-solar-400/60 focus:bg-white/8 transition-all duration-200 text-sm font-body
                      disabled:opacity-60"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isGeocoding || !inputValue.trim()}
                  className={`px-5 py-3 rounded-xl font-display text-sm transition-all ${
                    inputValue.trim() && !isGeocoding
                      ? 'bg-solar-400 hover:bg-solar-300 text-slate-950 hover:scale-[1.02]'
                      : 'bg-white/5 text-slate-600 cursor-not-allowed'
                  }`}
                  style={{ fontWeight: 700 }}
                >
                  {isGeocoding ? 'Searching...' : 'Search'}
                </button>
              </form>

              {/* Example addresses */}
              {!coords && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-slate-600 font-body self-center">Try:</span>
                  {EXAMPLES.map(ex => (
                    <button
                      key={ex}
                      type="button"
                      onClick={() => { setInputValue(ex); handleGeocode(ex) }}
                      className="text-xs font-body text-slate-400 hover:text-solar-300 border border-white/10 hover:border-solar-400/30 px-2.5 py-1 rounded-lg transition-all hover:bg-solar-400/5"
                    >
                      {ex.split(',')[0]}
                    </button>
                  ))}
                </div>
              )}

              {/* Geocoded address badge */}
              {coords && (
                <div className="flex items-center gap-2.5 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl animate-fade-in">
                  <MapPin size={14} className="text-solar-400 flex-shrink-0" />
                  <p className="font-body text-xs text-slate-300 flex-1 truncate">{address}</p>
                  <button
                    onClick={handleReset}
                    className="text-slate-500 hover:text-white text-xs font-display border border-white/10 hover:border-white/20 px-2.5 py-1 rounded-lg transition-all hover:bg-white/5 flex-shrink-0"
                    style={{ fontWeight: 600 }}
                  >
                    Clear
                  </button>
                </div>
              )}

              {/* Error */}
              {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}

              {/* Leaflet map */}
              <LeafletMap
                coords={coords}
                onMapClick={handleMapClick}
                onSnapshot={handleSnapshot}
                disabled={isAnalyzing}
              />
            </div>

            {/* Sidebar */}
            <div className="flex flex-col gap-4">

              {/* Steps */}
              <div className="card p-5">
                <p className="font-display text-xs text-slate-400 uppercase tracking-widest mb-4" style={{ fontWeight: 700 }}>
                  How it works
                </p>
                {[
                  { n: '1', label: 'Search address', done: !!coords },
                  { n: '2', label: 'Zoom in on roof', done: false },
                  { n: '3', label: 'Capture & analyze', done: !!results },
                ].map(({ n, label, done }) => (
                  <div key={n} className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                      done ? 'bg-green-500/20 text-green-400' : 'bg-white/8 text-slate-400'
                    }`} style={{ fontWeight: 700 }}>
                      {done ? <CheckCircle2 size={13} /> : n}
                    </div>
                    <span className={`font-body text-sm ${done ? 'text-slate-300 line-through' : 'text-slate-400'}`}>
                      {label}
                    </span>
                  </div>
                ))}
              </div>

              {/* Tips */}
              <div className="card p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Info size={14} className="text-solar-400" />
                  <h3 className="font-display text-sm text-white" style={{ fontWeight: 700 }}>Tips</h3>
                </div>
                <ul className="flex flex-col gap-2.5">
                  {TIPS.map((tip, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <div className="w-1.5 h-1.5 bg-solar-400/50 rounded-full mt-1.5 flex-shrink-0" />
                      <p className="font-body text-slate-400 text-xs leading-relaxed">{tip}</p>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Free stack */}
              <div className="card p-5 border-green-400/15 bg-green-400/5">
                <p className="font-display text-xs text-green-400 uppercase tracking-widest mb-3" style={{ fontWeight: 700 }}>
                  Free Stack
                </p>
                {[
                  { label: 'Geocoding', value: 'Nominatim / OSM' },
                  { label: 'Satellite tiles', value: 'Esri / Google' },
                  { label: 'Roof detection', value: 'OpenCV + SAM' },
                  { label: 'Shadow analysis', value: 'pvlib + numpy' },
                  { label: 'Backend', value: 'FastAPI (Python)' },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between py-1.5 border-b border-white/5 last:border-0">
                    <span className="font-body text-xs text-slate-500">{label}</span>
                    <span className="font-body text-xs text-green-400">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
