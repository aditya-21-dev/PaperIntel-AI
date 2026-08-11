import { useState } from 'react'
import Icon from '../components/Icon'
import { runSystemEvaluation } from '../services/api'

function value(value) {
  if (value === null || value === undefined) return 'Not available'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')
  return String(value)
}

function primaryMetric(metrics) {
  if (!metrics) return '—'
  for (const key of ['accuracy', 'f1', 'success_rate', 'precision', 'recall']) {
    if (metrics[key] !== undefined) return `${key.replace('_', ' ')}: ${value(metrics[key])}`
  }
  if (metrics.classification?.accuracy !== undefined) return `accuracy: ${value(metrics.classification.accuracy)}`
  if (metrics.by_method?.astar?.plan_success_rate !== undefined) return `A* plan success: ${value(metrics.by_method.astar.plan_success_rate)}`
  return 'Measured details available'
}

function StatusBadge({ status }) {
  const classes = status === 'MEASURED'
    ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
    : 'bg-amber-50 text-amber-800 ring-amber-200'
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${classes}`}>{status === 'MEASURED' ? 'MEASURED' : 'NOT EVALUATED'}</span>
}

function ModuleMetrics({ module }) {
  const metrics = module.metrics || {}
  const hasPlanningMetrics = metrics.by_method
  return <details className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
    <summary className="cursor-pointer text-sm font-semibold text-slate-800">View measured details</summary>
    {module.status === 'NOT_EVALUATED' ? <p className="mt-3 text-sm leading-6 text-amber-900">{module.reason}</p> : <div className="mt-4 space-y-4">
      <pre className="max-h-72 overflow-auto rounded bg-white p-3 text-xs leading-5 text-slate-700">{JSON.stringify(metrics, null, 2)}</pre>
      {hasPlanningMetrics && <div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="text-xs uppercase tracking-wide text-slate-500"><tr><th className="pb-2 pr-4">Case</th><th className="pb-2 pr-4">UCS</th><th className="pb-2">A*</th></tr></thead><tbody>{metrics.comparisons?.map((item) => <tr key={item.case_id} className="border-t border-slate-200"><td className="py-2 pr-4 font-mono text-xs">{item.case_id}</td><td className="py-2 pr-4 text-xs">states {item.ucs.states_explored} · cost {item.ucs.path_cost} · {value(item.ucs.execution_time_ms)} ms</td><td className="py-2 text-xs">states {item.astar.states_explored} · cost {item.astar.path_cost} · {value(item.astar.execution_time_ms)} ms</td></tr>)}</tbody></table></div>}
    </div>}
  </details>
}

export default function EvaluationPage() {
  const [report, setReport] = useState(null)
  const [state, setState] = useState('idle')
  const [error, setError] = useState('')

  const runEvaluation = async () => {
    setState('loading')
    setError('')
    try {
      setReport(await runSystemEvaluation())
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'The system evaluation could not be completed.')
    } finally {
      setState('idle')
    }
  }

  return <div className="page-container py-12 sm:py-16">
    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div><p className="eyebrow">Module 9 · System evaluation and benchmarking</p><h1 className="section-title mt-3">Measure PaperIntel AI</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">Run maintained deterministic benchmark cases against the existing pipeline. Results are measured at runtime; no model is trained and no paper is changed.</p></div>
      <button type="button" onClick={runEvaluation} disabled={state === 'loading'} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={state === 'loading' ? 'clock' : 'chart'} className="h-4 w-4" />{state === 'loading' ? 'Running benchmarks…' : 'Run system evaluation'}</button>
    </div>

    {error && <div className="mt-8 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}

    {!report && !error && <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="chart" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">No benchmark report yet</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">The run includes PDF extraction, knowledge representation, reasoning, logic, compliance, search planning, and end-to-end integrated analysis.</p></section>}

    {report && <><section className="surface-card mt-8 p-5 sm:p-6"><div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Benchmark cases" value={report.summary?.case_count} /><Metric label="Passed" value={`${report.summary?.passed_cases}/${report.summary?.case_count}`} /><Metric label="End-to-end success" value={report.summary?.end_to_end_success_rate} /><Metric label="API response" value={`${value(report.api_response_time_ms)} ms`} /></div><p className="mt-5 text-sm leading-6 text-slate-600">{report.benchmark?.description}</p></section>
      <section className="surface-card mt-6 overflow-hidden"><div className="border-b border-slate-200 p-5 sm:p-6"><p className="eyebrow">Evaluation report</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Module results</h2></div><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3 sm:px-6">Module</th><th className="px-5 py-3">Status</th><th className="px-5 py-3">Metric</th><th className="px-5 py-3">Cases</th><th className="px-5 py-3 sm:px-6">Execution</th></tr></thead><tbody>{report.modules?.map((module) => <tr key={module.id} className="border-t border-slate-200 align-top"><td className="px-5 py-4 font-semibold text-slate-900 sm:px-6">{module.module}<p className="mt-1 max-w-sm text-xs font-normal leading-5 text-slate-500">{module.reason}</p></td><td className="px-5 py-4"><StatusBadge status={module.status} /></td><td className="px-5 py-4 text-slate-700">{primaryMetric(module.metrics)}</td><td className="px-5 py-4 font-mono text-xs text-slate-700">{module.status === 'MEASURED' ? `${module.passed_cases}/${module.case_count} pass` : '—'}</td><td className="px-5 py-4 font-mono text-xs text-slate-700 sm:px-6">{module.execution_time_ms === null ? '—' : `${value(module.execution_time_ms)} ms`}</td></tr>)}</tbody></table></div></section>
      <section className="mt-6 grid gap-5 xl:grid-cols-2">{report.modules?.map((module) => <article key={`${module.id}-details`} className="surface-card p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold text-slate-900">{module.module}</h2><StatusBadge status={module.status} /></div><p className="mt-2 text-sm text-slate-600">{module.status === 'MEASURED' ? `${module.passed_cases} of ${module.case_count} maintained cases passed.` : module.reason}</p><ModuleMetrics module={module} /></article>)}</section>
    </>}
  </div>
}

function Metric({ label, value: metricValue }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 font-mono text-lg font-semibold text-slate-900">{value(metricValue)}</p></div>
}
