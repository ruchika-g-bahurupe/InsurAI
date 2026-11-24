import { Loader2 } from 'lucide-react'

export function Spinner({ size = 18 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-blue-700" />
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center h-80">
      <div className="flex flex-col items-center gap-2.5 text-slate-500">
        <Spinner size={24} />
        <p className="text-sm">Loading data...</p>
      </div>
    </div>
  )
}
