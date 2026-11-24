import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  fetchPolicies,
  fetchExpiringPolicies,
  fetchRenewalFollowUps,
} from '../services/api'
import { Badge } from '../components/ui/Badge'
import { StatCard } from '../components/ui/StatCard'
import { PageLoader } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import { formatCurrency, formatDate, statusColor, tierColor, urgencyColor } from '../lib/utils'

type Tab = 'all' | 'expiring' | 'renewals'

export default function PoliciesPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('expiring')

  // All Policies filters
  const [policyType, setPolicyType] = useState('')
  const [policyStatus, setPolicyStatus] = useState('')

  // Expiring filter
  const [withinDays, setWithinDays] = useState(30)

  // Renewals filter
  const [onlyUnactioned, setOnlyUnactioned] = useState(false)

  const allQuery = useQuery({
    queryKey: ['policies', policyType, policyStatus],
    queryFn: () =>
      fetchPolicies({
        policy_type: policyType || undefined,
        status: policyStatus || undefined,
        limit: 100,
      }),
    enabled: activeTab === 'all',
  })

  const expiringQuery = useQuery({
    queryKey: ['expiring-policies', withinDays, policyType],
    queryFn: () =>
      fetchExpiringPolicies({
        within_days: withinDays,
        policy_type: policyType || undefined,
        limit: 100,
      }),
    enabled: activeTab === 'expiring',
  })

  const renewalsQuery = useQuery({
    queryKey: ['renewal-followups', onlyUnactioned],
    queryFn: () =>
      fetchRenewalFollowUps({
        within_days: 60,
        only_unactioned: onlyUnactioned,
        limit: 100,
      }),
    enabled: activeTab === 'renewals',
  })

  return (
    <div className="space-y-5">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-xl font-semibold text-slate-900">Policies & Renewal Pipeline</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Track active coverage inventory, upcoming expirations, and prioritized renewal follow-ups.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200">
        {(
          [
            { key: 'expiring', label: 'Expiring Soon' },
            { key: 'renewals', label: 'Renewal Pipeline (60d)' },
            { key: 'all', label: 'All Policies' },
          ] as { key: Tab; label: string }[]
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Expiring Soon */}
      {activeTab === 'expiring' && (
        <div className="space-y-4">
          {expiringQuery.data && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatCard label={`Expiring in ${withinDays} Days`} value={expiringQuery.data.total_expiring} accent="blue" />
              <StatCard
                label="Premium at Stake"
                value={formatCurrency(expiringQuery.data.total_premium_at_stake)}
                accent="amber"
              />
              <StatCard label="Window" value={`${expiringQuery.data.filter_window_days} Days`} />
            </div>
          )}

          <div className="card p-3.5 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              {[7, 15, 30, 60].map((d) => (
                <button
                  key={d}
                  onClick={() => setWithinDays(d)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium border ${
                    withinDays === d
                      ? 'bg-blue-700 text-white border-blue-700'
                      : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  {d} Days
                </button>
              ))}
            </div>
            <select
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
              className="input text-xs"
            >
              <option value="">All Policy Types</option>
              <option value="HEALTH">Health</option>
              <option value="MOTOR">Motor</option>
              <option value="LIFE">Life</option>
              <option value="PROPERTY">Property</option>
              <option value="COMMERCIAL">Commercial</option>
            </select>
          </div>

          {expiringQuery.isLoading ? (
            <PageLoader />
          ) : expiringQuery.error ? (
            <ErrorState onRetry={() => expiringQuery.refetch()} />
          ) : (
            <div className="card overflow-hidden">
              {expiringQuery.data?.items.length === 0 ? (
                <EmptyState title="No expiring policies in this window" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="table-header">
                        <th className="px-4 py-2.5">Policy</th>
                        <th className="px-4 py-2.5">Customer</th>
                        <th className="px-4 py-2.5">Type</th>
                        <th className="px-4 py-2.5">Premium</th>
                        <th className="px-4 py-2.5">Expiry Date</th>
                        <th className="px-4 py-2.5">Days Left</th>
                        <th className="px-4 py-2.5">Renewal Prob.</th>
                        <th className="px-4 py-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {expiringQuery.data?.items.map((p) => (
                        <tr
                          key={p.policy_id}
                          onClick={() => navigate(`/customers/${p.customer_id}`)}
                          className="table-row cursor-pointer"
                        >
                          <td className="px-4 py-3">
                            <div className="font-mono text-xs font-medium text-slate-900">{p.policy_number}</div>
                            <div className="text-xs text-slate-500">{p.plan_name}</div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-blue-700">{p.customer_name}</div>
                            <div className="text-xs text-slate-500">{p.customer_code}</div>
                          </td>
                          <td className="px-4 py-3 text-xs">{p.policy_type}</td>
                          <td className="px-4 py-3 font-medium">{formatCurrency(p.premium_amount)}</td>
                          <td className="px-4 py-3 text-xs">{formatDate(p.expiry_date)}</td>
                          <td className="px-4 py-3">
                            <span
                              className={`text-xs font-semibold ${
                                p.days_remaining <= 7 ? 'text-red-700' : 'text-amber-700'
                              }`}
                            >
                              {p.days_remaining}d
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs">{Math.round(p.renewal_probability * 100)}%</td>
                          <td className="px-4 py-3">
                            <Badge className={statusColor(p.status)}>{p.status}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Renewal Pipeline */}
      {activeTab === 'renewals' && (
        <div className="space-y-4">
          {renewalsQuery.data && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="In 60-Day Pipeline" value={renewalsQuery.data.total_in_window} />
              <StatCard label="Critical Follow-ups" value={renewalsQuery.data.critical_followups} accent="red" />
              <StatCard label="Already Actioned" value={renewalsQuery.data.already_actioned_count} accent="green" />
              <StatCard
                label="Pipeline Premium"
                value={formatCurrency(renewalsQuery.data.total_premium_in_pipeline)}
                accent="blue"
              />
            </div>
          )}

          <div className="card p-3.5 flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyUnactioned}
                onChange={(e) => setOnlyUnactioned(e.target.checked)}
                className="rounded border-slate-300 text-blue-700 focus:ring-blue-600"
              />
              <span>Show only unactioned renewals (no active Watchdog alert)</span>
            </label>
          </div>

          {renewalsQuery.isLoading ? (
            <PageLoader />
          ) : renewalsQuery.error ? (
            <ErrorState onRetry={() => renewalsQuery.refetch()} />
          ) : (
            <div className="card overflow-hidden">
              {renewalsQuery.data?.items.length === 0 ? (
                <EmptyState title="No renewal follow-ups match the filter" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="table-header">
                        <th className="px-4 py-2.5">Customer</th>
                        <th className="px-4 py-2.5">Policy</th>
                        <th className="px-4 py-2.5">Priority</th>
                        <th className="px-4 py-2.5">Days Left</th>
                        <th className="px-4 py-2.5">Premium</th>
                        <th className="px-4 py-2.5">Alert Status</th>
                        <th className="px-4 py-2.5">Recommended Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {renewalsQuery.data?.items.map((r) => (
                        <tr
                          key={r.policy_id}
                          onClick={() => navigate(`/customers/${r.customer_id}`)}
                          className="table-row cursor-pointer"
                        >
                          <td className="px-4 py-3">
                            <div className="font-medium text-blue-700">{r.customer_name}</div>
                            <div className="text-xs text-slate-500">
                              {r.customer_code} · <Badge className={tierColor(r.customer_tier)}>{r.customer_tier}</Badge>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-mono text-xs text-slate-900">{r.policy_number}</div>
                            <div className="text-xs text-slate-500">{r.plan_name}</div>
                          </td>
                          <td className="px-4 py-3">
                            <Badge className={urgencyColor(r.follow_up_priority)}>{r.follow_up_priority}</Badge>
                          </td>
                          <td className="px-4 py-3 text-xs font-semibold">{r.days_to_expiry}d</td>
                          <td className="px-4 py-3 font-medium">{formatCurrency(r.premium_amount)}</td>
                          <td className="px-4 py-3 text-xs">
                            {r.has_active_attention_item ? (
                              <Badge className="text-blue-700 bg-blue-50 border-blue-200">Active Alert</Badge>
                            ) : (
                              <span className="text-slate-400">Unactioned</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-xs text-slate-600 max-w-xs truncate">
                            {r.recommended_action}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: All Policies */}
      {activeTab === 'all' && (
        <div className="space-y-4">
          <div className="card p-3.5 flex flex-wrap gap-3">
            <select
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
              className="input text-xs"
            >
              <option value="">All Policy Types</option>
              <option value="HEALTH">Health</option>
              <option value="MOTOR">Motor</option>
              <option value="LIFE">Life</option>
              <option value="PROPERTY">Property</option>
              <option value="COMMERCIAL">Commercial</option>
            </select>
            <select
              value={policyStatus}
              onChange={(e) => setPolicyStatus(e.target.value)}
              className="input text-xs"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="RENEWAL_PENDING">Renewal Pending</option>
              <option value="GRACE_PERIOD">Grace Period</option>
              <option value="LAPSED">Lapsed</option>
            </select>
          </div>

          {allQuery.isLoading ? (
            <PageLoader />
          ) : allQuery.error ? (
            <ErrorState onRetry={() => allQuery.refetch()} />
          ) : (
            <div className="card overflow-hidden">
              {!allQuery.data || allQuery.data.length === 0 ? (
                <EmptyState title="No policies match your filters" />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="table-header">
                        <th className="px-4 py-2.5">Policy Number</th>
                        <th className="px-4 py-2.5">Plan</th>
                        <th className="px-4 py-2.5">Type</th>
                        <th className="px-4 py-2.5">Sum Insured</th>
                        <th className="px-4 py-2.5">Premium</th>
                        <th className="px-4 py-2.5">Expiry Date</th>
                        <th className="px-4 py-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {allQuery.data.map((p) => (
                        <tr
                          key={p.id}
                          onClick={() => navigate(`/customers/${p.customer_id}`)}
                          className="table-row cursor-pointer"
                        >
                          <td className="px-4 py-3 font-mono text-xs font-medium text-blue-700">
                            {p.policy_number}
                          </td>
                          <td className="px-4 py-3 text-slate-900">{p.plan_name}</td>
                          <td className="px-4 py-3 text-xs text-slate-600">{p.policy_type}</td>
                          <td className="px-4 py-3">{formatCurrency(p.sum_insured)}</td>
                          <td className="px-4 py-3 font-medium">{formatCurrency(p.premium_amount)}</td>
                          <td className="px-4 py-3 text-xs">{formatDate(p.expiry_date)}</td>
                          <td className="px-4 py-3">
                            <Badge className={statusColor(p.status)}>{p.status}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
