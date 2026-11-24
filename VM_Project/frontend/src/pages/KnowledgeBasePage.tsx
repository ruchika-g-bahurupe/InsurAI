import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Upload,
  FileText,
  Search,
  RefreshCw,
  Trash2,
  Eye,
  AlertCircle,
  CheckCircle2,
  BookOpen,
  X,
  Send,
} from 'lucide-react'
import {
  KNOWLEDGE_CATEGORIES,
  askKnowledgeBase,
  deleteKnowledgeDocument,
  fetchKnowledgeDocumentDetail,
  fetchKnowledgeDocuments,
  fetchKnowledgeStats,
  reindexKnowledgeDocument,
  uploadKnowledgeDocument,
} from '../services/knowledgeBaseApi'
import { Badge } from '../components/ui/Badge'
import { StatCard } from '../components/ui/StatCard'
import { PageLoader, Spinner } from '../components/ui/Spinner'
import { EmptyState, ErrorState } from '../components/ui/EmptyState'
import { formatDateTime } from '../lib/utils'
import type {
  KnowledgeAskResponse,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
} from '../types'

const PROCESSING_STAGES = [
  { key: 'UPLOADED', label: 'Uploaded' },
  { key: 'EXTRACTING_TEXT', label: 'Extracting Text' },
  { key: 'CHUNKING', label: 'Chunking' },
  { key: 'GENERATING_EMBEDDINGS', label: 'Generating Embeddings' },
  { key: 'INDEXING', label: 'Indexing' },
  { key: 'COMPLETED', label: 'Completed' },
] as const

const EXAMPLE_QUESTIONS = [
  'Explain the accidental damage coverage in this motor insurance policy.',
  'What are the standard exclusions for claim payouts?',
  'What is the required claim reporting timeframe and documentation?',
]

