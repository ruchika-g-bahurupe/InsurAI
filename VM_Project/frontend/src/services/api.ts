import axios from 'axios'
import type {
  HealthResponse,
  DashboardMetrics,
  CustomerSummary,
  Customer360,
  AttentionItem,
  AttentionItemDetail,
  AttentionOverviewMetrics,
  Policy,
  PolicyExpirySummaryResponse,
  RenewalFollowUpSummary,
  PremiumIssuesSummaryResponse,
  MissingDocumentsSummaryResponse,
  AnalysisRun,
  ChatResponse,
  ConversationSummary,
  ConversationDetail,
  ToolCatalogResponse,
} from '../types'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// System Health
export const fetchHealth = async (): Promise<HealthResponse> => {
  const { data } = await api.get('/health')
  return data
}

// Dashboard
export const fetchDashboardMetrics = async (): Promise<DashboardMetrics> => {
  const { data } = await api.get('/dashboard/metrics')
  return data
}

// Customers
export const fetchCustomers = async (params: {
  search?: string
  tier?: string
  risk_segment?: string
  status?: string
  skip?: number
  limit?: number
}): Promise<CustomerSummary[]> => {
  const { data } = await api.get('/customers', { params })
  return data
}

export const fetchCustomer360 = async (customerId: string): Promise<Customer360> => {
  const { data } = await api.get(`/customers/${customerId}`)
  return data
}

// Attention
export const fetchAttentionItems = async (params: {
  category?: string
  urgency_level?: string
  status?: string
  customer_id?: string
  sort_by?: string
  order?: string
  skip?: number
  limit?: number
}): Promise<AttentionItem[]> => {
  const { data } = await api.get('/attention', { params })
  return data
}

export const fetchAttentionOverview = async (): Promise<AttentionOverviewMetrics> => {
  const { data } = await api.get('/attention/overview')
  return data
}

export const fetchAttentionDetail = async (attentionId: string): Promise<AttentionItemDetail> => {
  const { data } = await api.get(`/attention/${attentionId}`)
  return data
}

export const updateAttentionStatus = async (
  attentionId: string,
  payload: { status: string; assigned_to?: string; resolved_by?: string; resolution_notes?: string }
): Promise<AttentionItem> => {
  const { data } = await api.patch(`/attention/${attentionId}/status`, payload)
  return data
}

// Policies & Renewals
export const fetchPolicies = async (params: {
  policy_type?: string
  status?: string
  customer_id?: string
  skip?: number
  limit?: number
}): Promise<Policy[]> => {
  const { data } = await api.get('/policies', { params })
  return data
}

export const fetchExpiringPolicies = async (params: {
  within_days?: number
  policy_type?: string
  skip?: number
  limit?: number
}): Promise<PolicyExpirySummaryResponse> => {
  const { data } = await api.get('/policies/expiring', { params })
  return data
}

export const fetchRenewalFollowUps = async (params: {
  within_days?: number
  only_unactioned?: boolean
  skip?: number
  limit?: number
}): Promise<RenewalFollowUpSummary> => {
  const { data } = await api.get('/renewals/follow-ups', { params })
  return data
}

// Billing
export const fetchPremiumIssues = async (params: {
  issue_type?: string
  customer_id?: string
  skip?: number
  limit?: number
}): Promise<PremiumIssuesSummaryResponse> => {
  const { data } = await api.get('/billing/issues', { params })
  return data
}

// Documents
export const fetchMissingDocuments = async (params: {
  status?: string
  document_type?: string
  customer_id?: string
  skip?: number
  limit?: number
}): Promise<MissingDocumentsSummaryResponse> => {
  const { data } = await api.get('/documents/missing', { params })
  return data
}

// Analysis
export const triggerWatchdogSweep = async (payload?: {
  run_type?: string
  trigger_source?: string
}): Promise<Record<string, unknown>> => {
  const { data } = await api.post(
    '/analysis/trigger',
    payload || {
      run_type: 'PROACTIVE_SWEEP',
      trigger_source: 'DASHBOARD_MANUAL',
    }
  )
  return data
}

export const fetchAnalysisRuns = async (params?: {
  status?: string
  run_type?: string
  limit?: number
}): Promise<AnalysisRun[]> => {
  const { data } = await api.get('/analysis/runs', { params })
  return data
}

export const fetchLatestAnalysisRun = async (): Promise<AnalysisRun> => {
  const { data } = await api.get('/analysis/runs/latest')
  return data
}

// Copilot
export const sendCopilotMessage = async (payload: {
  message: string
  conversation_id?: string
  customer_id?: string
}): Promise<ChatResponse> => {
  const { data } = await api.post('/copilot/chat', payload)
  return data
}

export const fetchConversations = async (): Promise<ConversationSummary[]> => {
  const { data } = await api.get('/copilot/conversations')
  return data
}

export const fetchConversation = async (conversationId: string): Promise<ConversationDetail> => {
  const { data } = await api.get(`/copilot/conversations/${conversationId}`)
  return data
}

export const fetchCopilotTools = async (): Promise<ToolCatalogResponse> => {
  const { data } = await api.get('/copilot/tools')
  return data
}

export const prepareOutreachDraft = async (
  attentionId: string,
  payload: { channel: 'EMAIL' | 'SMS'; approved_by: string }
): Promise<{
  channel: string
  customer_name: string
  customer_email: string
  customer_phone: string
  subject: string
  body: string
  is_draft: boolean
  requires_employee_approval: boolean
}> => {
  const { data } = await api.post(`/attention/${attentionId}/draft-outreach`, payload)
  return data
}
