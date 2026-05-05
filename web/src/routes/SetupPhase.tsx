import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, fetchSetupPhase, submitSetupPhase } from '../api/client'
import type { SetupPhasePayload, SetupQuestionField, SetupServiceCatalogItem } from '../api/types'
import { FieldEditor } from '../components/FieldEditor'
import { fieldLabel, renderFieldValue } from '../components/FieldRenderer'
import { SetupShell } from '../components/SetupShell'

const phaseLabels: Record<number, { title: string; description: string }> = {
  1: {
    title: 'Choose Your Host',
    description: 'Tell Rakkib what kind of machine this server is running on.',
  },
  2: {
    title: 'Name Your Server',
    description: 'Set the public identity Rakkib will use for your services.',
  },
  3: {
    title: 'Pick Your Services',
    description: 'Build your self-hosted stack from friendly service cards.',
  },
  4: {
    title: 'Connect The Internet',
    description: 'Rakkib will prepare a Cloudflare tunnel handoff during launch.',
  },
  5: {
    title: 'Handle Secrets',
    description: 'Choose whether Rakkib should create passwords and keys for you.',
  },
  6: {
    title: 'Final Review',
    description: 'Review the friendly summary, then approve the launch.',
  },
}

type PhaseState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; payload: SetupPhasePayload }

type CatalogFieldKey = 'foundation_services' | 'optional_services' | 'host_addons'

function formatServiceSubdomain(item: SetupServiceCatalogItem) {
  return item.default_subdomain ? `${item.default_subdomain}.your domain` : 'Local or host tool'
}

function friendlyLabel(value: string) {
  const labels: Record<string, string> = {
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
    'cloudflare.auth_method': 'Cloudflare sign-in',
    'cloudflare.headless': 'Remote approval',
    'cloudflare.tunnel_strategy': 'Tunnel plan',
    'cloudflare.tunnel_name': 'Tunnel name',
    'cloudflare.ssh_subdomain': 'SSH address',
    'secrets.mode': 'Secret strategy',
  }

  return labels[value] ?? value.replace(/[._-]+/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase())
}

function friendlyScalar(value: unknown) {
  if (typeof value === 'boolean') {
    return value ? 'Ready' : 'Needs attention'
  }

  const text = String(value)
  const labels: Record<string, string> = {
    linux: 'Linux server',
    mac: 'Mac machine',
    amd64: 'AMD64',
    arm64: 'ARM64',
    sudo: 'Normal admin user',
    root: 'Root shell',
    on_demand: 'Ask only when needed',
    root_process: 'Direct admin setup',
    browser_login: 'Browser approval',
    new: 'Create a new tunnel',
    generate: 'Generate locally',
    manual: 'Use my values',
  }

  return labels[text] ?? text
}

function serviceInitials(item: SetupServiceCatalogItem) {
  const label = item.label ?? item.slug
  const words = label.replace(/\.[a-z]+$/i, '').split(/\s+|-/).filter(Boolean)
  const initials = words.length > 1 ? `${words[0][0]}${words[1][0]}` : label.slice(0, 2)
  return initials.toUpperCase()
}

function serviceTone(slug: string) {
  const tones = ['blue', 'green', 'amber', 'rose', 'violet', 'cyan']
  const index = Array.from(slug).reduce((total, char) => total + char.charCodeAt(0), 0) % tones.length
  return tones[index]
}

function serviceDescription(fieldId: CatalogFieldKey, item: SetupServiceCatalogItem) {
  const known: Record<string, string> = {
    nocodb: 'No-code database workspace',
    homepage: 'Your home dashboard',
    'uptime-kuma': 'Service health monitoring',
    dockge: 'Compose stack manager',
    n8n: 'Automation workflows',
    immich: 'Photo and video library',
    transfer: 'Simple file handoff',
    jellyfin: 'Personal media streaming',
    openclaw: 'AI control surface',
    adguard: 'Network ad blocking',
    vaultwarden: 'Password vault',
    forgejo: 'Git hosting',
    gitea: 'Git hosting',
    'open-webui': 'Local AI chat UI',
    'ollama-cpu': 'Local AI models',
    'ollama-amd': 'Local AI models',
    'ollama-nvidia': 'Local AI models',
  }

  if (known[item.slug]) {
    return known[item.slug]
  }
  if (fieldId === 'foundation_services') {
    return 'Recommended core service'
  }
  if (fieldId === 'host_addons') {
    return 'Runs directly on the host'
  }
  return 'Optional self-hosted app'
}

