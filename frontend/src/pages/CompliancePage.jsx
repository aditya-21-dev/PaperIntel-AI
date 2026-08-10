import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { runComplianceCsp } from '../services/api'

const CORE_SECTIONS = ['Introduction', 'Methodology', 'Results', 'Conclusion']

function readKnowledgeBase() {
  try {
    const stored = sessionStorage.getItem('paperintel.knowledgeBase')
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function statusClasses(status) {
  if (status === 'COMPLIANT') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (status === 'NON_COMPLIANT' || status === 'NO_SOLUTION') return 'border-rose-200 bg-rose-50 text-rose-900'
  if (status === 'INCOMPLETE') return 'border-amber-200 bg-amber-50 text-amber-900'
  return 'border-slate-200 bg-slate-50 text-slate-800'
}

function constraintClasses(group) {
  if (group === 'violated') return 'border-rose-200 bg-rose-50'
  if (group === 'unknown') return 'border-amber-200 bg-amber-50'
  return 'border-emerald-200 bg-emerald-50'
}

function formatValue(value) {
  if (value === null || value === undefined) return 'Unknown'
  if (typeof value === 'object') return Object.entries(value).map(([name, item]) => `${name}: ${item ?? 'Unknown'}`).join(' | ')
  return String(value)
}

function ConstraintList({ title, group, constraints }) {
  return <section className="surface-card p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><h2 className="font-semibold text-slate-900">{title}</h2><span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-700">{constraints.length}</span></div>{constraints.length ? <ul className="mt-4 space-y-3">{constraints.map((item) => <li key={item.constraint_id} className={`rounded-xl border p-4 ${constraintClasses(group)}`}><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold text-slate-900">{item.constraint_name}</p><span className="rounded-full bg-white/80 px-2 py-1 font-mono text-xs font-semibold text-slate-700">{item.constraint_id} · {item.severity}</span></div><dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2"><div><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Required</dt><dd className="mt-0.5 font-mono text-slate-800">{item.expected}</dd></div><div><dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Actual</dt><dd className="mt-0.5 font-mono text-slate-800">{formatValue(item.actual)}</dd></div></dl>{item.difference !== null && item.difference !== undefined && <p className="mt-2 text-sm font-medium text-rose-800">Difference: {item.difference > 0 ? '+' : ''}{item.difference}</p>}<p className="mt-3 text-sm leading-6 text-slate-700">{item.explanation}</p>{item.evidence?.length > 0 && <p className="mt-2 text-xs text-slate-600">Evidence: {item.evidence.map((evidence) => [evidence.source_module, evidence.source_field, evidence.section].filter(Boolean).join(' · ')).join(' | ')}</p>}</li>)}</ul> : <p className="mt-4 text-sm text-slate-500">None.</p>}</section>
}

function SolverMetrics({ result }) {
  if (!result?.solver) return null
  const metrics = [
    ['Solutions', result.solver.solutions_found],
    ['Constraint checks', result.solver.constraint_checks],
    ['Propagation steps', result.solver.propagation_steps],
    ['Backtracks', result.solver.backtracking_steps],
    ['Search nodes', result.solver.nodes_visited],
  ]
  return <section className="surface-card mt-6 p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">CSP solver</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Search and propagation record</h2><p className="mt-1 text-sm leading-6 text-slate-600">Requirement consistency is solved before the fixed paper assignment. The totals include both phases.</p></div><span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${result.requirements_consistent ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-800'}`}>{result.requirements_consistent ? 'Requirements consistent' : 'Requirements inconsistent'}</span></div><div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">{metrics.map(([label, value]) => <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-1 font-mono text-lg font-semibold text-slate-900">{value}</p></div>)}</div>{result.solver.conflicts?.length > 0 && <div className="mt-5 rounded-lg border border-rose-200 bg-rose-50 p-4"><p className="font-semibold text-rose-900">Solver conflicts</p><ul className="mt-2 space-y-1 text-sm text-rose-800">{result.solver.conflicts.map((conflict, index) => <li key={`${conflict.type}-${index}`}>{conflict.type.replaceAll('_', ' ')}{conflict.constraint_id ? ` · ${conflict.constraint_id}` : ''}{conflict.variable ? ` · ${conflict.variable}` : ''}</li>)}</ul></div>}<details className="mt-5 rounded-lg border border-slate-200 bg-white p-4"><summary className="cursor-pointer font-semibold text-slate-900">Expand detailed CSP trace ({result.solver_trace?.length ?? 0} events)</summary><ol className="mt-4 max-h-96 space-y-2 overflow-auto pr-1">{result.solver_trace?.map((event) => <li key={`${event.phase}-${event.step}`} className="rounded-lg bg-slate-50 p-3 text-xs text-slate-700"><div className="flex flex-wrap items-center gap-2"><span className="font-mono font-semibold text-indigo-700">{event.step}</span><span className="rounded-full bg-white px-2 py-0.5 font-mono font-semibold">{event.event_type}</span><span className="text-slate-500">{event.phase.replaceAll('_', ' ')}</span></div><p className="mt-2 font-mono">{Object.entries(event).filter(([key]) => !['step', 'phase', 'phase_step', 'event', 'event_type'].includes(key)).map(([key, value]) => `${key}=${formatValue(value)}`).join(' · ') || 'Solver event'}</p></li>)}</ol></details></section>
}

export default function CompliancePage() {
  const [knowledgeBase] = useState(readKnowledgeBase)
  const [profileType, setProfileType] = useState('generic')
  const [custom, setCustom] = useState({
    venue: 'Custom Venue', maxPages: '6', maxAbstractWords: '250', minKeywords: '1', minReferences: '15',
    abstractRequired: true, keywordsRequired: true, coreSectionsRequired: true,
  })
  const [result, setResult] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const selectedProfile = useMemo(() => {
    if (profileType === 'generic') return { profile_id: 'generic_research_paper', requirements: {} }
    const requirements = {}
    const numericRequirements = [
      ['max_pages', custom.maxPages], ['max_abstract_words', custom.maxAbstractWords],
      ['min_keywords', custom.minKeywords], ['min_references', custom.minReferences],
    ]
    numericRequirements.forEach(([name, rawValue]) => {
      if (rawValue !== '') requirements[name] = Number(rawValue)
    })
    if (custom.abstractRequired) requirements.abstract_required = true
    if (custom.keywordsRequired) requirements.keywords_required = true
    if (custom.coreSectionsRequired) requirements.required_sections = CORE_SECTIONS
    return { profile_id: 'custom', venue: custom.venue.trim() || 'Custom Venue', requirements }
  }, [custom, profileType])

  const updateCustom = (field, value) => setCustom((current) => ({ ...current, [field]: value }))

  const analyze = async () => {
    if (!knowledgeBase) return
    setStatus('loading')
    setError('')
    try {
      const response = await runComplianceCsp(knowledgeBase, selectedProfile)
      setResult(response)
      try {
        sessionStorage.setItem('paperintel.complianceResult', JSON.stringify(response))
      } catch {
        // Planning can still request a fresh generic compliance result if storage is unavailable.
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Compliance analysis could not be completed.')
    } finally {
      setStatus('idle')
    }
  }

  return <div className="page-container py-12 sm:py-16"><div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Module 6 · Constraint satisfaction</p><h1 className="section-title mt-3">Publication compliance analysis</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">Map the existing Module 3 paper knowledge base into finite CSP variables, propagate venue constraints, and search for compliant assignments. Missing evidence remains unknown rather than becoming a violation.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-800"><Icon name="target" className="h-4 w-4" /> Variables + domains + constraints</span></div>{!knowledgeBase ? <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="brain" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">Build a knowledge base first</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Compliance consumes the already extracted Module 3 knowledge base. It never reparses a PDF or duplicates the knowledge-engineering step.</p><Link to="/knowledge-base" className="primary-button mt-6"><Icon name="brain" className="h-4 w-4" /> Open knowledge base</Link></section> : <><section className="surface-card mt-8 p-5 sm:p-6"><div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div><p className="eyebrow">Paper selected</p><h2 className="mt-1 text-xl font-semibold text-slate-900">{knowledgeBase.paper?.name || knowledgeBase.paper?.id}</h2><p className="mt-1 text-sm text-slate-500">{knowledgeBase.paper?.attributes?.filename || 'Module 3 knowledge base'} · {knowledgeBase.paper?.attributes?.page_count ?? 'Unknown'} pages</p></div><button type="button" onClick={analyze} disabled={status === 'loading'} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={status === 'loading' ? 'clock' : 'shield'} className="h-4 w-4" />{status === 'loading' ? 'Analyzing...' : 'Run compliance analysis'}</button></div><fieldset className="mt-6 border-t border-slate-200 pt-5"><legend className="text-sm font-semibold text-slate-900">Requirement profile</legend><div className="mt-3 flex flex-col gap-3 sm:flex-row"><label className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${profileType === 'generic' ? 'border-indigo-300 bg-indigo-50' : 'border-slate-200'}`}><input type="radio" name="profile" checked={profileType === 'generic'} onChange={() => setProfileType('generic')} /> <span><span className="block font-semibold text-slate-900">Generic Research Paper</span><span className="text-slate-600">Controlled baseline requirements</span></span></label><label className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm ${profileType === 'custom' ? 'border-indigo-300 bg-indigo-50' : 'border-slate-200'}`}><input type="radio" name="profile" checked={profileType === 'custom'} onChange={() => setProfileType('custom')} /> <span><span className="block font-semibold text-slate-900">Custom requirement profile</span><span className="text-slate-600">Supply a target venue's constraints</span></span></label></div></fieldset>{profileType === 'custom' && <div className="mt-5 grid gap-4 border-t border-slate-200 pt-5 sm:grid-cols-2 xl:grid-cols-5"><label className="text-sm font-medium text-slate-700">Venue<input value={custom.venue} onChange={(event) => updateCustom('venue', event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label><NumberInput label="Maximum pages" value={custom.maxPages} onChange={(value) => updateCustom('maxPages', value)} /><NumberInput label="Maximum abstract words" value={custom.maxAbstractWords} onChange={(value) => updateCustom('maxAbstractWords', value)} /><NumberInput label="Minimum keywords" value={custom.minKeywords} onChange={(value) => updateCustom('minKeywords', value)} /><NumberInput label="Minimum references" value={custom.minReferences} onChange={(value) => updateCustom('minReferences', value)} /><CheckInput label="Abstract required" checked={custom.abstractRequired} onChange={(value) => updateCustom('abstractRequired', value)} /><CheckInput label="Keywords required" checked={custom.keywordsRequired} onChange={(value) => updateCustom('keywordsRequired', value)} /><CheckInput label="Require core sections" checked={custom.coreSectionsRequired} onChange={(value) => updateCustom('coreSectionsRequired', value)} /></div>}{error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}</section>{result && <><section className={`mt-6 rounded-xl border p-5 sm:p-6 ${statusClasses(result.status)}`}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-medium">Overall compliance</p><h2 className="mt-1 text-2xl font-semibold">{result.status}</h2></div><span className="rounded-full bg-white/80 px-3 py-1.5 text-xs font-semibold">{result.profile.name}</span></div><p className="mt-3 max-w-3xl text-sm leading-6">{result.status === 'NO_SOLUTION' ? 'The publication requirements conflict with each other, so no paper can satisfy them together.' : result.status === 'INCOMPLETE' ? 'No confirmed violation was found, but at least one required paper value is unavailable.' : result.status === 'NON_COMPLIANT' ? 'One or more observed paper values definitely violate the selected requirements.' : 'All selected requirements are satisfied by the observed paper values.'}</p></section><div className="mt-6 grid gap-6 xl:grid-cols-3"><ConstraintList title="Violated constraints" group="violated" constraints={result.constraints.violated} /><ConstraintList title="Satisfied constraints" group="satisfied" constraints={result.constraints.satisfied} /><ConstraintList title="Unknown constraints" group="unknown" constraints={result.constraints.unknown} /></div><SolverMetrics result={result} /></>}</>}</div>
}

function NumberInput({ label, value, onChange }) {
  return <label className="text-sm font-medium text-slate-700">{label}<input type="number" min="0" value={value} onChange={(event) => onChange(event.target.value)} className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" /></label>
}

function CheckInput({ label, checked, onChange }) {
  return <label className="flex items-center gap-2 text-sm font-medium text-slate-700"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /> {label}</label>
}
