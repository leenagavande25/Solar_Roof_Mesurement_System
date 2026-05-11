import { useNavigate } from 'react-router-dom'
import { Upload, Sun, Zap, BarChart3, Shield, Clock, ArrowRight, ChevronRight } from 'lucide-react'
import PageHeader from '../components/PageHeader'

const features = [
  {
    icon: Sun,
    title: 'AI-Powered Detection',
    description: 'Advanced computer vision identifies your roof boundaries with exceptional precision.',
    color: 'text-solar-400',
    bg: 'bg-solar-400/10',
  },
  {
    icon: BarChart3,
    title: 'Precise Measurements',
    description: 'Get exact roof area calculations to optimize your solar installation plans.',
    color: 'text-blue-400',
    bg: 'bg-blue-400/10',
  },
  {
    icon: Zap,
    title: 'Panel Estimation',
    description: 'Instantly know how many solar panels will fit and the estimated energy output.',
    color: 'text-green-400',
    bg: 'bg-green-400/10',
  },
  {
    icon: Shield,
    title: 'Secure Processing',
    description: 'Your images are processed securely and never stored beyond your session.',
    color: 'text-purple-400',
    bg: 'bg-purple-400/10',
  },
  {
    icon: Clock,
    title: 'Results in Seconds',
    description: 'Get comprehensive roof analysis in under 30 seconds — no waiting around.',
    color: 'text-pink-400',
    bg: 'bg-pink-400/10',
  },
  {
    icon: Upload,
    title: 'Easy Upload',
    description: 'Simple drag-and-drop interface accepts any standard aerial or satellite image.',
    color: 'text-orange-400',
    bg: 'bg-orange-400/10',
  },
]

const steps = [
  { number: '01', title: 'Upload Image', desc: 'Upload a satellite or aerial image of the roof you want to analyze.' },
  { number: '02', title: 'AI Analysis', desc: 'Our model detects roof boundaries and calculates the exact usable area.' },
  { number: '03', title: 'Get Results', desc: 'Receive detailed measurements and panel count recommendations instantly.' },
]