function statusBadgeClass(status: string): string {
  if (status === 'COMPLETED') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  if (status === 'FAILED') return 'bg-red-50 text-red-700 border-red-200'
  if (status === 'UPLOADED') return 'bg-slate-100 text-slate-700 border-slate-200'
  return 'bg-blue-50 text-blue-700 border-blue-200'
}

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function StageTracker({ status }: { status: string }) {
  const activeIdx = PROCESSING_STAGES.findIndex((s) => s.key === status)
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
      {PROCESSING_STAGES.map((stage, idx) => {
        const isDone = status === 'COMPLETED' || (activeIdx >= 0 && idx < activeIdx)
        const isCurrent = status !== 'COMPLETED' && idx === activeIdx
        return (
          <div key={stage.key} className="flex items-center gap-1.5">
            <span
              className={`px-2 py-0.5 rounded border font-medium ${
                isDone
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : isCurrent
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : status === 'FAILED' && idx === 0
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-slate-50 text-slate-400 border-slate-200'
              }`}
            >
              {stage.label}
            </span>
            {idx < PROCESSING_STAGES.length - 1 && (
              <span className="text-slate-300">&rarr;</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function KnowledgeBasePage() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const qaInputRef = useRef<HTMLInputElement>(null)

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadCategory, setUploadCategory] = useState<string>(KNOWLEDGE_CATEGORIES[0])
  const [policyType, setPolicyType] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [uploadPercent, setUploadPercent] = useState<number | null>(null)
  const [uploadNotice, setUploadNotice] = useState<{
    type: 'success' | 'error' | 'info'
    text: string
    status?: string
  } | null>(null)

  // Library filters & actions
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedDocDetail, setSelectedDocDetail] = useState<KnowledgeDocumentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [confirmDeleteDoc, setConfirmDeleteDoc] = useState<KnowledgeDocument | null>(null)

  // Knowledge Assistant Q&A state
  const [question, setQuestion] = useState('')
  const [qaCategory, setQaCategory] = useState('')
  const [qaPolicyType, setQaPolicyType] = useState('')
  const [qaDocId, setQaDocId] = useState('')
  const [qaResult, setQaResult] = useState<KnowledgeAskResponse | null>(null)
  const [qaError, setQaError] = useState<string | null>(null)

  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['kb-stats'],
    queryFn: fetchKnowledgeStats,
  })

  const {
    data: documents,
    isLoading: docsLoading,
    error: docsError,
    refetch: refetchDocs,
  } = useQuery({
    queryKey: ['kb-documents', categoryFilter, statusFilter],
    queryFn: () =>
      fetchKnowledgeDocuments({
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      }),
  })

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['kb-stats'] })
    queryClient.invalidateQueries({ queryKey: ['kb-documents'] })
  }

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error('Select a PDF file first.')
      return uploadKnowledgeDocument(selectedFile, uploadCategory, policyType, (pct) =>
        setUploadPercent(pct)
      )
    },
    onSuccess: (res) => {
      setUploadPercent(null)
      setSelectedFile(null)
      setPolicyType('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      setUploadNotice({
        type:
          res.document.processing_status === 'FAILED'
            ? 'error'
            : res.is_duplicate
            ? 'info'
            : 'success',
        text: res.message,
        status: res.document.processing_status,
      })
      refreshAll()
    },
    onError: (err: any) => {
      setUploadPercent(null)
      const msg =
        err?.response?.data?.detail || err?.message || 'PDF upload failed.'
      setUploadNotice({ type: 'error', text: msg })
    },
  })

  const reindexMutation = useMutation({
    mutationFn: reindexKnowledgeDocument,
    onSuccess: (doc) => {
      setUploadNotice({
        type: doc.processing_status === 'COMPLETED' ? 'success' : 'error',
        text:
          doc.processing_status === 'COMPLETED'
            ? `Reindexed "${doc.document_name}" (${doc.chunk_count} chunks).`
            : `Reindex failed for "${doc.document_name}": ${doc.error_message}`,
        status: doc.processing_status,
      })
      refreshAll()
    },
    onError: (err: any) => {
      setUploadNotice({
        type: 'error',
        text: err?.response?.data?.detail || 'Reindex request failed.',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteKnowledgeDocument,
    onSuccess: (res) => {
      setConfirmDeleteDoc(null)
      if (selectedDocDetail?.id === res.document_id) {
        setSelectedDocDetail(null)
      }
      if (qaDocId === res.document_id) {
        setQaDocId('')
      }
      setUploadNotice({
        type: 'info',
        text: `Deleted "${res.document_name}" and removed associated vector records.`,
      })
      refreshAll()
    },
    onError: (err: any) => {
      setConfirmDeleteDoc(null)
      setUploadNotice({
        type: 'error',
        text: err?.response?.data?.detail || 'Failed to delete document.',
      })
    },
  })

  const askMutation = useMutation({
    mutationFn: askKnowledgeBase,
    onSuccess: (res) => {
      setQaError(null)
      setQaResult(res)
    },
    onError: (err: any) => {
      setQaError(
        err?.response?.data?.detail || 'Unable to query Insurance Knowledge Base.'
      )
    },
  })

  const validateAndSelectFile = (file: File | undefined) => {
    if (!file) return
    const isPdf =
      file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf'
    if (!isPdf) {
      setUploadNotice({
        type: 'error',
        text: `Invalid file "${file.name}". Only PDF (.pdf) documents are supported.`,
      })
      return
    }
    if (file.size === 0) {
      setUploadNotice({ type: 'error', text: 'Selected PDF file is empty (0 bytes).' })
      return
    }
    if (file.size > 20 * 1024 * 1024) {
      setUploadNotice({
        type: 'error',
        text: 'Selected PDF exceeds the 20 MB maximum file size limit.',
      })
      return
    }
    setUploadNotice(null)
    setSelectedFile(file)
  }

  const openDocumentDetail = async (docId: string) => {
    setDetailLoading(true)
    try {
      const detail = await fetchKnowledgeDocumentDetail(docId)
      setSelectedDocDetail(detail)
    } catch (err: any) {
      setUploadNotice({
        type: 'error',
        text: err?.response?.data?.detail || 'Failed to load document details.',
      })
    } finally {
      setDetailLoading(false)
    }
  }

  const handleSearchWithinDoc = (doc: KnowledgeDocument) => {
    setQaDocId(doc.id)
    setQaCategory('')
    qaInputRef.current?.focus()
  }

  const handleAsk = (overrideQ?: string) => {
    const q = (overrideQ ?? question).trim()
    if (q.length < 2 || askMutation.isPending) return
    if (overrideQ) setQuestion(overrideQ)
    askMutation.mutate({
      question: q,
      category: qaCategory || undefined,
      policy_type: qaPolicyType || undefined,
      document_id: qaDocId || undefined,
      top_k: 5,
    })
  }

  if (statsLoading && docsLoading) return <PageLoader />
  if (statsError || docsError) {
    return (
      <ErrorState
        onRetry={() => {
          refetchStats()
          refetchDocs()
        }}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-slate-200 pb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            Insurance Knowledge Base
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Upload policy wordings, claim guidelines, and underwriting manuals for grounded RAG retrieval.
          </p>
        </div>
        <button
          onClick={refreshAll}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 self-start"
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {/* Real-time KPI Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <StatCard label="Total Documents" value={stats?.total_documents ?? 0} />
        <StatCard label="Indexed Documents" value={stats?.indexed_documents ?? 0} accent="green" />
        <StatCard label="Processing" value={stats?.processing_documents ?? 0} accent="blue" />
        <StatCard label="Failed" value={stats?.failed_documents ?? 0} accent="red" />
        <StatCard label="Total Indexed Chunks" value={stats?.total_chunks ?? 0} accent="blue" />
      </div>

      {/* Upload + Insurance Knowledge Assistant Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Document Upload Card */}
        <div className="card p-5 lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">
              Upload Policy or Guideline PDF
            </h2>
            <span className="text-[11px] text-slate-500">PDF only, max 20 MB</span>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              validateAndSelectFile(e.dataTransfer.files?.[0])
            }}
            onClick={() => { if (!uploadMutation.isPending) fileInputRef.current?.click() }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
            }}
            className={`border-2 border-dashed rounded-md p-5 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-blue-600 bg-blue-50/50'
                : 'border-slate-300 hover:border-slate-400 bg-slate-50/60'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={(e) => validateAndSelectFile(e.target.files?.[0])}
            />
            <Upload size={20} className="mx-auto text-slate-500 mb-2" />
            {selectedFile ? (
              <div>
                <p className="text-xs font-medium text-slate-900 truncate">
                  {selectedFile.name}
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {formatBytes(selectedFile.size)} &middot; Click to replace
                </p>
              </div>
            ) : (
              <div>
                <p className="text-xs font-medium text-slate-700">
                  Drag and drop a PDF here, or click to browse
                </p>
                <p className="text-[11px] text-slate-500 mt-1">
                  Text-based PDFs are extracted page-by-page and indexed in ChromaDB
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-600 mb-1">
                Document Category
              </label>
              <select
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                className="input text-xs w-full"
              >
                {KNOWLEDGE_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-600 mb-1">
                Policy Type (Optional)
              </label>
              <input
                type="text"
                value={policyType}
                onChange={(e) => setPolicyType(e.target.value)}
                placeholder="e.g. AUTO, HEALTH, LIFE"
                className="input text-xs w-full"
              />
            </div>
          </div>

          {uploadPercent !== null && (
            <div className="space-y-1">
              <div className="flex justify-between text-[11px] text-slate-600">
                <span>Uploading PDF...</span>
                <span>{uploadPercent}%</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-1.5">
                <div
                  className="bg-blue-700 h-1.5 rounded-full transition-all"
                  style={{ width: `${uploadPercent}%` }}
                />
              </div>
            </div>
          )}

          {uploadMutation.isPending && uploadPercent === 100 && (
            <div className="flex items-center gap-2 text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2">
              <Spinner size={14} />
              <span>Extracting text, generating Gemini embeddings, and indexing vectors...</span>
            </div>
          )}

          {uploadNotice && (
            <div
              className={`rounded-md border px-3 py-2.5 text-xs space-y-2 ${
                uploadNotice.type === 'error'
                  ? 'bg-red-50 border-red-200 text-red-800'
                  : uploadNotice.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}
            >
              <div className="flex items-start gap-2">
                {uploadNotice.type === 'error' ? (
                  <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 size={14} className="flex-shrink-0 mt-0.5" />
                )}
                <span>{uploadNotice.text}</span>
              </div>
              {uploadNotice.status && <StageTracker status={uploadNotice.status} />}
            </div>
          )}

          <button
            onClick={() => uploadMutation.mutate()}
            disabled={!selectedFile || uploadMutation.isPending}
            className="w-full py-2 px-4 bg-blue-700 text-white text-xs font-medium rounded-md hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {uploadMutation.isPending ? (
              <>
                <Spinner size={14} />
                Processing Document...
              </>
            ) : (
              <>
                <Upload size={14} />
                Upload &amp; Index Document
              </>
            )}
          </button>
        </div>

        {/* Insurance Knowledge Assistant Q&A */}
        <div className="card p-5 lg:col-span-7 flex flex-col space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-2">
              <BookOpen size={16} className="text-blue-700" />
              <h2 className="text-sm font-semibold text-slate-900">
                Insurance Knowledge Assistant
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={qaCategory}
                onChange={(e) => setQaCategory(e.target.value)}
                className="input text-xs"
              >
                <option value="">All Categories</option>
                {KNOWLEDGE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <select
                value={qaPolicyType}
                onChange={(e) => setQaPolicyType(e.target.value)}
                className="input text-xs"
              >
                <option value="">All Policy Types</option>
                <option value="AUTO">AUTO</option>
                <option value="HEALTH">HEALTH</option>
                <option value="LIFE">LIFE</option>
                <option value="PROPERTY">PROPERTY</option>
              </select>
              {qaDocId && (
                <button
                  onClick={() => setQaDocId('')}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[11px] bg-blue-50 text-blue-700 border border-blue-200 rounded"
                >
                  <span>
                    Scoped:{' '}
                    {documents?.find((d) => d.id === qaDocId)?.document_name || 'Document'}
                  </span>
                  <X size={11} />
                </button>
              )}
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleAsk()
            }}
            className="flex gap-2"
          >
            <input
              ref={qaInputRef}
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about policy coverage, exclusions, or claim guidelines..."
              className="input flex-1 text-xs"
            />
            <button
              type="submit"
              disabled={askMutation.isPending || question.trim().length < 2}
              className="px-4 py-2 bg-blue-700 text-white text-xs font-medium rounded-md hover:bg-blue-800 disabled:opacity-50 flex items-center gap-1.5"
            >
              {askMutation.isPending ? <Spinner size={14} /> : <Send size={13} />}
              Ask
            </button>
          </form>

          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => handleAsk(q)}
                className="text-[11px] text-slate-600 bg-slate-100 hover:bg-slate-200 px-2.5 py-1 rounded border border-slate-200 text-left"
              >
                {q}
              </button>
            ))}
          </div>

          {qaError && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-800">
              {qaError}
            </div>
          )}

          {qaResult ? (
            <div className="space-y-3 border-t border-slate-200 pt-3">
              {qaResult.insufficient_evidence && (
                <div className="flex items-center gap-2 text-xs bg-amber-50 text-amber-800 border border-amber-200 rounded px-3 py-2">
                  <AlertCircle size={14} className="flex-shrink-0" />
                  <span>
                    Insufficient evidence in indexed documents to fully answer this question.
                  </span>
                </div>
              )}

              <div className="bg-slate-50 border border-slate-200 rounded-md p-3.5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Grounded Answer
                  </span>
                  {qaResult.retrieval_note && (
                    <span className="text-[11px] text-slate-500">
                      {qaResult.retrieval_note}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-800 whitespace-pre-wrap leading-relaxed">
                  {qaResult.answer}
                </p>
              </div>

              {qaResult.sources.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    Source References ({qaResult.sources.length})
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                    {qaResult.sources.map((src, idx) => (
                      <div
                        key={`${src.document_id}-${src.page_number}-${idx}`}
                        className="border border-slate-200 rounded-md p-2.5 bg-white text-xs space-y-1"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <button
                            type="button"
                            onClick={() => openDocumentDetail(src.document_id)}
                            className="font-medium text-blue-700 hover:underline flex items-center gap-1"
                          >
                            <FileText size={12} />
                            {src.document_name} &middot; Page {src.page_number}
                          </button>
                          <div className="flex items-center gap-2">
                            <Badge className="bg-slate-100 text-slate-700 border-slate-200">{src.category}</Badge>
                            <span className="text-[11px] text-slate-500">
                              Similarity: {(src.retrieval_similarity * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                        <p className="text-[11px] text-slate-600 leading-relaxed">
                          &ldquo;{src.relevant_excerpt}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center border border-dashed border-slate-200 rounded-md p-6 text-center">
              <p className="text-xs text-slate-500 max-w-md">
                Ask any policy wording, coverage, exclusion, or claim guideline question. Answers are strictly grounded in uploaded PDFs with document and page citations.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Document Library */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Document Library</h2>
            <p className="text-xs text-slate-500">
              Indexed insurance PDFs available to the Knowledge Assistant and AI Investigator.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="input text-xs"
            >
              <option value="">All Categories</option>
              {KNOWLEDGE_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input text-xs"
            >
              <option value="">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
              <option value="INDEXING">Indexing</option>
            </select>
          </div>
        </div>

        {!documents || documents.length === 0 ? (
          <EmptyState
            title="No knowledge base documents uploaded"
            description="Upload a policy wording, claim guideline, or underwriting PDF above to enable RAG retrieval."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5 text-left">Document Name</th>
                  <th className="px-4 py-2.5 text-left">Category</th>
                  <th className="px-4 py-2.5 text-right">Pages</th>
                  <th className="px-4 py-2.5 text-right">Indexed Chunks</th>
                  <th className="px-4 py-2.5 text-left">Status</th>
                  <th className="px-4 py-2.5 text-left">Uploaded</th>
                  <th className="px-4 py-2.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="table-row">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900 text-xs">
                        {doc.document_name}
                      </div>
                      {doc.policy_type && (
                        <div className="text-[11px] text-slate-500">
                          Policy Type: {doc.policy_type}
                        </div>
                      )}
                      {doc.error_message && (
                        <div className="text-[11px] text-red-600 mt-0.5 max-w-xs truncate" title={doc.error_message}>
                          {doc.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-700">{doc.category}</td>
                    <td className="px-4 py-3 text-xs text-slate-700 text-right">
                      {doc.page_count}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-700 text-right">
                      {doc.chunk_count}
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={statusBadgeClass(doc.processing_status)}>
                        {doc.processing_status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {formatDateTime(doc.upload_timestamp)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => openDocumentDetail(doc.id)}
                          title="View Details"
                          className="p-1.5 text-slate-600 hover:text-blue-700 hover:bg-slate-100 rounded"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSearchWithinDoc(doc)}
                          disabled={doc.processing_status !== 'COMPLETED'}
                          title="Search Within Document"
                          className="p-1.5 text-slate-600 hover:text-blue-700 hover:bg-slate-100 rounded disabled:opacity-40"
                        >
                          <Search size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => reindexMutation.mutate(doc.id)}
                          disabled={reindexMutation.isPending}
                          title="Reindex Document"
                          className="p-1.5 text-slate-600 hover:text-blue-700 hover:bg-slate-100 rounded disabled:opacity-40"
                        >
                          <RefreshCw size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteDoc(doc)}
                          title="Delete Document"
                          className="p-1.5 text-slate-600 hover:text-red-700 hover:bg-red-50 rounded"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Document Details Modal / Drawer */}
      {(selectedDocDetail || detailLoading) && (
        <div className="fixed inset-0 bg-slate-900/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-lg max-w-2xl w-full max-h-[85vh] flex flex-col">
            <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 truncate pr-3">
                {detailLoading
                  ? 'Loading Document Details...'
                  : selectedDocDetail?.document_name}
              </h3>
              <div className="flex items-center gap-2">
                {selectedDocDetail && (
                  <a
                    href={`/api/v1/knowledge-base/documents/${selectedDocDetail.id}/file`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100"
                  >
                    <FileText size={12} />
                    Open PDF
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => setSelectedDocDetail(null)}
                  className="text-slate-400 hover:text-slate-700"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
            <div className="p-5 overflow-y-auto space-y-4">
              {detailLoading ? (
                <div className="py-8 flex justify-center">
                  <Spinner />
                </div>
              ) : (
                selectedDocDetail && (
                  <>
                    <StageTracker status={selectedDocDetail.processing_status} />
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-3.5 rounded border border-slate-200">
                      <div>
                        <span className="text-slate-500 block">Category</span>
                        <span className="font-medium text-slate-900">
                          {selectedDocDetail.category}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Policy Type</span>
                        <span className="font-medium text-slate-900">
                          {selectedDocDetail.policy_type || 'General'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">File Size</span>
                        <span className="font-medium text-slate-900">
                          {formatBytes(selectedDocDetail.file_size_bytes)}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Pages</span>
                        <span className="font-medium text-slate-900">
                          {selectedDocDetail.page_count}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Indexed Chunks</span>
                        <span className="font-medium text-slate-900">
                          {selectedDocDetail.chunk_count}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">SHA-256 Prefix</span>
                        <span className="font-mono text-slate-700">
                          {selectedDocDetail.file_hash.slice(0, 12)}...
                        </span>
                      </div>
                    </div>

                    {selectedDocDetail.error_message && (
                      <div className="bg-red-50 border border-red-200 rounded p-3 text-xs text-red-800">
                        <strong>Processing Error:</strong> {selectedDocDetail.error_message}
                      </div>
                    )}

                    <div>
                      <h4 className="text-xs font-semibold text-slate-700 mb-2">
                        Indexed Text Excerpts ({selectedDocDetail.excerpts.length})
                      </h4>
                      {selectedDocDetail.excerpts.length === 0 ? (
                        <p className="text-xs text-slate-500">
                          No indexed excerpts available for this document.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {selectedDocDetail.excerpts.map((ex) => (
                            <div
                              key={ex.chunk_id}
                              className="border border-slate-200 rounded p-2.5 text-xs bg-white"
                            >
                              <div className="text-[11px] font-medium text-blue-700 mb-1">
                                Page {ex.page_number} &middot; Chunk #{ex.chunk_index + 1}
                              </div>
                              <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                                {ex.excerpt}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDeleteDoc && (
        <div className="fixed inset-0 bg-slate-900/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg border border-slate-200 shadow-lg max-w-md w-full p-5 space-y-4">
            <h3 className="text-sm font-semibold text-slate-900">
              Delete Knowledge Document
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to delete{' '}
              <strong>{confirmDeleteDoc.document_name}</strong>? This will permanently remove its metadata and all {confirmDeleteDoc.chunk_count} indexed vector chunks from ChromaDB. Customer and policy records will not be affected.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteDoc(null)}
                className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(confirmDeleteDoc.id)}
                disabled={deleteMutation.isPending}
                className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete Document'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
