import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, fetchSetupRunStatus, startSetupRun } from '../api/client'
import type { SetupRunStatus } from '../api/types'
import { SetupShell } from '../components/SetupShell'

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
        <section className="placeholder-card" aria-labelledby="setup-run-title">
          <p className="section-label">Setup Run</p>
          <h2 id="setup-run-title">Loading execution state...</h2>
          <p className="hero-text">Checking whether the background installer is active and loading the latest log output.</p>
        </section>
      )
    }

    if (state.status === 'error') {
      return (
        <section className="placeholder-card" aria-labelledby="setup-run-title">
          <p className="section-label">Setup Run</p>
          <h2 id="setup-run-title">Unable to load execution state</h2>
          <p className="hero-text">{state.message}</p>
        </section>
      )
    }

    const run = state.run

    return (
      <div className="setup-phase-stack">
        <article className="setup-field-card">
          <div className="setup-field-header">
            <div>
              <p className="section-label">Setup Run</p>
              <h2>Live installer status</h2>
            </div>
            <span className={`setup-status-pill is-${run.status}`}>{run.status}</span>
          </div>

          <p className="hero-text">{run.message}</p>
          {actionError ? <p className="setup-submit-error">{actionError}</p> : null}

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
              <strong>PID</strong>
              <span>{run.pid ?? 'Not running'}</span>
            </div>
            <div>
              <strong>Exit code</strong>
              <span>{run.exit_code ?? 'Not finished yet'}</span>
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

          {run.command.length > 0 ? (
            <div className="setup-command-block">
              <strong>Command</strong>
              <code>{run.command.join(' ')}</code>
            </div>
          ) : null}

          <div className="setup-run-actions">
            {run.can_start ? (
              <button type="button" className="bridge-button" onClick={handleStart} disabled={isStarting}>
                {isStarting ? 'Starting...' : run.status === 'idle' ? 'Run setup' : 'Run again'}
              </button>
            ) : null}
            <button type="button" className="bridge-button" onClick={() => setReloadToken((current) => current + 1)}>
              Refresh now
            </button>
            <button type="button" className="bridge-button" onClick={() => navigate('/setup/confirm')}>
              Back to confirmation
            </button>
          </div>
        </article>

        <article className="setup-field-card">
          <div className="setup-field-header">
            <div>
              <p className="section-label">Live Log</p>
              <h2>Background `rakkib pull` output</h2>
            </div>
            <span className="badge">{run.running ? 'Auto-refreshing' : 'Static snapshot'}</span>
          </div>

          <p className="hero-text">
            {run.log_path ? `Log file: ${run.log_path}` : 'The log file will appear once the installer starts.'}
          </p>
          <pre className="setup-run-log">{run.log_tail.length > 0 ? run.log_tail.join('\n') : 'No log output yet.'}</pre>
        </article>
      </div>
    )
  }

  return (
    <SetupShell
      title="Setup Runner"
      description="Follow the live background installer run, refresh status, and review the most recent setup log output."
    >
      {renderContent()}
    </SetupShell>
  )
}
