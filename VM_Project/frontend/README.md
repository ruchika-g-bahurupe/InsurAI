# VM_project Frontend - Insurance Customer Intelligence Platform

Modern React + TypeScript + Tailwind CSS enterprise dashboard for insurance customer intelligence, retention risk monitoring, and AI copilot interaction.

## Planned Tech Stack
- **Framework**: React 18 / 19 with Vite
- **Styling**: Tailwind CSS + PostCSS
- **Icons**: Lucide React
- **State & Data Fetching**: TanStack Query (React Query) + Axios
- **Design Aesthetic**: Premium Enterprise SaaS (Dark slate navigation, high-contrast typography, crisp status badges)

## Directory Structure Overview
- `src/components/common`: Design system primitives (Badges, Buttons, Modals, StatCards, Tables, Drawers)
- `src/components/layout`: Sidebar, Header, Breadcrumbs, Shell layout
- `src/components/dashboard`: MetricGrid, PriorityQueue, CategoryCards, ScannerTrigger
- `src/components/attention`: AttentionFilter, AttentionCard, ActionDialog
- `src/components/customer`: CustomerTable, ProfileHeader, PolicyList, DocumentVault, PremiumTimeline
- `src/components/copilot`: CopilotDrawer, ChatMessage, ToolCallBadge, QuickPromptChips, ChatInput
- `src/pages`: DashboardPage, AttentionHubPage, CustomersPage, CustomerDetailPage, PoliciesPage
- `src/services`: API client integrations (Axios)
- `src/types`: TypeScript definitions matching backend Pydantic schemas

*Note: Frontend implementation will begin in Phase 4.*
