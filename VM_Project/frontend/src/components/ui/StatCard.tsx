interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon?: React.ReactNode
  accent?: 'default' | 'red' | 'amber' | 'green' | 'blue'
  onClick?: () => void
}

const accentBorder: Record<string, string> = {
  default: 'border-slate-200',
  red: 'border-red-200',
  amber: 'border-amber-200',
  green: 'border-emerald-200',
  blue: 'border-blue-200',
}

const accentValue: Record<string, string> = {
  default: 'text-slate-900',
  red: 'text-red-700',
  amber: 'text-amber-700',
  green: 'text-emerald-700',
  blue: 'text-blue-700',
}

export function StatCard({ label, value, sub, icon, accent = 'default', onClick }: StatCardProps) {
  return (
    <div
      className={`card p-4 flex flex-col gap-2 ${accentBorder[accent]} ${
        onClick ? 'cursor-pointer hover:border-blue-300 transition-colors' : ''
      }`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</span>
        {icon && <span className="text-slate-400">{icon}</span>}
      </div>
      <div>
        <p className={`text-2xl font-semibold tracking-tight ${accentValue[accent]}`}>{value}</p>
        {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

export default StatCard
