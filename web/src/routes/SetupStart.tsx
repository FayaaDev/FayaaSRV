import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchSetupResume } from '../api/client'
import { SetupBridge } from './SetupBridge'

type StartState =
  | { status: 'loading' }
  | { status: 'error'; message: string }

export function SetupStart() {
  const location = useLocation()
  const navigate = useNavigate()
  const [state, setState] = useState<StartState>({ status: 'loading' })

  const params = new URLSearchParams(location.search)

  if (params.has('token')) {
    return <SetupBridge />
  }

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const resume = await fetchSetupResume()
        if (cancelled) {
          return
        }

        if (resume.resume_phase >= 7) {
          navigate('/setup/confirm', { replace: true })
          return
        }

        navigate(`/setup/phase/${resume.resume_phase}`, { replace: true })
      } catch (error) {
        if (cancelled) {
          return
        }

        const message = error instanceof Error ? error.message : 'Unable to load the active setup session.'
        setState({ status: 'error', message })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [navigate])

  if (state.status === 'loading') {
    return (
      <main className="shell route-placeholder">
        <p className="simple-loading" role="status">Loading...</p>
      </main>
    )
  }

  return (
    <main className="shell route-placeholder">
      <section className="placeholder-card bridge-card" aria-labelledby="setup-start-title">
        <p className="section-label">Setup Session</p>
        <h1 id="setup-start-title">Unable to resume setup</h1>
        <p className="hero-text">{state.message}</p>
      </section>
    </main>
  )
}
