export default function PageHeader({ badge, title, highlight, description, centered = false }) {
  return (
    <div className={`flex flex-col gap-4 animate-slide-up ${centered ? 'items-center text-center' : ''}`}>
      {badge && (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-solar-400/10 border border-solar-400/20 rounded-full">
          {badge.icon && <span className="text-solar-400">{badge.icon}</span>}
          <span className="text-solar-400 text-xs font-display uppercase tracking-widest" style={{ fontWeight: 700 }}>
            {badge.text}
          </span>
        </div>
      )}

      <h1 className="font-display text-4xl sm:text-5xl text-white leading-tight" style={{ fontWeight: 800 }}>
        {title}
        {highlight && (
          <>
            {' '}
            <span className="bg-gradient-to-r from-solar-300 via-solar-400 to-solar-500 bg-clip-text text-transparent">
              {highlight}
            </span>
          </>
        )}
      </h1>

      {description && (
        <p className="font-body text-slate-400 text-lg leading-relaxed max-w-2xl">
          {description}
        </p>
      )}
    </div>
  )
}
