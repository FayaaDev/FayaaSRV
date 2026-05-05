import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, fetchSetupRunStatus, startSetupRun } from '../api/client'
import type { SetupRunStatus } from '../api/types'
import { SetupShell } from '../components/SetupShell'

const progressSteps = ['Preparing machine', 'Creating secure access', 'Starting services', 'Final checks']

function statusTitle(run: SetupRunStatus) {
  if (run.status === 'running') {
    return 'Installing your server stack'
  }
  if (run.status === 'succeeded') {
    return 'Setup complete'
  }
  if (run.status === 'failed') {
    return 'Setup needs attention'
  }
  return 'Ready when you are'
}

function statusCopy(run: SetupRunStatus) {
  if (run.status === 'running') {
    return 'Rakkib is preparing the machine, connecting the tunnel, and starting your selected services.'
  }
  if (run.status === 'succeeded') {
    return 'Your setup finished successfully. You can now open your services from their configured domains.'
  }
  if (run.status === 'failed') {
    return 'Setup stopped before completion. Keep this session open and retry after checking your saved choices.'
  }
  return 'Start setup to let Rakkib prepare the host and launch your services.'
}

type RunScreenState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; run: SetupRunStatus }

export function SetupRun() {
  const navigate = useNavigate()
  const [state, setState] = useState<RunScreenState>({ status: 'loading' })
  const [actionError, setActionError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    let timeoutId: number | null = null

    const load = async () => {
      try {
        const run = await fetchSetupRunStatus()
        if (cancelled) {
          return
        }

        setState({ status: 'ready', run })
        if (run.running) {
          timeoutId = window.setTimeout(load, 2000)
        }
      } catch (error) {
        if (cancelled) {
          return
        }

        const message = error instanceof Error ? error.message : 'Unable to load the installer run state.'
        setState({ status: 'error', message })
      }
    }

    void load()

    return () => {
      cancelled = true
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [reloadToken])

  async function handleStart() {
    setActionError(null)
    setIsStarting(true)

    try {
      const run = await startSetupRun()
      setState({ status: 'ready', run })
      if (run.running) {
        setReloadToken((current) => current + 1)
      }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Unable to start the installer run right now.'
      setActionError(message)
    } finally {
      setIsStarting(false)
    }
  }

  function renderContent() {
    if (state.status === 'loading') {
      return (
        <section className="placeholder-card bridge-card onboarding-loader" aria-labelledby="setup-run-title">
          <img className="setup-loader-logo" src="/logo.png" alt="" width="56" height="56" />
          <p className="section-label">Progress</p>
          <h2 id="setup-run-title">Opening progress view</h2>
          <p className="hero-text">Checking the current setup state.</p>
          <div className="bridge-spinner" aria-hidden="true" />
        </section>
      )
    }

    if (state.status === 'error') {
      return (
        <section className="placeholder-card" aria-labelledby="setup-run-title">
          <p className="section-label">Progress</p>
          <h2 id="setup-run-title">Unable to open progress</h2>
          <p className="hero-text">{state.message}</p>
        </section>
      )
    }

    const run = state.run

    const activeIndex = run.status === 'succeeded' ? progressSteps.length : run.status === 'running' ? 2 : run.status === 'failed' ? 1 : 0

    return (
      <section className="setup-progress-card" aria-labelledby="setup-run-title">
        <div className="setup-progress-visual" aria-hidden="true">
          <div className={`setup-launch-ring is-${run.status}`}>
            <img src="/logo-hero.png" alt="" width="144" height="144" />
          </div>
          <div className="setup-service-orbit">
            <span>DB</span>
            <span>AI</span>
            <span>DNS</span>
            <span>APP</span>
          </div>
        </div>

        <div className="setup-progress-copy">
          <p className="section-label">Progress</p>
          <h2 id="setup-run-title">{statusTitle(run)}</h2>
          <p className="hero-text">{statusCopy(run)}</p>
          <span className={`setup-status-pill is-${run.status}`}>{run.status}</span>

          <div className="setup-progress-steps" aria-label="Setup progress steps">
            {progressSteps.map((step, index) => (
              <div key={step} className={`setup-progress-step${index < activeIndex ? ' is-done' : ''}${index === activeIndex && run.running ? ' is-active' : ''}`}>
                <span />
                <strong>{step}</strong>
              </div>
            ))}
          </div>

          {actionError ? <p className="setup-submit-error">{actionError}</p> : null}

          <div className="setup-run-actions">
            {run.can_start ? (
              <button type="button" className="bridge-button bridge-button-primary" onClick={handleStart} disabled={isStarting}>
                {isStarting ? 'Starting...' : run.status === 'idle' ? 'Launch setup' : 'Try again'}
              </button>
            ) : null}
            <button type="button" className="bridge-button" onClick={() => setReloadToken((current) => current + 1)}>
              Check progress
            </button>
            <button type="button" className="bridge-button" onClick={() => navigate('/setup/confirm')}>
              Launch screen
            </button>
          </div>
        </div>
      </section>
    )
  }

  return (
    <SetupShell
      title="Setup Progress"
      description="Follow the installation as a guided browser experience, without raw terminal output."
      currentPhase={state.status === 'ready' && state.run.status === 'succeeded' ? 8 : 7}
    >
      {renderContent()}
    </SetupShell>
  )
}
