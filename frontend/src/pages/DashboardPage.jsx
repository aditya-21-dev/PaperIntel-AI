import Icon from '../components/Icon'

const evaluationScores = [
  ['Structural Completeness', '14 / 15', 'layers'],
  ['Conference Compliance', '13 / 15', 'shield'],
  ['Citation Integrity', '8 / 10', 'link'],
  ['Logical Consistency', '16 / 20', 'brain'],
  ['Research Quality', '12 / 15', 'chart'],
  ['Figures, Tables & Equations', '5 / 5', 'grid'],
  ['Knowledge Dependency', '9 / 10', 'target'],
  ['Improvement Planner', '10 / 10', 'sparkles'],
]

const strengths = ['Clear problem framing and paper structure', 'Well-presented figures, tables, and equations', 'Strong connection between core research ideas']
const weaknesses = ['Several references need formatting review', 'Methodology limitations need a clearer discussion', 'Conclusion can map results back to objectives more directly']
const priorities = ['Verify citation formatting against the IEEE template', 'Expand the limitations and future-work section', 'Tighten the evidence behind the primary conclusion']

export default function DashboardPage() {
  return (
    <div className="page-container py-12 sm:py-16">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Dashboard · mock data</p><h1 className="section-title mt-3">Paper analysis overview</h1><p className="mt-3 text-slate-600">A demonstration of the future analysis dashboard. No real paper has been evaluated.</p></div><span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800"><Icon name="info" className="h-4 w-4" /> Demo Data — Real analysis will be implemented in later modules.</span></div>

      <section className="surface-card mt-8 overflow-hidden"><div className="grid gap-5 border-b border-slate-200 p-5 sm:grid-cols-3 sm:p-6"><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Paper</p><p className="mt-2 font-semibold text-slate-900">Sample Research Paper</p></div><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Guideline</p><p className="mt-2 font-semibold text-slate-900">IEEE</p></div><div><p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Status</p><p className="mt-2 inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-700"><span className="h-2 w-2 rounded-full bg-indigo-500" /> Demo Analysis</p></div></div><div className="flex flex-col gap-6 p-5 sm:flex-row sm:items-center sm:p-6"><div className="flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-full border-[10px] border-indigo-100 bg-indigo-50"><span className="font-display text-3xl font-semibold text-indigo-800">87</span><span className="text-xs font-medium text-indigo-700">/ 100</span></div><div><p className="text-sm font-semibold text-slate-500">Overall score</p><h2 className="mt-1 font-display text-2xl font-semibold text-slate-950">Strong demonstration result</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">This score is illustrative only. It shows the kind of summary that future PaperIntel analysis will provide.</p></div></div></section>

      <section className="mt-10"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold text-slate-900">Evaluation dimensions</h2><span className="text-sm text-slate-500">Mock scores</span></div><div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{evaluationScores.map(([title, score, icon]) => <article key={title} className="surface-card p-5"><div className="flex items-start justify-between gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name={icon} className="h-4.5 w-4.5" /></span><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">Demo</span></div><h3 className="mt-5 text-sm font-semibold text-slate-800">{title}</h3><p className="mt-2 font-display text-2xl font-semibold text-slate-950">{score}</p></article>)}</div></section>

      <section className="mt-10 grid gap-5 lg:grid-cols-3"><InsightList title="Illustrative strengths" icon="circleCheck" tone="emerald" items={strengths} /><InsightList title="Illustrative weaknesses" icon="warning" tone="amber" items={weaknesses} /><InsightList title="Improvement priorities" icon="sparkles" tone="indigo" items={priorities} numbered /></section>
    </div>
  )
}

function InsightList({ title, icon, tone, items, numbered = false }) {
  const tones = { emerald: 'bg-emerald-50 text-emerald-700', amber: 'bg-amber-50 text-amber-700', indigo: 'bg-indigo-50 text-indigo-700' }
  return <section className="surface-card p-5"><div className="flex items-center gap-3"><span className={`flex h-9 w-9 items-center justify-center rounded-lg ${tones[tone]}`}><Icon name={icon} className="h-4.5 w-4.5" /></span><h2 className="font-semibold text-slate-900">{title}</h2></div><ol className="mt-5 space-y-3">{items.map((item, index) => <li key={item} className="flex gap-3 text-sm leading-6 text-slate-600"><span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${tones[tone]}`}>{numbered ? index + 1 : <Icon name="check" className="h-3.5 w-3.5" />}</span>{item}</li>)}</ol></section>
}
