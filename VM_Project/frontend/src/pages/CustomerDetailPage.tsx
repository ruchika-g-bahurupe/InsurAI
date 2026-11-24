import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, MessageSquare, FileText, FileCheck, AlertTriangle, ShieldAlert } from 'lucide-react'
import { fetchCustomer360 } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { PageLoader } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/EmptyState'
import {
  categoryLabel,
  formatCurrency,
  formatDate,
  formatDateTime,
  statusColor,
  tierColor,
  urgencyColor,
} from '../lib/utils'

export default function CustomerDetailPage() {
  const { customerId } = useParams<{ customerId: string }>()
  const navigate = useNavigate()

  const { data: customer, isLoading, error, refetch } = useQuery({
    queryKey: ['customer-360', customerId],
    queryFn: () => fetchCustomer360(customerId!),
    enabled: !!customerId,
  })

  if (isLoading) return <PageLoader />
  if (error || !customer) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/customers')} className="btn-secondary px-2.5 py-1.5 text-xs">
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-semibold text-slate-900">{customer.full_name}</h1>
              <span className="text-xs font-mono text-slate-500">{customer.customer_code}</span>
              <Badge className={tierColor(customer.tier)}>{customer.tier}</Badge>
              <Badge className={statusColor(customer.status)}>{customer.status}</Badge>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {customer.email} · {customer.phone} · {customer.city}, {customer.state} · Agent:{' '}
              {customer.assigned_agent}
            </p>
          </div>
        </div>

        <button
          onClick={() => navigate(`/copilot?customer_id=${customer.id}`)}
          className="btn-primary text-xs"
        >
          <MessageSquare size={14} />
          <span>Investigate in AI Copilot</span>
        </button>
      </div>

      {/* Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-xs text-slate-500">Customer Lifetime Value</p>
          <p className="text-lg font-semibold text-slate-900 mt-1">{formatCurrency(customer.total_clv)}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-slate-500">Risk Segment</p>
          <p className="text-lg font-semibold text-slate-900 mt-1">{customer.risk_segment}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-slate-500">Policies</p>
          <p className="text-lg font-semibold text-slate-900 mt-1">{customer.policies.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-slate-500">Active Attention Alerts</p>
          <p className="text-lg font-semibold text-red-700 mt-1">
            {customer.attention_items.filter((a) => a.is_active).length}
          </p>
        </div>
      </div>

      {/* Watchdog Attention Items */}
      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2">
          <AlertTriangle size={15} className="text-amber-600" />
          <h2 className="text-sm font-semibold text-slate-900">Watchdog Attention Items</h2>
        </div>
        {customer.attention_items.length === 0 ? (
          <p className="p-5 text-sm text-slate-500">No attention alerts for this customer.</p>
        ) : (
          <div className="divide-y divide-slate-200">
            {customer.attention_items.map((att) => (
              <div
                key={att.id}
                onClick={() => navigate(`/attention/${att.id}`)}
                className="p-4 hover:bg-slate-50 cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <Badge className={urgencyColor(att.urgency_level)}>{att.urgency_level}</Badge>
                    <Badge className={statusColor(att.status)}>{att.status}</Badge>
                    <span className="text-xs text-slate-500">{categoryLabel(att.category)}</span>
                    <span className="text-xs font-semibold text-slate-800">
                      Score: {att.attention_score.toFixed(1)}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-900 mt-1">{att.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{att.ai_recommendation}</p>
                </div>
                <span className="text-xs text-blue-700 font-medium whitespace-nowrap">View Case →</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Policies & Schedules */}
      <div className="card overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2">
          <FileText size={15} className="text-blue-700" />
          <h2 className="text-sm font-semibold text-slate-900">Policies & Premium Schedules</h2>
        </div>
        <div className="divide-y divide-slate-200">
          {customer.policies.map((p) => (
            <div key={p.id} className="p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-mono text-sm font-semibold text-slate-900">{p.policy_number}</span>
                  <span className="text-sm text-slate-600 ml-2">
                    {p.plan_name} ({p.policy_type})
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-600">
                    Premium: <strong>{formatCurrency(p.premium_amount)}</strong>
                  </span>
                  <span className="text-slate-600">Expires: {formatDate(p.expiry_date)}</span>
                  <Badge className={statusColor(p.status)}>{p.status}</Badge>
                </div>
              </div>

              {p.schedules.length > 0 && (
                <div className="bg-slate-50 border border-slate-200 rounded-md overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 text-left">
                        <th className="px-3 py-2">Installment</th>
                        <th className="px-3 py-2">Amount</th>
                        <th className="px-3 py-2">Due Date</th>
                        <th className="px-3 py-2">Grace End</th>
                        <th className="px-3 py-2">Method</th>
                        <th className="px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.schedules.map((s) => (
                        <tr key={s.id} className="border-b border-slate-200 last:border-0">
                          <td className="px-3 py-2">#{s.installment_number}</td>
                          <td className="px-3 py-2 font-medium">{formatCurrency(s.amount_due)}</td>
                          <td className="px-3 py-2">{formatDate(s.due_date)}</td>
                          <td className="px-3 py-2">{formatDate(s.grace_period_end)}</td>
                          <td className="px-3 py-2">{s.payment_method}</td>
                          <td className="px-3 py-2">
                            <Badge className={statusColor(s.status)}>{s.status}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Document Vault & Claims */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2">
            <FileCheck size={15} className="text-slate-600" />
            <h2 className="text-sm font-semibold text-slate-900">Compliance Document Vault</h2>
          </div>
          {customer.documents.length === 0 ? (
            <p className="p-5 text-sm text-slate-500">No documents on file.</p>
          ) : (
            <div className="divide-y divide-slate-200">
              {customer.documents.map((d) => (
                <div key={d.id} className="p-4 flex items-center justify-between gap-2 text-xs">
                  <div>
                    <p className="font-medium text-slate-900">{d.document_name}</p>
                    <p className="text-slate-500">
                      {d.document_type} {d.is_mandatory ? '· Mandatory' : '· Optional'}
                    </p>
                    {d.rejection_reason && <p className="text-red-600 mt-0.5">{d.rejection_reason}</p>}
                  </div>
                  <Badge className={statusColor(d.status)}>{d.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2">
            <ShieldAlert size={15} className="text-slate-600" />
            <h2 className="text-sm font-semibold text-slate-900">Claims & Audit Trail</h2>
          </div>
          <div className="p-4 space-y-4">
            {customer.claims.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold text-slate-500 uppercase">Claims</p>
                {customer.claims.map((cl) => (
                  <div key={cl.id} className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs flex justify-between">
                    <div>
                      <span className="font-mono font-medium text-slate-900">{cl.claim_number}</span>
                      <p className="text-slate-600 mt-0.5">{cl.description}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-slate-900">{formatCurrency(cl.claim_amount)}</p>
                      <Badge className={statusColor(cl.status)}>{cl.status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-500 uppercase">Recent Activity</p>
              {customer.audit_logs.length === 0 ? (
                <p className="text-xs text-slate-500">No activity recorded.</p>
              ) : (
                customer.audit_logs.slice(0, 6).map((log) => (
                  <div key={log.id} className="text-xs border-b border-slate-100 pb-2 last:border-0">
                    <div className="flex justify-between">
                      <span className="font-medium text-slate-800">{log.action_type}</span>
                      <span className="text-slate-400">{formatDateTime(log.created_at)}</span>
                    </div>
                    <p className="text-slate-600 mt-0.5">{log.description}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
