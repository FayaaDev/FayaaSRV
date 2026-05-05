import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchSetupResume } from '../api/client'
import type { SetupResume } from '../api/types'
import { StepTimeline } from './StepTimeline'

const recoveryCommand = 'rakkib web --lan'

type SetupShellProps = {
  title: string
  description: string
  currentPhase?: number
  children: ReactNode
}

type ShellState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; resume: SetupResume }

export function SetupShell({ title, description, currentPhase, children }: SetupShellProps) {
  const [state, setState] = useState<ShellState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const resume = await fetchSetupResume()
        if (cancelled) {
          return
        }

        setState({ status: 'ready', resume })
      } catch (error) {
        if (cancelled) {
          return
        }

        const message = error instanceof Error ? error.message : 'Unable to load the setup session.'
        setState({ status: 'error', message })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  if (state.status === 'loading') {
    return (
      <main className="shell setup-shell-frame setup-onboarding">
        <p className="simple-loading" role="status">Loading...</p>
      </main>
    )
  }

  if (state.status === 'error') {
    return (
      <main className="shell setup-shell-frame setup-onboarding">
        <section className="placeholder-card bridge-card" aria-labelledby="setup-shell-error-title">
          <p className="section-label">Setup Access</p>
          <h1 id="setup-shell-error-title">Setup session required</h1>
          <p className="hero-text">Open Rakkib from the setup link shown by the local web server.</p>
          <div className="bridge-command" aria-label="Recovery command">
            <code>{recoveryCommand}</code>
          </div>
          <div className="bridge-actions">
            <button type="button" className="bridge-button" onClick={() => window.location.assign('/')}>
              Back to landing page
            </button>
          </div>
        </section>
      </main>
    )
  }

  return (
    <div className="shell setup-shell-frame setup-onboarding">
      <header className="setup-shell-header">
        <div className="setup-title-lockup">
          <Link className="brand setup-brand" to="/" aria-label="Rakkib landing page">
            <img className="brand-logo" src="/logo.png" alt="Rakkib logo" width="28" height="28" />
            [rakkib]
          </Link>
          <h1>{title}</h1>
          <p className="hero-text">{description}</p>
        </div>

        <div className="setup-shell-status">
          <span className="badge">Saved session</span>
          <Link className="github-link" to="/">
            Landing page
          </Link>
        </div>
      </header>

      <StepTimeline phases={state.resume.phases} currentPhase={currentPhase} />
      <section className="setup-shell-content">{children}</section>
    </div>
  )
}
