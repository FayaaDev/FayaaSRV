import type { SetupRunStatus } from '../api/types'

type HostAuthCardProps = {
  hostAuth: SetupRunStatus['host_auth']
  onRefresh: () => void
}

export function HostAuthCard({ hostAuth, onRefresh }: HostAuthCardProps) {
  if (hostAuth.ok) {
    return null
  }

  return (
    <article className="setup-field-card" aria-labelledby="host-auth-title">
      <div className="setup-field-header">
        <div>
          <p className="section-label">Action Required</p>
          <h2 id="host-auth-title">Host authorization required</h2>
        </div>
        <span className="setup-status-pill setup-status-pill-attention">Blocked</span>
      </div>

      <p className="hero-text">{hostAuth.message}</p>
      {hostAuth.command ? <code className="setup-link-code" dir="ltr">{hostAuth.command}</code> : null}
      <div className="setup-run-actions">
        <button type="button" className="bridge-button" onClick={onRefresh}>
          Recheck authorization
        </button>
      </div>
    </article>
  )
}
