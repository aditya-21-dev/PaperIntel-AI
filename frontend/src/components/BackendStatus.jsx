import { useEffect, useState } from 'react'
import { getBackendHealth } from '../services/api'

export default function BackendStatus() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let active = true
    async function checkConnection() {
      try {
        await getBackendHealth()
        if (active) setStatus('connected')
      } catch {
        if (active) setStatus('offline')
      }
    }
    checkConnection()
    return () => { active = false }
  }, [])

  const isConnected = status === 'connected'
  const isChecking = status === 'checking'
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${isConnected ? 'text-emerald-700' : isChecking ? 'text-slate-500' : 'text-rose-700'}`} title={isConnected ? 'Connected to the FastAPI backend' : 'Unable to reach the FastAPI backend'}>
      <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-emerald-500' : isChecking ? 'bg-slate-400' : 'bg-rose-500'}`} />
      {isConnected ? 'Backend Connected' : isChecking ? 'Checking backend' : 'Backend Offline'}
    </span>
  )
}
