import { useNavigate } from 'react-router-dom'
import { Sun, Layers, SquareStack, Zap, Leaf, TrendingUp, Compass,
         RotateCcw, Upload, ArrowRight, RefreshCw, BarChart3, Info, AlertTriangle } from 'lucide-react'
import { useRoofAnalysis } from '../hooks/useRoofAnalysis'
import { solarEfficiencyScore, azimuthToDirection } from '../utils/geoUtils'
import PageHeader from '../components/PageHeader'

// ── Compass rose SVG ─────────────────────────────────────────────────────────
function CompassRose({ azimuth = 180 }) {
  return (
    <div className="relative w-20 h-20 mx-auto">
      <svg viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="36" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="1"/>
        <circle cx="40" cy="40" r="28" fill="none" stroke="rgba(251,191,36,0.12)" strokeWidth="0.5"/>
        {[['N',40,9],['S',40,75],['E',75,43],['W',5,43]].map(([l,x,y])=>(
          <text key={l} x={x} y={y} textAnchor="middle" fill="rgba(255,255,255,0.25)" fontSize="8" fontFamily="sans-serif">{l}</text>
        ))}
        <g transform={`rotate(${azimuth} 40 40)`}>
          <polygon points="40,10 37,40 40,36 43,40" fill="rgba(251,191,36,0.85)"/>
          <polygon points="40,70 37,40 40,44 43,40" fill="rgba(255,255,255,0.15)"/>
        </g>
        <circle cx="40" cy="40" r="2.5" fill="rgba(251,191,36,0.8)"/>
      </svg>
    </div>
  )
}

