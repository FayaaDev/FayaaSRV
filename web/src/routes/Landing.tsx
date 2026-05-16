import { useEffect, useState, type CSSProperties } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { fetchPublicServices, fetchSession, fetchSetupResume, fetchSetupRunStatus } from '../api/client'
import type { PublicService } from '../api/types'
import { LanguageToggle } from '../components/LanguageToggle'
import { Marquee } from '../components/MagicMarquee'
import { ServiceMark } from '../components/ServiceMark'
import { SmoothCursor } from '../components/SmoothCursor'
import { useI18n } from '../i18n/useI18n'
import { SetupBridge } from './SetupBridge'

const installCommand = 'curl -fsSL https://install.rakkib.app | bash'
const repoUrl = 'https://github.com/FayaaDev/Rakkib'
const demoVideoUrl = 'https://github.com/user-attachments/assets/5d57317f-0d64-4bf3-90c7-89a2cbbac547'

type PublicServiceItem = PublicService

type ServicesState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; services: PublicServiceItem[] }

function formatServiceSubdomain(item: PublicServiceItem, subdomainSuffix: string) {
  return item.default_subdomain ? `${item.default_subdomain}${subdomainSuffix}` : null
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

function distributeServices(items: PublicServiceItem[], columnCount: number) {
  const safeColumnCount = Math.max(1, Math.min(columnCount, Math.max(items.length, 1)))
  const columns = Array.from({ length: safeColumnCount }, () => [] as PublicServiceItem[])
  items.forEach((item, index) => columns[index % safeColumnCount].push(item))
  return columns
}

function ServiceCatalogCard({
  item,
  subdomainSuffix,
  ts,
  tc,
  detailLabels,
}: {
  item: PublicServiceItem
  subdomainSuffix: string
  ts: (key: string) => string
  tc: (key: string) => string
  detailLabels: { alwaysInstalled: string; runsOnHost: string; optionalApp: string }
}) {
  const serviceSubdomain = formatServiceSubdomain(item, subdomainSuffix)
  const label = item.name ?? item.id

  return (
    <article className="catalog-service-card">
      <ServiceMark slug={item.id} label={label} />
      <span className="catalog-service-copy">
        <strong>{label}</strong>
        <span>{serviceDetail(item, ts, detailLabels)}</span>
      </span>
      <span className="catalog-service-meta">
        <span>{tc(item.category?.trim() || 'Other')}</span>
        {serviceSubdomain ? <span dir="ltr">{serviceSubdomain}</span> : null}
      </span>
    </article>
  )
}

function ServicesMarquee3D({
  services,
  subdomainSuffix,
  ts,
  tc,
  detailLabels,
}: {
  services: PublicServiceItem[]
  subdomainSuffix: string
  ts: (key: string) => string
  tc: (key: string) => string
  detailLabels: { alwaysInstalled: string; runsOnHost: string; optionalApp: string }
}) {
  const columns = distributeServices(services, 4)
  const shouldRepeat = services.length > 6
  const densityClass = services.length <= 2 ? ' is-sparse' : shouldRepeat ? '' : ' is-static'

  return (
    <div className={`services-marquee-3d${densityClass}`} aria-label="Animated service catalog">
      <div
        className="services-marquee-tilt"
        style={{ '--service-column-count': columns.length } as CSSProperties}
      >
        {columns.map((column, index) => (
          <Marquee
            key={index}
            className={`services-marquee-column${shouldRepeat ? '' : ' services-marquee-column-static'}`}
            vertical
            reverse={index % 2 === 1}
            pauseOnHover
            repeat={shouldRepeat ? 3 : 1}
            style={{ '--marquee-duration': `${34 + index * 7}s` } as CSSProperties}
          >
            {column.map((item) => (
              <ServiceCatalogCard
                key={item.id}
                item={item}
                subdomainSuffix={subdomainSuffix}
                ts={ts}
                tc={tc}
                detailLabels={detailLabels}
              />
            ))}
          </Marquee>
        ))}
      </div>
      <div className="services-marquee-fade services-marquee-fade-top" />
      <div className="services-marquee-fade services-marquee-fade-bottom" />
      <div className="services-marquee-fade services-marquee-fade-start" />
      <div className="services-marquee-fade services-marquee-fade-end" />
    </div>
  )
}

export function Landing() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t, tf, ts, tc } = useI18n()
  const [copied, setCopied] = useState(false)
  const [serviceSearch, setServiceSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [servicesState, setServicesState] = useState<ServicesState>({ status: 'loading' })

  const subdomainSuffix = t('subdomainSuffix')
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
    <div className="shell marketing-shell">
      <SmoothCursor />
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
        <section className="landing-hero" aria-labelledby="hero-title">
          <div className="landing-hero-copy">
            <p className="eyebrow">{t('heroEyebrow')}</p>
            <h1 id="hero-title">{t('heroTitle')}</h1>
            <p className="hero-text">{t('heroText')}</p>

            <div className="install-box marketing-install-box" aria-label="Install command">
              <code>{installCommand}</code>
              <button type="button" onClick={copyInstallCommand} aria-live="polite" style={{ direction: 'ltr' }}>
                {copied ? t('copied') : t('copy')}
              </button>
            </div>
            <p className="install-note">{t('installNote')}</p>

            <div className="hero-actions">
              <a className="bridge-button bridge-button-primary" href="#services">
                {t('heroPrimaryAction')}
              </a>
            </div>
          </div>

          <div className="landing-hero-visual" aria-hidden="true">
            <div className="hero-logo-stage">
              <img className="hero-logo" src="/logo-hero.png" alt="" width="240" height="240" />
            </div>
          </div>
        </section>

        <section id="demo" className="demo-showcase marketing-demo" aria-label="Rakkib demo">
          <div className="demo-frame">
            <video
              className="demo-video"
              src={demoVideoUrl}
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              aria-label="Rakkib setup demo"
            />
          </div>
        </section>

        <section id="services" className="services marketing-services" aria-labelledby="services-title">
          <p className="section-label">{t('sectionLabel')}</p>
          <h2 id="services-title">{t('servicesTitle')}</h2>
          <p className="services-intro">{t('catalogIntro')}</p>

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
            const activeCategory = serviceCategories.some(([category]) => category === selectedCategory)
              ? selectedCategory
              : null
            const activeCategoryItems = activeCategory
              ? serviceCategories.find(([category]) => category === activeCategory)?.[1] ?? []
              : filteredItems

            return (
              <div className="catalog-showcase">
                <article className="catalog-search-card">
                  <div>
                    <p className="section-label">{t('serviceLibraryLabel')}</p>
                    <h2>{t('serviceSearchTitle')}</h2>
                  </div>
                  <input
                    className="setup-input catalog-service-search"
                    type="search"
                    value={serviceSearch}
                    onChange={(event) => setServiceSearch(event.target.value)}
                    placeholder={t('serviceSearchPlaceholder')}
                    aria-label={t('serviceSearchAriaLabel')}
                  />
                  <p className="setup-field-help catalog-search-summary">
                    {tf('serviceSearchSummary', {
                      shown: filteredItems.length,
                      total: allItems.length,
                      categories: serviceCategories.length,
                    })}
                  </p>
                </article>

                {serviceCategories.length > 0 ? (
                  <>
                    <div className="catalog-category-rail" aria-label={t('categoriesLabel')}>
                      {serviceCategories.map(([category, items]) => (
                        <button
                          className={`catalog-category-chip${category === activeCategory ? ' is-active' : ''}`}
                          type="button"
                          key={category}
                          aria-pressed={category === activeCategory}
                          onClick={() => setSelectedCategory((current) => (current === category ? null : category))}
                        >
                          <strong>{tc(category)}</strong>
                          <span>{tf(items.length === 1 ? 'serviceCountOne' : 'serviceCountMany', { count: items.length })}</span>
                        </button>
                      ))}
                    </div>

                    <div className="catalog-interactive-stage">
                      <ServicesMarquee3D
                        services={activeCategoryItems}
                        subdomainSuffix={subdomainSuffix}
                        ts={ts}
                        tc={tc}
                        detailLabels={detailLabels}
                      />
                      <div className="catalog-mobile-list" role="list">
                        {activeCategoryItems.map((item) => (
                          <ServiceCatalogCard
                            key={item.id}
                            item={item}
                            subdomainSuffix={subdomainSuffix}
                            ts={ts}
                            tc={tc}
                            detailLabels={detailLabels}
                          />
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <article className="setup-service-section setup-service-empty catalog-empty">
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

      <footer className="site-footer">
        <a href="https://x.com/DrFayaa" target="_blank" rel="noreferrer">
          FayaaDev@2026
        </a>
      </footer>
    </div>
  )
}
