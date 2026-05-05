import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, fetchSetupPhase, fetchSetupRunStatus, startSetupRun, submitSetupPhase } from '../api/client'
import type { SetupPhasePayload, SetupRunStatus } from '../api/types'
import { renderFieldValue } from '../components/FieldRenderer'
import { SetupShell } from '../components/SetupShell'

type ConfirmState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; run: SetupRunStatus; summary: SetupPhasePayload | null; summaryError?: string }

const summaryLabels: Record<string, string> = {
  platform: 'Platform',
  arch: 'Architecture',
  privilege_mode: 'System access',
  privilege_strategy: 'Privilege handling',
  data_root: 'Data location',
  server_name: 'Server name',
  domain: 'Domain',
  admin_user: 'Admin user',
  admin_email: 'Admin email',
  lan_ip: 'LAN address',
  tz: 'Timezone',
  foundation_services: 'Foundation services',
  selected_services: 'Extra services',
  host_addons: 'Host add-ons',
  subdomains: 'Service addresses',
  'cloudflare.zone_in_cloudflare': 'Cloudflare zone',
  'cloudflare.auth_method': 'Cloudflare approval',
  'cloudflare.headless': 'Remote approval',
  'cloudflare.tunnel_strategy': 'Tunnel plan',
  'secrets.mode': 'Secret strategy',
}

function friendlySummaryLabel(key: string) {
  return summaryLabels[key] ?? key.replace(/[._-]+/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase())
}

function deploymentSummaryEntries(summary: SetupPhasePayload) {
  const summaryField = summary.fields.find((field) => field.id === 'deployment_summary')
  const value = summaryField ? summary.answers[summaryField.id] : null

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return []
  }

  return Object.entries(value as Record<string, unknown>).filter(([, entryValue]) => {
    if (entryValue === null || entryValue === undefined || entryValue === '') {
      return false
    }
    if (Array.isArray(entryValue)) {
      return entryValue.length > 0
    }
    if (typeof entryValue === 'object') {
      return Object.keys(entryValue).length > 0
    }
    return true
  })
}

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

        try {
          const summary = await fetchSetupPhase(6)
          if (cancelled) {
            return
          }

          setState({ status: 'ready', run, summary })
        } catch (error) {
          if (cancelled) {
            return
          }

          setState({
            status: 'ready',
            run,
            summary: null,
            summaryError: 'Some summary details could not be loaded. The final review screen can still be reopened.',
          })
        }
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

  async function handleProceed() {
    setIsStarting(true)
    setActionError(null)

    try {
      await submitSetupPhase(6, { answers: { confirmed: true } })
      await startSetupRun()
      navigate('/setup/run')
    } catch (error) {
      const message = error instanceof ApiError ? error.message : 'Unable to proceed with deployment right now.'
      setActionError(message)
    } finally {
      setIsStarting(false)
    }
  }

  function renderContent() {
    if (state.status === 'loading') {
      return (
        <p className="simple-loading" role="status">Loading...</p>
      )
    }

    if (state.status === 'error') {
      return (
        <section className="placeholder-card" aria-labelledby="setup-confirm-title">
          <p className="section-label">Deployment Summary</p>
          <h2 id="setup-confirm-title">Unable to prepare summary</h2>
          <p className="hero-text">{state.message}</p>
        </section>
      )
    }

    const run = state.run
    const entries = state.summary ? deploymentSummaryEntries(state.summary) : []

    if (!run.confirmed) {
      return (
        <section className="setup-deployment-summary" aria-labelledby="setup-confirm-title">
          <div className="setup-field-header">
            <div>
              <p className="section-label">Deployment Summary</p>
              <h2 id="setup-confirm-title">Proceed with deployment using the above configuration?</h2>
            </div>
          </div>
          {entries.length > 0 ? (
            <div className="setup-summary-grid">
              {entries.map(([key, value]) => (
                <div key={key} className="setup-summary-item">
                  <span>{friendlySummaryLabel(key)}</span>
                  <strong>{renderFieldValue(value)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <p className="hero-text">
              The deployment summary is not available yet. You can edit the final review, or proceed if your saved setup choices are already confirmed.
            </p>
          )}
          {state.summaryError ? <p className="setup-field-error">{state.summaryError}</p> : null}
          {actionError ? <p className="setup-submit-error">{actionError}</p> : null}
          <div className="setup-run-actions">
            <button type="button" className="bridge-button" onClick={() => navigate('/setup/phase/6')}>
              Edit summary
            </button>
            <button type="button" className="bridge-button bridge-button-primary" onClick={handleProceed} disabled={isStarting}>
              {isStarting ? 'Starting deployment...' : 'Proceed with deployment'}
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
          <p className="section-label">Deployment Summary</p>
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
      title="Deployment Summary"
      description="Review the saved configuration and decide whether to proceed with deployment."
      currentPhase={7}
    >
      {renderContent()}
    </SetupShell>
  )
}
