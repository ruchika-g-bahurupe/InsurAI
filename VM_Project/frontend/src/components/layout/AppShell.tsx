import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile Header + Drawer */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="lg:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
          <span className="text-sm font-semibold text-slate-900">InsureDesk</span>
          <button
            onClick={() => setMobileNavOpen(!mobileNavOpen)}
            className="btn-ghost p-1.5"
            aria-label="Toggle navigation"
          >
            {mobileNavOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </header>

        {mobileNavOpen && (
          <div className="lg:hidden border-b border-slate-200 bg-white" onClick={() => setMobileNavOpen(false)}>
            <Sidebar />
          </div>
        )}

        <main className="flex-1 overflow-y-auto p-5 lg:p-6 max-w-[1440px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
