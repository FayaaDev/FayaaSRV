import { SetupShell } from '../components/SetupShell'

export function SetupConfirm() {
  return (
    <SetupShell
      title="Run Confirmation"
      description="The save-and-run phases are still being wired. The backend can now drive read-only setup navigation through the real phase data."
    >
      <section className="placeholder-card" aria-labelledby="setup-confirm-title">
        <p className="section-label">Next Phase</p>
        <h2 id="setup-confirm-title">Confirmation and execution are next</h2>
        <p className="hero-text">
          This route stays reserved for the final confirmation screen and setup runner. Use the phase timeline to inspect the live backend state now.
        </p>
      </section>
    </SetupShell>
  )
}
