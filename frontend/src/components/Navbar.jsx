import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import BackendStatus from './BackendStatus'
import Icon from './Icon'

const navigationLinks = [
  { to: '/', label: 'Home', end: true },
  { to: '/analyze', label: 'Analyze Paper' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/knowledge-base', label: 'Knowledge Base' },
  { to: '/reasoning', label: 'Reasoning' },
  { to: '/history', label: 'History' },
  { to: '/about', label: 'About' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const linkClass = ({ isActive }) => `relative text-sm font-medium transition-colors ${isActive ? 'text-indigo-700' : 'text-slate-600 hover:text-slate-950'}`

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="page-container flex h-16 items-center justify-between">
        <NavLink to="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-800 text-white">
            <Icon name="target" className="h-4 w-4" strokeWidth={2} />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight text-slate-950">
            PaperIntel <span className="text-indigo-700">AI</span>
          </span>
        </NavLink>

        <nav className="hidden items-center gap-7 lg:flex" aria-label="Primary">
          {navigationLinks.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.end} className={linkClass}>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden lg:block"><BackendStatus /></div>
        <button type="button" className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-300 text-slate-900 lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'} aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          <Icon name={open ? 'close' : 'menu'} className="h-5 w-5" />
        </button>
      </div>

      {open && (
        <nav className="border-t border-slate-200 bg-white lg:hidden" aria-label="Mobile">
          <ul className="flex flex-col px-4 py-2">
            {navigationLinks.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.end} onClick={() => setOpen(false)} className={({ isActive }) => `block rounded-md px-2 py-3 text-sm font-medium ${isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-50'}`}>
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="border-t border-slate-100 px-6 py-3"><BackendStatus /></div>
        </nav>
      )}
    </header>
  )
}
