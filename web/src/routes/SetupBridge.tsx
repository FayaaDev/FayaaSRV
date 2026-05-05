import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { bootstrapSession } from '../api/client'

const recoveryCommand = 'rakkib web --lan'

type BridgeState =
  | { status: 'loading' }
  | { status: 'error'; title: string; message: string }

function stripTokenFromVisibleUrl(search: string, pathname: string, hash: string) {
  const params = new URLSearchParams(search)
  params.delete('token')
  const nextSearch = params.toString()
  const nextUrl = `${pathname}${nextSearch ? `?${nextSearch}` : ''}${hash}`
  window.history.replaceState(window.history.state, '', nextUrl)
}

export function SetupBridge() {
  const location = useLocation()
  const navigate = useNavigate()
  const [state, setState] = useState<BridgeState>({ status: 'loading' })

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const token = params.get('token')?.trim()

    if (token) {
      // Persist token for subsequent setup pages (we remove it from the visible URL).
      sessionStorage.setItem('rakkib_setup_token', token)
      sessionStorage.setItem('rakkib_setup_url', `${window.location.origin}/?token=${encodeURIComponent(token)}`)
    }

    stripTokenFromVisibleUrl(location.search, location.pathname, location.hash)

    if (!token) {
      setState({
        status: 'error',
        title: 'Missing setup token',
        message: 'Open the printed setup URL again, or restart the local web session to generate a fresh token.',
      })
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const result = await bootstrapSession(token)

        if (cancelled) {
          return
        }

        if (result.ok) {
          navigate('/setup', { replace: true })
          return
        }

        setState({
          status: 'error',
          title: 'Setup token was rejected',
          message:
            result.message ??
            'This setup link is invalid, stale, or no longer matches the active `rakkib web` process.',
        })
      } catch {
        if (cancelled) {
          return
        }

        setState({
          status: 'error',
          title: 'Unable to connect to the setup session',
          message: 'The local web backend did not complete session bootstrap. Make sure `rakkib web --lan` is running and retry the printed URL.',
        })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [location.hash, location.pathname, location.search, navigate])

  if (state.status === 'loading') {
    return (
      <main className="shell route-placeholder">
        <p className="simple-loading" role="status">Loading...</p>
      </main>
    )
  }

  return (
    <main className="shell route-placeholder">
      <section className="placeholder-card bridge-card" aria-labelledby="setup-bridge-title">
        <p className="section-label">Setup Access</p>
        <h1 id="setup-bridge-title">{state.title}</h1>
        <p className="hero-text">{state.message}</p>

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
