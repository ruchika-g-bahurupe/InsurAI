import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import {
  AlertTriangle,
  Users,
  FileText,
  CreditCard,
  FileCheck,
  Play,
  ArrowRight,
  Clock,
} from 'lucide-react'
import {
  fetchDashboardMetrics,
  fetchLatestAnalysisRun,
  fetchAttentionItems,
  triggerWatchdogSweep,
} from '../services/api'
import { StatCard } from '../components/ui/StatCard'
import { Badge } from '../components/ui/Badge'
import { PageLoader, Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/EmptyState'
import {
  formatCurrency,
  formatDateTime,
  urgencyColor,
  statusColor,
  categoryLabel,
} from '../lib/utils'

export default function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardMetrics,
  })

  const { data: latestRun } = useQuery({
    queryKey: ['latest-run'],
    queryFn: fetchLatestAnalysisRun,
    retry: 0,
  })

  const { data: topAlerts } = useQuery({
    queryKey: ['attention', 'dashboard-top'],
    queryFn: () => fetchAttentionItems({ status: 'ACTIVE', sort_by: 'attention_score', order: 'desc', limit: 6 }),
  })

  const watchdogMutation = useMutation({
    mutationFn: () =>
      triggerWatchdogSweep({ run_type: 'PROACTIVE_SWEEP', trigger_source: 'DASHBOARD_MANUAL' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['latest-run'] })
      queryClient.invalidateQueries({ queryKey: ['attention'] })
      queryClient.invalidateQueries({ queryKey: ['attention-overview'] })
      queryClient.invalidateQueries({ queryKey: ['analysis-runs'] })
    },
  })

  if (metricsLoading) return <PageLoader />
  if (metricsError || !metrics) {
    return <ErrorState onRetry={() => refetchMetrics()} />
  }

  const categoryData = Object.entries(metrics.attention_by_category).map(([key, count]) => ({
    name: categoryLabel(key),
    count,
  }))

  const urgencyData = [
    { name: 'Critical', count: metrics.attention_by_urgency.CRITICAL ?? 0 },
    { name: 'High', count: metrics.attention_by_urgency.HIGH ?? 0 },
    { name: 'Medium', count: metrics.attention_by_urgency.MEDIUM ?? 0 },
    { name: 'Low', count: metrics.attention_by_urgency.LOW ?? 0 },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Executive Operations Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Live portfolio risk telemetry, retention exposure, and Watchdog monitoring status.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {latestRun && (
            <div className="hidden md:flex items-center gap-2 text-xs text-slate-600 bg-white border border-slate-200 px-3 py-1.5 rounded-md">
              <Clock size={13} className="text-slate-400" />
              <span>Last Sweep: {formatDateTime(latestRun.started_at)}</span>
              <Badge className={statusColor(latestRun.status)}>{latestRun.status}</Badge>
            </div>
          )}
          <button
            onClick={() => watchdogMutation.mutate()}
            disabled={watchdogMutation.isPending}
            className="btn-primary"
          >
            {watchdogMutation.isPending ? <Spinner size={15} /> : <Play size={14} />}
            <span>{watchdogMutation.isPending ? 'Running Sweep...' : 'Run Watchdog Sweep'}</span>
          </button>
        </div>
      </div>

      {watchdogMutation.isSuccess &&
        (watchdogMutation.data as Record<string, unknown>)?.status === 'DEGRADED' && (
          <div className="card px-4 py-3 bg-amber-50 border-amber-200 text-amber-900 text-sm flex items-center justify-between gap-2">
            <span>
              {String((watchdogMutation.data as Record<string, unknown>)?.error || 'Autonomous AI unavailable.')}
            </span>
            <button onClick={() => watchdogMutation.mutate()} className="text-xs font-semibold underline">
              Retry Investigation
            </button>
          </div>
        )}

      {watchdogMutation.isSuccess &&
        (watchdogMutation.data as Record<string, unknown>)?.status === 'COMPLETED' && (
          <div className="card px-4 py-3 bg-emerald-50 border-emerald-200 text-emerald-800 text-sm flex items-center justify-between">
            <span>
              Watchdog investigation finished:{' '}
              {String((watchdogMutation.data as Record<string, unknown>)?.summary || 'Portfolio updated.')}
            </span>
            <button onClick={() => navigate('/attention')} className="text-xs font-semibold underline">
              View Attention Queue
            </button>
          </div>
        )}

      {watchdogMutation.isError && (
        <div className="card px-4 py-3 bg-red-50 border-red-200 text-red-700 text-sm">
          Failed to trigger Watchdog sweep. Check backend server logs.
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Customers Requiring Attention"
          value={metrics.customers_requiring_attention}
          sub={`${metrics.high_priority_cases} Critical / High priority alerts`}
          icon={<AlertTriangle size={16} />}
          accent={metrics.high_priority_cases > 0 ? 'red' : 'default'}
          onClick={() => navigate('/attention')}
        />
        <StatCard
          label="Premium at Risk"
          value={formatCurrency(metrics.total_premium_at_risk)}
          sub={`${metrics.premium_issues_count} overdue or failed installments`}
          icon={<CreditCard size={16} />}
          accent={metrics.premium_issues_count > 0 ? 'amber' : 'default'}
          onClick={() => navigate('/billing')}
        />
        <StatCard
          label="Expiring Within 30 Days"
          value={metrics.upcoming_policy_expirations.in_30_days}
          sub={`${metrics.upcoming_policy_expirations.in_7_days} critical within 7 days`}
          icon={<FileText size={16} />}
          accent="blue"
          onClick={() => navigate('/policies')}
        />
        <StatCard
          label="Missing Mandatory Docs"
          value={metrics.missing_documents_count}
          sub={`${metrics.total_active_policies} active policies across ${metrics.total_customers} customers`}
          icon={<FileCheck size={16} />}
          accent={metrics.missing_documents_count > 0 ? 'amber' : 'green'}
          onClick={() => navigate('/documents')}
        />
      </div>

      {/* Secondary Portfolio Snapshot */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="card p-3.5 flex items-center justify-between">
          <span className="text-xs text-slate-500">Total Customers</span>
          <span className="text-sm font-semibold text-slate-900">{metrics.total_customers}</span>
        </div>
        <div className="card p-3.5 flex items-center justify-between">
          <span className="text-xs text-slate-500">VIP / HNW</span>
          <span className="text-sm font-semibold text-blue-700">{metrics.vip_customers_count}</span>
        </div>
        <div className="card p-3.5 flex items-center justify-between">
          <span className="text-xs text-slate-500">High Risk Segment</span>
          <span className="text-sm font-semibold text-red-700">{metrics.high_risk_customers_count}</span>
        </div>
        <div className="card p-3.5 flex items-center justify-between">
          <span className="text-xs text-slate-500">60-Day Renewals</span>
          <span className="text-sm font-semibold text-slate-900">
            {metrics.upcoming_policy_expirations.in_60_days}
          </span>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Active Alerts by Category</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryData} margin={{ top: 5, right: 16, left: -16, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#475569' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#cbd5e1',
                    fontSize: '12px',
                    borderRadius: '6px',
                  }}
                />
                <Bar dataKey="count" fill="#1d4ed8" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Active Alerts by Urgency</h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={urgencyData} margin={{ top: 5, right: 16, left: -16, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#475569' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    borderColor: '#cbd5e1',
                    fontSize: '12px',
                    borderRadius: '6px',
                  }}
                />
                <Bar dataKey="count" fill="#334155" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top Priority Attention Preview */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Top Priority Attention Queue</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Highest-scoring cases automatically identified by The Watchdog.
            </p>
          </div>
          <button onClick={() => navigate('/attention')} className="btn-ghost text-blue-700 text-xs">
            <span>Open Attention Center</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-header">
                <th className="px-4 py-2.5">Customer</th>
                <th className="px-4 py-2.5">Policy</th>
                <th className="px-4 py-2.5">Category</th>
                <th className="px-4 py-2.5">Urgency</th>
                <th className="px-4 py-2.5">Score</th>
                <th className="px-4 py-2.5">Issue</th>
                <th className="px-4 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody>
              {(topAlerts || []).map((item) => (
                <tr
                  key={item.id}
                  onClick={() => navigate(`/attention/${item.id}`)}
                  className="table-row cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{item.customer_name || 'Unknown'}</div>
                    <div className="text-xs text-slate-500">{item.customer_code}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-700 font-mono text-xs">
                    {item.policy_number || '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-700">{categoryLabel(item.category)}</td>
                  <td className="px-4 py-3">
                    <Badge className={urgencyColor(item.urgency_level)}>{item.urgency_level}</Badge>
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-900">{item.attention_score.toFixed(1)}</td>
                  <td className="px-4 py-3 text-slate-700 max-w-xs truncate">{item.title}</td>
                  <td className="px-4 py-3">
                    <Badge className={statusColor(item.status)}>{item.status}</Badge>
                  </td>
                </tr>
              ))}
              {(!topAlerts || topAlerts.length === 0) && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-slate-500">
                    No active attention items. Run a Watchdog sweep to scan customer portfolios.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
