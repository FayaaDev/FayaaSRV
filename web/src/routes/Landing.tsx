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
const repoUrl = 'https://github.com/FayaaDev/rakkib'
const demoVideoUrl = 'https://github.com/user-attachments/assets/ca819df9-1efe-48a7-9127-a747474dc4fb'

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

function CategoryIcon({ category }: { category: string }) {
  const paths: Record<string, string[]> = {
    AI: ['M12 3v3', 'M12 18v3', 'M3 12h3', 'M18 12h3', 'M7.8 7.8l2.1 2.1', 'M14.1 14.1l2.1 2.1', 'M16.2 7.8l-2.1 2.1', 'M9.9 14.1l-2.1 2.1', 'M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0Z'],
    Automation: ['M5 7h7a4 4 0 0 1 4 4v1', 'M13 9l3 3 3-3', 'M19 17h-7a4 4 0 0 1-4-4v-1', 'M11 15l-3-3-3 3'],
    Books: ['M5 5.5A2.5 2.5 0 0 1 7.5 3H19v16H7.5A2.5 2.5 0 0 0 5 21.5v-16Z', 'M5 5.5A2.5 2.5 0 0 1 7.5 8H19', 'M9 12h6'],
    Dashboards: ['M4 5h7v6H4z', 'M13 5h7v4h-7z', 'M13 11h7v8h-7z', 'M4 13h7v6H4z'],
    'Developer Tools': ['M8 8l-4 4 4 4', 'M16 8l4 4-4 4', 'M14 5l-4 14'],
    'Diagram And Design': ['M5 5h5v5H5z', 'M14 14h5v5h-5z', 'M10 8h4', 'M16 10v4', 'M6 16l4-4'],
    Documents: ['M7 3h7l5 5v13H7z', 'M14 3v5h5', 'M10 13h6', 'M10 17h4'],
    'File Sharing': ['M12 4v10', 'M8 8l4-4 4 4', 'M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4'],
    Finance: ['M4 19h16', 'M7 16v-4', 'M12 16V8', 'M17 16v-7', 'M6 8l4-3 4 2 4-4'],
    'Home Automation': ['M4 11l8-7 8 7', 'M6 10v10h12V10', 'M10 20v-6h4v6', 'M15.5 8.5a2.5 2.5 0 0 1 0 5'],
    Infrastructure: ['M5 18h14', 'M7 18V8h10v10', 'M9 8V5h6v3', 'M9 12h2', 'M13 12h2', 'M9 15h2', 'M13 15h2'],
    Lifestyle: ['M5 19c8 0 13-5 14-14-9 1-14 6-14 14Z', 'M5 19c0-5 4-9 9-9'],
    Media: ['M7 5v14l12-7z'],
    Monitoring: ['M3 13h4l2-5 4 10 2-5h6'],
    News: ['M5 5h14v14H5z', 'M8 9h8', 'M8 13h8', 'M8 17h5'],
    Personal: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z', 'M4 21a8 8 0 0 1 16 0'],
    Utility: ['M14.7 6.3a4 4 0 0 0 3 5.8L11 18.8 7.2 15l6.7-6.7a4 4 0 0 0 .8-2Z', 'M5 17l2 2'],
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none">
      {(paths[category] ?? paths.Infrastructure).map((path) => (
        <path key={path} d={path} />
      ))}
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
        <span>{tc(item.category?.trim() || 'Infrastructure')}</span>
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
                const category = item.category?.trim() || 'Infrastructure'
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
                    <div className="catalog-category-dock" aria-label={t('categoriesLabel')}>
                      {serviceCategories.map(([category, items]) => (
                        <button
                          className={`catalog-category-dock-item${category === activeCategory ? ' is-active' : ''}`}
                          type="button"
                          key={category}
                          aria-pressed={category === activeCategory}
                          onClick={() => setSelectedCategory((current) => (current === category ? null : category))}
                        >
                          <span className="catalog-category-dock-mark" aria-hidden="true">
                            <CategoryIcon category={category} />
                          </span>
                          <strong>{tc(category)}</strong>
                          <span className="catalog-category-dock-count">
                            {tf(items.length === 1 ? 'serviceCountOne' : 'serviceCountMany', { count: items.length })}
                          </span>
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