export default function HomePage() {
  const navigate = useNavigate()

  return (
    <div className="relative min-h-screen">
      {/* Background glow elements */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-solar-400/5 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed top-1/3 left-0 w-[300px] h-[300px] bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-1/3 right-0 w-[300px] h-[300px] bg-solar-400/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* HERO */}
        <section className="pt-32 pb-20 lg:pt-40 lg:pb-28">
          <div className="flex flex-col lg:flex-row items-start lg:items-center gap-12 lg:gap-16">

            {/* Left: Hero text */}
            <div className="flex-1 max-w-2xl">
              <PageHeader
                badge={{ text: 'AI Solar Analysis', icon: <Sun size={12} /> }}
                title="Measure Every Roof."
                highlight="Maximize Solar Potential."
                description="Upload a satellite or aerial image of any roof. Our AI instantly maps the surface, calculates usable area, and tells you exactly how many solar panels will fit."
              />

              <div className="flex flex-col sm:flex-row gap-3 mt-8">
                <button
                  onClick={() => navigate('/upload')}
                  className="btn-primary text-base"
                >
                  <Upload size={18} />
                  Upload Image
                  <ArrowRight size={16} />
                </button>
                <button
                  onClick={() => navigate('/results')}
                  className="btn-secondary text-base"
                >
                  View Sample Results
                </button>
              </div>

              {/* Social proof */}
              <div className="flex items-center gap-6 mt-10">
                <div className="flex flex-col">
                  <span className="font-display text-2xl font-extrabold text-white" style={{ fontWeight: 800 }}>±2%</span>
                  <span className="text-xs text-slate-500 font-body">Accuracy</span>
                </div>
                <div className="w-px h-10 bg-white/10" />
                <div className="flex flex-col">
                  <span className="font-display text-2xl font-extrabold text-white" style={{ fontWeight: 800 }}>&lt;30s</span>
                  <span className="text-xs text-slate-500 font-body">Processing Time</span>
                </div>
                <div className="w-px h-10 bg-white/10" />
                <div className="flex flex-col">
                  <span className="font-display text-2xl font-extrabold text-white" style={{ fontWeight: 800 }}>Free</span>
                  <span className="text-xs text-slate-500 font-body">To Use</span>
                </div>
              </div>
            </div>

            {/* Right: Visual mockup card */}
            <div className="flex-1 w-full max-w-lg lg:max-w-none animate-fade-in" style={{ animationDelay: '200ms' }}>
              <div className="card-elevated p-1 glow-solar">
                {/* Fake roof image placeholder */}
                <div className="relative rounded-xl overflow-hidden bg-gradient-to-br from-slate-800 to-slate-900 aspect-video flex items-center justify-center">
                  {/* Roof grid simulation */}
                  <svg viewBox="0 0 400 240" className="absolute inset-0 w-full h-full opacity-30">
                    <defs>
                      <pattern id="roofGrid" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
                        <rect width="38" height="18" x="1" y="1" fill="rgba(251,191,36,0.15)" stroke="rgba(251,191,36,0.3)" strokeWidth="0.5" rx="1" />
                        <rect width="38" height="18" x="1" y="21" fill="rgba(251,191,36,0.1)" stroke="rgba(251,191,36,0.2)" strokeWidth="0.5" rx="1" />
                      </pattern>
                    </defs>
                    <rect width="400" height="240" fill="url(#roofGrid)" />
                  </svg>
                  {/* Roof outline */}
                  <svg viewBox="0 0 400 240" className="absolute inset-0 w-full h-full">
                    <polygon
                      points="50,180 200,60 350,180"
                      fill="rgba(251,191,36,0.08)"
                      stroke="rgba(251,191,36,0.6)"
                      strokeWidth="2"
                      strokeDasharray="8,4"
                    />
                  </svg>
                  <div className="relative flex flex-col items-center gap-3 text-center p-6">
                    <div className="w-14 h-14 bg-solar-400/20 rounded-2xl flex items-center justify-center">
                      <Sun size={24} className="text-solar-400 animate-pulse-glow" />
                    </div>
                    <p className="font-display font-bold text-solar-300 text-sm" style={{ fontWeight: 700 }}>
                      Roof Analysis Preview
                    </p>
                    <p className="text-slate-500 text-xs font-body">Upload an image to see your results here</p>
                  </div>
                </div>

                {/* Fake result bar */}
                <div className="flex gap-3 p-4">
                  <div className="flex-1 bg-white/5 rounded-xl p-3 border border-white/8">
                    <p className="text-slate-500 text-xs font-body mb-1">Roof Area</p>
                    <p className="font-display font-extrabold text-solar-300 text-lg" style={{ fontWeight: 800 }}>142 m²</p>
                  </div>
                  <div className="flex-1 bg-white/5 rounded-xl p-3 border border-white/8">
                    <p className="text-slate-500 text-xs font-body mb-1">Solar Panels</p>
                    <p className="font-display font-extrabold text-white text-lg" style={{ fontWeight: 800 }}>56 units</p>
                  </div>
                  <div className="flex-1 bg-solar-400/10 rounded-xl p-3 border border-solar-400/20">
                    <p className="text-solar-400/70 text-xs font-body mb-1">Coverage</p>
                    <p className="font-display font-extrabold text-solar-400 text-lg" style={{ fontWeight: 800 }}>82%</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="py-16 border-t border-white/8">
          <div className="flex flex-col items-center text-center mb-12">
            <span className="text-solar-400 text-xs font-display uppercase tracking-widest font-bold mb-3" style={{ fontWeight: 700 }}>
              How It Works
            </span>
            <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-white" style={{ fontWeight: 800 }}>
              Three steps to your<br />
              <span className="bg-gradient-to-r from-solar-300 to-solar-500 bg-clip-text text-transparent">solar measurement</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {steps.map((step, i) => (
              <div key={step.number} className="relative">
                <div className="card p-6 h-full hover:border-white/20 transition-all duration-300 group">
                  <div className="flex items-start gap-4">
                    <span className="font-display text-4xl font-extrabold text-solar-400/20 group-hover:text-solar-400/40 transition-colors leading-none" style={{ fontWeight: 800 }}>
                      {step.number}
                    </span>
                    <div>
                      <h3 className="font-display font-bold text-white mb-2" style={{ fontWeight: 700 }}>{step.title}</h3>
                      <p className="font-body text-slate-400 text-sm leading-relaxed">{step.desc}</p>
                    </div>
                  </div>
                </div>
                {i < steps.length - 1 && (
                  <div className="hidden md:flex absolute top-1/2 -right-3 -translate-y-1/2 z-10 text-slate-600">
                    <ChevronRight size={20} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* FEATURES */}
        <section className="py-16 border-t border-white/8">
          <div className="flex flex-col items-center text-center mb-12">
            <span className="text-solar-400 text-xs font-display uppercase tracking-widest font-bold mb-3" style={{ fontWeight: 700 }}>
              Features
            </span>
            <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-white" style={{ fontWeight: 800 }}>
              Everything you need for<br />
              <span className="bg-gradient-to-r from-solar-300 to-solar-500 bg-clip-text text-transparent">solar planning</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f, i) => (
              <div
                key={f.title}
                className="card p-5 hover:border-white/20 hover:-translate-y-0.5 transition-all duration-300 animate-slide-up"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div className={`w-10 h-10 ${f.bg} rounded-xl flex items-center justify-center mb-4`}>
                  <f.icon size={18} className={f.color} />
                </div>
                <h3 className="font-display font-bold text-white mb-2 text-sm" style={{ fontWeight: 700 }}>{f.title}</h3>
                <p className="font-body text-slate-400 text-sm leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 border-t border-white/8">
          <div className="relative card p-10 sm:p-16 text-center overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-solar-400/8 via-transparent to-solar-600/5 pointer-events-none" />
            <div className="relative">
              <div className="w-14 h-14 bg-solar-400/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Sun size={24} className="text-solar-400" />
              </div>
              <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-white mb-4" style={{ fontWeight: 800 }}>
                Ready to measure your roof?
              </h2>
              <p className="font-body text-slate-400 mb-8 max-w-md mx-auto">
                Upload any roof image and get detailed solar panel calculations in seconds.
              </p>
              <button
                onClick={() => navigate('/upload')}
                className="btn-primary text-base mx-auto"
              >
                <Upload size={18} />
                Upload Your Roof Image
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-8 border-t border-white/8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Sun size={16} className="text-solar-400" />
            <span className="font-display font-bold text-white text-sm" style={{ fontWeight: 700 }}>SolarMeasure</span>
          </div>
          <p className="font-body text-slate-600 text-sm">
            Solar Roof Measurement System — AI-powered roof analysis
          </p>
        </footer>
      </div>
    </div>
  )
}
