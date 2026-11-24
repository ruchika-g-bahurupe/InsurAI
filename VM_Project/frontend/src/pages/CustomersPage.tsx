import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronRight } from 'lucide-react'
import { fetchCustomers } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { PageLoader } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import { formatCurrency, statusColor, tierColor } from '../lib/utils'

export default function CustomersPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [tier, setTier] = useState('')
  const [riskSegment, setRiskSegment] = useState('')

  const { data: customers, isLoading, error, refetch } = useQuery({
    queryKey: ['customers', search, tier, riskSegment],
    queryFn: () =>
      fetchCustomers({
        search: search.trim() || undefined,
        tier: tier || undefined,
        risk_segment: riskSegment || undefined,
        status: 'ACTIVE',
        limit: 100,
      }),
  })

  if (isLoading) return <PageLoader />
  if (error) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-5">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-xl font-semibold text-slate-900">Customer Directory</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Search policyholders and open complete 360° intelligence profiles.
        </p>
      </div>

      {/* Filters */}
      <div className="card p-3.5 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, code (CUST-1005), email, or city..."
            className="input w-full pl-9"
          />
        </div>

        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="input text-xs"
          aria-label="Filter by tier"
        >
          <option value="">All Tiers</option>
          <option value="HIGH_NET_WORTH">High Net Worth</option>
          <option value="VIP">VIP</option>
          <option value="STANDARD">Standard</option>
        </select>

        <select
          value={riskSegment}
          onChange={(e) => setRiskSegment(e.target.value)}
          className="input text-xs"
          aria-label="Filter by risk segment"
        >
          <option value="">All Risk Segments</option>
          <option value="HIGH">High Risk</option>
          <option value="MEDIUM">Medium Risk</option>
          <option value="LOW">Low Risk</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {!customers || customers.length === 0 ? (
          <EmptyState
            title="No matching customers"
            description="Try clearing your search query or adjusting the tier/risk filters."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5">Contact</th>
                  <th className="px-4 py-2.5">Tier</th>
                  <th className="px-4 py-2.5">Risk Segment</th>
                  <th className="px-4 py-2.5">Lifetime Value</th>
                  <th className="px-4 py-2.5">Active Policies</th>
                  <th className="px-4 py-2.5">Open Alerts</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/customers/${c.id}`)}
                    className="table-row cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{c.full_name}</div>
                      <div className="text-xs font-mono text-slate-500">{c.customer_code}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      <div>{c.email}</div>
                      <div className="text-slate-400">{c.phone}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={tierColor(c.tier)}>{c.tier}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-slate-700">{c.risk_segment}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{formatCurrency(c.total_clv)}</td>
                    <td className="px-4 py-3 text-slate-700">{c.active_policies_count}</td>
                    <td className="px-4 py-3">
                      {c.open_attention_count > 0 ? (
                        <Badge className="text-red-700 bg-red-50 border-red-200">
                          {c.open_attention_count} active
                        </Badge>
                      ) : (
                        <span className="text-xs text-slate-400">None</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={statusColor(c.status)}>{c.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ChevronRight size={15} className="text-slate-400 inline" />
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
