import { Link } from 'react-router-dom'
import Icon from '../components/Icon'

const features = [
  { icon: 'layers', title: 'Structural Completeness', description: 'Check whether essential research-paper sections are present and clearly organized.' },
  { icon: 'shield', title: 'Conference Guideline Compliance', description: 'Prepare to compare a paper against the selected publication guidelines.' },
  { icon: 'link', title: 'Citation & Reference Integrity', description: 'Surface citation and reference issues for a more reliable manuscript.' },
  { icon: 'brain', title: 'Logical Consistency', description: 'Help identify gaps between claims, evidence, methods, and conclusions.' },
  { icon: 'chart', title: 'Research Quality', description: 'Review signals that support a rigorous and well-positioned contribution.' },
  { icon: 'grid', title: 'Figures, Tables & Equations', description: 'Assess the supporting elements that make technical work easier to verify.' },
  { icon: 'target', title: 'Knowledge Dependency', description: 'Explore how the key ideas in a paper depend on and support one another.' },
  { icon: 'sparkles', title: 'Intelligent Improvement Planner', description: 'Turn observations into a focused revision plan before submission.' },
]

const steps = [
  ['01', 'Upload Paper', 'Add your finished research paper when document processing is available.'],
  ['02', 'Select Guideline', 'Choose the target publisher or conference requirements.'],
  ['03', 'Analyze', 'PaperIntel will evaluate the paper across eight dimensions.'],
  ['04', 'Review Results', 'Inspect a transparent summary of strengths and issues.'],
  ['05', 'Improve Paper', 'Use ordered recommendations to prepare your final revision.'],
]

export default function HomePage() {
  return (
    <>
      <section className="border-b border-slate-200 bg-white">
        <div className="page-container grid items-center gap-12 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <div>
            <p className="eyebrow">Research paper readiness, made clearer</p>
            <h1 className="mt-4 max-w-3xl font-display text-4xl font-semibold leading-[1.1] tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">Analyze Your Research Paper Before Submission</h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">PaperIntel AI intelligently evaluates research papers for structure, compliance, citation integrity, logical consistency, research quality, and improvement opportunities.</p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link to="/analyze" className="primary-button">Analyze Your Paper <Icon name="arrowRight" className="h-4 w-4" /></Link>
              <Link to="/about" className="secondary-button">Learn More</Link>
            </div>
            <p className="mt-5 flex items-center gap-2 text-sm text-slate-500"><Icon name="info" className="h-4 w-4 text-indigo-600" /> Module 1 foundation — analysis will be introduced in later modules.</p>
          </div>

          <div className="relative mx-auto w-full max-w-xl">
            <div className="absolute -inset-3 rounded-[2rem] bg-indigo-100/70" />
            <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 p-5 shadow-xl sm:p-7">
              <div className="flex items-center justify-between border-b border-white/10 pb-5">
                <div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-200"><Icon name="fileSearch" className="h-5 w-5" /></span><div><p className="text-sm font-semibold text-white">Paper analysis workspace</p><p className="text-xs text-slate-400">Preview of the future workflow</p></div></div>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-slate-200">8 dimensions</span>
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {features.slice(0, 4).map((feature, index) => (
                  <div key={feature.title} className="rounded-xl border border-white/10 bg-white/[0.06] p-4">
                    <div className="flex items-center justify-between"><Icon name={feature.icon} className="h-4 w-4 text-indigo-300" /><span className="text-xs text-slate-500">0{index + 1}</span></div>
                    <p className="mt-5 text-sm font-medium text-slate-100">{feature.title}</p>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10"><span className="block h-full rounded-full bg-indigo-400" style={{ width: `${62 + index * 8}%` }} /></div>
                  </div>
                ))}
              </div>
              <div className="mt-5 flex items-center gap-3 rounded-xl border border-indigo-400/20 bg-indigo-500/10 p-4 text-sm text-indigo-100"><Icon name="sparkles" className="h-5 w-5 shrink-0 text-indigo-300" /> A single, organized view for preparing a stronger submission.</div>
            </div>
          </div>
        </div>
      </section>

      <section className="page-container py-16 sm:py-20">
        <div className="max-w-2xl"><p className="eyebrow">A complete review framework</p><h2 className="section-title mt-3">Built around the questions reviewers ask</h2><p className="mt-4 leading-7 text-slate-600">Each future module will contribute an explainable signal to help authors improve a paper before it reaches a review committee.</p></div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => <article key={feature.title} className="surface-card p-5"><span className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700"><Icon name={feature.icon} className="h-5 w-5" /></span><h3 className="mt-5 font-semibold text-slate-900">{feature.title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{feature.description}</p></article>)}
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white"><div className="page-container py-16 sm:py-20"><div className="max-w-2xl"><p className="eyebrow">How it will work</p><h2 className="section-title mt-3">A focused path from draft to submission</h2></div><ol className="mt-10 grid gap-5 md:grid-cols-5">{steps.map(([number, title, description]) => <li key={number} className="relative"><span className="font-display text-4xl font-semibold text-indigo-200">{number}</span><h3 className="mt-3 font-semibold text-slate-900">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{description}</p></li>)}</ol></div></section>

      <section className="page-container py-16 sm:py-20"><div className="surface-card flex flex-col items-start justify-between gap-6 bg-indigo-800 p-8 text-white sm:flex-row sm:items-center"><div><p className="eyebrow text-indigo-200">Start with the foundation</p><h2 className="mt-2 font-display text-3xl font-semibold">Set up your next paper review.</h2><p className="mt-2 max-w-xl text-indigo-100">The upload workspace is ready now; the real evaluation pipeline arrives in the next modules.</p></div><Link to="/analyze" className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-indigo-800 hover:bg-indigo-50">Open Analyze Paper <Icon name="arrowRight" className="h-4 w-4" /></Link></div></section>
    </>
  )
}