function ServiceMark({ item }: { item: SetupServiceCatalogItem }) {
  return (
    <span className={`setup-service-mark tone-${serviceTone(item.slug)}`} aria-hidden="true">
      <span>{serviceInitials(item)}</span>
    </span>
  )
}

function renderCatalogSection(
  title: string,
  eyebrow: string,
  fieldId: CatalogFieldKey,
  items: SetupServiceCatalogItem[] | undefined,
  selected: Set<string>,
  error: string | undefined,
  onToggle: (fieldId: CatalogFieldKey, slug: string) => void,
) {
  if (!items || items.length === 0) {
    return null
  }

  return (
    <article className="setup-service-section">
      <div className="setup-field-header">
        <div>
          <p className="section-label">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </div>

      <div className="setup-service-list" role="list">
        {items.map((item) => (
          <button
            key={item.slug}
            type="button"
            className={`setup-service-item${selected.has(item.slug) ? ' is-selected' : ''}`}
            onClick={() => onToggle(fieldId, item.slug)}
            role="listitem"
          >
            <ServiceMark item={item} />
            <span className="setup-service-copy">
              <strong>{item.label ?? item.slug}</strong>
              <span>{serviceDescription(fieldId, item)}</span>
            </span>
            <span className="setup-service-tags">
              <span className="setup-service-tag">{formatServiceSubdomain(item)}</span>
              <span className="setup-service-status">{selected.has(item.slug) ? 'Added' : 'Add'}</span>
            </span>
          </button>
        ))}
      </div>

      {error ? <p className="setup-field-error">{error}</p> : null}
    </article>
  )
}

function sanitizeBackendValue(phase: number, fieldId: string, value: unknown) {
  if (phase === 4 && fieldId === 'cloudflare_defaults' && value && typeof value === 'object' && !Array.isArray(value)) {
    const source = value as Record<string, unknown>
    const visibleEntries = Object.entries(source).filter(([key, entryValue]) => {
      if (entryValue === null || entryValue === undefined || entryValue === '') {
        return false
      }

      return ![
        'cloudflare.tunnel_uuid',
        'cloudflare.tunnel_creds_host_path',
        'cloudflare.tunnel_creds_container_path',
      ].includes(key)
    })

    return Object.fromEntries(visibleEntries)
  }

  return value
}

