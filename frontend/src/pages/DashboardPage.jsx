import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { runIntegratedAnalysis } from '../services/api'

function readSessionItem(key) {
  try {
    const value = sessionStorage.getItem(key)
    return value ? JSON.parse(value) : null
  } catch {
    return null
  }
}

function statusClasses(status) {
  if (status === 'READY' || status === 'COMPLIANT' || status === 'PLAN_FOUND' || status === 'NO_IMPROVEMENT_NEEDED') return 'border-emerald-200 bg-emerald-50 text-emerald-950'
  if (status === 'INCOMPLETE' || status === 'PARTIAL_ANALYSIS' || status === 'SEARCH_LIMIT_REACHED') return 'border-amber-200 bg-amber-50 text-amber-950'
  return 'border-rose-200 bg-rose-50 text-rose-950'
}

function displayName(value) {
  return String(value || 'Unknown').replace(/([a-z])([A-Z])/g, '$1 $2')
}

function ModuleStatus({ item }) {
  const complete = item.status === 'COMPLETE'
  const failed = item.status === 'FAILED'
  return <li className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm"><span className="font-medium text-slate-900">{item.module}</span><span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${complete ? 'bg-emerald-100 text-emerald-800' : failed ? 'bg-rose-100 text-rose-800' : 'bg-slate-200 text-slate-700'}`}><Icon name={complete ? 'circleCheck' : failed ? 'warning' : 'clock'} className="h-3.5 w-3.5" />{complete ? `Complete${item.result_status && item.result_status !== 'COMPLETE' ? ` · ${item.result_status}` : ''}` : failed ? 'Failed' : 'Not run'}</span></li>
}

