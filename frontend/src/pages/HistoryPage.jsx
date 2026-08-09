import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'

const historyRows = [
  { paper: 'Neural Network Optimization Study', guideline: 'IEEE', date: '2026-07-18', score: 87, status: 'Demo Analysis' },
  { paper: 'Sustainable Edge Computing', guideline: 'ACM', date: '2026-07-05', score: 82, status: 'Demo Analysis' },
  { paper: 'Privacy-Preserving Data Systems', guideline: 'Springer', date: '2026-06-21', score: 91, status: 'Demo Analysis' },
  { paper: 'Adaptive Learning Framework', guideline: 'Elsevier', date: '2026-06-02', score: 76, status: 'Demo Analysis' },
]

export default function HistoryPage() {
  const [query, setQuery] = useState('')
  const [guideline, setGuideline] = useState('All guidelines')
  const [sortOrder, setSortOrder] = useState('newest')
  const results = useMemo(() => historyRows.filter((row) => row.paper.toLowerCase().includes(query.toLowerCase()) && (guideline === 'All guidelines' || row.guideline === guideline)).sort((a, b) => sortOrder === 'score' ? b.score - a.score : new Date(b.date) - new Date(a.date)), [query, guideline, sortOrder])

  return (
    <div className="page-container py-12 sm:py-16"><div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">History · mock data</p><h1 className="section-title mt-3">Previous paper reviews</h1><p className="mt-3 text-slate-600">This sample history is for interface preview only; results are not stored during Module 1.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600"><Icon name="info" className="h-4 w-4" /> No database records yet</span></div>
      <section className="surface-card mt-8 overflow-hidden"><div className="grid gap-3 border-b border-slate-200 p-4 md:grid-cols-[minmax(0,1fr)_190px_170px]"><label className="relative block"><span className="sr-only">Search paper history</span><Icon name="search" className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search papers" className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm text-slate-800 placeholder:text-slate-400" /></label><label className="relative block"><span className="sr-only">Filter by guideline</span><select value={guideline} onChange={(event) => setGuideline(event.target.value)} className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700"><option>All guidelines</option><option>IEEE</option><option>ACM</option><option>Springer</option><option>Elsevier</option></select><Icon name="filter" className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500" /></label><label className="relative block"><span className="sr-only">Sort history</span><select value={sortOrder} onChange={(event) => setSortOrder(event.target.value)} className="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-700"><option value="newest">Newest first</option><option value="score">Highest score</option></select><Icon name="chevronDown" className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500" /></label></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500"><tr>{['Paper', 'Guideline', 'Date', 'Score', 'Status', 'Action'].map((head) => <th key={head} className="px-5 py-3 font-semibold">{head}</th>)}</tr></thead><tbody className="divide-y divide-slate-200">{results.map((row) => <tr key={row.paper} className="text-slate-700"><td className="px-5 py-4 font-medium text-slate-900">{row.paper}</td><td className="px-5 py-4">{row.guideline}</td><td className="px-5 py-4">{new Intl.DateTimeFormat('en-US', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(`${row.date}T00:00:00`))}</td><td className="px-5 py-4 font-semibold text-indigo-700">{row.score} / 100</td><td className="px-5 py-4"><span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">{row.status}</span></td><td className="px-5 py-4"><Link to="/dashboard" className="text-sm font-semibold text-indigo-700 hover:text-indigo-900">View demo</Link></td></tr>)}</tbody></table>{results.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No mock records match these filters.</p>}</div></section></div>
  )
}
