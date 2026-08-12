import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon'
import { getPaperAnalysisHistory, getSavedAnalysis, getSavedPapers } from '../services/api'

function formatDate(value) {
  if (!value) return 'Unknown date'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? 'Unknown date' : new Intl.DateTimeFormat('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(parsed)
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [papers, setPapers] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [openingPaperId, setOpeningPaperId] = useState('')

  const loadHistory = async () => {
    setStatus('loading')
    setError('')
    try {
      const response = await getSavedPapers()
      setPapers(response.papers || [])
      setStatus('ready')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Saved paper history could not be loaded.')
      setStatus('error')
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  const openLatestAnalysis = async (paperId) => {
    setOpeningPaperId(paperId)
    setError('')
    try {
      const history = await getPaperAnalysisHistory(paperId)
      const latest = history.analyses?.[0]
      if (!latest) throw new Error('No saved analyses are available for this paper yet.')
      const response = await getSavedAnalysis(latest.analysis_id)
      sessionStorage.setItem('paperintel.integratedAnalysis', JSON.stringify(response.analysis))
      sessionStorage.setItem('paperintel.persistedPaperId', JSON.stringify(paperId))
      navigate('/analysis')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Saved analysis could not be opened.')
    } finally {
      setOpeningPaperId('')
    }
  }

  return <div className="page-container py-12 sm:py-16"><div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Module 11 · MongoDB persistence</p><h1 className="section-title mt-3">Previous paper analyses</h1><p className="mt-3 max-w-2xl text-slate-600">Saved Module 8 results are listed here when MongoDB persistence is configured. Uploaded PDF binaries are never stored.</p></div><button type="button" onClick={loadHistory} disabled={status === 'loading'} className="secondary-button disabled:cursor-not-allowed disabled:opacity-60"><Icon name={status === 'loading' ? 'clock' : 'activity'} className="h-4 w-4" />{status === 'loading' ? 'Loading…' : 'Refresh history'}</button></div>
    {error && <section className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-950"><div className="flex gap-3"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><div><h2 className="font-semibold">History is unavailable</h2><p className="mt-1 text-sm leading-6">{error}</p></div></div></section>}
    {status === 'ready' && papers.length === 0 && <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="document" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">No saved analyses yet</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Run an integrated analysis after MongoDB is configured to save its structured result and see it here.</p><Link to="/analysis" className="primary-button mt-6"><Icon name="activity" className="h-4 w-4" /> Open integrated analysis</Link></section>}
    {status === 'ready' && papers.length > 0 && <section className="surface-card mt-8 overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500"><tr>{['Paper', 'Filename', 'Pages', 'Saved', 'Action'].map((head) => <th key={head} className="px-5 py-3 font-semibold">{head}</th>)}</tr></thead><tbody className="divide-y divide-slate-200">{papers.map((paper) => <tr key={paper.paper_id} className="text-slate-700"><td className="px-5 py-4 font-medium text-slate-900">{paper.metadata?.title || 'Untitled paper'}</td><td className="px-5 py-4">{paper.filename}</td><td className="px-5 py-4">{paper.page_count}</td><td className="px-5 py-4">{formatDate(paper.created_at)}</td><td className="px-5 py-4"><button type="button" onClick={() => openLatestAnalysis(paper.paper_id)} disabled={openingPaperId === paper.paper_id} className="text-sm font-semibold text-indigo-700 hover:text-indigo-900 disabled:cursor-not-allowed disabled:text-slate-400">{openingPaperId === paper.paper_id ? 'Opening…' : 'Open latest analysis'}</button></td></tr>)}</tbody></table></div></section>}
  </div>
}
