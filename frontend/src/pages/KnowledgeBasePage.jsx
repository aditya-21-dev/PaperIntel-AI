import { useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/Icon'
import { generateKnowledgeBase, queryKnowledgeFact } from '../services/api'

const TABS = ['Entities', 'Facts', 'Relationships', 'Evidence']
const FACT_PREDICATES = [
  'PaperHasAbstract', 'PaperHasKeywords', 'PaperHasIntroduction', 'PaperHasMethodology',
  'PaperHasResults', 'PaperHasConclusion', 'PaperHasReferences', 'PaperHasFigures', 'PaperHasTables',
]

function readStructuredDocument() {
  try {
    const stored = sessionStorage.getItem('paperintel.structuredDocument')
    return stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

function entityMap(knowledgeBase) {
  const entities = { [knowledgeBase.paper.id]: knowledgeBase.paper }
  Object.values(knowledgeBase.entities).flat().forEach((entity) => { entities[entity.id] = entity })
  return entities
}

function displayEntity(entity) {
  return entity?.name || entity?.id || 'Unknown entity'
}

function Evidence({ evidence }) {
  if (!evidence) return <span className="text-slate-400">No evidence</span>
  const context = [evidence.source_field, evidence.section, evidence.page ? `page ${evidence.page}` : null].filter(Boolean).join(' · ')
  return <span className="text-xs text-slate-500">{evidence.source_module}{context ? ` · ${context}` : ''}</span>
}

export default function KnowledgeBasePage() {
  const [structuredDocument] = useState(readStructuredDocument)
  const [knowledgeBase, setKnowledgeBase] = useState(null)
  const [validation, setValidation] = useState(null)
  const [activeTab, setActiveTab] = useState('Entities')
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')
  const [selectedPredicate, setSelectedPredicate] = useState('PaperHasAbstract')
  const [queryResult, setQueryResult] = useState(null)

  const buildKnowledgeBase = async () => {
    if (!structuredDocument) return
    setStatus('loading')
    setError('')
    setQueryResult(null)
    try {
      const response = await generateKnowledgeBase(structuredDocument)
      setKnowledgeBase(response.knowledge_base)
      setValidation(response.validation)
      setStatus('ready')
    } catch (requestError) {
      setStatus('error')
      setError(requestError.response?.data?.detail || requestError.message || 'The knowledge base could not be generated.')
    }
  }

  const runFactQuery = async () => {
    if (!knowledgeBase) return
    setQueryResult(null)
    try {
      const response = await queryKnowledgeFact({
        predicate: selectedPredicate,
        arguments: [knowledgeBase.paper.id],
        knowledge_base: knowledgeBase,
      })
      setQueryResult(response)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || requestError.message || 'The fact query could not be completed.')
    }
  }

  const counts = knowledgeBase ? [
    ['Authors', knowledgeBase.entities.authors.length, 'users'],
    ['Sections', knowledgeBase.entities.sections.length + knowledgeBase.entities.subsections.length, 'layers'],
    ['References', knowledgeBase.entities.references.length, 'bookOpen'],
    ['Figures & tables', knowledgeBase.entities.figures.length + knowledgeBase.entities.tables.length, 'grid'],
  ] : []

  return (
    <div className="page-container py-12 sm:py-16">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="eyebrow">Module 3 · Knowledge engineering</p><h1 className="section-title mt-3">Paper knowledge base</h1><p className="mt-3 max-w-3xl leading-7 text-slate-600">Transform the latest Module 2 structured document into traceable entities, controlled facts, and first-order-style relationships. No paper quality or compliance evaluation is performed.</p></div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-800"><Icon name="brain" className="h-4 w-4" /> Deterministic knowledge agent</span>
      </div>

      {!structuredDocument ? (
        <section className="surface-card mt-8 p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name="fileSearch" className="h-5 w-5" /></span><h2 className="mt-5 text-xl font-semibold text-slate-900">Analyze a paper first</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">This page consumes Module 2’s structured result. Upload and process a PDF, then return here to construct its knowledge base—no PDF is parsed again.</p><Link to="/analyze" className="primary-button mt-6"><Icon name="upload" className="h-4 w-4" /> Analyze a paper</Link></section>
      ) : (
        <section className="surface-card mt-8 p-5 sm:p-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-semibold text-slate-900">Latest structured document</h2><p className="mt-1 text-sm text-slate-500">{structuredDocument.document?.filename || 'Unnamed paper'} · {structuredDocument.document?.page_count || 0} pages</p></div><button type="button" onClick={buildKnowledgeBase} disabled={status === 'loading'} className="primary-button disabled:cursor-not-allowed disabled:bg-slate-300"><Icon name={status === 'loading' ? 'clock' : 'brain'} className="h-4 w-4" />{status === 'loading' ? 'Building…' : knowledgeBase ? 'Rebuild knowledge base' : 'Build knowledge base'}</button></div>
          {error && <div className="mt-5 flex gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert"><Icon name="warning" className="mt-0.5 h-5 w-5 shrink-0" /><p>{error}</p></div>}
          {validation && <div className={`mt-5 flex gap-3 rounded-lg border p-4 text-sm ${validation.valid ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-rose-200 bg-rose-50 text-rose-800'}`}><Icon name={validation.valid ? 'circleCheck' : 'warning'} className="mt-0.5 h-5 w-5 shrink-0" /><div><p className="font-semibold">{validation.valid ? 'Knowledge base validated' : 'Knowledge base has validation errors'}</p>{validation.errors.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5">{validation.errors.map((item) => <li key={`${item.code}-${item.message}`}>{item.message}</li>)}</ul>}</div></div>}
        </section>
      )}

      {knowledgeBase && <KnowledgeBaseView knowledgeBase={knowledgeBase} activeTab={activeTab} setActiveTab={setActiveTab} selectedPredicate={selectedPredicate} setSelectedPredicate={setSelectedPredicate} queryResult={queryResult} runFactQuery={runFactQuery} counts={counts} />}
    </div>
  )
}

function KnowledgeBaseView({ knowledgeBase, activeTab, setActiveTab, selectedPredicate, setSelectedPredicate, queryResult, runFactQuery, counts }) {
  const entities = entityMap(knowledgeBase)
  const entityGroups = [
    ['Authors', knowledgeBase.entities.authors], ['Abstracts', knowledgeBase.entities.abstracts], ['Keywords', knowledgeBase.entities.keywords],
    ['Sections', [...knowledgeBase.entities.sections, ...knowledgeBase.entities.subsections]], ['References', knowledgeBase.entities.references],
    ['Figures', knowledgeBase.entities.figures], ['Tables', knowledgeBase.entities.tables], ['Citations', knowledgeBase.entities.citations],
  ]

  return <div className="mt-8 space-y-6">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{counts.map(([label, value, icon]) => <div key={label} className="surface-card p-4"><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p><Icon name={icon} className="h-4 w-4 text-indigo-600" /></div><p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p></div>)}</div>
    <section className="surface-card overflow-hidden"><div className="border-b border-slate-200 px-4 pt-3 sm:px-6"><div className="flex gap-1 overflow-x-auto" role="tablist" aria-label="Knowledge base views">{TABS.map((tab) => <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)} className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm font-semibold transition-colors ${activeTab === tab ? 'border-indigo-700 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>{tab}</button>)}</div></div><div className="p-5 sm:p-6">
      {activeTab === 'Entities' && <div className="grid gap-5 lg:grid-cols-2">{entityGroups.map(([title, group]) => <section key={title} className="rounded-xl border border-slate-200 p-4"><div className="flex items-center justify-between"><h2 className="font-semibold text-slate-900">{title}</h2><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{group.length}</span></div>{group.length ? <ul className="mt-4 divide-y divide-slate-100">{group.map((entity) => <li key={entity.id} className="py-3 first:pt-0 last:pb-0"><p className="text-sm font-medium text-slate-800">{displayEntity(entity)}</p><p className="mt-1 font-mono text-xs text-slate-500">{entity.id} · {entity.type}</p><div className="mt-1"><Evidence evidence={entity.evidence} /></div></li>)}</ul> : <p className="mt-4 text-sm text-slate-500">None detected.</p>}</section>)}</div>}
      {activeTab === 'Facts' && <div className="space-y-6"><div className="rounded-xl bg-slate-50 p-4"><h2 className="font-semibold text-slate-900">Deterministic fact query</h2><p className="mt-1 text-sm text-slate-600">Exact lookup against this knowledge base; it performs no inference.</p><div className="mt-4 flex flex-col gap-3 sm:flex-row"><select value={selectedPredicate} onChange={(event) => setSelectedPredicate(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800">{FACT_PREDICATES.map((predicate) => <option key={predicate}>{predicate}</option>)}</select><button type="button" onClick={runFactQuery} className="secondary-button"><Icon name="search" className="h-4 w-4" /> Query fact</button></div>{queryResult && <p className={`mt-3 text-sm font-medium ${queryResult.found ? 'text-emerald-700' : 'text-slate-600'}`}>{queryResult.found ? `${queryResult.fact.predicate} is ${String(queryResult.fact.value)}.` : 'No exact fact was found.'}</p>}</div><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-3">Predicate</th><th className="px-3 py-3">Arguments</th><th className="px-3 py-3">Value</th><th className="px-3 py-3">Evidence</th></tr></thead><tbody>{knowledgeBase.propositional_facts.map((fact) => <tr key={fact.predicate} className="border-b border-slate-100"><td className="px-3 py-3 font-medium text-slate-900">{fact.predicate}</td><td className="px-3 py-3 font-mono text-xs text-slate-600">{fact.arguments.join(', ')}</td><td className="px-3 py-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${fact.value ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{String(fact.value)}</span></td><td className="px-3 py-3"><Evidence evidence={fact.evidence} /></td></tr>)}</tbody></table></div></div>}
      {activeTab === 'Relationships' && <div><p className="mb-4 text-sm leading-6 text-slate-600">This relationship table is the graph representation for Module 3. Each edge uses a controlled predicate and includes a first-order-style notation.</p><div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-3">Subject</th><th className="px-3 py-3">Predicate</th><th className="px-3 py-3">Object</th><th className="px-3 py-3">Logical form</th><th className="px-3 py-3">Evidence</th></tr></thead><tbody>{knowledgeBase.relationships.map((relationship, index) => <tr key={`${relationship.subject}-${relationship.predicate}-${relationship.object}-${index}`} className="border-b border-slate-100 align-top"><td className="px-3 py-3 text-slate-800">{displayEntity(entities[relationship.subject])}</td><td className="px-3 py-3 font-mono text-xs text-indigo-700">{relationship.predicate}</td><td className="px-3 py-3 text-slate-800">{displayEntity(entities[relationship.object])}</td><td className="px-3 py-3 font-mono text-xs text-slate-600">{relationship.logical_form}</td><td className="px-3 py-3"><Evidence evidence={relationship.evidence} /></td></tr>)}</tbody></table></div></div>}
      {activeTab === 'Evidence' && <div><p className="mb-4 text-sm leading-6 text-slate-600">Evidence is retained from Module 2 fields so later reasoning can explain each represented item without inventing a source.</p><ol className="space-y-3">{knowledgeBase.evidence.map((item) => <li key={item.id} className="rounded-lg border border-slate-200 p-4"><p className="font-mono text-xs font-semibold text-indigo-700">{item.id}</p><p className="mt-1 text-sm text-slate-800">{item.source_module} · {item.source_field}</p><p className="mt-1 text-xs text-slate-500">{[item.section, item.page ? `page ${item.page}` : null, item.citation].filter(Boolean).join(' · ') || 'Structured document field'}</p></li>)}</ol></div>}
    </div></section>
  </div>
}
