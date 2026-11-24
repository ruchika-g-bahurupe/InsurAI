import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Play } from 'lucide-react'
import { fetchAnalysisRuns, triggerWatchdogSweep } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { PageLoader, Spinner } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import { formatDateTime, statusColor } from '../lib/utils'

export default function AnalysisHistoryPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [runTypeFilter, setRunTypeFilter] = useState('')

  const { data: runs, isLoading, error, refetch } = useQuery({
    queryKey: ['analysis-runs', statusFilter, runTypeFilter],
    queryFn: () =>
      fetchAnalysisRuns({
        status: statusFilter || undefined,
        run_type: runTypeFilter || undefined,
        limit: 50,
      }),
  })

  const sweepMutation = useMutation({
    mutationFn: () =>
      triggerWatchdogSweep({ run_type: 'ON_DEMAND', trigger_source: 'ANALYSIS_HISTORY_PAGE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis-runs'] })
      queryClient.invalidateQueries({ queryKey: ['latest-run'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['attention'] })
    },
  })

  if (isLoading) return <PageLoader />
  if (error) return <ErrorState onRetry={() => refetch()} />

  const sweepData = sweepMutation.data as Record<string, unknown> | undefined

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Analysis History & Agent Execution Logs</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Telemetry, tool-call counts, iterations, and outcomes for autonomous Watchdog investigations.
          </p>
        </div>
        <button
          onClick={() => sweepMutation.mutate()}
          disabled={sweepMutation.isPending}
          className="btn-primary"
        >
          {sweepMutation.isPending ? <Spinner size={15} /> : <Play size={14} />}
          <span>{sweepMutation.isPending ? 'Investigating...' : 'Trigger On-Demand Investigation'}</span>
        </button>
      </div>

      {sweepMutation.isSuccess && sweepData?.status === 'DEGRADED' && (
        <div className="card px-4 py-3 bg-amber-50 border-amber-200 text-amber-900 text-sm flex items-center justify-between">
          <span>{String(sweepData.error || sweepData.summary)}</span>
          <button onClick={() => sweepMutation.mutate()} className="text-xs font-semibold underline">
            Retry
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="card p-3.5 flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input text-xs"
        >
          <option value="">All Statuses</option>
          <option value="COMPLETED">Completed</option>
          <option value="DEGRADED">Degraded</option>
          <option value="RUNNING">Running</option>
          <option value="FAILED">Failed</option>
        </select>

        <select
          value={runTypeFilter}
          onChange={(e) => setRunTypeFilter(e.target.value)}
          className="input text-xs"
        >
          <option value="">All Run Types</option>
          <option value="PROACTIVE_SWEEP">Proactive Sweep</option>
          <option value="ON_DEMAND">On-Demand</option>
        </select>
      </div>

      {/* Logs Table */}
      <div className="card overflow-hidden">
        {!runs || runs.length === 0 ? (
          <EmptyState title="No analysis runs recorded" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5">Started</th>
                  <th className="px-4 py-2.5">Type / Trigger</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Model Used</th>
                  <th className="px-4 py-2.5">Iterations / Tools</th>
                  <th className="px-4 py-2.5">Detected</th>
                  <th className="px-4 py-2.5">Created / Updated</th>
                  <th className="px-4 py-2.5">Duration</th>
                  <th className="px-4 py-2.5">Summary</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="table-row">
                    <td className="px-4 py-3 text-xs whitespace-nowrap text-slate-700">
                      {formatDateTime(run.started_at)}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <div className="font-medium text-slate-900">{run.run_type}</div>
                      <div className="text-slate-500">{run.trigger_source}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={statusColor(run.status)}>{run.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-700">{run.model_used}</td>
                    <td className="px-4 py-3 text-xs text-slate-700">
                      {run.iterations_used ?? 0} iter / {run.tool_calls_count ?? 0} tools
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-slate-900">{run.issues_detected}</td>
                    <td className="px-4 py-3 text-xs text-slate-700">
                      {run.new_recommendations_created} new / {run.recommendations_updated} upd
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">{run.execution_time_ms.toFixed(0)} ms</td>
                    <td className="px-4 py-3 text-xs text-slate-600 max-w-xs truncate">
                      {run.error_message || run.summary_notes || '—'}
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
