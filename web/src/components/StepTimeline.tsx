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

const phaseHints: Record<number, string> = {
  1: 'Host basics',
  2: 'Name and domain',
  3: 'Pick apps',
  4: 'Public access',
  5: 'Passwords',
  6: 'Review',
  7: 'Launch',
}

type StepTimelineProps = {
  phases: SetupPhaseSummary[]
  currentPhase?: number
}

export function StepTimeline({ phases, currentPhase }: StepTimelineProps) {
  const launchComplete = currentPhase === 8
  const timeline = [
    ...phases,
    {
      phase: 7,
      complete: launchComplete,
      writes_state: [],
      has_service_catalog: false,
      route: '/setup/confirm',
    },
  ]

  return (
    <nav className="setup-timeline" aria-label="Setup phases">
      <div className="setup-timeline-header">
        <p className="section-label">Setup Flow</p>
        <h2>Choose, review, launch</h2>
      </div>

      <ol className="setup-timeline-list">
        {timeline.map((phase) => {
          const isCurrent = phase.phase === currentPhase
          const label = phaseLabels[phase.phase] ?? `Phase ${phase.phase}`
          const state = isCurrent ? 'Current' : phase.complete ? 'Done' : 'Next'

          return (
            <li key={phase.phase}>
              <NavLink
                to={phase.route}
                className={`setup-timeline-link${isCurrent ? ' is-current' : ''}${phase.complete ? ' is-complete' : ''}`}
              >
                <span className="setup-timeline-number">{phase.complete ? 'OK' : `0${phase.phase}`}</span>
                <span className="setup-timeline-copy">
                  <strong>{label}</strong>
                  <span>{phaseHints[phase.phase] ?? state}</span>
                </span>
                <span className="setup-timeline-state">{state}</span>
              </NavLink>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
