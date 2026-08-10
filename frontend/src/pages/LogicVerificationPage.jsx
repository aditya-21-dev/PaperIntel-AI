import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { checkLogicConsistency, runLogicModelCheck, runResolutionProof } from '../services/api'

const QUERY_SUGGESTIONS = [
  'CoreStructureComplete',
  'HasMajorStructuralComponents',
  'HasReferenceSection',
  'HasAtLeastOneFigure',
  'HasAtLeastOneTable',
  'PaperHasAbstract',
  'PaperHasIntroduction',
  'PaperHasMethodology',
  'PaperHasResults',
  'PaperHasConclusion',
  'PaperHasReferences',
]

function readKnowledgeBase() {
  try {
    const stored = sessionStorage.getItem('paperintel.knowledgeBase')
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function statusClasses(status) {
  if (status === 'ENTAILED') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (status === 'CONTRADICTED' || status === 'INCONSISTENT') return 'border-rose-200 bg-rose-50 text-rose-900'
  if (status === 'UNKNOWN') return 'border-amber-200 bg-amber-50 text-amber-900'
  return 'border-slate-200 bg-slate-50 text-slate-800'
}

function ResultCard({ title, result, children }) {
  if (!result) return null
  return <section className={`rounded-xl border p-5 ${statusClasses(result.status)}`}><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{title}</h2><span className="rounded-full bg-white/70 px-2.5 py-1 font-mono text-xs font-semibold">{result.status || (result.consistent ? 'CONSISTENT' : 'INCONSISTENT')}</span></div>{result.error && <p className="mt-3 text-sm leading-6">{result.error}</p>}{result.explanation && <p className="mt-3 text-sm leading-6">{result.explanation}</p>}{children}</section>
}

function ProofTrace({ proofSteps }) {
  if (!proofSteps?.length) return <p className="mt-4 text-sm text-slate-600">No derived resolution clauses were needed for this result.</p>
  return <ol className="mt-4 space-y-3">{proofSteps.map((step) => <li key={step.step} className="rounded-lg border border-slate-200 bg-white/70 p-3 text-xs text-slate-700"><p className="font-semibold text-indigo-800">Step {step.step} · resolve {step.resolved_literal}</p><p className="mt-2 font-mono">({step.clause_a.map((literal) => literal.notation).join(' OR ')}) + ({step.clause_b.map((literal) => literal.notation).join(' OR ')})</p><p className="mt-2 font-mono font-semibold">⇒ {step.result_notation}</p></li>)}</ol>
}

function ModelDetails({ result }) {
  if (!result) return null
  return <div className="mt-5 grid gap-3 sm:grid-cols-3"><Metric label="Models checked" value={result.models_checked ?? '—'} /><Metric label="KB-satisfying models" value={result.models_satisfying_kb ?? '—'} /><Metric label="Symbols" value={result.symbols?.length ?? '—'} /></div>
}

function Metric({ label, value }) {
  return <div className="rounded-lg border border-slate-200 bg-white/70 p-3"><p className="text-xs font-medium text-slate-500">{label}</p><p className="mt-1 font-mono text-lg font-semibold text-slate-900">{value}</p></div>
}

function FactList({ knowledgeBase }) {
  return <section className="surface-card mt-8 p-5 sm:p-6"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="list" className="h-4 w-4" /></span><div><h2 className="font-semibold text-slate-900">Logical knowledge base</h2><p className="text-sm text-slate-500">Module 3 facts are retained; Module 4 conclusions are added when verification runs.</p></div></div><div className="mt-5 max-h-64 overflow-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-2 py-2">Proposition</th><th className="px-2 py-2">State</th></tr></thead><tbody>{knowledgeBase.propositional_facts.map((fact) => <tr key={fact.predicate} className="border-b border-slate-100"><td className="px-2 py-3 font-mono text-xs text-slate-700">{fact.value ? '' : 'NOT '}{fact.predicate}({fact.arguments.join(', ')})</td><td className="px-2 py-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${fact.value ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{fact.value ? 'True' : 'False'}</span></td></tr>)}</tbody></table></div></section>
}

export default function LogicVerificationPage() {
  const [knowledgeBase] = useState(readKnowledgeBase)
  const [predicate, setPredicate] = useState('CoreStructureComplete')
  const [value, setValue] = useState(true)
  const [modelResult, setModelResult] = useState(null)
  const [resolutionResult, setResolutionResult] = useState(null)
  const [consistencyResult, setConsistencyResult] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  const query = knowledgeBase ? { predicate: predicate.trim(), arguments: [knowledgeBase.paper.id], value } : null

  const execute = async (operation) => {
    if (!knowledgeBase || (operation !== 'consistency' && !query.predicate)) return
    setStatus(operation)
    setError('')
    try {
      if (operation === 'model') setModelResult(await runLogicModelCheck(knowledgeBase, query))
      if (operation === 'resolution') setResolutionResult(await runResolutionProof(knowledgeBase, query))
      if (operation === 'consistency') setConsistencyResult(await checkLogicConsistency(knowledgeBase))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Logical verification could not be completed.')
    } finally {
      setStatus('idle')
    }
  }

  return <div className="page-container py-12 sm:py-16"><div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Module 5 · Logical verification</p><h1 className="section-title mt-3">Verify paper propositions</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">Use deterministic propositional model checking and resolution to classify a claim as entailed, contradicted, or unknown—and verify whether the knowledge base itself is consistent.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs font-semibold text-cyan-800"><Icon name="shield" className="h-4 w-4" /> Models + CNF + resolution</span></div>
    {!knowledgeBase ? <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="brain" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">Build a knowledge base first</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Logical verification uses the Module 3 knowledge base and transparently includes Module 4’s derived facts and reasoning trace. It never reparses the PDF.</p><Link to="/knowledge-base" className="primary-button mt-6"><Icon name="brain" className="h-4 w-4" /> Open knowledge base</Link></section> : <><section className="surface-card mt-8 p-5 sm:p-6"><div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between"><div><h2 className="font-semibold text-slate-900">Verification query</h2><p className="mt-1 text-sm text-slate-500">{knowledgeBase.paper.name || knowledgeBase.paper.id} · {knowledgeBase.propositional_facts.length} source facts</p></div><div className="flex w-full flex-col gap-3 sm:flex-row lg:w-auto"><div><label htmlFor="logic-predicate" className="sr-only">Predicate to verify</label><input id="logic-predicate" list="logic-predicates" value={predicate} onChange={(event) => setPredicate(event.target.value)} placeholder="Enter a predicate" className="min-w-60 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800" /><datalist id="logic-predicates">{QUERY_SUGGESTIONS.map((item) => <option key={item} value={item} />)}</datalist></div><select aria-label="Query truth value" value={String(value)} onChange={(event) => setValue(event.target.value === 'true')} className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800"><option value="true">Verify proposition</option><option value="false">Verify NOT proposition</option></select></div></div>{error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}<div className="mt-5 flex flex-col gap-3 sm:flex-row"><button type="button" onClick={() => execute('model')} disabled={status !== 'idle' || !predicate.trim()} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={status === 'model' ? 'clock' : 'search'} className="h-4 w-4" />{status === 'model' ? 'Checking models…' : 'Model Check'}</button><button type="button" onClick={() => execute('resolution')} disabled={status !== 'idle' || !predicate.trim()} className="secondary-button disabled:cursor-not-allowed disabled:opacity-60"><Icon name={status === 'resolution' ? 'clock' : 'layers'} className="h-4 w-4" />{status === 'resolution' ? 'Resolving…' : 'Resolution Proof'}</button><button type="button" onClick={() => execute('consistency')} disabled={status !== 'idle'} className="secondary-button disabled:cursor-not-allowed disabled:opacity-60"><Icon name={status === 'consistency' ? 'clock' : 'shield'} className="h-4 w-4" />{status === 'consistency' ? 'Checking…' : 'Check Consistency'}</button></div></section>
      <FactList knowledgeBase={knowledgeBase} />
      <div className="mt-6 grid gap-6 xl:grid-cols-2"><ResultCard title="Model-checking result" result={modelResult}><ModelDetails result={modelResult} />{modelResult?.counter_models?.length > 0 && <div className="mt-4"><h3 className="text-sm font-semibold">Representative models</h3><ul className="mt-2 space-y-2">{modelResult.counter_models.map((model, index) => <li key={index} className="rounded-lg border border-slate-200 bg-white/70 p-3 font-mono text-xs text-slate-700">Query: {String(model.query_value)} · {Object.entries(model.assignment).map(([symbol, assignment]) => `${symbol}=${String(assignment)}`).join(', ')}</li>)}</ul></div>}</ResultCard><ResultCard title="Knowledge-base consistency" result={consistencyResult}>{consistencyResult && <div className="mt-4"><p className="text-sm font-semibold">{consistencyResult.consistent ? 'No contradiction was derived.' : 'Conflict information'}</p>{consistencyResult.conflicts?.length > 0 && <ul className="mt-2 space-y-2">{consistencyResult.conflicts.map((conflict, index) => <li key={`${conflict.type}-${index}`} className="rounded-lg border border-slate-200 bg-white/70 p-3 text-sm">{conflict.message}</li>)}</ul>}</div>}</ResultCard></div>
      <div className="mt-6"><ResultCard title="Resolution proof" result={resolutionResult}>{resolutionResult && <><div className="mt-4 grid gap-3 sm:grid-cols-3"><Metric label="Initial / final clauses" value={`${resolutionResult.initial_clauses?.length ?? 0} / ${resolutionResult.clause_count ?? 0}`} /><Metric label="Proof steps" value={resolutionResult.proof_steps?.length ?? 0} /><Metric label="Iterations" value={resolutionResult.iterations ?? '—'} /></div><ProofTrace proofSteps={resolutionResult.proof_steps} /></>}</ResultCard></div>
      {(modelResult || resolutionResult || consistencyResult) && <section className="surface-card mt-6 p-5 sm:p-6"><h2 className="font-semibold text-slate-900">Module 4 integration retained</h2><p className="mt-1 text-sm leading-6 text-slate-600">Each verification run keeps the source facts, the Module 4 derived facts, rules, and the original forward-chaining trace available in its API result.</p><p className="mt-3 text-sm font-medium text-slate-700">{(modelResult || resolutionResult || consistencyResult).module_4?.derived_facts?.length || 0} derived facts were included as logical propositions.</p></section>}</>}</div>
}
