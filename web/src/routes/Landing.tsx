import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchPublicServices, fetchSession, fetchSetupResume, fetchSetupRunStatus } from '../api/client'
import type { PublicService } from '../api/types'
import { LanguageToggle } from '../components/LanguageToggle'
import { ServiceMark } from '../components/ServiceMark'
import { useI18n } from '../i18n/useI18n'
import { SetupBridge } from './SetupBridge'

const installCommand = 'curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash'
const repoUrl = 'https://github.com/FayaaDev/Rakkib'

type PublicServiceItem = PublicService

type ServicesState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; services: PublicServiceItem[] }

function formatServiceSubdomain(item: PublicServiceItem, subdomainSuffix: string, localOrHostTool: string) {
  return item.default_subdomain ? `${item.default_subdomain}${subdomainSuffix}` : localOrHostTool
}

function catalogSearchText(item: PublicServiceItem) {
  // Search across raw catalog fields; keep this stable regardless of locale.
  return [
    item.name,
    item.id,
    item.category,
    item.default_subdomain,
    item.description,
    item.required ? 'required core' : null,
    item.foundation ? 'foundation' : null,
    item.host_service ? 'host addon' : null,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

function serviceStatusLabel(
  item: PublicServiceItem,
  labels: { required: string; foundation: string; optional: string },
) {
  if (item.required) {
    return labels.required
  }
  if (item.foundation) {
    return labels.foundation
  }
  return labels.optional
}

function serviceDetail(
  item: PublicServiceItem,
  ts: (key: string) => string,
  labels: { alwaysInstalled: string; runsOnHost: string; optionalApp: string },
) {
  const localized = item.name ? ts(item.name) : null
  if (localized && localized !== item.name) return localized
  if (item.description) return item.description

  if (item.required) {
    return labels.alwaysInstalled
  }

  if (item.host_service) {
    return labels.runsOnHost
  }

  return labels.optionalApp
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 .5a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.4-4-1.4-.5-1.3-1.3-1.7-1.3-1.7-1.1-.7.1-.7.1-.7 1.2.1 1.9 1.3 1.9 1.3 1 .1.7 2.9 3.2 2.1.1-.8.4-1.4.8-1.7-2.7-.3-5.5-1.3-5.5-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.6.1-3.2 0 0 1-.3 3.3 1.2a11.3 11.3 0 0 1 6 0C17 6 18 6.3 18 6.3c.6 1.6.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.8 5.6-5.5 5.9.5.4.9 1.2.9 2.4v3.6c0 .3.2.7.8.6A12 12 0 0 0 12 .5Z" />
    </svg>
  )
}

export function Landing() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t, tf, ts, tc } = useI18n()
  const [copied, setCopied] = useState(false)
  const [serviceSearch, setServiceSearch] = useState('')
  const [servicesState, setServicesState] = useState<ServicesState>({ status: 'loading' })

  const subdomainSuffix = t('subdomainSuffix')
  const localOrHostTool = t('localOrHostTool')
  const statusLabels = {
    required: t('statusRequired'),
    foundation: t('statusFoundation'),
    optional: t('statusOptional'),
  }
  const detailLabels = {
    alwaysInstalled: t('detailAlwaysInstalled'),
    runsOnHost: t('detailRunsOnHost'),
    optionalApp: t('detailOptionalApp'),
  }

  const params = new URLSearchParams(location.search)
  const isTokenBootstrap = params.has('token')

  useEffect(() => {
    if (isTokenBootstrap) {
      return
    }

    let cancelled = false

    void (async () => {
      try {
        await fetchSession()
        const resume = await fetchSetupResume()
        if (cancelled) {
          return
        }

        if (resume.resume_phase >= 7) {
          const run = await fetchSetupRunStatus()
          if (cancelled) {
            return
          }

          if (run.running) {
            navigate('/setup/run', { replace: true })
            return
          }

          if (resume.deployment_succeeded) {
            navigate('/setup/phase/3', { replace: true })
            return
          }

          navigate('/setup/confirm', { replace: true })
          return
        }

        navigate(`/setup/phase/${resume.resume_phase}`, { replace: true })
      } catch {
        // Stay on the public landing page when there is no active authenticated session.
      }
    })()

    return () => {
      cancelled = true
    }
  }, [isTokenBootstrap, navigate])

  useEffect(() => {
    if (isTokenBootstrap) {
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const payload = await fetchPublicServices()
        if (cancelled) {
          return
        }
        setServicesState({ status: 'ready', services: payload.services })
      } catch (error) {
        if (cancelled) {
          return
        }
        const message = error instanceof Error ? error.message : 'Unable to load services right now.'
        setServicesState({ status: 'error', message })
      }
    })()

    return () => {
      cancelled = true
    }
  }, [isTokenBootstrap])

  if (isTokenBootstrap) {
    return <SetupBridge />
  }

  async function copyInstallCommand() {
    await navigator.clipboard.writeText(installCommand)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="shell">
      <header className="site-header">
        <a className="brand" href="#top" aria-label={t('brandLabel')}>
          <img className="brand-logo" src="/logo.png" alt="Rakkib logo" width="28" height="28" />
          [rakkib]
        </a>
        <div className="site-nav">
          <LanguageToggle />
          <a className="github-link" href={repoUrl} target="_blank" rel="noreferrer" aria-label="Rakkib on GitHub">
            <GitHubIcon />
            <span>{t('github')}</span>
          </a>
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <img className="hero-logo" src="/logo-hero.png" alt="Rakkib" width="240" height="240" />
          <h1 id="hero-title">{t('heroTitle')}</h1>
          <p className="hero-text">{t('heroText')}</p>

          <div className="install-box" aria-label="Install command">
            <code>{installCommand}</code>
            <button type="button" onClick={copyInstallCommand} aria-live="polite" style={{ direction: 'ltr' }}>
              {copied ? t('copied') : t('copy')}
            </button>
          </div>
          <p className="install-note">{t('installNote')}</p>
        </section>

        <section className="services" aria-labelledby="services-title">
          <p className="section-label">{t('sectionLabel')}</p>
          <h2 id="services-title">{t('servicesTitle')}</h2>

          {servicesState.status === 'loading' ? (
            <p className="simple-loading" role="status">Loading...</p>
          ) : null}

          {servicesState.status === 'error' ? (
            <article className="setup-service-section setup-service-empty">
              <p className="section-label">Services</p>
              <h2>Unable to load services</h2>
              <p className="hero-text">{servicesState.message}</p>
            </article>
          ) : null}

          {servicesState.status === 'ready' ? (() => {
            const allItems = servicesState.services
            const serviceSearchQuery = serviceSearch.trim().toLowerCase()
            const filteredItems = serviceSearchQuery
              ? allItems.filter((item) => catalogSearchText(item).includes(serviceSearchQuery))
              : allItems

            const serviceCategories = Array.from(
              filteredItems.reduce((groups, item) => {
                const category = item.category?.trim() || 'Other'
                groups.set(category, [...(groups.get(category) ?? []), item])
                return groups
              }, new Map<string, PublicServiceItem[]>()),
            )

            return (
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
                      shown: filteredItems.length,
                      total: allItems.length,
                      categories: serviceCategories.length,
                    })}
                  </p>
                </article>

                {serviceCategories.length > 0 ? (
                  serviceCategories.map(([category, items]) => (
                    <article className="setup-service-section" key={category}>
                      <div className="setup-field-header">
                        <div>
                          <p className="section-label">
                            {tf(items.length === 1 ? 'serviceCountOne' : 'serviceCountMany', { count: items.length })}
                          </p>
                          <h2>{tc(category)}</h2>
                        </div>
                      </div>

                      <div className="setup-service-list" role="list">
                        {items.map((item) => (
                          <article
                            key={item.id}
                            className="setup-service-item"
                            role="listitem"
                            style={{ cursor: 'default' }}
                          >
                            <ServiceMark slug={item.id} label={item.name ?? item.id} />
                            <span className="setup-service-copy">
                              <strong>{item.name ?? item.id}</strong>
                              <span>{serviceDetail(item, ts, detailLabels)}</span>
                            </span>
                            <span className="setup-service-tags">
                              <span className="setup-service-tag">{formatServiceSubdomain(item, subdomainSuffix, localOrHostTool)}</span>
                              <span className="setup-service-tag">{serviceStatusLabel(item, statusLabels)}</span>
                              {item.host_service ? <span className="setup-service-tag">{t('tagHost')}</span> : null}
                            </span>
                          </article>
                        ))}
                      </div>
                    </article>
                  ))
                ) : (
                  <article className="setup-service-section setup-service-empty">
                    <p className="section-label">{t('noMatchesLabel')}</p>
                    <h2>{t('noMatchesTitle')}</h2>
                    <p className="hero-text">{t('noMatchesHint')}</p>
                  </article>
                )}
              </div>
            )
          })() : null}
        </section>
      </main>
    </div>
  )
}
