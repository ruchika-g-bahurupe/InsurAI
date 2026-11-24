// TypeScript interfaces strictly aligned with Backend Pydantic v2 Schemas

export interface HealthResponse {
  status: string
  app_name: string
  environment: string
  database: {
    status: string
    engine: string
    error?: string | null
  }
  gemini_live: boolean
  ai_mode: 'LIVE_GEMINI' | 'COGNITIVE_EMULATION'
  gemini_model_configured: string
  analysis_model_configured: string
}

// Dashboard
export interface ExpirationsByWindow {
  in_7_days: number
  in_15_days: number
  in_30_days: number
  in_60_days: number
}

export interface DashboardMetrics {
  total_customers: number
  total_active_policies: number
  customers_requiring_attention: number
  high_priority_cases: number
  upcoming_policy_expirations: ExpirationsByWindow
  missing_documents_count: number
  premium_issues_count: number
  total_premium_at_risk: number
  attention_by_category: Record<string, number>
  attention_by_urgency: Record<string, number>
  attention_by_status: Record<string, number>
  vip_customers_count: number
  high_risk_customers_count: number
  timestamp: string
}

// Customers
export interface CustomerSummary {
  id: string
  customer_code: string
  full_name: string
  email: string
  phone: string
  tier: 'STANDARD' | 'VIP' | 'HIGH_NET_WORTH' | string
  risk_segment: 'LOW' | 'MEDIUM' | 'HIGH' | string
  total_clv: number
  status: 'ACTIVE' | 'INACTIVE' | 'DORMANT' | string
  active_policies_count: number
  open_attention_count: number
}

export interface Customer360PolicySchedule {
  id: string
  installment_number: number
  amount_due: number
  due_date: string
  grace_period_end: string
  status: string
  payment_method: string
  paid_at?: string | null
  retry_attempts: number
  failure_reason?: string | null
}

export interface Customer360Policy {
  id: string
  policy_number: string
  policy_type: string
  plan_name: string
  sum_insured: number
  premium_amount: number
  payment_frequency: string
  start_date: string
  expiry_date: string
  status: string
  auto_renew: boolean
  renewal_probability: number
  schedules: Customer360PolicySchedule[]
}

export interface Customer360Document {
  id: string
  policy_id: string
  document_type: string
  document_name: string
  status: string
  is_mandatory: boolean
  rejection_reason?: string | null
  expiry_date?: string | null
  submitted_at?: string | null
  verified_at?: string | null
}

export interface Customer360Claim {
  id: string
  policy_id: string
  claim_number: string
  claim_amount: number
  payout_amount?: number | null
  status: string
  incident_date: string
  description: string
  adjuster_notes?: string | null
}

export interface Customer360 {
  id: string
  customer_code: string
  first_name: string
  last_name: string
  full_name: string
  email: string
  phone: string
  date_of_birth?: string | null
  tier: string
  risk_segment: string
  total_clv: number
  assigned_agent: string
  city: string
  state: string
  status: string
  created_at: string
  policies: Customer360Policy[]
  documents: Customer360Document[]
  claims: Customer360Claim[]
  attention_items: AttentionItem[]
  audit_logs: AuditEntry[]
}

// Attention
export type UrgencyLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
export type AttentionCategory =
  | 'POLICY_EXPIRY'
  | 'MISSING_DOCS'
  | 'PREMIUM_OVERDUE'
  | 'RENEWAL_FOLLOWUP'
  | 'RISK_ALERT'
export type AttentionStatus = 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'DISMISSED'

export interface AttentionItem {
  id: string
  customer_id: string
  policy_id?: string | null
  category: AttentionCategory | string
  urgency_level: UrgencyLevel | string
  attention_score: number
  confidence_level?: string | null
  dedup_key: string
  is_active: boolean
  title: string
  reasoning_summary?: string | null
  root_cause: string
  ai_summary: string
  ai_recommendation: string
  identified_risk_factors?: string[] | null
  investigation_steps?: string[] | null
  supporting_evidence?: string[] | null
  data_gaps?: string[] | null
  suggested_action?: Record<string, unknown> | null
  status: AttentionStatus | string
  assigned_to?: string | null
  detected_at: string
  resolved_at?: string | null
  resolved_by?: string | null
  resolution_notes?: string | null
  customer_name?: string | null
  customer_code?: string | null
  customer_tier?: string | null
  customer_email?: string | null
  customer_phone?: string | null
  policy_number?: string | null
  policy_type?: string | null
}

