import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, fetchSetupPhase, fetchSetupState, startSetupRun, submitSetupPhase } from '../api/client'
import type { SetupPhasePayload, SetupQuestionField, SetupServiceCatalogItem } from '../api/types'
import { FieldEditor } from '../components/FieldEditor'
import { fieldLabel, renderFieldValue } from '../components/FieldRenderer'
import { SetupShell } from '../components/SetupShell'
import { useI18n } from '../i18n/useI18n'

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
  | { status: 'ready'; payload: SetupPhasePayload; deploymentSucceeded: boolean }

type CatalogFieldKey = 'foundation_services' | 'optional_services' | 'host_addons'
type CatalogServiceItem = SetupServiceCatalogItem & { fieldId: CatalogFieldKey }

function formatServiceSubdomain(item: SetupServiceCatalogItem, subdomainSuffix: string, localOrHostTool: string) {
  return item.default_subdomain ? `${item.default_subdomain}${subdomainSuffix}` : localOrHostTool
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

function serviceDescription(
  fieldId: CatalogFieldKey,
  item: SetupServiceCatalogItem,
  labels: { recommendedCore: string; runsOnHost: string; optionalApp: string },
) {
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
    return labels.recommendedCore
  }
  if (fieldId === 'host_addons') {
    return labels.runsOnHost
  }
  return labels.optionalApp
}

function ServiceMark({ item }: { item: SetupServiceCatalogItem }) {
  return (
    <span className={`setup-service-mark tone-${serviceTone(item.slug)}`} aria-hidden="true">
      <span>{serviceInitials(item)}</span>
    </span>
  )
}