// ── Efficiency bar ────────────────────────────────────────────────────────────
function EfficiencyBar({ score }) {
  const color = score >= 75 ? 'from-green-500 to-green-400'
    : score >= 50 ? 'from-solar-500 to-solar-400' : 'from-red-500 to-orange-400'
  const label = score >= 75 ? 'Excellent' : score >= 50 ? 'Good' : 'Fair'
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between text-xs font-body">
        <span className="text-slate-400">Solar efficiency</span>
        <span className="text-white">{score}% — {label}</span>
      </div>
      <div className="h-2 bg-white/8 rounded-full overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${color} rounded-full transition-all duration-1000`}
          style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

// ── Confidence badge ──────────────────────────────────────────────────────────
function ConfidenceBadge({ value }) {
  const color = value >= 80 ? 'text-green-400 bg-green-400/10 border-green-400/20'
    : value >= 60 ? 'text-solar-400 bg-solar-400/10 border-solar-400/20'
    : 'text-orange-400 bg-orange-400/10 border-orange-400/20'
  return (
    <span className={`text-[10px] font-display px-2 py-0.5 rounded-md border ${color}`} style={{ fontWeight: 700 }}>
      {value}% confidence
    </span>
  )
}

// ── SAMPLE DATA ───────────────────────────────────────────────────────────────
const SAMPLE = {
  roof_area_m2: 124.6,
  pitch_degrees: 24.3,
  pitch_confidence: 74,
  orientation_degrees: 172.4,
  orientation_confidence: 91,
  shadow_length_px: 38,
  sun_elevation_degrees: 42.1,
  max_panels: 48,
  panel_capacity_w: 400,
  system_capacity_kw: 19.2,
  yearly_energy_kwh: 22118,
  sunshine_hours: 1820,
  processed_image_url: null,
  segments: [
    { pitch: 24.3, orientation: 172.4, area: 68.4, label: 'South face' },
    { pitch: 24.3, orientation: 352.4, area: 56.2, label: 'North face' },
  ],
  warnings: ['Shadow-based pitch estimate — accuracy ±8°'],
}

// ── PAGE ─────────────────────────────────────────────────────────────────────
export default function ResultsPage() {
  const navigate = useNavigate()
  const { results, previewUrl, address, reset } = useRoofAnalysis()
  const data = results || SAMPLE
  const isSample = !results

  const direction = azimuthToDirection(data.orientation_degrees)
  const effScore = solarEfficiencyScore(data.pitch_degrees, data.orientation_degrees)
  const dailyKwh = Math.round(data.yearly_energy_kwh / 365)
  const monthlyKwh = Math.round(data.yearly_energy_kwh / 12)
  const yearlySavings = Math.round(data.yearly_energy_kwh * 7)
  const carbonTons = parseFloat(((data.yearly_energy_kwh * 0.82) / 1000).toFixed(1))
  const trees = Math.round(carbonTons * 50)

  return (
    <div className="relative min-h-screen">
      <div className="fixed top-0 right-1/4 w-[500px] h-[300px] bg-solar-400/4 rounded-full blur-3xl pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-28 pb-16">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-8">
          <PageHeader
            badge={{ text: isSample ? 'Sample Results' : 'Analysis Complete', icon: isSample ? null : <Sun size={12} /> }}
            title="Roof Analysis"
            highlight="Results"
            description={isSample ? 'Sample data shown. Analyze a real roof to see live results.' : address}
          />
          <div className="flex gap-2 pt-2">
            <button onClick={() => { reset(); navigate('/upload') }} className="btn-secondary text-sm">
              <RefreshCw size={14} /> New Analysis
            </button>
          </div>
        </div>

        {/* Sample banner */}
        {isSample && (
          <div className="mb-6 flex items-center gap-3 p-4 bg-solar-400/8 border border-solar-400/20 rounded-xl">
            <Sun size={15} className="text-solar-400 flex-shrink-0" />
            <p className="font-body text-solar-300/80 text-sm flex-1">Showing sample data. Go to the Analyze page and capture a real roof.</p>
            <button onClick={() => navigate('/upload')}
              className="text-xs font-display text-solar-400 border border-solar-400/30 hover:border-solar-400 px-3 py-1.5 rounded-lg transition-colors flex-shrink-0"
              style={{ fontWeight: 600 }}>Analyze now</button>
          </div>
        )}

        {/* Warnings */}
        {data.warnings?.length > 0 && (
          <div className="mb-6 flex flex-col gap-2">
            {data.warnings.map((w, i) => (
              <div key={i} className="flex items-center gap-2.5 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                <AlertTriangle size={14} className="text-amber-400 flex-shrink-0" />
                <p className="font-body text-xs text-amber-300">{w}</p>
              </div>
            ))}
          </div>
        )}

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { icon: Layers,      label: 'Roof Area',        value: data.roof_area_m2,          unit: 'm²',   accent: true },
            { icon: RotateCcw,   label: 'Pitch Angle',      value: `${data.pitch_degrees}°`,   unit: '',     conf: data.pitch_confidence },
            { icon: Compass,     label: 'Orientation',      value: direction,                  unit: '',     conf: data.orientation_confidence },
            { icon: SquareStack, label: 'Max Panels',       value: data.max_panels,            unit: 'units' },
          ].map(({ icon: Icon, label, value, unit, accent, conf }, i) => (
            <div key={label}
              className={`card p-4 flex flex-col gap-1 hover:border-solar-400/25 animate-bounce-in transition-all ${accent ? 'border-solar-400/20 bg-solar-400/5' : ''}`}
              style={{ animationDelay: `${i*80}ms` }}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-1 ${accent ? 'bg-solar-400/20' : 'bg-white/8'}`}>
                <Icon size={15} className={accent ? 'text-solar-400' : 'text-slate-400'} />
              </div>
              <div className="flex items-baseline gap-1 flex-wrap">
                <span className={`font-display text-xl ${accent ? 'text-solar-300' : 'text-white'}`}
                  style={{ fontWeight: 800 }}>{value}</span>
                {unit && <span className="text-slate-500 text-xs font-body">{unit}</span>}
              </div>
              <p className="font-display text-xs text-slate-400" style={{ fontWeight: 600 }}>{label}</p>
              {conf !== undefined && <ConfidenceBadge value={conf} />}
            </div>
          ))}
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

          {/* Left col */}
          <div className="xl:col-span-2 flex flex-col gap-6">

            {/* Processed image */}
            {(data.processed_image_url || previewUrl) && (
              <div className="card overflow-hidden animate-fade-in">
                <div className="flex items-center gap-2 px-5 py-3 border-b border-white/8">
                  <div className="w-2 h-2 bg-solar-400 rounded-full animate-pulse" />
                  <span className="font-display text-sm text-white" style={{ fontWeight: 600 }}>
                    Processed Roof Image
                  </span>
                  {data.processed_image_url && (
                    <span className="ml-auto text-xs font-body text-green-400">AI overlay applied</span>
                  )}
                </div>
                <img
                  src={data.processed_image_url || previewUrl}
                  alt="Processed roof"
                  className="w-full aspect-video object-cover"
                />
              </div>
            )}

            {/* Roof segments */}
            {data.segments?.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Layers size={15} className="text-solar-400" />
                  <h2 className="font-display text-white" style={{ fontWeight: 700 }}>
                    Detected Roof Segments
                  </h2>
                  <div className="flex-1 h-px bg-white/8" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {data.segments.map((seg, i) => {
                    const score = solarEfficiencyScore(seg.pitch, seg.orientation)
                    return (
                      <div key={i} className={`card p-4 hover:border-white/20 transition-all animate-slide-up ${i===0?'border-solar-400/20 bg-solar-400/5':''}`}
                        style={{ animationDelay: `${i*100}ms` }}>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <div className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-display ${i===0?'bg-solar-400/20 text-solar-400':'bg-white/10 text-slate-400'}`}
                              style={{ fontWeight: 700 }}>{i+1}</div>
                            <span className="font-display text-sm text-white" style={{ fontWeight: 600 }}>{seg.label || `Segment ${i+1}`}</span>
                            {i===0 && <span className="text-[10px] font-display text-solar-400 bg-solar-400/10 px-1.5 py-0.5 rounded" style={{ fontWeight: 700 }}>BEST</span>}
                          </div>
                          <CompassRose azimuth={seg.orientation} />
                        </div>
                        <div className="grid grid-cols-2 gap-2 mb-3">
                          {[
                            { l: 'Area', v: `${seg.area} m²` },
                            { l: 'Facing', v: azimuthToDirection(seg.orientation) },
                            { l: 'Pitch', v: `${seg.pitch}°` },
                            { l: 'Azimuth', v: `${seg.orientation}°` },
                          ].map(({ l, v }) => (
                            <div key={l} className="bg-white/4 rounded-lg p-2">
                              <p className="text-slate-500 text-[10px] font-body mb-0.5">{l}</p>
                              <p className="text-white text-xs font-display" style={{ fontWeight: 600 }}>{v}</p>
                            </div>
                          ))}
                        </div>
                        <EfficiencyBar score={score} />
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Shadow analysis details */}
            <div className="card p-5 animate-fade-in">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-amber-400/15 rounded-lg flex items-center justify-center">
                  <Sun size={15} className="text-amber-400" />
                </div>
                <h3 className="font-display text-white text-sm" style={{ fontWeight: 700 }}>Shadow Analysis Details</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'Shadow length', value: `${data.shadow_length_px}px` },
                  { label: 'Sun elevation', value: `${data.sun_elevation_degrees}°` },
                  { label: 'Computed pitch', value: `${data.pitch_degrees}°` },
                  { label: 'Pitch confidence', value: `${data.pitch_confidence}%` },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-white/4 rounded-xl p-3">
                    <p className="text-slate-500 text-[10px] font-body mb-1">{label}</p>
                    <p className="text-white text-sm font-display" style={{ fontWeight: 700 }}>{value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex items-start gap-2 p-3 bg-amber-500/8 border border-amber-500/15 rounded-xl">
                <Info size={13} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <p className="font-body text-xs text-amber-300/80 leading-relaxed">
                  Pitch is estimated from shadow length and sun elevation angle at capture time.
                  Accuracy is ±5–8° depending on shadow clarity and nearby obstructions.
                </p>
              </div>
            </div>
          </div>

          {/* Right col */}
          <div className="flex flex-col gap-4">

            {/* Orientation card */}
            <div className="card p-5 animate-slide-up">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-blue-400/15 rounded-lg flex items-center justify-center">
                  <Compass size={15} className="text-blue-400" />
                </div>
                <h3 className="font-display text-white text-sm" style={{ fontWeight: 700 }}>Roof Orientation</h3>
              </div>
              <CompassRose azimuth={data.orientation_degrees} />
              <div className="mt-4 grid grid-cols-2 gap-2">
                {[
                  { l: 'Direction', v: direction },
                  { l: 'Azimuth', v: `${data.orientation_degrees}°` },
                  { l: 'Pitch', v: `${data.pitch_degrees}°` },
                  { l: 'Efficiency', v: `${effScore}%` },
                ].map(({ l, v }) => (
                  <div key={l} className="bg-white/4 rounded-lg p-2.5">
                    <p className="text-slate-500 text-[10px] font-body mb-0.5">{l}</p>
                    <p className="text-white text-xs font-display" style={{ fontWeight: 600 }}>{v}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3">
                <EfficiencyBar score={effScore} />
              </div>
            </div>

            {/* Energy */}
            <div className="card p-5 animate-slide-up" style={{ animationDelay: '100ms' }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-solar-400/15 rounded-lg flex items-center justify-center">
                  <BarChart3 size={15} className="text-solar-400" />
                </div>
                <h3 className="font-display text-white text-sm" style={{ fontWeight: 700 }}>Energy Production</h3>
              </div>
              <div className="flex flex-col gap-2">
                {[
                  { l: 'Per day', v: `${dailyKwh} kWh` },
                  { l: 'Per month', v: `${monthlyKwh.toLocaleString()} kWh` },
                  { l: 'Per year', v: `${data.yearly_energy_kwh.toLocaleString()} kWh`, highlight: true },
                  { l: 'System size', v: `${data.system_capacity_kw} kWp` },
                  { l: 'Sunshine hrs', v: `${data.sunshine_hours} hrs/yr` },
                ].map(({ l, v, highlight }) => (
                  <div key={l} className={`flex justify-between items-center p-2.5 rounded-xl ${highlight ? 'bg-solar-400/10 border border-solar-400/20' : 'bg-white/4'}`}>
                    <span className="font-body text-xs text-slate-400">{l}</span>
                    <span className={`font-display text-xs ${highlight ? 'text-solar-300' : 'text-white'}`} style={{ fontWeight: 700 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Savings + carbon */}
            <div className="card p-5 animate-slide-up" style={{ animationDelay: '200ms' }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-green-400/15 rounded-lg flex items-center justify-center">
                  <TrendingUp size={15} className="text-green-400" />
                </div>
                <h3 className="font-display text-white text-sm" style={{ fontWeight: 700 }}>Financial &amp; Environment</h3>
              </div>
              <div className="flex flex-col gap-3">
                <div className="p-3 bg-green-500/8 border border-green-500/20 rounded-xl">
                  <p className="text-slate-400 text-xs font-body mb-1">Yearly savings (₹7/kWh)</p>
                  <p className="font-display text-2xl text-green-400" style={{ fontWeight: 800 }}>
                    ₹{yearlySavings.toLocaleString()}
                  </p>
                </div>
                <div className="p-3 bg-teal-500/8 border border-teal-500/20 rounded-xl">
                  <p className="text-slate-400 text-xs font-body mb-1">CO₂ offset / year</p>
                  <p className="font-display text-2xl text-teal-400" style={{ fontWeight: 800 }}>{carbonTons} tons</p>
                  <p className="text-slate-600 text-[10px] font-body mt-0.5">≈ {trees} trees planted</p>
                </div>
              </div>
            </div>

            <button
              onClick={() => { reset(); navigate('/upload') }}
              className="w-full flex items-center justify-center gap-2 py-3 bg-solar-400 hover:bg-solar-300 text-slate-950 rounded-xl font-display text-sm transition-all hover:scale-[1.02] shadow-lg shadow-solar-400/20"
              style={{ fontWeight: 700 }}>
              <Upload size={15} />
              Analyze Another Roof
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
