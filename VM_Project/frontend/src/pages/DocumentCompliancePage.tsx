import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchMissingDocuments } from '../services/api'
import { Badge } from '../components/ui/Badge'
import { StatCard } from '../components/ui/StatCard'
import { PageLoader } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import { statusColor, tierColor } from '../lib/utils'

export default function DocumentCompliancePage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('')
  const [docType, setDocType] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['missing-documents', statusFilter, docType],
    queryFn: () =>
      fetchMissingDocuments({
        status: statusFilter || undefined,
        document_type: docType || undefined,
        limit: 100,
      }),
  })

  if (isLoading) return <PageLoader />
  if (error || !data) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="space-y-5">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-xl font-semibold text-slate-900">Document Compliance</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Mandatory underwriting and KYC document deficits across active policies.
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard label="Total Deficits" value={data.total_deficits} accent="amber" />
        <StatCard label="Pending Submission" value={data.pending_count} accent="blue" />
        <StatCard label="Rejected" value={data.rejected_count} accent="red" />
        <StatCard label="Expired" value={data.expired_count} accent="red" />
        <StatCard label="Affected Customers" value={data.affected_customers_count} />
      </div>

      {/* Filters */}
      <div className="card p-3.5 flex flex-wrap items-center gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input text-xs"
        >
          <option value="">All Deficit Statuses</option>
          <option value="PENDING_SUBMISSION">Pending Submission</option>
          <option value="REJECTED">Rejected</option>
          <option value="EXPIRED">Expired</option>
        </select>

        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="input text-xs"
        >
          <option value="">All Document Types</option>
          <option value="KYC_ID">KYC ID</option>
          <option value="MEDICAL_DECLARATION">Medical Declaration</option>
          <option value="VEHICLE_INSPECTION">Vehicle Inspection</option>
          <option value="PROOF_OF_ADDRESS">Proof of Address</option>
          <option value="INCOME_PROOF">Income Proof</option>
          <option value="PROPERTY_SURVEY">Property Survey</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {data.items.length === 0 ? (
          <EmptyState title="No compliance deficits found" description="All mandatory documents are verified." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5">Customer</th>
                  <th className="px-4 py-2.5">Policy</th>
                  <th className="px-4 py-2.5">Document Type</th>
                  <th className="px-4 py-2.5">Document Name</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Rejection / Notes</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((d) => (
                  <tr
                    key={d.document_id}
                    onClick={() => navigate(`/customers/${d.customer_id}`)}
                    className="table-row cursor-pointer"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-blue-700">{d.customer_name}</div>
                      <div className="text-xs text-slate-500">
                        {d.customer_code} · <Badge className={tierColor(d.customer_tier)}>{d.customer_tier}</Badge>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-mono text-xs text-slate-900">{d.policy_number}</div>
                      <div className="text-xs text-slate-500">{d.policy_type}</div>
                    </td>
                    <td className="px-4 py-3 text-xs font-medium text-slate-800">{d.document_type}</td>
                    <td className="px-4 py-3 text-xs text-slate-700">{d.document_name}</td>
                    <td className="px-4 py-3">
                      <Badge className={statusColor(d.status)}>{d.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 max-w-xs truncate">
                      {d.rejection_reason || 'Awaiting policyholder upload'}
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
