import { Link } from 'react-router-dom'
import Icon from './Icon'

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="page-container py-10">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-800 text-white"><Icon name="target" className="h-3.5 w-3.5" strokeWidth={2} /></span>
              <span className="font-display text-base font-semibold text-slate-950">PaperIntel <span className="text-indigo-700">AI</span></span>
            </div>
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-slate-500">Intelligent Research Paper Analysis and Improvement Assistant</p>
          </div>
          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-10 gap-y-2 text-sm sm:flex sm:gap-8">
            <Link to="/" className="text-slate-600 hover:text-indigo-700">Home</Link>
            <Link to="/analyze" className="text-slate-600 hover:text-indigo-700">Analyze</Link>
            <Link to="/dashboard" className="text-slate-600 hover:text-indigo-700">Dashboard</Link>
            <Link to="/about" className="text-slate-600 hover:text-indigo-700">About</Link>
          </nav>
        </div>
        <div className="mt-8 flex flex-col gap-2 border-t border-slate-200 pt-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} PaperIntel AI. All rights reserved.</p>
          <p>Analysis capabilities will be introduced in later modules.</p>
        </div>
      </div>
    </footer>
  )
}
