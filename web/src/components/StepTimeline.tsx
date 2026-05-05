import { NavLink } from 'react-router-dom'
import type { SetupPhaseSummary } from '../api/types'

const phaseLabels: Record<number, string> = {
  1: 'Platform',
  2: 'Identity',
  3: 'Services',
  4: 'Cloudflare',
  5: 'Secrets',
  6: 'Confirm',
}

type StepTimelineProps = {
  phases: SetupPhaseSummary[]
  currentPhase?: number
}

export function StepTimeline({ phases, currentPhase }: StepTimelineProps) {
  return (
    <nav className="setup-timeline" aria-label="Setup phases">
      <div className="setup-timeline-header">
        <p className="section-label">Installer Flow</p>
        <h2>Setup Phases</h2>
      </div>

      <ol className="setup-timeline-list">
        {phases.map((phase) => {
          const isCurrent = phase.phase === currentPhase
          const label = phaseLabels[phase.phase] ?? `Phase ${phase.phase}`

          return (
            <li key={phase.phase}>
              <NavLink
                to={phase.route}
                className={`setup-timeline-link${isCurrent ? ' is-current' : ''}${phase.complete ? ' is-complete' : ''}`}
              >
                <span className="setup-timeline-number">0{phase.phase}</span>
                <span className="setup-timeline-copy">
                  <strong>{label}</strong>
                  <span>{phase.complete ? 'Complete' : 'Pending'}</span>
                </span>
              </NavLink>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
