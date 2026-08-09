import { Route, Routes } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import AboutPage from '../pages/AboutPage'
import AnalyzePage from '../pages/AnalyzePage'
import DashboardPage from '../pages/DashboardPage'
import HistoryPage from '../pages/HistoryPage'
import HomePage from '../pages/HomePage'
import KnowledgeBasePage from '../pages/KnowledgeBasePage'
import NotFoundPage from '../pages/NotFoundPage'
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
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
