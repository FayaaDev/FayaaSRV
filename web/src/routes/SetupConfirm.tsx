import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, fetchSetupRunStatus, startSetupRun } from '../api/client'
import type { SetupRunStatus } from '../api/types'
import { SetupShell } from '../components/SetupShell'

type ConfirmState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; run: SetupRunStatus }

export function SetupConfirm() {
  const navigate = useNavigate()
  const [state, setState] = useState<ConfirmState>({ status: 'loading' })
  const [actionError, setActionError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const run = await fetchSetupRunStatus()
        if (cancelled) {
          return
        }

        setState({ status: 'ready', run })
      } catch (error) {
        if (cancelled) {
          return
        }

        const message = error instanceof Error ? error.message : 'Unable to load the setup run state.'
        setState({ status: 'error', message })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  async function handleStart() {
    setIsStarting(true)
    setActionError(null)

    try {
      await startSetupRun()
      navigate('/setup/run')
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
        <section className="placeholder-card bridge-card onboarding-loader" aria-labelledby="setup-confirm-title">
          <img className="setup-loader-logo" src="/logo.png" alt="" width="56" height="56" />
          <p className="section-label">Launch</p>
          <h2 id="setup-confirm-title">Preparing your launch</h2>
          <p className="hero-text">Checking whether your saved choices are ready.</p>
          <div className="bridge-spinner" aria-hidden="true" />
        </section>
      )
    }

    if (state.status === 'error') {
      return (
        <section className="placeholder-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Launch</p>
          <h2 id="setup-confirm-title">Unable to prepare launch</h2>
          <p className="hero-text">{state.message}</p>
        </section>
      )
    }

    const run = state.run

    if (!run.confirmed) {
      return (
        <section className="placeholder-card setup-launch-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Launch</p>
          <h2 id="setup-confirm-title">One last approval is needed</h2>
          <p className="hero-text">
            Revisit the final review, approve the configuration, then return here to start setup.
          </p>
          <div className="setup-run-actions">
            <button type="button" className="bridge-button bridge-button-primary" onClick={() => navigate('/setup/phase/6')}>
              Open final review
            </button>
          </div>
        </section>
      )
    }

    const isRunning = run.status === 'running'
    const isFinished = run.status === 'succeeded' || run.status === 'failed'
    const title = isRunning
      ? 'Your server is being prepared'
      : run.status === 'succeeded'
        ? 'Your server is ready'
        : run.status === 'failed'
          ? 'Setup needs attention'
          : 'Ready to launch'

    const description = isRunning
      ? 'Rakkib is installing the selected services in the background.'
      : run.status === 'succeeded'
        ? 'The last setup finished successfully. You can reopen the progress screen or run again after changing your choices.'
        : run.status === 'failed'
          ? 'The last setup stopped before completion. You can retry after reviewing your saved choices.'
          : 'Your answers are saved and confirmed. Rakkib can now prepare the machine and bring your services online.'

    return (
      <section className="setup-launch-card" aria-labelledby="setup-confirm-title">
        <div className="setup-launch-visual" aria-hidden="true">
          <div className={`setup-launch-ring is-${run.status}`}>
            <img src="/logo-hero.png" alt="" width="132" height="132" />
          </div>
        </div>
        <div className="setup-launch-copy">
          <p className="section-label">Launch</p>
          <h2 id="setup-confirm-title">{title}</h2>
          <p className="hero-text">{description}</p>
          {actionError ? <p className="setup-submit-error">{actionError}</p> : null}
          <div className="setup-run-actions">
            {run.can_start ? (
              <button type="button" className="bridge-button bridge-button-primary" onClick={handleStart} disabled={isStarting}>
                {isStarting ? 'Starting...' : isFinished ? 'Launch again' : 'Launch setup'}
              </button>
            ) : null}
            {(isRunning || isFinished) ? (
              <button type="button" className="bridge-button" onClick={() => navigate('/setup/run')}>
                View progress
              </button>
            ) : null}
          </div>
        </div>
      </section>
    )
  }

  return (
    <SetupShell
      title="Launch Setup"
      description="Start the browser-guided install and follow progress without terminal output."
      currentPhase={7}
    >
      {renderContent()}
    </SetupShell>
  )
}
