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
        <section className="placeholder-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Run Preparation</p>
          <h2 id="setup-confirm-title">Loading confirmation state...</h2>
          <p className="hero-text">Checking whether setup is ready to start and whether a run is already active.</p>
        </section>
      )
    }

    if (state.status === 'error') {
      return (
        <section className="placeholder-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Run Preparation</p>
          <h2 id="setup-confirm-title">Unable to load run state</h2>
          <p className="hero-text">{state.message}</p>
        </section>
      )
    }

    const run = state.run

    if (!run.confirmed) {
      return (
        <section className="placeholder-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Run Confirmation</p>
          <h2 id="setup-confirm-title">Deployment still needs final confirmation</h2>
          <p className="hero-text">
            Phase 6 was saved without approving the deployment. Revisit the final phase or any earlier phase, then return here once you are ready to run.
          </p>
          <div className="setup-run-actions">
            <button type="button" className="bridge-button" onClick={() => navigate('/setup/phase/6')}>
              Revisit phase 6
            </button>
          </div>
        </section>
      )
    }

    const isRunning = run.status === 'running'
    const isFinished = run.status === 'succeeded' || run.status === 'failed'
    const title = isRunning
      ? 'Setup is already running'
      : run.status === 'succeeded'
        ? 'Setup completed successfully'
        : run.status === 'failed'
          ? 'Setup finished with errors'
          : 'Ready to run setup'

    const description = isRunning
      ? 'The installer is currently executing in the background. Open the live run screen to follow progress.'
      : run.status === 'succeeded'
        ? 'The last installer run completed successfully. You can reopen the log or run it again if you changed the saved state.'
        : run.status === 'failed'
          ? 'The last installer run stopped with errors. Review the live log, fix the saved state if needed, and run again.'
          : 'Your answers are saved and confirmed. Starting now will launch `rakkib pull` in the background from this checkout.'

    return (
      <div className="setup-phase-stack">
        <section className="placeholder-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Run Confirmation</p>
          <h2 id="setup-confirm-title">{title}</h2>
          <p className="hero-text">{description}</p>
          {actionError ? <p className="setup-submit-error">{actionError}</p> : null}
          <div className="setup-run-actions">
            {run.can_start ? (
              <button type="button" className="bridge-button" onClick={handleStart} disabled={isStarting}>
                {isStarting ? 'Starting...' : isFinished ? 'Run again' : 'Run setup'}
              </button>
            ) : null}
            {(isRunning || isFinished) ? (
              <button type="button" className="bridge-button" onClick={() => navigate('/setup/run')}>
                Open live run
              </button>
            ) : null}
          </div>
        </section>

        <article className="setup-field-card">
          <div className="setup-field-header">
            <div>
              <p className="section-label">Run Snapshot</p>
              <h2>Current execution state</h2>
            </div>
            <span className={`setup-status-pill is-${run.status}`}>{run.status}</span>
          </div>

          <div className="setup-meta-grid">
            <div>
              <strong>Resume phase</strong>
              <span>{run.resume_phase}</span>
            </div>
            <div>
              <strong>Confirmed</strong>
              <span>{run.confirmed ? 'Yes' : 'No'}</span>
            </div>
            <div>
              <strong>Started</strong>
              <span>{run.started_at ?? 'Not started yet'}</span>
            </div>
            <div>
              <strong>Finished</strong>
              <span>{run.finished_at ?? 'Still running or not started'}</span>
            </div>
          </div>
        </article>
      </div>
    )
  }

  return (
    <SetupShell
      title="Run Confirmation"
      description="Review the saved confirmation state, then launch the background installer run when you are ready."
    >
      {renderContent()}
    </SetupShell>
  )
}