function FactList({ facts }) {
  if (!facts?.length) return <p className="mt-3 text-sm text-slate-500">No structural facts are available.</p>
  return <ul className="mt-4 grid gap-2 sm:grid-cols-2">{facts.map((fact) => <li key={fact.predicate} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm"><Icon name={fact.value ? 'circleCheck' : 'warning'} className={`h-4 w-4 shrink-0 ${fact.value ? 'text-emerald-600' : 'text-amber-600'}`} /><span className="font-medium text-slate-800">{displayName(fact.predicate.replace('PaperHas', ''))}</span><span className="ml-auto text-xs text-slate-500">{String(fact.value)}</span></li>)}</ul>
}

function ConstraintList({ title, constraints, tone }) {
  const classes = { emerald: 'border-emerald-200 bg-emerald-50', rose: 'border-rose-200 bg-rose-50', amber: 'border-amber-200 bg-amber-50' }
  if (!constraints?.length) return <p className="mt-3 text-sm text-slate-500">No {title.toLowerCase()}.</p>
  return <ul className="mt-3 space-y-2">{constraints.map((constraint) => <li key={constraint.constraint_id} className={`rounded-lg border p-3 text-sm ${classes[tone]}`}><p className="font-semibold text-slate-900">{displayName(constraint.constraint_name)}</p><p className="mt-1 text-slate-700">Required: {String(constraint.expected)} · Actual: {typeof constraint.actual === 'object' ? JSON.stringify(constraint.actual) : String(constraint.actual)}</p><p className="mt-1 text-xs leading-5 text-slate-600">{constraint.explanation}</p></li>)}</ul>
}

function TracePanel({ title, items }) {
  return <details className="surface-card p-5"><summary className="cursor-pointer font-semibold text-slate-900">{title} <span className="font-normal text-slate-500">({items?.length ?? 0})</span></summary>{items?.length ? <ol className="mt-4 max-h-80 space-y-2 overflow-auto pr-1">{items.map((item, index) => <li key={`${item.step || index}-${item.event || item.rule_id || title}`} className="rounded-lg bg-slate-50 p-3 font-mono text-xs leading-5 text-slate-700">{JSON.stringify(item)}</li>)}</ol> : <p className="mt-3 text-sm text-slate-500">No trace events were recorded.</p>}</details>
}

function EvidenceList({ evidence }) {
  if (!evidence?.length) return <p className="mt-3 text-sm text-slate-500">No evidence was retained.</p>
  return <ul className="mt-4 space-y-3">{evidence.map((item, index) => <li key={`${item.source_module}-${item.finding}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-sm font-semibold text-slate-900">{displayName(item.finding)}</p><span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-indigo-700">{item.source_module}</span></div>{item.source_constraint && <p className="mt-2 font-mono text-xs text-slate-600">Constraint: {item.source_constraint}</p>}<pre className="mt-2 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-5 text-slate-600">{JSON.stringify(item.evidence || { verification: item.verification, status: item.status }, null, 2)}</pre></li>)}</ul>
}

export default function DashboardPage() {
  const [paper] = useState(() => readSessionItem('paperintel.structuredDocument'))
  const [paperId, setPaperId] = useState(() => readSessionItem('paperintel.persistedPaperId'))
  const [method, setMethod] = useState('astar')
  const [result, setResult] = useState(() => readSessionItem('paperintel.integratedAnalysis'))
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const runAnalysis = async () => {
    if (!paper) return
    setStatus('loading')
    setError('')
    try {
      const response = await runIntegratedAnalysis({ paper, options: { planning_method: method }, paperId })
      setResult(response)
      try {
        sessionStorage.setItem('paperintel.integratedAnalysis', JSON.stringify(response))
        if (response.persistence?.status === 'SAVED' && response.persistence.paper_id) {
          setPaperId(response.persistence.paper_id)
          sessionStorage.setItem('paperintel.persistedPaperId', JSON.stringify(response.persistence.paper_id))
        }
      } catch {
        // The report remains available in this page session if browser storage is unavailable.
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Integrated analysis could not be completed.')
    } finally {
      setStatus('idle')
    }
  }

  if (!paper && !result) return <div className="page-container py-12 sm:py-16"><div><p className="eyebrow">Module 8 · Integrated pipeline</p><h1 className="section-title mt-3">PaperIntel AI analysis</h1><p className="mt-3 max-w-2xl leading-7 text-slate-600">This dashboard combines the existing knowledge, reasoning, logic, compliance, and planning modules. It consumes the structured paper already produced by Module 2 and does not parse a PDF again.</p></div><section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="fileSearch" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">Analyze a paper first</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Upload and process a PDF to create the structured paper that the integrated analysis needs.</p><Link to="/analyze" className="primary-button mt-6"><Icon name="upload" className="h-4 w-4" /> Analyze a paper</Link></section></div>

  const assessment = result?.overall_assessment
  const compliance = result?.compliance_analysis
  const plan = result?.improvement_plan
  const logical = result?.logical_verification
  const traces = result?.report?.reasoning_trace

  return <div className="page-container py-12 sm:py-16"><div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div><p className="eyebrow">Module 8 · Integrated pipeline</p><h1 className="section-title mt-3">PaperIntel AI analysis</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">One deterministic, explainable report built from Modules 3–7. It keeps their evidence and traces, and it never changes the source paper.</p></div><div className="flex flex-col gap-3 sm:flex-row sm:items-end"><label className="text-sm font-medium text-slate-700">Planning algorithm<select value={method} onChange={(event) => setMethod(event.target.value)} className="mt-1.5 block rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800"><option value="astar">A* Search</option><option value="ucs">Uniform-Cost Search</option></select></label><button type="button" onClick={runAnalysis} disabled={!paper || status === 'loading'} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={status === 'loading' ? 'clock' : 'activity'} className="h-4 w-4" />{status === 'loading' ? 'Running analysis…' : result ? 'Run again' : 'Run integrated analysis'}</button></div></div>
    <section className="surface-card mt-8 p-5 sm:p-6"><div className="grid gap-5 sm:grid-cols-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Paper</p><p className="mt-2 font-semibold text-slate-900">{paper?.metadata?.title || paper?.document?.filename || result?.paper?.name || result?.paper?.filename || 'Structured paper'}</p></div><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pages</p><p className="mt-2 font-semibold text-slate-900">{paper?.document?.page_count ?? result?.paper?.page_count ?? 'Unknown'}</p></div><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Requirements</p><p className="mt-2 font-semibold text-slate-900">{compliance?.profile?.name || 'Generic Research Paper'}</p></div></div>{result?.persistence && <div className={`mt-5 rounded-lg border p-4 text-sm ${result.persistence.status === 'SAVED' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : 'border-amber-200 bg-amber-50 text-amber-900'}`}><span className="font-semibold">Analysis history: </span>{result.persistence.status === 'SAVED' ? 'Saved to MongoDB.' : result.persistence.message}</div>}{error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}</section>
    {result && <><section className={`mt-6 rounded-xl border p-5 sm:p-6 ${statusClasses(assessment?.status || result.analysis_status)}`}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-medium">Overall status</p><h2 className="mt-1 text-2xl font-semibold">{assessment?.status || result.analysis_status}</h2></div><span className="rounded-full bg-white/80 px-3 py-1.5 text-xs font-semibold">{result.success ? 'Complete analysis' : 'Partial analysis'}</span></div><p className="mt-3 max-w-3xl text-sm leading-6">{assessment?.meaning || result.error?.message}</p>{assessment?.reasons?.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6">{assessment.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}</section>
      {result.error && <section className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-950"><div className="flex gap-3"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><div><h2 className="font-semibold">{result.failed_module} failed</h2><p className="mt-1 text-sm leading-6">{result.error.message}. Later modules were not run, so this is not presented as a complete assessment.</p></div></div></section>}
      <section className="mt-6 grid gap-6 xl:grid-cols-2"><article className="surface-card p-5 sm:p-6"><p className="eyebrow">Structural analysis</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Extracted paper structure</h2><FactList facts={result.knowledge_analysis?.important_facts} /></article><article className="surface-card p-5 sm:p-6"><p className="eyebrow">Module status</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Pipeline execution</h2><ul className="mt-4 space-y-2">{result.module_statuses?.map((item) => <ModuleStatus key={item.id} item={item} />)}</ul></article></section>
      {logical && <section className="surface-card mt-6 p-5 sm:p-6"><p className="eyebrow">Logical verification</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Query and consistency results</h2><div className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="Resolution" value={logical.resolution?.status} /><Metric label="Model checking" value={logical.model_checking?.status} /><Metric label="Consistency" value={logical.consistency?.status} /></div><p className="mt-4 text-sm leading-6 text-slate-600">{logical.resolution?.explanation}</p></section>}
      {compliance && <section className="mt-6"><div><p className="eyebrow">Publication compliance</p><h2 className="mt-1 text-xl font-semibold text-slate-900">{compliance.status}</h2></div><div className="mt-4 grid gap-5 xl:grid-cols-3"><article className="surface-card p-5"><h3 className="font-semibold text-slate-900">Violated constraints</h3><ConstraintList title="Violations" constraints={compliance.constraints?.violated} tone="rose" /></article><article className="surface-card p-5"><h3 className="font-semibold text-slate-900">Satisfied constraints</h3><ConstraintList title="Satisfied constraints" constraints={compliance.constraints?.satisfied} tone="emerald" /></article><article className="surface-card p-5"><h3 className="font-semibold text-slate-900">Unknown constraints</h3><ConstraintList title="Unknown constraints" constraints={compliance.constraints?.unknown} tone="amber" /></article></div></section>}
      {plan && <section className="surface-card mt-6 p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">Recommended improvement plan</p><h2 className="mt-1 text-xl font-semibold text-slate-900">{plan.status} · {plan.algorithm}</h2></div><span className="rounded-full bg-indigo-50 px-3 py-1.5 text-sm font-semibold text-indigo-800">Total cost: {plan.total_cost}</span></div>{plan.actions?.length ? <ol className="mt-5 space-y-3">{plan.actions.map((action, index) => <li key={`${action.id}-${index}`} className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-4"><p className="font-semibold text-slate-900">{index + 1}. {displayName(action.name)}</p><p className="mt-1 text-sm leading-6 text-slate-700">{action.explanation}</p></li>)}</ol> : <p className="mt-4 text-sm leading-6 text-slate-600">{plan.explanation}</p>}<div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><span className="font-semibold">Projected state notice: </span>The projected state is hypothetical. The paper has not been modified.</div></section>}
      {result.cross_module_findings?.length > 0 && <section className="surface-card mt-6 p-5 sm:p-6"><p className="eyebrow">Cross-module analysis</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Correlated conclusions</h2><ul className="mt-4 space-y-3">{result.cross_module_findings.map((finding, index) => <li key={`${finding.finding}-${index}`} className="rounded-lg border border-slate-200 bg-slate-50 p-4"><p className="font-semibold text-slate-900">{finding.finding}</p><p className="mt-1 text-sm leading-6 text-slate-700">{finding.explanation}</p><p className="mt-2 text-xs font-semibold text-indigo-700">{finding.source_modules?.join(' + ')}</p>{finding.recommended_actions?.length > 0 && <p className="mt-2 text-sm text-slate-700">Recommended: {finding.recommended_actions.map((action) => displayName(action.name)).join(', ')}</p>}</li>)}</ul></section>}
      {result.cross_module_inconsistencies?.length > 0 && <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-950"><h2 className="font-semibold">Cross-module data inconsistencies</h2><ul className="mt-3 space-y-2 text-sm">{result.cross_module_inconsistencies.map((item) => <li key={item.affected_field}>{item.explanation} Severity: {item.severity}.</li>)}</ul></section>}
      <section className="surface-card mt-6 p-5 sm:p-6"><p className="eyebrow">Evidence</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Source provenance</h2><EvidenceList evidence={result.evidence} /></section>
      <section className="mt-6 grid gap-5 lg:grid-cols-2"><TracePanel title="Knowledge Trace" items={result.knowledge_analysis?.knowledge_trace?.relationships} /><TracePanel title="Reasoning Trace" items={traces?.forward} /><TracePanel title="Logical Proof" items={traces?.logical_proof} /><TracePanel title="Compliance Constraints" items={traces?.compliance_constraints} /><TracePanel title="Search Trace" items={traces?.search_trace} /></section>
    </>}
  </div>
}

function Metric({ label, value }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 p-3"><p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p><p className="mt-1 font-mono text-sm font-semibold text-slate-900">{value || 'Unavailable'}</p></div>
}
