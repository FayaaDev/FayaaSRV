import { SetupShell } from '../components/SetupShell'

export function SetupRun() {
  return (
    <SetupShell
      title="Setup Runner"
      description="The execution screen will attach to the background pull runner and live event stream in the next backend/frontend phases."
    >
      <section className="placeholder-card" aria-labelledby="setup-run-title">
        <p className="section-label">Next Phase</p>
        <h2 id="setup-run-title">Live execution is not wired yet</h2>
        <p className="hero-text">
          This route remains reserved for streamed setup output once the mutating runner endpoints are implemented.
        </p>
      </section>
    </SetupShell>
  )
}
