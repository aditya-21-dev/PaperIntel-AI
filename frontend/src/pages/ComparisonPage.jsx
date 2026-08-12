import { useEffect, useState } from 'react'
import Icon from '../components/Icon'
import { compareAnalyses, getPaperAnalysisHistory, getSavedPapers } from '../services/api'

function formatDate(value) {
  if (!value) return 'Unknown'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime())
    ? 'Unknown'
    : new Intl.DateTimeFormat('en-US', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(parsed)
}

function StatusBadge({ value }) {
  const positive = ['IMPROVED', 'COMPLIANT', 'SATISFIED', 'READY', 'ENTAILED', 'CONSISTENT']
  const negative = ['REGRESSED', 'NON_COMPLIANT', 'VIOLATED', 'NEEDS_IMPROVEMENT', 'ANALYSIS_ERROR']
  const neutral = ['UNCHANGED', 'MIXED', 'INSUFFICIENT_DATA', 'NEUTRAL', 'INCOMPLETE']
  const cls = positive.includes(value)
    ? 'bg-emerald-100 text-emerald-800'
    : negative.includes(value)
      ? 'bg-red-100 text-red-800'
      : neutral.includes(value)
        ? 'bg-slate-100 text-slate-700'
        : 'bg-indigo-100 text-indigo-800'
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`}>{value}</span>
}

function Arrow() {
  return <span className="mx-2 text-slate-400">&#8594;</span>
}

function Section({ title, children }) {
  return (
    <section className="surface-card mt-6 overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-600">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </section>
  )
}

function ChangeRow({ label, before, after, direction }) {
  return (
    <tr className="text-sm text-slate-700">
      <td className="py-2 pr-4 font-medium text-slate-900">{label}</td>
      <td className="py-2 pr-2">{String(before)}</td>
      <td className="py-2 px-2 text-slate-400">&#8594;</td>
      <td className="py-2 pl-2">{String(after)}</td>
      <td className="py-2 pl-4">{direction && <StatusBadge value={direction} />}</td>
    </tr>
  )
}

export default function ComparisonPage() {
  const [papers, setPapers] = useState([])
  const [selectedPaperId, setSelectedPaperId] = useState('')
  const [analyses, setAnalyses] = useState([])
  const [analysisIdA, setAnalysisIdA] = useState('')
  const [analysisIdB, setAnalysisIdB] = useState('')
  const [status, setStatus] = useState('idle')
  const [loadStatus, setLoadStatus] = useState('loading')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    getSavedPapers()
      .then((data) => { setPapers(data.papers || []); setLoadStatus('ready') })
      .catch((err) => {
        setError(err.response?.data?.detail || err.message || 'Could not load saved papers.')
        setLoadStatus('error')
      })
  }, [])

  const loadAnalyses = async (paperId) => {
    setSelectedPaperId(paperId)
    setAnalyses([])
    setAnalysisIdA('')
    setAnalysisIdB('')
    setResult(null)
    setError('')
    if (!paperId) return
    try {
      const data = await getPaperAnalysisHistory(paperId)
      setAnalyses(data.analyses || [])
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not load analysis history for this paper.')
    }
  }

  const runComparison = async () => {
    if (!analysisIdA || !analysisIdB) return
    setStatus('running')
    setResult(null)
    setError('')
    try {
      const data = await compareAnalyses(analysisIdA, analysisIdB)
      setResult(data.comparison)
      setStatus('done')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Comparison failed.')
      setStatus('error')
    }
  }

  const overallClasses = {
    IMPROVED: 'border-emerald-300 bg-emerald-50 text-emerald-900',
    REGRESSED: 'border-red-300 bg-red-50 text-red-900',
    UNCHANGED: 'border-slate-300 bg-slate-50 text-slate-800',
    MIXED: 'border-amber-300 bg-amber-50 text-amber-900',
    INSUFFICIENT_DATA: 'border-slate-200 bg-slate-50 text-slate-600',
  }

  return (
    <div className="page-container py-12 sm:py-16">
      <div className="mb-8">
        <p className="eyebrow">Module 12 &#xB7; Paper comparison</p>
        <h1 className="section-title mt-3">Compare Analyses</h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          Select two stored analyses for the same paper to compare them side-by-side.
          Only fields that were stored are compared; no algorithms are re-run.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
          <div className="flex gap-3">
            <Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      <section className="surface-card p-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1" htmlFor="paper-select">
              Paper
            </label>
            <select
              id="paper-select"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={selectedPaperId}
              onChange={(e) => loadAnalyses(e.target.value)}
              disabled={loadStatus !== 'ready'}
            >
              <option value="">{loadStatus === 'loading' ? 'Loading papers...' : '--- select a paper ---'}</option>
              {papers.map((p) => (
                <option key={p.paper_id} value={p.paper_id}>
                  {p.metadata?.title || p.filename} ({p.page_count}p)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1" htmlFor="analysis-a-select">
              Analysis A (before)
            </label>
            <select
              id="analysis-a-select"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={analysisIdA}
              onChange={(e) => setAnalysisIdA(e.target.value)}
              disabled={analyses.length === 0}
            >
              <option value="">--- select analysis A ---</option>
              {analyses.map((a) => (
                <option key={a.analysis_id} value={a.analysis_id}>
                  {formatDate(a.created_at)} - {a.overall_assessment?.status || 'Unknown'}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1" htmlFor="analysis-b-select">
              Analysis B (after)
            </label>
            <select
              id="analysis-b-select"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              value={analysisIdB}
              onChange={(e) => setAnalysisIdB(e.target.value)}
              disabled={analyses.length === 0}
            >
              <option value="">--- select analysis B ---</option>
              {analyses.map((a) => (
                <option key={a.analysis_id} value={a.analysis_id}>
                  {formatDate(a.created_at)} - {a.overall_assessment?.status || 'Unknown'}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-4">
          <button
            id="run-comparison-button"
            type="button"
            onClick={runComparison}
            disabled={!analysisIdA || !analysisIdB || status === 'running'}
            className="primary-button disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Icon name={status === 'running' ? 'clock' : 'activity'} className="h-4 w-4" />
            {status === 'running' ? 'Comparing...' : 'Compare Analyses'}
          </button>
          {analyses.length === 0 && selectedPaperId && (
            <p className="text-sm text-slate-500">No saved analyses found for this paper.</p>
          )}
          {analyses.length > 0 && (
            <p className="text-sm text-slate-500">{analyses.length} saved {analyses.length === 1 ? 'analysis' : 'analyses'} available</p>
          )}
        </div>
      </section>

      {result && (
        <>
          <div className={`mt-8 rounded-xl border p-5 ${overallClasses[result.overall_result] || overallClasses.INSUFFICIENT_DATA}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider opacity-70">Overall classification</p>
                <p className="mt-1 text-2xl font-bold">{result.overall_result}</p>
              </div>
              <div className="text-right text-sm opacity-75">
                <p>A: {formatDate(result.analysis_a_created_at)}</p>
                <p>B: {formatDate(result.analysis_b_created_at)}</p>
              </div>
            </div>
            {result.improvement_summary?.message && (
              <p className="mt-3 text-sm opacity-80">{result.improvement_summary.message}</p>
            )}
          </div>

          {(result.improvement_summary?.overall_assessment_before || result.improvement_summary?.overall_assessment_after) && (
            <Section title="Overall Assessment">
              <div className="flex items-center gap-3 text-sm">
                <StatusBadge value={result.improvement_summary.overall_assessment_before || '---'} />
                <Arrow />
                <StatusBadge value={result.improvement_summary.overall_assessment_after || '---'} />
              </div>
            </Section>
          )}

          {result.changes?.length > 0 && (
            <Section title="Metric Changes">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-slate-400">
                    <th className="pb-2 pr-4">Field</th>
                    <th className="pb-2 pr-2">Before</th>
                    <th className="pb-2 px-2"></th>
                    <th className="pb-2 pl-2">After</th>
                    <th className="pb-2 pl-4">Direction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.changes.map((c) => (
                    <ChangeRow
                      key={c.field}
                      label={c.field.replace(/_/g, ' ')}
                      before={c.before}
                      after={c.after}
                      direction={c.direction}
                    />
                  ))}
                </tbody>
              </table>
            </Section>
          )}

          {!result.compliance_changes?.insufficient_data && (
            <Section title="Compliance Changes">
              <div className="grid gap-4 sm:grid-cols-3 text-center">
                <div className="rounded-lg bg-emerald-50 p-4">
                  <p className="text-2xl font-bold text-emerald-700">{result.compliance_changes.constraints_resolved_count}</p>
                  <p className="mt-1 text-xs font-medium text-emerald-600 uppercase tracking-wider">Resolved</p>
                </div>
                <div className="rounded-lg bg-red-50 p-4">
                  <p className="text-2xl font-bold text-red-700">{result.compliance_changes.newly_violated_count}</p>
                  <p className="mt-1 text-xs font-medium text-red-600 uppercase tracking-wider">New Violations</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-4">
                  <p className="text-2xl font-bold text-slate-700">{result.compliance_changes.unchanged?.length ?? 0}</p>
                  <p className="mt-1 text-xs font-medium text-slate-500 uppercase tracking-wider">Unchanged</p>
                </div>
              </div>

              {result.compliance_changes.resolved?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-emerald-600 mb-2">Resolved constraints</p>
                  <ul className="space-y-1">
                    {result.compliance_changes.resolved.map((c) => (
                      <li key={c.constraint_id} className="flex items-center gap-2 text-sm text-slate-700">
                        <span className="text-emerald-500">&#x2713;</span>
                        <span>{c.constraint_name || c.constraint_id}</span>
                        <span className="text-slate-400 text-xs">VIOLATED &#8594; SATISFIED</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.compliance_changes.newly_violated?.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-red-600 mb-2">New violations</p>
                  <ul className="space-y-1">
                    {result.compliance_changes.newly_violated.map((c) => (
                      <li key={c.constraint_id} className="flex items-center gap-2 text-sm text-slate-700">
                        <span className="text-red-500">&#x2717;</span>
                        <span>{c.constraint_name || c.constraint_id}</span>
                        <span className="text-slate-400 text-xs">SATISFIED &#8594; VIOLATED</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Section>
          )}

          {!result.logical_changes?.insufficient_data && result.logical_changes?.changed?.length > 0 && (
            <Section title="Logical Verification Changes">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-xs uppercase tracking-wider text-slate-400">
                    <th className="pb-2 pr-4">Check</th>
                    <th className="pb-2 pr-2">Before</th>
                    <th className="pb-2 px-2"></th>
                    <th className="pb-2 pl-2">After</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.logical_changes.changed.map((c) => (
                    <tr key={c.field} className="text-sm text-slate-700">
                      <td className="py-2 pr-4 font-medium text-slate-900 capitalize">{c.field.replace(/_/g, ' ')}</td>
                      <td className="py-2 pr-2"><StatusBadge value={c.before} /></td>
                      <td className="py-2 px-2 text-slate-400">&#8594;</td>
                      <td className="py-2 pl-2"><StatusBadge value={c.after} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>
          )}

          {result.structural_changes?.length > 0 && (
            <Section title="Structural Changes">
              <ul className="space-y-2">
                {result.structural_changes.map((c) => (
                  <li key={c.field} className="flex items-center gap-3 text-sm text-slate-700">
                    <span className="capitalize font-medium text-slate-900">{c.field}</span>
                    <span className="text-slate-400">{String(c.before)}</span>
                    <Arrow />
                    <span className="text-slate-700">{String(c.after)}</span>
                    <StatusBadge value={c.direction} />
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {!result.improvement_plan_changes?.insufficient_data && (
            <Section title="Improvement Plan Changes">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-sm font-medium text-slate-700">Plan status:</span>
                <StatusBadge value={result.improvement_plan_changes.before_status || 'N/A'} />
                <Arrow />
                <StatusBadge value={result.improvement_plan_changes.after_status || 'N/A'} />
              </div>
              {result.improvement_plan_changes.summary && (
                <p className="text-sm text-slate-600">{result.improvement_plan_changes.summary}</p>
              )}
              {result.improvement_plan_changes.before_actions?.length > 0 && (
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Before actions</p>
                    <ul className="space-y-1">
                      {result.improvement_plan_changes.before_actions.map((a) => (
                        <li key={a} className="text-sm text-slate-700 flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-400 shrink-0"></span>{a}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {result.improvement_plan_changes.after_actions?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">After actions</p>
                      <ul className="space-y-1">
                        {result.improvement_plan_changes.after_actions.map((a) => (
                          <li key={a} className="text-sm text-slate-700 flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 shrink-0"></span>{a}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Section>
          )}

          {(result.improvement_summary?.compliance_status_before || result.improvement_summary?.compliance_status_after) && (
            <Section title="Compliance Status">
              <div className="flex items-center gap-3 text-sm">
                <StatusBadge value={result.improvement_summary.compliance_status_before || '---'} />
                <Arrow />
                <StatusBadge value={result.improvement_summary.compliance_status_after || '---'} />
              </div>
            </Section>
          )}

          {result.overall_result === 'UNCHANGED' && result.changes?.length === 0 && (
            <Section title="Result">
              <p className="text-sm text-slate-600">No material differences were detected in the comparable stored fields.</p>
            </Section>
          )}

          {result.overall_result === 'INSUFFICIENT_DATA' && (
            <Section title="Result">
              <p className="text-sm text-slate-600">
                Insufficient comparable stored data is available. Both analyses must contain Module 8 results to produce a meaningful comparison.
              </p>
            </Section>
          )}
        </>
      )}
    </div>
  )
}
