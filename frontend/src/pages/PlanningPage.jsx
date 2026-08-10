import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { runImprovementPlanning } from '../services/api'

function readSessionItem(key) {
  try {
    const value = sessionStorage.getItem(key)
    return value ? JSON.parse(value) : null
  } catch {
    return null
  }
}

function stateFromCompliance(compliance) {
  if (!compliance?.variables) return {}
  return Object.fromEntries(Object.entries(compliance.variables)
    .filter(([, details]) => details.known)
    .map(([name, details]) => [name, details.value]))
}

function displayName(name) {
  return name.replace(/([a-z])([A-Z])/g, '$1 $2')
}

function statusClasses(status) {
  if (status === 'PLAN_FOUND' || status === 'NO_IMPROVEMENT_NEEDED') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (status === 'INCOMPLETE' || status === 'SEARCH_LIMIT_REACHED') return 'border-amber-200 bg-amber-50 text-amber-900'
  return 'border-rose-200 bg-rose-50 text-rose-900'
}

function StateGrid({ state, title, empty }) {
  const entries = Object.entries(state || {})
  return <section className="surface-card p-5 sm:p-6"><h2 className="font-semibold text-slate-900">{title}</h2>{entries.length ? <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{entries.map(([name, value]) => <div key={name} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{displayName(name)}</dt><dd className="mt-1 font-mono text-sm font-semibold text-slate-900">{String(value)}</dd></div>)}</dl> : <p className="mt-3 text-sm leading-6 text-slate-500">{empty}</p>}</section>
}

function ViolationList({ violations }) {
  return <section className="surface-card p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h2 className="font-semibold text-slate-900">Current Module 6 violations</h2><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{violations.length}</span></div>{violations.length ? <ul className="mt-4 space-y-3">{violations.map((item) => <li key={item.constraint_id} className="rounded-lg border border-rose-200 bg-rose-50 p-3"><p className="font-semibold text-rose-900">{item.constraint_name}</p><p className="mt-1 text-sm text-rose-800">Required: {item.expected} · Actual: {typeof item.actual === 'object' ? JSON.stringify(item.actual) : String(item.actual)}</p><p className="mt-2 text-xs leading-5 text-rose-800">{item.explanation}</p></li>)}</ul> : <p className="mt-3 text-sm leading-6 text-slate-500">No known violations are available yet. Generate a plan to run the generic Module 6 profile, or run a custom profile from Compliance first.</p>}</section>
}

function PlannedActions({ actions }) {
  if (!actions.length) return <p className="mt-4 text-sm text-slate-600">No hypothetical actions are needed or available for this result.</p>
  return <ol className="mt-5 space-y-3">{actions.map((action, index) => <li key={`${action.id}-${index}`} className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold text-slate-900">{index + 1}. {displayName(action.name)}</p><span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-indigo-800">Cost {action.cost}</span></div><p className="mt-2 text-sm leading-6 text-slate-700">{action.explanation}</p>{Object.keys(action.estimated_effect || {}).length > 0 && <p className="mt-2 font-mono text-xs text-indigo-800">Projected effect: {Object.entries(action.estimated_effect).map(([variable, effect]) => `${displayName(variable)} ${String(effect.from)} → ${String(effect.to)}`).join(' · ')}</p>}</li>)}</ol>
}