function renderBackendField(phase: number, field: SetupQuestionField, answer: unknown) {
  const value = sanitizeBackendValue(phase, field.id, answer)

  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return (
      <div key={field.id} className="setup-summary-card setup-summary-card-wide">
        <strong>{fieldLabel(field).replace(/\s*\[[^\]]*\]\s*$/, '')}</strong>
        <div className="setup-summary-grid">
          {Object.entries(value as Record<string, unknown>).map(([key, entryValue]) => (
            <div key={key} className="setup-summary-item">
              <span>{friendlyLabel(key)}</span>
              <strong>{renderFieldValue(entryValue)}</strong>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div key={field.id} className="setup-auto-chip">
      <span>{friendlyLabel(field.id)}</span>
      <strong>{friendlyScalar(value)}</strong>
    </div>
  )
}

export function SetupPhase() {
  const { phase } = useParams()
  const navigate = useNavigate()
  const phaseNumber = Number(phase)
  const [state, setState] = useState<PhaseState>({ status: 'loading' })
  const [draft, setDraft] = useState<Record<string, unknown>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [transferRiskAccepted, setTransferRiskAccepted] = useState(false)

  useEffect(() => {
    if (!Number.isInteger(phaseNumber) || phaseNumber < 1) {
      setState({ status: 'error', message: 'Unknown setup phase.' })
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const payload = await fetchSetupPhase(phaseNumber)
        if (cancelled) {
          return
        }

        setState({ status: 'ready', payload })
        setDraft(buildInitialDraft(payload))
        setFieldErrors({})
        setSubmitError(null)
        setTransferRiskAccepted(false)
      } catch (error) {
        if (cancelled) {
          return
        }

        const message = error instanceof Error ? error.message : 'Unable to load this setup phase.'
        setState({ status: 'error', message })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [phaseNumber])

  const page = phaseLabels[phaseNumber] ?? {
    title: `Phase ${phaseNumber}`,
    description: 'Review the current backend-provided phase data.',
  }

  if (state.status === 'loading') {
    return (
      <SetupShell title={page.title} description={page.description} currentPhase={phaseNumber}>
        <section className="placeholder-card bridge-card" aria-labelledby="setup-phase-loading-title">
          <p className="section-label">Setup Step</p>
          <h2 id="setup-phase-loading-title">Preparing this step</h2>
          <p className="hero-text">Loading your saved answers and the choices available for this server.</p>
          <div className="bridge-spinner" aria-hidden="true" />
        </section>
      </SetupShell>
    )
  }

  if (state.status === 'error') {
    return (
      <SetupShell title={page.title} description={page.description} currentPhase={phaseNumber}>
        <section className="placeholder-card bridge-card" aria-labelledby="setup-phase-error-title">
          <p className="section-label">Setup Step</p>
          <h2 id="setup-phase-error-title">Unable to open this step</h2>
          <p className="hero-text">{state.message}</p>
        </section>
      </SetupShell>
    )
  }

  const payload = state.payload
  const selectedServices = new Set<string>()
  const foundation = draft.foundation_services ?? payload.answers.foundation_services
  const selected = draft.optional_services ?? payload.answers.optional_services
  const hostAddons = draft.host_addons ?? payload.answers.host_addons
  const hasCatalogSelection = payload.phase === 3

  if (Array.isArray(foundation)) {
    foundation.forEach((item) => selectedServices.add(String(item)))
  }
  if (Array.isArray(selected)) {
    selected.forEach((item) => selectedServices.add(String(item)))
  }
  if (Array.isArray(hostAddons)) {
    hostAddons.forEach((item) => selectedServices.add(String(item)))
  }

  const editableFields = payload.fields.filter((field) => {
    if (field.repeat_for || ['derived', 'summary'].includes(field.type)) {
      return false
    }

    if (hasCatalogSelection && ['foundation_services', 'optional_services', 'host_addons'].includes(field.id)) {
      return false
    }

    return true
  })
  const readOnlyFields = payload.fields.filter((field) => field.repeat_for || ['derived', 'summary'].includes(field.type))
  const selectedValue = draft.optional_services
  const transferSelected = Array.isArray(selectedValue) && selectedValue.some((item) => String(item) === 'transfer')

  function toggleCatalogSelection(fieldId: CatalogFieldKey, slug: string) {
    setDraft((current) => {
      const existing = current[fieldId]
      const selectedValues = Array.isArray(existing)
        ? existing.map((item) => String(item))
        : []

      const nextValues = selectedValues.includes(slug)
        ? selectedValues.filter((item) => item !== slug)
        : [...selectedValues, slug]

      return { ...current, [fieldId]: nextValues }
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsSubmitting(true)
    setSubmitError(null)
    setFieldErrors({})

    try {
      const result = await submitSetupPhase(payload.phase, {
        answers: draft,
        confirmations: transferSelected ? { transfer_public_risk: transferRiskAccepted } : {},
      })

      if (result.resume_phase >= 7) {
        navigate('/setup/confirm')
        return
      }

      if (result.resume_phase === payload.phase) {
        setState({ status: 'ready', payload: result.phase })
        setDraft(buildInitialDraft(result.phase))
        setTransferRiskAccepted(false)
        return
      }

      navigate(`/setup/phase/${result.resume_phase}`)
    } catch (error) {
      if (error instanceof ApiError) {
        setSubmitError(error.message)
        setFieldErrors(error.fieldErrors ?? {})
      } else {
        setSubmitError('Unable to save this phase right now.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <SetupShell title={page.title} description={page.description} currentPhase={payload.phase}>
      <div className="setup-stage">
        <aside className="setup-stage-brief">
          <div className="setup-orbit" aria-hidden="true">
            <img src="/logo.png" alt="" width="72" height="72" />
            <span />
            <span />
            <span />
          </div>
          <p className="section-label">Step {payload.phase} of 6</p>
          <h2>{page.title}</h2>
          <p>{page.description}</p>
          <span className="badge">{payload.complete ? 'Saved' : 'In progress'}</span>
        </aside>

        <div className="setup-stage-work">
          {readOnlyFields.length > 0 ? (
            <article className="setup-field-card setup-phase-meta">
              <div className="setup-field-header">
                <div>
                  <p className="section-label">Prepared For You</p>
                  <h2>{payload.phase === 6 ? 'Deployment summary' : 'Automatic setup details'}</h2>
                </div>
              </div>

              <div className="setup-backend-state-list">
                {readOnlyFields.map((field) => renderBackendField(payload.phase, field, payload.answers[field.id]))}
              </div>
            </article>
          ) : null}

          {payload.service_catalog.foundation_bundle || payload.service_catalog.optional_services || payload.service_catalog.host_addons ? (
            <div className="setup-phase-stack setup-service-catalog">
            {renderCatalogSection(
              'Foundation Bundle',
              'Recommended Core',
              'foundation_services',
              payload.service_catalog.foundation_bundle,
              selectedServices,
              fieldErrors.foundation_services,
              toggleCatalogSelection,
            )}
            {renderCatalogSection(
              'Optional Services',
              'Add What You Need',
              'optional_services',
              payload.service_catalog.optional_services,
              selectedServices,
              fieldErrors.optional_services,
              toggleCatalogSelection,
            )}
            {renderCatalogSection(
              'Host Addons',
              'Machine Tools',
              'host_addons',
              payload.service_catalog.host_addons,
              selectedServices,
              fieldErrors.host_addons,
              toggleCatalogSelection,
            )}
            </div>
          ) : null}

          <form className="setup-phase-form" onSubmit={handleSubmit}>
            {submitError ? <p className="setup-submit-error">{submitError}</p> : null}

            {editableFields.map((field) => (
              <FieldEditor
                key={field.id}
                field={field}
                value={draft[field.id]}
                persistedAnswer={payload.answers[field.id]}
                error={fieldErrors[field.id]}
                onChange={(value) => setDraft((current) => ({ ...current, [field.id]: value }))}
              />
            ))}

            {transferSelected ? (
              <article className="setup-field-card setup-warning-card">
                <div className="setup-field-header">
                  <div>
                    <p className="section-label">Public Uploads</p>
                    <h2>transfer.sh is open to anyone with the link</h2>
                  </div>
                </div>
                <p className="hero-text">
                  This service is intentionally public and unauthenticated. Keep it selected only if you want an open upload endpoint.
                </p>
                <label className="setup-checkbox-row setup-native-check">
                  <input
                    type="checkbox"
                    checked={transferRiskAccepted}
                    onChange={(event) => setTransferRiskAccepted(event.target.checked)}
                  />
                  <span>I understand and want to include transfer.sh.</span>
                </label>
              </article>
            ) : null}
            <div className="setup-phase-actions">
              <button type="submit" className="bridge-button bridge-button-primary" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : payload.phase === 6 ? 'Approve launch' : 'Save and continue'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </SetupShell>
  )
}

function buildInitialDraft(payload: SetupPhasePayload) {
  const initial: Record<string, unknown> = {}

  const defaultFoundation = (payload.service_catalog.foundation_bundle ?? []).map((item) => item.slug)

  payload.fields.forEach((field) => {
    if (field.repeat_for || ['derived', 'summary'].includes(field.type)) {
      return
    }

    const answer = payload.answers[field.id]

    if (field.type === 'secret_group') {
      initial[field.id] = {}
      return
    }

    if (answer !== undefined && answer !== null) {
      initial[field.id] = answer
      return
    }

    if (field.id === 'foundation_services') {
      initial[field.id] = defaultFoundation
      return
    }

    if (field.id === 'optional_services' || field.id === 'host_addons') {
      initial[field.id] = []
      return
    }

    if (field.type === 'multi_select') {
      initial[field.id] = []
      return
    }

    if (field.type === 'confirm') {
      const acceptedValues = Object.values(field.accepted_inputs ?? {})
      if (acceptedValues.every((value) => typeof value === 'boolean')) {
        initial[field.id] = typeof field.default === 'boolean' ? field.default : false
      } else {
        initial[field.id] = ''
      }
      return
    }

    initial[field.id] = ''
  })

  return initial
}
