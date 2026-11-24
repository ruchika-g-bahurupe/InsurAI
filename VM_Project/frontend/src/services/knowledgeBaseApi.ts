import { api } from './api'
import type {
  DocumentUploadResponse,
  KnowledgeAskResponse,
  KnowledgeBaseStats,
  KnowledgeDocument,
  KnowledgeDocumentDetail,
  KnowledgeSearchResponse,
} from '../types'

export const KNOWLEDGE_CATEGORIES = [
  'Insurance Policy Documents',
  'Claim Guidelines',
  'Insurance Terms and Conditions',
  'Underwriting Guidelines',
  'Insurance Operational Procedures',
] as const

export const fetchKnowledgeStats = async (): Promise<KnowledgeBaseStats> => {
  const { data } = await api.get('/knowledge-base/stats')
  return data
}

export const fetchKnowledgeDocuments = async (params?: {
  category?: string
  status?: string
}): Promise<KnowledgeDocument[]> => {
  const { data } = await api.get('/knowledge-base/documents', { params })
  return data
}

export const fetchKnowledgeDocumentDetail = async (
  documentId: string
): Promise<KnowledgeDocumentDetail> => {
  const { data } = await api.get(`/knowledge-base/documents/${documentId}`)
  return data
}

export const uploadKnowledgeDocument = async (
  file: File,
  category: string,
  policyType?: string,
  onUploadProgress?: (percent: number) => void
): Promise<DocumentUploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', category)
  if (policyType && policyType.trim()) {
    formData.append('policy_type', policyType.trim())
  }

  const { data } = await api.post('/knowledge-base/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
    onUploadProgress: (evt) => {
      if (onUploadProgress && evt.total) {
        onUploadProgress(Math.round((evt.loaded * 100) / evt.total))
      }
    },
  })
  return data
}

export const reindexKnowledgeDocument = async (
  documentId: string
): Promise<KnowledgeDocument> => {
  const { data } = await api.post(`/knowledge-base/documents/${documentId}/reindex`, null, {
    timeout: 120000,
  })
  return data
}

export const deleteKnowledgeDocument = async (
  documentId: string
): Promise<{ deleted: boolean; document_id: string; document_name: string }> => {
  const { data } = await api.delete(`/knowledge-base/documents/${documentId}`)
  return data
}

export const searchKnowledgeBase = async (payload: {
  query: string
  category?: string
  policy_type?: string
  document_id?: string
  top_k?: number
}): Promise<KnowledgeSearchResponse> => {
  const { data } = await api.post('/knowledge-base/search', payload)
  return data
}

export const askKnowledgeBase = async (payload: {
  question: string
  category?: string
  policy_type?: string
  document_id?: string
  top_k?: number
}): Promise<KnowledgeAskResponse> => {
  const { data } = await api.post('/knowledge-base/ask', payload, {
    timeout: 60000,
  })
  return data
}
