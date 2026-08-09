import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { getReasoningRules, runBackwardReasoning, runForwardReasoning } from '../services/api'

const GOALS = [
  'CoreStructureComplete',
  'HasMajorStructuralComponents',
  'HasReferenceSection',
  'HasAtLeastOneFigure',
  'HasAtLeastOneTable',
  'HasCompleteResultsDiscussionFlow',
]

function readKnowledgeBase() {
  try {
    const stored = sessionStorage.getItem('paperintel.knowledgeBase')
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function FactBadge({ value }) {
  return <span className={`rounded-full px-2 py-1 text-xs font-semibold ${value ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>{value ? 'Known true' : 'Known false'}</span>
}

function TraceList({ trace }) {
  if (!trace?.length) return <p className="text-sm text-slate-500">No reasoning steps are available yet.</p>
  return <ol className="space-y-3">{trace.map((item, index) => <li key={`${item.rule_id || item.goal || item.derived_fact?.predicate}-${index}`} className="rounded-lg border border-slate-200 p-4"><p className="font-mono text-xs font-semibold text-indigo-700">{item.rule_id || item.step || 'derived fact'}</p><p className="mt-1 text-sm font-medium text-slate-900">{item.rule_name || item.derived_fact?.predicate || item.goal}</p>{item.supporting_facts?.length > 0 && <p className="mt-2 text-sm text-slate-600">Supports: {item.supporting_facts.join(', ')}</p>}{item.explanation && <p className="mt-2 text-sm leading-6 text-slate-600">{item.explanation}</p>}</li>)}</ol>
}

export default function ReasoningPage() {
  const [knowledgeBase] = useState(readKnowledgeBase)
  const [rules, setRules] = useState([])
  const [forwardResult, setForwardResult] = useState(null)
  const [backwardResult, setBackwardResult] = useState(null)
  const [goal, setGoal] = useState('CoreStructureComplete')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getReasoningRules().then((response) => {
      if (active) setRules(response.rules)
    }).catch((requestError) => {
      if (active) setError(requestError.response?.data?.detail || 'The reasoning rule base could not be loaded.')
    })
    return () => { active = false }
  }, [])

  const runForward = async () => {
    if (!knowledgeBase) return
    setStatus('forward')
    setError('')
    try {
      setForwardResult(await runForwardReasoning(knowledgeBase))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Forward chaining could not be completed.')
    } finally {
      setStatus('idle')
    }
  }

  const runBackward = async () => {
    if (!knowledgeBase) return
    setStatus('backward')
    setError('')
    try {
      setBackwardResult(await runBackwardReasoning(knowledgeBase, {
        predicate: goal,
        arguments: [knowledgeBase.paper.id],
      }))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'Backward chaining could not be completed.')
    } finally {
      setStatus('idle')
    }
  }

  return (
    <div className="page-container py-12 sm:py-16">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Module 4 · Knowledge-based reasoning</p><h1 className="section-title mt-3">Explainable paper reasoning</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">Run data-defined rules over a Module 3 knowledge base. Forward chaining derives every supported conclusion; backward chaining attempts to prove one selected goal and reports unknown or known-false prerequisites.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-semibold text-violet-800"><Icon name="brain" className="h-4 w-4" /> Facts + rules + goals</span></div>

      {!knowledgeBase ? <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="layers" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">Build a knowledge base first</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Reasoning accepts only the structured knowledge base produced by Module 3. It cannot receive a PDF or independently inspect paper content.</p><Link to="/knowledge-base" className="primary-button mt-6"><Icon name="brain" className="h-4 w-4" /> Open knowledge base</Link></section> : <>
        <section className="surface-card mt-8 p-5 sm:p-6"><div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold text-slate-900">Reasoning input</h2><p className="mt-1 text-sm text-slate-500">{knowledgeBase.paper.name || knowledgeBase.paper.id} · {knowledgeBase.propositional_facts.length} Module 3 facts</p></div><span className="text-xs font-medium text-slate-500">Knowledge base schema {knowledgeBase.metadata.schema_version}</span></div>{error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}</section>

        <div className="mt-8 grid gap-6 xl:grid-cols-2"><section className="surface-card p-5 sm:p-6"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="list" className="h-4 w-4" /></span><div><h2 className="font-semibold text-slate-900">Available facts</h2><p className="text-sm text-slate-500">Directly loaded from Module 3; absence remains unknown.</p></div></div><div className="mt-5 max-h-96 overflow-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-2 py-2">Fact</th><th className="px-2 py-2">State</th></tr></thead><tbody>{knowledgeBase.propositional_facts.map((fact) => <tr key={fact.predicate} className="border-b border-slate-100"><td className="px-2 py-3 font-mono text-xs text-slate-700">{fact.predicate}({fact.arguments.join(', ')})</td><td className="px-2 py-3"><FactBadge value={fact.value} /></td></tr>)}</tbody></table></div></section>
          <section className="surface-card p-5 sm:p-6"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50 text-violet-700"><Icon name="layers" className="h-4 w-4" /></span><div><h2 className="font-semibold text-slate-900">Available rules</h2><p className="text-sm text-slate-500">Rules are separate data, not route-level checks.</p></div></div><div className="mt-5 max-h-96 space-y-3 overflow-auto">{rules.map((rule) => <article key={rule.id} className="rounded-lg border border-slate-200 p-4"><p className="font-mono text-xs font-semibold text-indigo-700">{rule.id}</p><h3 className="mt-1 text-sm font-semibold text-slate-900">{rule.name}</h3><p className="mt-2 text-xs leading-5 text-slate-600">IF {rule.premises.map((premise) => `${premise.predicate}(${premise.arguments.join(', ')})`).join(' AND ')} THEN {rule.conclusion.predicate}({rule.conclusion.arguments.join(', ')})</p></article>)}</div></section></div>

        <section className="surface-card mt-6 p-5 sm:p-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="eyebrow">Forward chaining</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Derive every supported conclusion</h2><p className="mt-1 text-sm leading-6 text-slate-600">Starts with all known facts, fires applicable rules to a fixed point, and records each rule application.</p></div><button type="button" onClick={runForward} disabled={status !== 'idle'} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={status === 'forward' ? 'clock' : 'arrowRight'} className="h-4 w-4" />{status === 'forward' ? 'Reasoning…' : 'Run Forward Chaining'}</button></div>{forwardResult && <div className="mt-6 grid gap-6 lg:grid-cols-2"><div><h3 className="font-semibold text-slate-900">Derived facts ({forwardResult.derived_facts.length})</h3>{forwardResult.derived_facts.length ? <ul className="mt-3 space-y-2">{forwardResult.derived_facts.map((fact) => <li key={fact.predicate} className="rounded-lg bg-emerald-50 px-3 py-2 font-mono text-xs text-emerald-800">{fact.predicate}({fact.arguments.join(', ')})</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">No new conclusions were supported by the available facts.</p>}</div><div><h3 className="font-semibold text-slate-900">Reasoning trace</h3><div className="mt-3"><TraceList trace={forwardResult.reasoning_trace} /></div></div></div>}</section>

        <section className="surface-card mt-6 p-5 sm:p-6"><div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between"><div><p className="eyebrow">Backward chaining</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Prove a specific goal</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-slate-600">Works backward from the selected conclusion through rule premises. Unknown and known-false facts are reported separately.</p></div><div className="flex w-full flex-col gap-3 sm:flex-row lg:w-auto"><select value={goal} onChange={(event) => setGoal(event.target.value)} className="min-w-64 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800">{GOALS.map((item) => <option key={item}>{item}</option>)}</select><button type="button" onClick={runBackward} disabled={status !== 'idle'} className="secondary-button disabled:cursor-not-allowed disabled:opacity-60"><Icon name={status === 'backward' ? 'clock' : 'search'} className="h-4 w-4" />{status === 'backward' ? 'Checking…' : 'Run Backward Chaining'}</button></div></div>{backwardResult && <div className="mt-6"><div className={`rounded-xl border p-4 ${backwardResult.established ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}><p className={`font-semibold ${backwardResult.established ? 'text-emerald-800' : 'text-amber-900'}`}>{backwardResult.established ? 'Goal established' : `Goal not established · ${backwardResult.status}`}</p><p className="mt-2 text-sm leading-6 text-slate-700">{backwardResult.explanation}</p></div><div className="mt-5 grid gap-5 lg:grid-cols-3"><ResultList title="Supporting facts" items={backwardResult.supporting_facts} empty="No supporting facts were needed." tone="emerald" /><ResultList title="Missing / unknown facts" items={backwardResult.missing_facts} empty="No unknown prerequisites." tone="amber" /><ResultList title="Known false facts" items={backwardResult.known_false_facts} empty="No contrary facts are known." tone="rose" /></div><div className="mt-6"><h3 className="font-semibold text-slate-900">Proof trace</h3><div className="mt-3"><TraceList trace={backwardResult.reasoning_trace} /></div></div></div>}</section>
      </>}
    </div>
  )
}

function ResultList({ title, items, empty, tone }) {
  const tones = { emerald: 'bg-emerald-50 text-emerald-800', amber: 'bg-amber-50 text-amber-900', rose: 'bg-rose-50 text-rose-800' }
  return <section className="rounded-xl border border-slate-200 p-4"><h3 className="font-semibold text-slate-900">{title}</h3>{items.length ? <ul className="mt-3 space-y-2">{items.map((item) => <li key={item} className={`rounded-lg px-3 py-2 font-mono text-xs ${tones[tone]}`}>{item}</li>)}</ul> : <p className="mt-3 text-sm text-slate-500">{empty}</p>}</section>
}
