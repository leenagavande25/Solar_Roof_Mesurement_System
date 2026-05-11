import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Sun, Menu, X, Zap } from 'lucide-react'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const links = [
    { to: '/', label: 'Home' },
    { to: '/upload', label: 'Upload' },
    { to: '/results', label: 'Results' },
  ]

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled || mobileOpen
          ? 'bg-slate-950/90 backdrop-blur-xl border-b border-white/8'
          : 'bg-transparent'
      }`}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2.5 group">
            <div className="relative">
              <div className="w-8 h-8 bg-solar-400 rounded-lg flex items-center justify-center transition-transform duration-300 group-hover:scale-110 group-hover:rotate-12">
                <Sun size={16} className="text-slate-950" strokeWidth={2.5} />
              </div>
              <div className="absolute -inset-1 bg-solar-400/30 rounded-lg blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>
            <div className="flex flex-col leading-none">
              <span className="font-display font-extrabold text-white text-sm tracking-tight" style={{ fontWeight: 800 }}>
                SolarMeasure
              </span>
              <span className="text-[10px] text-solar-400 font-body font-medium tracking-widest uppercase">
                Roof Analysis
              </span>
            </div>
          </NavLink>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {links.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg text-sm font-display transition-all duration-200 ${
                    isActive
                      ? 'text-solar-400 bg-solar-400/10 font-bold'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`
                }
                style={({ isActive }) => ({ fontWeight: isActive ? 700 : 500 })}
              >
                {label}
              </NavLink>
            ))}
          </div>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-3">
            <NavLink
              to="/upload"
              className="flex items-center gap-2 px-4 py-2 bg-solar-400 hover:bg-solar-300 text-slate-950 rounded-lg font-display text-sm transition-all duration-200 hover:scale-[1.03] active:scale-[0.97]"
              style={{ fontWeight: 700 }}
            >
              <Zap size={14} strokeWidth={2.5} />
              Analyze Now
            </NavLink>
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            onClick={() => setMobileOpen(v => !v)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Mobile Menu */}
        <div className={`md:hidden transition-all duration-300 overflow-hidden ${mobileOpen ? 'max-h-64 pb-4' : 'max-h-0'}`}>
          <div className="flex flex-col gap-1 pt-2 border-t border-white/8">
            {links.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `px-4 py-3 rounded-lg text-sm font-display transition-all duration-200 ${
                    isActive
                      ? 'text-solar-400 bg-solar-400/10'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`
                }
                style={({ isActive }) => ({ fontWeight: isActive ? 700 : 500 })}
              >
                {label}
              </NavLink>
            ))}
            <NavLink
              to="/upload"
              className="mt-2 flex items-center justify-center gap-2 px-4 py-3 bg-solar-400 hover:bg-solar-300 text-slate-950 rounded-lg font-display text-sm"
              style={{ fontWeight: 700 }}
            >
              <Zap size={14} strokeWidth={2.5} />
              Analyze Now
            </NavLink>
          </div>
        </div>
      </nav>
    </header>
  )
}
