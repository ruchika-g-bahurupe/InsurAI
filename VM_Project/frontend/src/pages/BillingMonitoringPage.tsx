import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchPremiumIssues } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { StatCard } from '../components/ui/StatCard'
import { PageLoader } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import { formatCurrencyExact, formatDate, statusColor } from '../lib/utils'

export default function BillingMonitoringPage() {
  const navigate = useNavigate()
  const [issueType, setIssueType] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['premium-issues', issueType],
    queryFn: () =>
      fetchPremiumIssues({
        issue_type: issueType || undefined,
        limit: 100,
      }),
  })

  if (isLoading) return <PageLoader />
  if (error || !data) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-5">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-xl font-semibold text-slate-900">Premium & Payment Monitoring</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Monitor overdue installments, grace period cutoffs, and failed auto-debits.
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard label="Total Issues" value={data.total_issues} />
        <StatCard label="In Grace Period" value={data.in_grace_period_count} accent="amber" />
        <StatCard label="Overdue" value={data.overdue_count} accent="red" />
        <StatCard label="Failed Auto-Debits" value={data.failed_auto_debit_count} accent="red" />
        <StatCard
          label="Amount at Risk"
          value={formatCurrencyExact(data.total_amount_at_risk)}
          accent="amber"
        />
      </div>

      {/* Filter Bar */}
      <div className="card p-3.5 flex flex-wrap items-center gap-2">
        {[
          { key: '', label: 'All Billing Issues' },
          { key: 'GRACE_PERIOD', label: 'Grace Period' },
          { key: 'OVERDUE', label: 'Overdue' },
          { key: 'FAILED_DEBIT', label: 'Failed Debit' },
          { key: 'UPCOMING', label: 'Upcoming (30d)' },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setIssueType(f.key)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium border ${
              issueType === f.key
                ? 'bg-blue-700 text-white border-blue-700'
                : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {data.items.length === 0 ? (
          <EmptyState title="No premium billing issues found" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5">Policy</th>
                  <th className="px-4 py-2.5">Classification</th>
                  <th className="px-4 py-2.5">Amount Due</th>
                  <th className="px-4 py-2.5">Due Date</th>
                  <th className="px-4 py-2.5">Grace Cutoff</th>
                  <th className="px-4 py-2.5">Retries</th>
                  <th className="px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr
                    key={item.schedule_id}
                    onClick={() => navigate(`/customers/${item.customer_id}`)}
                    className="table-row cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-blue-700">{item.customer_name}</div>
                      <div className="text-xs text-slate-500">{item.customer_code}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-mono text-xs text-slate-900">{item.policy_number}</div>
                      <div className="text-xs text-slate-500">Installment #{item.installment_number}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={statusColor(item.issue_type)}>{item.issue_type}</Badge>
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {formatCurrencyExact(item.amount_due)}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <div>{formatDate(item.due_date)}</div>
                      {item.days_overdue > 0 && (
                        <div className="text-red-700 font-medium">{item.days_overdue}d overdue</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <div>{formatDate(item.grace_period_end)}</div>
                      <div className="text-slate-500">{item.days_grace_remaining}d left</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-700">{item.retry_attempts}</td>
                    <td className="px-4 py-3">
                      <Badge className={statusColor(item.status)}>{item.status}</Badge>
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
