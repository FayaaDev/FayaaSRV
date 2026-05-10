import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { ApiError, fetchSetupRunStatus, startSetupRun } from '../api/client'
import type { SetupRunStatus } from '../api/types'
import { HostAuthCard } from '../components/HostAuthCard'
import { SetupShell } from '../components/SetupShell'

function progressSteps(run: SetupRunStatus) {
  if (run.operation === 'service_sync') {
    return ['Loading saved selection', 'Applying service changes', 'Reloading routes', 'Finishing sync']
  }
  return ['Preparing machine', 'Creating secure access', 'Starting services', 'Final checks']
}
const ansiPattern = new RegExp(`${String.fromCharCode(27)}\\[[0-9;]*m`, 'g')

function statusTitle(run: SetupRunStatus) {
  const isServiceSync = run.operation === 'service_sync'
  if (run.status === 'running') {
    return isServiceSync ? 'Updating your services' : 'Installing your server stack'
  }
  if (run.status === 'succeeded') {
    return isServiceSync ? 'Service update complete' : 'Setup complete'
  }
  if (run.status === 'failed') {
    return isServiceSync ? 'Service update needs attention' : 'Setup needs attention'
  }
  return isServiceSync ? 'Ready to update services' : 'Ready when you are'
}

function statusCopy(run: SetupRunStatus) {
  const isServiceSync = run.operation === 'service_sync'
  if (run.status === 'running') {
    return isServiceSync
      ? 'Rakkib is syncing your saved service selection without re-running the full machine setup.'
      : 'Rakkib is preparing the machine, connecting the tunnel, and starting your selected services.'
  }
  if (run.status === 'succeeded') {
    return isServiceSync
      ? 'Your service selection finished syncing. You can now open your updated services from their configured domains.'
      : 'Your setup finished successfully. You can now open your services from their configured domains.'
  }
  if (run.status === 'failed') {
    return isServiceSync
      ? 'Service syncing stopped before completion. Keep this session open and retry after checking your saved choices.'
      : 'Setup stopped before completion. Keep this session open and retry after checking your saved choices.'
  }
  return isServiceSync
    ? 'Apply your saved service changes when you are ready.'
    : 'Start setup to let Rakkib prepare the host and launch your services.'
}

function activityTone(line: string) {
  const lower = line.toLowerCase()
  if (lower.startsWith('wrn ') || lower.includes(' wrn ')) {
    return 'attention'
  }
  if (lower.includes('error') || lower.includes('failed') || lower.includes('exited with errors')) {
    return 'error'
  }
  if (lower.includes('success') || lower.includes('completed') || lower.includes('finished') || lower.includes('deployed services')) {
    return 'success'
  }
  if (lower.includes('waiting') || lower.includes('cloudflare') || lower.includes('approve')) {
    return 'attention'
  }
  return 'info'
}

function activityLines(run: SetupRunStatus) {
  const lines = run.log_tail
    .map((line) => line.replace(ansiPattern, '').trim())
    .filter(Boolean)
    .slice(-80)

  if (lines.length > 0) {
    return lines
  }

  if (run.status === 'idle') {
    return ['Deployment has not started yet.']
  }
  if (run.status === 'running') {
    return ['Deployment is starting. Activity will appear here automatically.']
  }
  return [run.message]
}

type RunScreenState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; run: SetupRunStatus }

type CloudflareAuthPromptProps = {
  url: string
}

