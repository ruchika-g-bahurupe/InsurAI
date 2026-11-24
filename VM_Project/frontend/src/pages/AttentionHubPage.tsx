import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Play, ExternalLink } from 'lucide-react'
import {
  fetchAttentionItems,
  fetchAttentionOverview,
  triggerWatchdogSweep,
} from '../services/api'
import { Badge } from '../components/ui/Badge'
import { StatCard } from '../components/ui/StatCard'
import { PageLoader, Spinner } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import {
  categoryLabel,
  formatCurrency,
  statusColor,
  urgencyColor,
} from '../lib/utils'
import type { AttentionItem } from '../types'

function extractTimingLabel(item: AttentionItem): string {
  const action = item.suggested_action || {}
  if (typeof action.days_to_expiry === 'number') {
    return `${action.days_to_expiry}d remaining`
  }
  if (typeof action.grace_days_remaining === 'number') {
    return `${action.grace_days_remaining}d grace left`
  }
  const match = item.root_cause.match(/(\d+\s*days?\s*(?:overdue|remaining|left)?)/i)
  return match ? match[1] : '—'
}

export default function AttentionHubPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [category, setCategory] = useState('')
  const [urgency, setUrgency] = useState('')
  const [status, setStatus] = useState('ACTIVE')
  const [sortBy, setSortBy] = useState('attention_score')

  const { data: overview } = useQuery({
    queryKey: ['attention-overview'],
    queryFn: fetchAttentionOverview,
  })

  const {
    data: items,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['attention', category, urgency, status, sortBy],
    queryFn: () =>
      fetchAttentionItems({
        category: category || undefined,
        urgency_level: urgency || undefined,
        status: status || undefined,
        sort_by: sortBy,
        order: 'desc',
        limit: 100,
      }),
  })

  const sweepMutation = useMutation({
    mutationFn: () =>
      triggerWatchdogSweep({ run_type: 'PROACTIVE_SWEEP', trigger_source: 'ATTENTION_CENTER' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attention'] })
      queryClient.invalidateQueries({ queryKey: ['attention-overview'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['analysis-runs'] })
    },
  })

  if (isLoading) return <PageLoader />
  if (error) return <ErrorState onRetry={() => refetch()} />

  const sweepData = sweepMutation.data as Record<string, unknown> | undefined

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Customer Attention Center</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Prioritized risk queue investigated autonomously by The Watchdog across all customer portfolios.
          </p>
        </div>
        <button
          onClick={() => sweepMutation.mutate()}
          disabled={sweepMutation.isPending}
          className="btn-primary"
        >
          {sweepMutation.isPending ? <Spinner size={15} /> : <Play size={14} />}
          <span>{sweepMutation.isPending ? 'Investigating Portfolios...' : 'Run Autonomous Investigation'}</span>
        </button>
      </div>

      {sweepMutation.isSuccess && sweepData?.status === 'DEGRADED' && (
        <div className="card px-4 py-3 bg-amber-50 border-amber-200 text-amber-900 text-sm flex flex-wrap items-center justify-between gap-2">
          <span>{String(sweepData.error || sweepData.summary)}</span>
          <button onClick={() => sweepMutation.mutate()} className="text-xs font-semibold underline">
            Retry Investigation
          </button>
        </div>
      )}

      {sweepMutation.isSuccess && sweepData?.status === 'COMPLETED' && (
        <div className="card px-4 py-3 bg-emerald-50 border-emerald-200 text-emerald-800 text-sm">
          {String(sweepData.summary)}
        </div>
      )}

      {/* Overview Metrics */}
      {overview && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <StatCard label="Active Alerts" value={overview.total_active_alerts} />
          <StatCard label="Critical" value={overview.critical_alerts} accent="red" />
          <StatCard label="High" value={overview.high_alerts} accent="amber" />
          <StatCard label="Medium" value={overview.medium_alerts} accent="blue" />
          <StatCard
            label="Premium at Risk"
            value={formatCurrency(overview.total_premium_at_risk)}
            accent="amber"
          />
        </div>
      )}

      {/* Filter Bar */}
      <div className="card p-3.5 flex flex-wrap items-center gap-3">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="input text-xs"
          aria-label="Filter by category"
        >
          <option value="">All Categories</option>
          <option value="POLICY_EXPIRY">Policy Expiry</option>
          <option value="PREMIUM_OVERDUE">Premium Overdue</option>
          <option value="MISSING_DOCS">Missing Documents</option>
          <option value="RENEWAL_FOLLOWUP">Renewal Follow-up</option>
          <option value="RISK_ALERT">Risk Alert</option>
        </select>

        <select
          value={urgency}
          onChange={(e) => setUrgency(e.target.value)}
          className="input text-xs"
          aria-label="Filter by urgency"
        >
          <option value="">All Priorities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="input text-xs"
          aria-label="Filter by status"
        >
          <option value="ACTIVE">All Active (Open + In Progress)</option>
          <option value="OPEN">Open Only</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="RESOLVED">Resolved</option>
          <option value="DISMISSED">Dismissed</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="input text-xs"
          aria-label="Sort by"
        >
          <option value="attention_score">Sort: Attention Score</option>
          <option value="detected_at">Sort: Detected Date</option>
          <option value="urgency_level">Sort: Urgency</option>
        </select>

        {(category || urgency || status !== 'ACTIVE') && (
          <button
            onClick={() => {
              setCategory('')
              setUrgency('')
              setStatus('ACTIVE')
            }}
            className="btn-ghost text-xs"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Structured Queue Table */}
      <div className="card overflow-hidden">
        {!items || items.length === 0 ? (
          <EmptyState
            title="No attention items match the selected filters"
            description="Adjust your filters or run an autonomous Watchdog investigation."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5">Policy</th>
                  <th className="px-4 py-2.5">Category</th>
                  <th className="px-4 py-2.5">Priority</th>
                  <th className="px-4 py-2.5">Score / Conf.</th>
                  <th className="px-4 py-2.5">Timing</th>
                  <th className="px-4 py-2.5">Reason for Flagging</th>
                  <th className="px-4 py-2.5">Recommended Action</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => navigate(`/attention/${item.id}`)}
                    className="table-row cursor-pointer"
                  >
                    <td className="px-4 py-3 whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/customers/${item.customer_id}`)
                        }}
                        className="font-medium text-blue-700 hover:underline text-left"
                      >
                        {item.customer_name || 'Unknown'}
                      </button>
                      <div className="text-xs text-slate-500">
                        {item.customer_code} · {item.customer_tier}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="font-mono text-xs text-slate-800">
                        {item.policy_number || '—'}
                      </div>
                      <div className="text-[11px] text-slate-500">{item.policy_type || ''}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-700">
                      {categoryLabel(item.category)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge className={urgencyColor(item.urgency_level)}>{item.urgency_level}</Badge>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-semibold text-slate-900">{item.attention_score.toFixed(1)}</span>
                      {item.confidence_level && (
                        <div className="text-[11px] text-slate-500">{item.confidence_level} conf.</div>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs font-medium text-slate-700">
                      {extractTimingLabel(item)}
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <div className="font-medium text-slate-900 text-xs truncate">{item.title}</div>
                      <div className="text-xs text-slate-500 truncate">
                        {item.reasoning_summary || item.root_cause}
                      </div>
                    </td>
                    <td className="px-4 py-3 max-w-xs text-xs text-slate-600 truncate">
                      {item.ai_recommendation}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge className={statusColor(item.status)}>{item.status}</Badge>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          navigate(`/attention/${item.id}`)
                        }}
                        className="btn-ghost text-xs text-blue-700"
                      >
                        <span>Inspect</span>
                        <ExternalLink size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
