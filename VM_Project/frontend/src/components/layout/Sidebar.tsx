import { NavLink, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  LayoutDashboard,
  AlertTriangle,
  Users,
  FileText,
  FileCheck,
  CreditCard,
  MessageSquare,
  Activity,
  Shield,
  BookOpen,
} from 'lucide-react'
import { fetchHealth } from '../../services/api'

const navItems = [
  { to: '/', label: 'Executive Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/attention', label: 'Attention Center', icon: AlertTriangle },
  { to: '/customers', label: 'Customers (360)', icon: Users },
  { to: '/policies', label: 'Policies & Renewals', icon: FileText },
  { to: '/documents', label: 'Document Compliance', icon: FileCheck },
  { to: '/knowledge-base', label: 'Insurance Knowledge Base', icon: BookOpen },
  { to: '/billing', label: 'Premium Monitoring', icon: CreditCard },
  { to: '/copilot', label: 'AI Investigator', icon: MessageSquare },
  { to: '/analysis', label: 'Analysis History', icon: Activity },
]

export function Sidebar() {
  const location = useLocation()
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 60_000,
    retry: 0,
  })

  return (
    <aside className="w-60 flex-shrink-0 flex flex-col bg-white border-r border-slate-200 min-h-screen sticky top-0">
      {/* Brand */}
      <div className="px-5 py-4 border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-md bg-blue-700 flex items-center justify-center">
            <Shield size={16} className="text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900 leading-none">InsureDesk</p>
            <p className="text-[11px] text-slate-500 leading-none mt-1">Operations Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, exact }) => {
          const isActive = exact ? location.pathname === to : location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-medium border border-blue-200'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          )
        })}
      </nav>

      {/* Real System Telemetry Footer */}
      <div className="px-4 py-3 border-t border-slate-200 bg-slate-50">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-slate-500 font-medium">Engine Mode</span>
          {health ? (
            <span
              className={`px-1.5 py-0.5 rounded font-medium ${
                health.gemini_live
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : 'bg-slate-200 text-slate-700'
              }`}
            >
              {health.gemini_live ? 'Live Gemini' : 'Cognitive Core'}
            </span>
          ) : (
            <span className="text-slate-400">Connecting...</span>
          )}
        </div>
        <p className="text-[10px] text-slate-400 mt-1.5">VM_Project v1.0.0</p>
      </div>
    </aside>
  )
}