function CloudflareAuthPrompt({ url }: CloudflareAuthPromptProps) {
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle')

  useEffect(() => {
    let cancelled = false

    void (async () => {
      try {
        const dataUrl = await QRCode.toDataURL(url, {
          errorCorrectionLevel: 'L',
          margin: 4,
          scale: 7,
        })
        if (!cancelled) {
          setQrDataUrl(dataUrl)
        }
      } catch {
        if (!cancelled) {
          setQrDataUrl(null)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [url])

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(url)
      setCopyState('copied')
      window.setTimeout(() => setCopyState('idle'), 1400)
    } catch {
      setCopyState('error')
      window.setTimeout(() => setCopyState('idle'), 1800)
    }
  }

  return (
    <article className="setup-field-card setup-cloudflare-auth" aria-labelledby="cloudflare-auth-title">
      <div className="setup-field-header">
        <div>
          <p className="section-label">Action Required</p>
          <h2 id="cloudflare-auth-title">Approve Cloudflare access</h2>
        </div>
        <span className="setup-status-pill setup-status-pill-attention">Waiting for you</span>
      </div>

      <div className="setup-cloudflare-grid">
        <div className="setup-cloudflare-qr" aria-hidden="true">
          {qrDataUrl ? <img src={qrDataUrl} alt="" loading="eager" decoding="async" /> : null}
        </div>
        <div className="setup-cloudflare-copy">
          <p className="hero-text">
            Scan this QR code or open the Cloudflare link to approve the domain. Keep this browser open; setup will continue after Cloudflare finishes the login.
          </p>
          <div className="setup-run-actions">
            <a className="bridge-button bridge-button-primary" href={url} target="_blank" rel="noreferrer">
              Open Cloudflare
            </a>
            <button type="button" className="bridge-button" onClick={handleCopy}>
              {copyState === 'copied' ? 'Copied' : copyState === 'error' ? 'Copy failed' : 'Copy link'}
            </button>
          </div>
          <code className="setup-link-code" dir="ltr">{url}</code>
        </div>
      </div>
    </article>
  )
}

export function SetupRun() {
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
      const mode = state.status === 'ready' ? state.run.operation : 'full_setup'
      const run = await startSetupRun(mode)
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

  function handleRefreshActivity() {
    setReloadToken((current) => current + 1)
  }

  function renderContent() {
    if (state.status === 'loading') {
      return (
        <section className="setup-loading-state" aria-live="polite">
          <p className="simple-loading" role="status">Loading...</p>
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

    const steps = progressSteps(run)
    const activeIndex = run.status === 'succeeded' ? steps.length : run.status === 'running' ? 2 : run.status === 'failed' ? 1 : 0
    const lines = activityLines(run)

    return (
      <div className="setup-phase-stack">
        {run.attention?.type === 'cloudflare_auth' ? <CloudflareAuthPrompt url={run.attention.url} /> : null}
        <HostAuthCard hostAuth={run.host_auth} onRefresh={handleRefreshActivity} />

        <section className="setup-progress-card" aria-labelledby="setup-run-title">
          <div className="setup-progress-visual" aria-hidden="true">
            <div className={`setup-launch-ring is-${run.status}`}>
              <img src="/logo-hero.png" alt="" width="144" height="144" />
            </div>
          </div>

          <div className="setup-progress-copy">
            <p className="section-label">Progress</p>
            <h2 id="setup-run-title">{statusTitle(run)}</h2>
            <p className="hero-text">{statusCopy(run)}</p>
            <span className={`setup-status-pill is-${run.status}`}>{run.status}</span>

            <div className="setup-progress-steps" aria-label="Setup progress steps">
              {steps.map((step, index) => (
                <div key={step} className={`setup-progress-step${index < activeIndex ? ' is-done' : ''}${index === activeIndex && run.running ? ' is-active' : ''}`}>
                  <span />
                  <strong>{step}</strong>
                </div>
              ))}
            </div>

            {actionError ? <p className="setup-submit-error">{actionError}</p> : null}

            <div className="setup-run-actions">
              {run.can_start && run.status !== 'succeeded' ? (
                <button type="button" className="bridge-button bridge-button-primary" onClick={handleStart} disabled={isStarting}>
                  {isStarting ? 'Starting...' : run.status === 'idle' ? 'Launch setup' : 'Try again'}
                </button>
              ) : null}
              <button type="button" className="bridge-button" onClick={handleRefreshActivity}>
                Refresh activity
              </button>
            </div>
          </div>
        </section>

        {run.status === 'succeeded' && run.deployed_urls.length > 0 ? (
          <article className="setup-field-card setup-deployed-services">
            <div className="setup-field-header">
              <div>
                <p className="section-label">Service URLs</p>
                <h2>Your deployed subdomains</h2>
              </div>
              <span className="badge">Ready</span>
            </div>
            <div className="setup-url-grid">
              {run.deployed_urls.map((item) => (
                <a key={item.service} className="setup-url-card" href={item.url} target="_blank" rel="noreferrer">
                  <span>{item.label}</span>
                  <strong>{item.url}</strong>
                </a>
              ))}
            </div>
          </article>
        ) : null}

        <article className="setup-field-card setup-log-panel">
          <div className="setup-field-header">
            <div>
              <p className="section-label">Built-in Logs</p>
              <h2>Setup activity</h2>
            </div>
            <span className="badge">{run.running ? 'Live' : 'Snapshot'}</span>
          </div>
          <div className="setup-activity-log" role="log" aria-live={run.running ? 'polite' : 'off'}>
            {lines.map((line, index) => (
              <div key={`${index}-${line}`} className={`setup-activity-row is-${activityTone(line)}`}>
                <span aria-hidden="true" />
                <p>{line}</p>
              </div>
            ))}
          </div>
        </article>
      </div>
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
