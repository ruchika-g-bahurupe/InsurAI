import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, MessageSquare, User, FileText, CheckCircle2, XCircle, Clock, Mail } from 'lucide-react'
import { fetchAttentionDetail, updateAttentionStatus, prepareOutreachDraft } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { PageLoader, Spinner } from '../components/ui/Spinner'
import { ErrorState } from '../components/ui/EmptyState'
import {
  categoryLabel,
  formatCurrency,
  formatDate,
  formatDateTime,
  statusColor,
  urgencyColor,
} from '../lib/utils'

export default function AttentionDetailPage() {
  const { attentionId } = useParams<{ attentionId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [assignedTo, setAssignedTo] = useState('')
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [draftChannel, setDraftChannel] = useState<'EMAIL' | 'SMS'>('EMAIL')

  const { data: item, isLoading, error, refetch } = useQuery({
    queryKey: ['attention-detail', attentionId],
    queryFn: () => fetchAttentionDetail(attentionId!),
    enabled: !!attentionId,
  })

  const statusMutation = useMutation({
    mutationFn: (payload: { status: string; assigned_to?: string; resolved_by?: string; resolution_notes?: string }) =>
      updateAttentionStatus(attentionId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attention-detail', attentionId] })
      queryClient.invalidateQueries({ queryKey: ['attention'] })
      queryClient.invalidateQueries({ queryKey: ['attention-overview'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const draftMutation = useMutation({
    mutationFn: () =>
      prepareOutreachDraft(attentionId!, {
        channel: draftChannel,
        approved_by: assignedTo || item?.assigned_to || 'Retention Desk',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attention-detail', attentionId] })
    },
  })

  if (isLoading) return <PageLoader />
  if (error || !item) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-5">
      {/* Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/attention')} className="btn-secondary px-2.5 py-1.5 text-xs">
            <ArrowLeft size={14} />
            <span>Back</span>
          </button>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className={urgencyColor(item.urgency_level)}>{item.urgency_level}</Badge>
              <Badge className={statusColor(item.status)}>{item.status}</Badge>
              {item.confidence_level && (
                <Badge className="text-slate-700 bg-slate-100 border-slate-300">
                  Confidence: {item.confidence_level}
                </Badge>
              )}
              <span className="text-xs font-medium text-slate-500">{categoryLabel(item.category)}</span>
              <span className="text-xs font-semibold text-slate-900">
                Score: {item.attention_score.toFixed(1)}
              </span>
            </div>
            <h1 className="text-lg font-semibold text-slate-900 mt-1">{item.title}</h1>
          </div>
        </div>

        <button
          onClick={() => navigate(`/copilot?customer_id=${item.customer_id}`)}
          className="btn-primary text-xs"
        >
          <MessageSquare size={14} />
          <span>Investigate in AI Copilot</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main Diagnostic Column */}
        <div className="lg:col-span-2 space-y-5">
          <div className="card p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
              Autonomous Watchdog Investigation Report
            </h2>

            {item.reasoning_summary && (
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Why Agent Selected This Customer
                </p>
                <p className="text-sm text-slate-800 mt-1 leading-relaxed">{item.reasoning_summary}</p>
              </div>
            )}

            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Root Cause</p>
              <p className="text-sm text-slate-800 mt-1">{item.root_cause}</p>
            </div>

            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Executive Summary</p>
              <p className="text-sm text-slate-700 mt-1 leading-relaxed">{item.ai_summary}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5">
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                  Discovered Risk Factors
                </p>
                {item.identified_risk_factors && item.identified_risk_factors.length > 0 ? (
                  <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                    {item.identified_risk_factors.map((f, idx) => (
                      <li key={idx}>{f}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-500">See root cause above.</p>
                )}
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5">
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                  Supporting Database Evidence
                </p>
                {item.supporting_evidence && item.supporting_evidence.length > 0 ? (
                  <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                    {item.supporting_evidence.map((ev, idx) => (
                      <li key={idx}>{ev}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-500">No itemized evidence recorded.</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5">
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1.5">
                  Investigation Steps
                </p>
                {item.investigation_steps && item.investigation_steps.length > 0 ? (
                  <ol className="list-decimal list-inside text-xs text-slate-700 space-y-1 font-mono">
                    {item.investigation_steps.map((st, idx) => (
                      <li key={idx} className="truncate">{st}</li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-xs text-slate-500">No tool trace recorded.</p>
                )}
              </div>

              <div className="bg-amber-50/60 border border-amber-200 rounded-md p-3.5">
                <p className="text-xs font-semibold text-amber-800 uppercase tracking-wider mb-1.5">
                  Missing Information / Data Gaps
                </p>
                {item.data_gaps && item.data_gaps.length > 0 ? (
                  <ul className="list-disc list-inside text-xs text-amber-900 space-y-1">
                    {item.data_gaps.map((g, idx) => (
                      <li key={idx}>{g}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-amber-800">No missing or contradictory records flagged.</p>
                )}
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-md p-3.5">
              <p className="text-xs font-semibold text-blue-800 uppercase tracking-wider">
                Recommended Employee Action
              </p>
              <p className="text-sm text-blue-950 mt-1">{item.ai_recommendation}</p>
            </div>
          </div>

          {/* Human-in-the-Loop Outreach Draft */}
          <div className="card p-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
              <h2 className="text-sm font-semibold text-slate-900">
                Prepare Outreach Draft (Requires Employee Review)
              </h2>
              <div className="flex items-center gap-2">
                <select
                  value={draftChannel}
                  onChange={(e) => setDraftChannel(e.target.value as 'EMAIL' | 'SMS')}
                  className="input text-xs py-1"
                >
                  <option value="EMAIL">Email</option>
                  <option value="SMS">SMS</option>
                </select>
                <button
                  onClick={() => draftMutation.mutate()}
                  disabled={draftMutation.isPending}
                  className="btn-secondary text-xs"
                >
                  {draftMutation.isPending ? <Spinner size={13} /> : <Mail size={13} />}
                  <span>Generate Draft</span>
                </button>
              </div>
            </div>

            {draftMutation.data && (
              <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">
                    Subject: {draftMutation.data.subject}
                  </span>
                  <Badge className="text-amber-700 bg-amber-50 border-amber-200">
                    Draft Only · Not Sent
                  </Badge>
                </div>
                <pre className="whitespace-pre-wrap font-sans text-slate-700 leading-relaxed">
                  {draftMutation.data.body}
                </pre>
              </div>
            )}
          </div>

          {/* Workflow Lifecycle Controls */}
          <div className="card p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
              Employee Review & Status Update
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Assign / Acting Employee
                </label>
                <input
                  type="text"
                  value={assignedTo}
                  onChange={(e) => setAssignedTo(e.target.value)}
                  placeholder={item.assigned_to || 'e.g. Sarah Jenkins'}
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Resolution / Action Notes
                </label>
                <input
                  type="text"
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Enter outreach or verification notes..."
                  className="input w-full"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              <button
                onClick={() =>
                  statusMutation.mutate({
                    status: 'IN_PROGRESS',
                    assigned_to: assignedTo || item.assigned_to || 'Retention Desk',
                    resolution_notes: resolutionNotes || undefined,
                  })
                }
                disabled={statusMutation.isPending}
                className="btn-secondary text-xs"
              >
                <Clock size={13} />
                <span>Mark In Progress</span>
              </button>
              <button
                onClick={() =>
                  statusMutation.mutate({
                    status: 'RESOLVED',
                    resolved_by: assignedTo || 'Retention Desk',
                    resolution_notes: resolutionNotes || 'Issue resolved by employee.',
                  })
                }
                disabled={statusMutation.isPending}
                className="btn-primary text-xs bg-emerald-700 hover:bg-emerald-800"
              >
                <CheckCircle2 size={13} />
                <span>Mark Resolved</span>
              </button>
              <button
                onClick={() =>
                  statusMutation.mutate({
                    status: 'DISMISSED',
                    resolved_by: assignedTo || 'Retention Desk',
                    resolution_notes: resolutionNotes || 'Dismissed after review.',
                  })
                }
                disabled={statusMutation.isPending}
                className="btn-secondary text-xs"
              >
                <XCircle size={13} />
                <span>Dismiss Alert</span>
              </button>
              {statusMutation.isPending && <Spinner size={16} />}
            </div>
          </div>

          {/* Audit History */}
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2 mb-3">
              Customer Activity & Audit Trail
            </h2>
            {item.audit_history.length === 0 ? (
              <p className="text-xs text-slate-500">No audit entries recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {item.audit_history.map((entry) => (
                  <div key={entry.id} className="flex items-start justify-between gap-4 text-xs border-b border-slate-100 pb-2.5 last:border-0">
                    <div>
                      <span className="font-semibold text-slate-800">{entry.action_type}</span>
                      <span className="text-slate-500"> · {entry.actor_name}</span>
                      <p className="text-slate-600 mt-0.5">{entry.description}</p>
                    </div>
                    <span className="text-slate-400 whitespace-nowrap">{formatDateTime(entry.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Side Context Cards */}
        <div className="space-y-5">
          {item.customer_details && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <User size={15} className="text-slate-500" />
                  <h2 className="text-sm font-semibold text-slate-900">Customer Context</h2>
                </div>
                <button
                  onClick={() => navigate(`/customers/${item.customer_id}`)}
                  className="text-xs text-blue-700 font-medium hover:underline"
                >
                  Open 360°
                </button>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Name</span>
                  <span className="font-medium text-slate-900">{item.customer_details.full_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Code</span>
                  <span className="font-mono text-slate-800">{item.customer_details.customer_code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Tier / Risk</span>
                  <span className="text-slate-800">
                    {item.customer_details.tier} / {item.customer_details.risk_segment}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Lifetime Value</span>
                  <span className="font-semibold text-slate-900">
                    {formatCurrency(item.customer_details.total_clv)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Email</span>
                  <span className="text-slate-800">{item.customer_details.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Phone</span>
                  <span className="text-slate-800">{item.customer_details.phone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Assigned Agent</span>
                  <span className="text-slate-800">{item.customer_details.assigned_agent}</span>
                </div>
              </div>
            </div>
          )}

          {item.policy_details && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
                <FileText size={15} className="text-slate-500" />
                <h2 className="text-sm font-semibold text-slate-900">Linked Policy</h2>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500">Policy Number</span>
                  <span className="font-mono font-medium text-slate-900">
                    {item.policy_details.policy_number}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Plan</span>
                  <span className="text-slate-800">{item.policy_details.plan_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Type / Status</span>
                  <span className="text-slate-800">
                    {item.policy_details.policy_type} · {item.policy_details.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Annual Premium</span>
                  <span className="font-semibold text-slate-900">
                    {formatCurrency(item.policy_details.premium_amount)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Sum Insured</span>
                  <span className="text-slate-800">{formatCurrency(item.policy_details.sum_insured)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Expiry Date</span>
                  <span className="text-slate-800">{formatDate(item.policy_details.expiry_date)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Renewal Prob.</span>
                  <span className="font-medium text-slate-900">
                    {Math.round(item.policy_details.renewal_probability * 100)}%
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
