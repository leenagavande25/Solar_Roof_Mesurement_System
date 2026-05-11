import { AlertTriangle, X } from 'lucide-react'

export default function ErrorAlert({ message, onDismiss }) {
  if (!message) return null

  return (
    <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl animate-slide-up">
      <div className="flex-shrink-0 mt-0.5">
        <AlertTriangle size={18} className="text-red-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-body text-red-300 leading-relaxed">{message}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 text-red-400/60 hover:text-red-300 transition-colors mt-0.5"
          aria-label="Dismiss error"
        >
          <X size={16} />
        </button>
      )}
    </div>
  )
}
