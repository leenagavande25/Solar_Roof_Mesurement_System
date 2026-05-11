import { Sun } from 'lucide-react'

export default function LoadingSpinner({ message = 'Processing...', subMessage = '' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16 animate-fade-in">
      {/* Spinning sun */}
      <div className="relative">
        {/* Outer ring */}
        <div className="w-20 h-20 rounded-full border-2 border-solar-400/20 border-t-solar-400 animate-spin" />
        {/* Middle ring */}
        <div className="absolute inset-2 w-16 h-16 rounded-full border-2 border-solar-300/10 border-b-solar-300/60 animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
        {/* Center icon */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-10 h-10 bg-solar-400/20 rounded-full flex items-center justify-center">
            <Sun size={18} className="text-solar-400 animate-pulse" />
          </div>
        </div>
        {/* Glow */}
        <div className="absolute inset-0 rounded-full bg-solar-400/10 blur-xl animate-pulse" />
      </div>

      <div className="flex flex-col items-center gap-1.5">
        <p className="font-display font-semibold text-white text-lg" style={{ fontWeight: 600 }}>
          {message}
        </p>
        {subMessage && (
          <p className="text-slate-400 text-sm font-body">{subMessage}</p>
        )}
      </div>

      {/* Progress bar */}
      <div className="w-48 h-1 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-solar-500 to-solar-300 rounded-full animate-pulse"
          style={{ width: '60%', animation: 'progressBar 2s ease-in-out infinite' }}
        />
      </div>

      <style>{`
        @keyframes progressBar {
          0% { width: 10%; margin-left: 0; }
          50% { width: 60%; }
          100% { width: 10%; margin-left: 85%; }
        }
      `}</style>
    </div>
  )
}