export default function PlanningPage() {
  const [knowledgeBase] = useState(() => readSessionItem('paperintel.knowledgeBase'))
  const [complianceResult] = useState(() => readSessionItem('paperintel.complianceResult'))
  const [method, setMethod] = useState('astar')
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const sourceCompliance = result?.module_6 || complianceResult
  const currentState = useMemo(() => result?.initial_state || stateFromCompliance(complianceResult), [complianceResult, result])
  const violations = sourceCompliance?.violations || sourceCompliance?.constraints?.violated || []

  const generatePlan = async () => {
    if (!knowledgeBase && !complianceResult) return
    setStatus('loading')
    setError('')
    try {
      setResult(await runImprovementPlanning({
        knowledgeBase,
        complianceResult,
        method,
      }))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'The improvement plan could not be generated.')
    } finally {
      setStatus('idle')
    }
  }

  return <div className="page-container py-12 sm:py-16"><div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Module 7 · Search-based improvement planning</p><h1 className="section-title mt-3">Plan a path toward compliance</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">Search hypothetical paper states to identify a low-cost sequence of planning actions. The source PDF and knowledge base are never changed.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-800"><Icon name="search" className="h-4 w-4" /> UCS + A* search</span></div>{!knowledgeBase && !complianceResult ? <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="shield" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">Run compliance analysis first</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Planning consumes a Module 6 compliance result. Build a knowledge base and run compliance analysis first so the planner has real paper variables, requirements, and violations.</p><Link to="/compliance" className="primary-button mt-6"><Icon name="shield" className="h-4 w-4" /> Open compliance analysis</Link></section> : <><section className="surface-card mt-8 p-5 sm:p-6"><div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div><p className="eyebrow">Planning input</p><h2 className="mt-1 text-xl font-semibold text-slate-900">{complianceResult ? 'Latest Module 6 compliance result' : knowledgeBase?.paper?.name || 'Current paper knowledge base'}</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">{complianceResult ? `Using ${complianceResult.profile?.name || 'the selected'} profile and its recorded violations.` : 'A fresh Generic Research Paper compliance result will be generated before planning.'}</p></div><div className="flex flex-col gap-3 sm:flex-row sm:items-end"><label className="text-sm font-medium text-slate-700">Search algorithm<select value={method} onChange={(event) => setMethod(event.target.value)} className="mt-1.5 block rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800"><option value="astar">A* Search</option><option value="ucs">Uniform-Cost Search</option></select></label><button type="button" onClick={generatePlan} disabled={status === 'loading'} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={status === 'loading' ? 'clock' : 'search'} className="h-4 w-4" />{status === 'loading' ? 'Searching...' : 'Generate improvement plan'}</button></div></div>{error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}</section><div className="mt-6 grid gap-6 xl:grid-cols-2"><StateGrid title="Current paper state" state={currentState} empty="No known Module 6 state values are available." /><ViolationList violations={violations} /></div>{result && <><section className={`mt-6 rounded-xl border p-5 sm:p-6 ${statusClasses(result.status)}`}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-medium">Planning outcome</p><h2 className="mt-1 text-2xl font-semibold">{result.status}</h2></div><span className="rounded-full bg-white/80 px-3 py-1.5 text-xs font-semibold">{result.algorithm}</span></div><p className="mt-3 max-w-3xl text-sm leading-6">{result.explanation}</p></section><section className="surface-card mt-6 p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Recommended plan</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Hypothetical improvement sequence</h2></div><span className="rounded-full bg-indigo-50 px-3 py-1.5 text-sm font-semibold text-indigo-800">Estimated total cost: {result.total_cost}</span></div><PlannedActions actions={result.actions} /></section><div className="mt-6 grid gap-6 xl:grid-cols-2"><StateGrid title="Projected hypothetical state" state={result.final_state} empty="No projected state is available." /><section className="surface-card p-5 sm:p-6"><h2 className="font-semibold text-slate-900">Search statistics</h2><dl className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="States explored" value={result.states_explored} /><Metric label="Plan depth" value={result.search_depth} /><Metric label="Actions available" value={result.available_actions?.length ?? 0} /></dl>{result.heuristic && <div className="mt-5 rounded-lg border border-indigo-100 bg-indigo-50 p-4"><p className="font-semibold text-indigo-900">Heuristic: {result.heuristic.name}</p><p className="mt-2 text-sm leading-6 text-indigo-900">{result.heuristic.description}</p></div>}</section></div><section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-950"><div className="flex gap-3"><Icon name="info" className="mt-0.5 h-5 w-5 shrink-0" /><div><h2 className="font-semibold">Hypothetical projected state — paper has not been modified</h2><p className="mt-1 text-sm leading-6">This plan predicts what the modeled state would be if the suggested editing tasks were successfully completed. It does not rewrite the PDF, generate paper content, or invent references.</p></div></div></section><details className="surface-card mt-6 p-5 sm:p-6"><summary className="cursor-pointer font-semibold text-slate-900">Expand detailed search trace ({result.trace?.length ?? 0} events)</summary><ol className="mt-5 max-h-96 space-y-2 overflow-auto pr-1">{result.trace?.map((event) => <li key={event.step} className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700"><div className="flex items-center gap-2"><span className="font-mono font-semibold text-indigo-700">{event.step}</span><span className="rounded-full bg-white px-2 py-0.5 font-mono font-semibold">{event.event}</span></div><p className="mt-2 font-mono">{Object.entries(event).filter(([key]) => !['step', 'event'].includes(key)).map(([key, value]) => `${key}=${typeof value === 'object' ? JSON.stringify(value) : String(value)}`).join(' · ') || 'Search event'}</p></li>)}</ol></details></>}</>}</div>
}

function Metric({ label, value }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 p-3"><dt className="text-xs font-medium text-slate-500">{label}</dt><dd className="mt-1 font-mono text-lg font-semibold text-slate-900">{value}</dd></div>
}
