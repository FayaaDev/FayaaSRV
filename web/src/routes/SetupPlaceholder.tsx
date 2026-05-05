type SetupPlaceholderProps = {
  title: string
  description: string
}

export function SetupPlaceholder({ title, description }: SetupPlaceholderProps) {
  return (
    <main className="shell route-placeholder">
      <section className="placeholder-card" aria-labelledby="placeholder-title">
        <p className="section-label">Setup Flow</p>
        <h1 id="placeholder-title">{title}</h1>
        <p className="hero-text">{description}</p>
      </section>
    </main>
  )
}
