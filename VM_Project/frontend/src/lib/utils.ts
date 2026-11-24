export function formatCurrency(amount: number | undefined | null): string {
  if (amount == null) return '$0'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function formatCurrencyExact(amount: number | undefined | null): string {
  if (amount == null) return '$0.00'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function formatDateTime(dateStr: string | undefined | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function timeAgo(dateStr: string | undefined | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function urgencyColor(urgency: string): string {
  switch (urgency?.toUpperCase()) {
    case 'CRITICAL':
      return 'text-red-700 bg-red-50 border-red-200'
    case 'HIGH':
      return 'text-amber-700 bg-amber-50 border-amber-200'
    case 'MEDIUM':
      return 'text-yellow-700 bg-yellow-50 border-yellow-200'
    case 'LOW':
      return 'text-slate-600 bg-slate-100 border-slate-200'
    default:
      return 'text-slate-600 bg-slate-100 border-slate-200'
  }
}

export function statusColor(status: string): string {
  switch (status?.toUpperCase()) {
    case 'OPEN':
      return 'text-blue-700 bg-blue-50 border-blue-200'
    case 'IN_PROGRESS':
    case 'RUNNING':
    case 'UNDER_REVIEW':
    case 'RENEWAL_PENDING':
    case 'PENDING_SUBMISSION':
    case 'PENDING':
    case 'DEGRADED':
      return 'text-amber-700 bg-amber-50 border-amber-200'
    case 'RESOLVED':
    case 'VERIFIED':
    case 'PAID':
    case 'ACTIVE':
    case 'COMPLETED':
    case 'APPROVED':
    case 'SETTLED':
      return 'text-emerald-700 bg-emerald-50 border-emerald-200'
    case 'DISMISSED':
    case 'CANCELLED':
    case 'INACTIVE':
      return 'text-slate-600 bg-slate-100 border-slate-200'
    case 'OVERDUE':
    case 'FAILED':
    case 'REJECTED':
    case 'EXPIRED':
    case 'LAPSED':
    case 'GRACE_PERIOD':
    case 'FAILED_DEBIT':
      return 'text-red-700 bg-red-50 border-red-200'
    default:
      return 'text-slate-600 bg-slate-100 border-slate-200'
  }
}

export function tierColor(tier: string): string {
  switch (tier?.toUpperCase()) {
    case 'HIGH_NET_WORTH':
      return 'text-indigo-700 bg-indigo-50 border-indigo-200'
    case 'VIP':
      return 'text-blue-700 bg-blue-50 border-blue-200'
    default:
      return 'text-slate-600 bg-slate-100 border-slate-200'
  }
}

export function categoryLabel(category: string): string {
  switch (category?.toUpperCase()) {
    case 'POLICY_EXPIRY':
      return 'Policy Expiry'
    case 'MISSING_DOCS':
      return 'Missing Docs'
    case 'PREMIUM_OVERDUE':
      return 'Premium Overdue'
    case 'RENEWAL_FOLLOWUP':
      return 'Renewal Follow-up'
    case 'RISK_ALERT':
      return 'Risk Alert'
    default:
      return category
  }
}