export interface AttentionAuditEntry {
  id: string
  action_type: string
  actor: string
  actor_name: string
  description: string
  created_at: string
}

export interface AttentionItemDetail extends AttentionItem {
  customer_details?: {
    id: string
    customer_code: string
    full_name: string
    email: string
    phone: string
    tier: string
    risk_segment: string
    total_clv: number
    assigned_agent: string
    city: string
    state: string
    status: string
  } | null
  policy_details?: {
    id: string
    policy_number: string
    policy_type: string
    plan_name: string
    sum_insured: number
    premium_amount: number
    start_date: string
    expiry_date: string
    status: string
    auto_renew: boolean
    renewal_probability: number
  } | null
  audit_history: AttentionAuditEntry[]
}

export interface AttentionOverviewMetrics {
  total_active_alerts: number
  critical_alerts: number
  high_alerts: number
  medium_alerts: number
  low_alerts: number
  policy_expiry_count: number
  missing_docs_count: number
  premium_issues_count: number
  renewal_followup_count: number
  risk_alert_count: number
  total_premium_at_risk: number
}

// Policies
export interface Policy {
  id: string
  customer_id: string
  policy_number: string
  policy_type: string
  plan_name: string
  sum_insured: number
  premium_amount: number
  payment_frequency: string
  start_date: string
  expiry_date: string
  status: string
  auto_renew: boolean
  renewal_probability: number
  created_at: string
  updated_at: string
}

export interface PolicyExpiryItem {
  policy_id: string
  policy_number: string
  policy_type: string
  plan_name: string
  premium_amount: number
  sum_insured: number
  start_date: string
  expiry_date: string
  days_remaining: number
  status: string
  auto_renew: boolean
  renewal_probability: number
  customer_id: string
  customer_name: string
  customer_code: string
  customer_email: string
  customer_phone: string
  customer_tier: string
  assigned_agent: string
}

export interface PolicyExpirySummaryResponse {
  filter_window_days: number
  total_expiring: number
  total_premium_at_stake: number
  items: PolicyExpiryItem[]
}

// Renewals
export interface RenewalFollowUpItem {
  policy_id: string
  policy_number: string
  policy_type: string
  plan_name: string
  premium_amount: number
  expiry_date: string
  days_to_expiry: number
  renewal_probability: number
  auto_renew: boolean
  policy_status: string
  customer_id: string
  customer_name: string
  customer_code: string
  customer_tier: string
  customer_clv: number
  assigned_agent: string
  has_active_attention_item: boolean
  attention_item_id?: string | null
  follow_up_priority: string
  recommended_action: string
}

export interface RenewalFollowUpSummary {
  total_in_window: number
  critical_followups: number
  high_followups: number
  medium_followups: number
  already_actioned_count: number
  total_premium_in_pipeline: number
  items: RenewalFollowUpItem[]
}

// Billing
export interface PremiumIssueItem {
  schedule_id: string
  installment_number: number
  amount_due: number
  due_date: string
  grace_period_end: string
  status: string
  payment_method: string
  retry_attempts: number
  failure_reason?: string | null
  issue_type: 'GRACE_PERIOD' | 'OVERDUE' | 'FAILED_DEBIT' | 'UPCOMING_DUE' | string
  days_overdue: number
  days_grace_remaining: number
  policy_id: string
  policy_number: string
  policy_type: string
  plan_name: string
  policy_status: string
  customer_id: string
  customer_name: string
  customer_code: string
  customer_email: string
  customer_phone: string
  customer_tier: string
  assigned_agent: string
}

export interface PremiumIssuesSummaryResponse {
  total_issues: number
  in_grace_period_count: number
  overdue_count: number
  failed_auto_debit_count: number
  total_amount_at_risk: number
  items: PremiumIssueItem[]
}

