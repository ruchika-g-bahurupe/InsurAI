import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import AttentionHubPage from './pages/AttentionHubPage'
import AttentionDetailPage from './pages/AttentionDetailPage'
import CustomersPage from './pages/CustomersPage'
import CustomerDetailPage from './pages/CustomerDetailPage'
import PoliciesPage from './pages/PoliciesPage'
import DocumentCompliancePage from './pages/DocumentCompliancePage'
import BillingMonitoringPage from './pages/BillingMonitoringPage'
import CopilotPage from './pages/CopilotPage'
import AnalysisHistoryPage from './pages/AnalysisHistoryPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/attention" element={<AttentionHubPage />} />
          <Route path="/attention/:attentionId" element={<AttentionDetailPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/customers/:customerId" element={<CustomerDetailPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/documents" element={<DocumentCompliancePage />} />
          <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
          <Route path="/billing" element={<BillingMonitoringPage />} />
          <Route path="/copilot" element={<CopilotPage />} />
          <Route path="/analysis" element={<AnalysisHistoryPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
