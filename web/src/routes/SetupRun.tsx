import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import QRCode from 'qrcode'
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
  const navigate = useNavigate()
  const [state, setState] = useState<RunScreenState>({ status: 'loading' })
  const [actionError, setActionError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)
  const [showLog, setShowLog] = useState(false)

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

  function handleCheckProgress() {
    setShowLog(true)
    setReloadToken((current) => current + 1)
  }

  function renderContent() {
    if (state.status === 'loading') {
      return (
        <p className="simple-loading" role="status">Loading...</p>
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
      <div className="setup-phase-stack">
        {run.attention?.type === 'cloudflare_auth' ? <CloudflareAuthPrompt url={run.attention.url} /> : null}

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
              <button type="button" className="bridge-button" onClick={handleCheckProgress}>
                {showLog ? 'Refresh log' : 'Check progress'}
              </button>
              <button type="button" className="bridge-button" onClick={() => navigate('/setup/confirm')}>
                Launch screen
              </button>
            </div>
          </div>
        </section>

        {showLog ? (
          <article className="setup-field-card setup-log-panel">
            <div className="setup-field-header">
              <div>
                <p className="section-label">Terminal Log</p>
                <h2>Latest setup output</h2>
              </div>
              <span className="badge">{run.running ? 'Live' : 'Snapshot'}</span>
            </div>
            <pre className="setup-run-log">{run.log_tail.length > 0 ? run.log_tail.join('\n') : 'No log output yet.'}</pre>
          </article>
        ) : null}
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
