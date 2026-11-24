import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, Plus, Database, MessageSquare, BookOpen } from 'lucide-react'
import {
  fetchConversations,
  fetchConversation,
  fetchHealth,
  sendCopilotMessage,
} from '../services/api'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'
import { formatDateTime } from '../lib/utils'
import type { ChatMessage, ToolCall } from '../types'

const QUICK_PROMPTS = [
  'Which customers require immediate attention?',
  'Show policies expiring within 15 days',
  'Which customers have overdue premiums?',
  'Which customers have missing mandatory documents?',
  'Explain accidental damage coverage and exclusions from policy documents',
]

function ToolCallList({ calls }: { calls?: ToolCall[] | null }) {
  if (!calls || calls.length === 0) return null
  return (
    <div className="mt-2 space-y-1">
      {calls.map((tc, idx) => (
        <div
          key={idx}
          className="flex items-center gap-1.5 text-[11px] text-slate-600 bg-slate-100 border border-slate-200 px-2.5 py-1 rounded"
        >
          {tc.name === 'search_insurance_documents' ? (
            <BookOpen size={11} className="text-emerald-700 flex-shrink-0" />
          ) : (
            <Database size={11} className="text-blue-700 flex-shrink-0" />
          )}
          <span className="font-mono font-medium text-slate-800">{tc.name}</span>
          {tc.args && Object.keys(tc.args).length > 0 && (
            <span className="text-slate-500 truncate">({JSON.stringify(tc.args)})</span>
          )}
        </div>
      ))}
    </div>
  )
}

export default function CopilotPage() {
  const [searchParams] = useSearchParams()
  const scopedCustomerId = searchParams.get('customer_id') || undefined
  const queryClient = useQueryClient()

  const [conversationId, setConversationId] = useState<string | undefined>()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [lastMode, setLastMode] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    retry: 0,
  })

  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: fetchConversations,
  })

  const loadConversation = async (id: string) => {
    const detail = await fetchConversation(id)
    setConversationId(detail.id)
    setMessages(detail.messages || [])
  }

  const mutation = useMutation({
    mutationFn: sendCopilotMessage,
    onSuccess: (data) => {
      setConversationId(data.conversation_id)
      setLastMode(data.mode)
      setMessages((prev) => [
        ...prev,
        {
          id: data.message_id,
          sender: 'ASSISTANT',
          content: data.reply,
          tool_calls: data.tool_calls,
          tool_results: data.tool_results,
          timestamp: data.timestamp,
        },
      ])
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
    },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = (overrideText?: string) => {
    const text = (overrideText ?? input).trim()
    if (!text || mutation.isPending) return

    setMessages((prev) => [...prev, { sender: 'USER', content: text }])
    if (!overrideText) setInput('')
    mutation.mutate({
      message: text,
      conversation_id: conversationId,
      customer_id: scopedCustomerId,
    })
  }

  const startNewSession = () => {
    setConversationId(undefined)
    setMessages([])
    setLastMode(null)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 h-[calc(100vh-5rem)]">
      {/* Left: Session History */}
      <div className="card flex flex-col overflow-hidden lg:col-span-1">
        <div className="p-3.5 border-b border-slate-200 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
            Investigations
          </span>
          <button onClick={startNewSession} className="btn-ghost text-xs text-blue-700 px-2 py-1">
            <Plus size={13} />
            <span>New</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {(conversations || []).map((conv) => (
            <button
              key={conv.id}
              onClick={() => loadConversation(conv.id)}
              className={`w-full text-left p-3 hover:bg-slate-50 transition-colors ${
                conversationId === conv.id ? 'bg-blue-50 border-l-2 border-blue-700' : ''
              }`}
            >
              <p className="text-xs font-medium text-slate-900 truncate">{conv.title}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {conv.message_count} messages · {formatDateTime(conv.updated_at)}
              </p>
            </button>
          ))}
          {(!conversations || conversations.length === 0) && (
            <p className="p-4 text-xs text-slate-400">No saved investigation sessions.</p>
          )}
        </div>
      </div>

      {/* Right: Conversational Workspace */}
      <div className="card flex flex-col overflow-hidden lg:col-span-3">
        {/* Header with Real Mode Indicator */}
        <div className="px-5 py-3.5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-base font-semibold text-slate-900">AI Investigator Copilot</h1>
            <p className="text-xs text-slate-500">
              Tool-first database investigation powered by the Python Tool Registry.
              {scopedCustomerId ? ` Scoped to customer ${scopedCustomerId}.` : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {health && (
              <Badge
                className={
                  health.gemini_live
                    ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                    : 'text-slate-700 bg-slate-100 border-slate-300'
                }
              >
                {health.gemini_live ? `Live Gemini (${health.gemini_model_configured})` : 'Offline Cognitive Mode'}
              </Badge>
            )}
            {lastMode && (
              <Badge className="text-blue-700 bg-blue-50 border-blue-200">Last Turn: {lastMode}</Badge>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/50">
          {messages.length === 0 && (
            <div className="max-w-xl mx-auto py-8 text-center space-y-4">
              <div className="w-10 h-10 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center mx-auto">
                <MessageSquare size={18} className="text-blue-700" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">Start a Customer Investigation</p>
                <p className="text-xs text-slate-500 mt-1">
                  Ask about high-risk customers, expiring policies, overdue premiums, or request an outreach draft.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {QUICK_PROMPTS.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="text-xs bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 px-3 py-1.5 rounded-md transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, idx) => {
            const isUser = m.sender === 'USER'
            return (
              <div key={idx} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                <span className="text-[10px] font-medium text-slate-400 mb-1">
                  {isUser ? 'Employee' : 'The Investigator'}
                </span>
                <div
                  className={`max-w-[82%] px-4 py-3 rounded-md text-sm leading-relaxed whitespace-pre-wrap ${
                    isUser
                      ? 'bg-blue-700 text-white'
                      : 'bg-white text-slate-800 border border-slate-200 shadow-sm'
                  }`}
                >
                  {m.content}
                </div>
                {!isUser && <ToolCallList calls={m.tool_calls} />}
              </div>
            )
          })}

          {mutation.isPending && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Spinner size={14} />
              <span>Executing database tools and synthesizing response...</span>
            </div>
          )}

          {mutation.isError && (
            <div className="text-xs text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md">
              Copilot request failed. Please verify the backend server is running.
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="p-3.5 border-t border-slate-200 bg-white flex items-center gap-2.5">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Ask The Investigator (e.g., Investigate CUST-1005 or draft a renewal email)..."
            className="input flex-1"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || mutation.isPending}
            className="btn-primary"
          >
            <Send size={14} />
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
