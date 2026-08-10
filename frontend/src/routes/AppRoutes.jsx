import { Route, Routes } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import AboutPage from '../pages/AboutPage'
import AnalyzePage from '../pages/AnalyzePage'
import CompliancePage from '../pages/CompliancePage'
import DashboardPage from '../pages/DashboardPage'
import HistoryPage from '../pages/HistoryPage'
import HomePage from '../pages/HomePage'
import KnowledgeBasePage from '../pages/KnowledgeBasePage'
import LogicVerificationPage from '../pages/LogicVerificationPage'
import NotFoundPage from '../pages/NotFoundPage'
import PlanningPage from '../pages/PlanningPage'
import ReasoningPage from '../pages/ReasoningPage'

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/knowledge-base" element={<KnowledgeBasePage />} />
        <Route path="/reasoning" element={<ReasoningPage />} />
        <Route path="/logical-verification" element={<LogicVerificationPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/planning" element={<PlanningPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