// Documents
export interface MissingDocumentItem {
  document_id: string
  document_type: string
  document_name: string
  status: string
  is_mandatory: boolean
  rejection_reason?: string | null
  expiry_date?: string | null
  submitted_at?: string | null
  policy_id: string
  policy_number: string
  policy_type: string
  plan_name: string
  policy_status: string
  customer_id: string
  customer_name: string
  customer_code: string
  customer_email: string
  customer_phone: string
  customer_tier: string
  assigned_agent: string
}

export interface MissingDocumentsSummaryResponse {
  total_deficits: number
  pending_count: number
  rejected_count: number
  expired_count: number
  affected_customers_count: number
  items: MissingDocumentItem[]
}

// Audit
export interface AuditEntry {
  id: string
  action_type: string
  actor: string
  actor_name: string
  description: string
  created_at: string
}

// Analysis Run
export interface AnalysisRun {
  id: string
  run_type: string
  trigger_source: string
  status: string
  records_scanned: number
  issues_detected: number
  new_recommendations_created: number
  recommendations_updated: number
  iterations_used?: number
  tool_calls_count?: number
  tool_calls_log?: Record<string, unknown>[] | null
  degraded_mode?: boolean
  execution_time_ms: number
  model_used: string
  summary_notes?: string | null
  error_message?: string | null
  started_at: string
  completed_at?: string | null
}

// Copilot
export interface ToolCall {
  name: string
  args: Record<string, unknown>
}

export interface ToolResult {
  name: string
  result: Record<string, unknown>
}

export interface ChatMessage {
  id?: string
  sender: 'USER' | 'ASSISTANT' | string
  content: string
  tool_calls?: ToolCall[] | null
  tool_results?: ToolResult[] | null
  created_at?: string
  timestamp?: string
}

export interface ChatResponse {
  conversation_id: string
  message_id: string
  title: string
  reply: string
  tool_calls: ToolCall[]
  tool_results: ToolResult[]
  mode: 'LIVE_GEMINI' | 'COGNITIVE_CORE' | 'IDLE'
  customer_id?: string | null
  timestamp: string
}

export interface ConversationSummary {
  id: string
  title: string
  customer_id?: string | null
  message_count: number
  updated_at: string
}

export interface ConversationDetail {
  id: string
  customer_id?: string | null
  title: string
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}

export interface ToolMetadata {
  name: string
  signature: string
  description: string
}

export interface ToolCatalogResponse {
  total_tools: number
  tools: ToolMetadata[]
}


// Insurance Knowledge Base (RAG)
export type KnowledgeProcessingStatus =
  | 'UPLOADED'
  | 'EXTRACTING_TEXT'
  | 'CHUNKING'
  | 'GENERATING_EMBEDDINGS'
  | 'INDEXING'
  | 'COMPLETED'
  | 'FAILED'

export interface KnowledgeDocument {
  id: string
  document_name: string
  category: string
  policy_type?: string | null
  file_hash: string
  file_size_bytes: number
  processing_status: KnowledgeProcessingStatus | string
  page_count: number
  chunk_count: number
  error_message?: string | null
  upload_timestamp: string
  last_indexed_timestamp?: string | null
}

export interface KnowledgeDocumentExcerpt {
  chunk_id: string
  page_number: number
  chunk_index: number
  excerpt: string
}

export interface KnowledgeDocumentDetail extends KnowledgeDocument {
  excerpts: KnowledgeDocumentExcerpt[]
}

export interface KnowledgeBaseStats {
  total_documents: number
  indexed_documents: number
  processing_documents: number
  failed_documents: number
  total_chunks: number
  categories_breakdown: Record<string, number>
}

export interface DocumentUploadResponse {
  document: KnowledgeDocument
  is_duplicate: boolean
  message: string
}

export interface RetrievedPassage {
  chunk_id: string
  document_id: string
  document_name: string
  category: string
  policy_type?: string | null
  page_number: number
  relevant_excerpt: string
  similarity_score: number
}

export interface KnowledgeSearchResponse {
  query: string
  total_results: number
  passages: RetrievedPassage[]
}

export interface SourceCitation {
  document_id: string
  document_name: string
  category: string
  page_number: number
  relevant_excerpt: string
  retrieval_similarity: number
}

export interface KnowledgeAskResponse {
  question: string
  answer: string
  sources: SourceCitation[]
  insufficient_evidence: boolean
  retrieval_note?: string | null
  model_used?: string | null
}