function catalogSearchText(item: CatalogServiceItem) {
  return [item.label, item.slug, item.category, item.default_subdomain]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

type CatalogCategoryProps = {
  title: string
  items: CatalogServiceItem[]
  selected: Set<string>
  onToggle: (fieldId: CatalogFieldKey, slug: string) => void
}

function CatalogCategory({ title, items, selected, onToggle }: CatalogCategoryProps) {
  const { t, tf, tc } = useI18n()
  const subdomainSuffix = t('serviceAddressSuffix')
  const localOrHostTool = t('localOrHostTool')
  const descriptionLabels = {
    recommendedCore: t('detailRecommendedCore'),
    runsOnHost: t('detailRunsOnHost'),
    optionalApp: t('detailOptionalApp'),
  }

  return (
    <article className="setup-service-section" key={title}>
      <div className="setup-field-header">
        <div>
          <p className="section-label">{tf(items.length === 1 ? 'serviceCountOne' : 'serviceCountMany', { count: items.length })}</p>
          <h2>{tc(title)}</h2>
        </div>
      </div>

      <div className="setup-service-list" role="list">
        {items.map((item) => (
          <button
            key={item.slug}
            type="button"
            className={`setup-service-item${selected.has(item.slug) ? ' is-selected' : ''}`}
            onClick={() => onToggle(item.fieldId, item.slug)}
            role="listitem"
          >
            <ServiceMark item={item} />
              <span className="setup-service-copy">
                <strong>{item.label ?? item.slug}</strong>
                <span>{serviceDescription(item.fieldId, item, descriptionLabels)}</span>
              </span>
              <span className="setup-service-tags">
                <span className="setup-service-tag">{formatServiceSubdomain(item, subdomainSuffix, localOrHostTool)}</span>
                <span className="setup-service-status">{selected.has(item.slug) ? t('statusAdded') : t('statusAdd')}</span>
              </span>
            </button>
        ))}
      </div>
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

function hasVisibleBackendValue(phase: number, field: SetupQuestionField, answer: unknown) {
  const value = sanitizeBackendValue(phase, field.id, answer)

  if (value === null || value === undefined || value === '') {
    return false
  }

  if (Array.isArray(value)) {
    return value.length > 0
  }

  if (typeof value === 'object') {
    return Object.keys(value).length > 0
  }

  return true
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
  const { t, tf } = useI18n()
  const phaseNumber = Number(phase)
  const invalidPhase = !Number.isInteger(phaseNumber) || phaseNumber < 1
  const [state, setState] = useState<PhaseState>({ status: 'loading' })
  const [draft, setDraft] = useState<Record<string, unknown>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serviceSearch, setServiceSearch] = useState('')

  useEffect(() => {
    if (invalidPhase) {
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const [payload, setupState] = await Promise.all([
          fetchSetupPhase(phaseNumber),
          fetchSetupState(),
        ])
        if (cancelled) {
          return
        }

        setState({ status: 'ready', payload, deploymentSucceeded: setupState.deployment_succeeded })
        setDraft(buildInitialDraft(payload))
        setFieldErrors({})
        setSubmitError(null)
        setServiceSearch('')
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
  }, [invalidPhase, phaseNumber])

  const page = phaseLabels[phaseNumber] ?? {
    title: `Phase ${phaseNumber}`,
    description: 'Review the current backend-provided phase data.',
  }

  if (invalidPhase) {
    return (
      <SetupShell title="Setup" description="Review the current backend-provided phase data." currentPhase={1}>
        <section className="placeholder-card bridge-card" aria-labelledby="setup-phase-error-title">
          <p className="section-label">Setup Step</p>
          <h2 id="setup-phase-error-title">Unable to open this step</h2>
          <p className="hero-text">Unknown setup phase.</p>
        </section>
      </SetupShell>
    )
  }

  if (state.status === 'loading') {
    return (
      <SetupShell title={page.title} description={page.description} currentPhase={phaseNumber}>
        <section className="setup-loading-state" aria-live="polite">
          <p className="simple-loading" role="status">Loading...</p>
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
  const deploymentSucceeded = state.deploymentSucceeded
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
  const visibleReadOnlyFields = readOnlyFields.filter((field) => hasVisibleBackendValue(payload.phase, field, payload.answers[field.id]))
  const hasServiceCatalog = Boolean(
    payload.service_catalog.foundation_bundle || payload.service_catalog.optional_services || payload.service_catalog.host_addons,
  )
  const serviceCatalogItems: CatalogServiceItem[] = [
    ...(payload.service_catalog.foundation_bundle ?? []).map((item) => ({ ...item, fieldId: 'foundation_services' as const })),
    ...(payload.service_catalog.optional_services ?? []).map((item) => ({ ...item, fieldId: 'optional_services' as const })),
    ...(payload.service_catalog.host_addons ?? []).map((item) => ({ ...item, fieldId: 'host_addons' as const })),
  ]
  const serviceSearchQuery = serviceSearch.trim().toLowerCase()
  const filteredCatalogItems = serviceSearchQuery
    ? serviceCatalogItems.filter((item) => catalogSearchText(item).includes(serviceSearchQuery))
    : serviceCatalogItems
  const serviceCategories = Array.from(
    filteredCatalogItems.reduce((groups, item) => {
      const category = item.category?.trim() || 'Other'
      groups.set(category, [...(groups.get(category) ?? []), item])
      return groups
    }, new Map<string, CatalogServiceItem[]>()),
  )

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
      const result = await submitSetupPhase(payload.phase, { answers: draft })

      if (payload.phase === 3 && deploymentSucceeded && result.resume_phase >= 7) {
        await submitSetupPhase(6, { answers: { confirmed: true } })
        await startSetupRun()
        navigate('/setup/run')
        return
      }

      if (result.resume_phase >= 7) {
        navigate('/setup/confirm')
        return
      }

      if (result.resume_phase === payload.phase) {
        setState({ status: 'ready', payload: result.phase, deploymentSucceeded: false })
        setDraft(buildInitialDraft(result.phase))
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
          <p className="section-label">Step {payload.phase} of 6</p>
          <h2>{page.title}</h2>
          <p>{page.description}</p>
          <span className="badge">{payload.complete ? 'Saved' : 'In progress'}</span>
        </aside>

        <div className="setup-stage-work">
          {visibleReadOnlyFields.length > 0 ? (
            <article className="setup-field-card setup-phase-meta">
              <div className="setup-field-header">
                <div>
                  <p className="section-label">Prepared For You</p>
                  <h2>{payload.phase === 6 ? 'Deployment summary' : 'Automatic setup details'}</h2>
                </div>
              </div>

              <div className="setup-backend-state-list">
                {visibleReadOnlyFields.map((field) => renderBackendField(payload.phase, field, payload.answers[field.id]))}
              </div>
            </article>
          ) : null}

          {payload.phase === 4 ? (
            <article className="setup-field-card setup-cloudflare-card">
              <div className="setup-field-header">
                <div>
                  <p className="section-label">Cloudflare Handoff</p>
                  <h2>No choices needed here</h2>
                </div>
              </div>
              <p className="hero-text">
                Rakkib will use a browser approval link during deployment, create a fresh tunnel, and route your selected services through Cloudflare.
              </p>
              <div className="setup-summary-grid">
                <div className="setup-summary-item">
                  <span>Approval</span>
                  <strong>Open Cloudflare login when prompted</strong>
                </div>
                <div className="setup-summary-item">
                  <span>Tunnel</span>
                  <strong>Create a new secure tunnel</strong>
                </div>
                <div className="setup-summary-item">
                  <span>Service URLs</span>
                  <strong>Use each selected subdomain</strong>
                </div>
              </div>
            </article>
          ) : null}

          {hasServiceCatalog ? (
            <div className="setup-phase-stack setup-service-catalog">
              <article className="setup-service-search-card">
                <div>
                  <p className="section-label">{t('serviceLibraryLabel')}</p>
                  <h2>{t('serviceSearchTitle')}</h2>
                </div>
                <input
                  className="setup-input setup-service-search"
                  type="search"
                  value={serviceSearch}
                  onChange={(event) => setServiceSearch(event.target.value)}
                  placeholder={t('serviceSearchPlaceholder')}
                  aria-label={t('serviceSearchAriaLabel')}
                />
                <p className="setup-field-help">
                  {tf('serviceSearchSummary', {
                    shown: filteredCatalogItems.length,
                    total: serviceCatalogItems.length,
                    categories: serviceCategories.length,
                  })}
                </p>
                {fieldErrors.foundation_services || fieldErrors.optional_services || fieldErrors.host_addons ? (
                  <p className="setup-field-error">
                    {fieldErrors.foundation_services ?? fieldErrors.optional_services ?? fieldErrors.host_addons}
                  </p>
                ) : null}
              </article>

              {serviceCategories.length > 0 ? (
                serviceCategories.map(([category, items]) => (
                  <CatalogCategory
                    key={category}
                    title={category}
                    items={items}
                    selected={selectedServices}
                    onToggle={toggleCatalogSelection}
                  />
                ))
              ) : (
                <article className="setup-service-section setup-service-empty">
                  <p className="section-label">{t('noMatchesLabel')}</p>
                  <h2>{t('noMatchesTitle')}</h2>
                  <p className="hero-text">{t('noMatchesHint')}</p>
                </article>
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

            <div className="setup-phase-actions">
              <button type="submit" className="bridge-button bridge-button-primary" disabled={isSubmitting}>
                {isSubmitting
                  ? payload.phase === 3 && deploymentSucceeded
                    ? 'Starting deployment...'
                    : 'Saving...'
                  : payload.phase === 3 && deploymentSucceeded
                    ? 'Deploy selected services'
                    : payload.phase === 6
                      ? 'Approve launch'
                      : 'Save and continue'}
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
