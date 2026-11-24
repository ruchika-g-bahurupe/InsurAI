import { Inbox, AlertCircle } from 'lucide-react'

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-10 h-10 rounded-md bg-slate-100 border border-slate-200 flex items-center justify-center mb-3">
        <Inbox size={18} className="text-slate-400" />
      </div>
      <p className="text-sm font-semibold text-slate-800">{title}</p>
      {description && <p className="text-xs text-slate-500 mt-1 max-w-md">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="card p-8 flex flex-col items-center justify-center text-center my-4">
      <div className="w-10 h-10 rounded-md bg-red-50 border border-red-200 flex items-center justify-center mb-3">
        <AlertCircle size={18} className="text-red-600" />
      </div>
      <p className="text-sm font-semibold text-slate-900">Unable to load data</p>
      <p className="text-xs text-slate-500 mt-1 max-w-md">
        {message || 'The backend service could not be reached. Ensure FastAPI is running on port 8000.'}
      </p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary mt-4 text-xs">
          Retry Request
        </button>
      )}
    </div>
  )
}
