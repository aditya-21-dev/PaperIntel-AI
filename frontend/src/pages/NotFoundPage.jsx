import { Link } from 'react-router-dom'
import Icon from '../components/Icon'

export default function NotFoundPage() {
  return <div className="page-container flex min-h-[62vh] items-center justify-center py-16 text-center"><div><p className="font-display text-8xl font-semibold text-indigo-100">404</p><h1 className="mt-2 font-display text-4xl font-semibold tracking-tight text-slate-950">Page Not Found</h1><p className="mx-auto mt-4 max-w-md leading-7 text-slate-600">The page you requested is not part of the PaperIntel AI workspace.</p><Link to="/" className="primary-button mt-8">Return to Home <Icon name="arrowRight" className="h-4 w-4" /></Link></div></div>
}
