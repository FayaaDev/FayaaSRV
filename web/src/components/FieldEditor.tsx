import type { SetupQuestionField } from '../api/types'

type FieldEditorProps = {
  field: SetupQuestionField
  value: unknown
  persistedAnswer: unknown
  error?: string
  onChange: (value: unknown) => void
}

function fieldLabel(field: SetupQuestionField) {
  return (field.prompt?.trim() || field.prompt_template?.trim() || field.id).replace(/\s*\[[^\]]*\]\s*$/, '')
}

function friendlyValue(value: unknown) {
  const text = String(value)
  const labels: Record<string, string> = {
    true: 'Yes, continue',
    false: 'Not right now',
    generate: 'Generate for me',
    manual: 'I will provide them',
    fresh: 'Fresh install',
    migrate: 'Restore existing',
    linux: 'Linux server',
    mac: 'Mac machine',
  }

  return labels[text] ?? text.replace(/[._-]+/g, ' ').replace(/\b\w/g, (match) => match.toUpperCase())
}

function helperText(field: SetupQuestionField) {
  if (field.id === 'docker_installed') {
    return 'If Docker is missing, Rakkib will prepare it during launch.'
  }
  if (field.id === 'zone_in_cloudflare') {
    return 'This helps Rakkib know whether public routing can be completed automatically.'
  }
  if (field.id === 'secrets_mode') {
    return 'Generated secrets are created locally on your server during setup.'
  }
  if (field.id === 'n8n_mode') {
    return 'Choose restore only when you already have an existing n8n encryption key.'
  }
  if (field.type === 'secret_group') {
    return 'Secrets are write-only here. Saved values stay hidden unless you replace them.'
  }
  return null
}

function uniqueConfirmOptions(field: SetupQuestionField) {
  const acceptedInputs = field.accepted_inputs ?? {}
  const seen = new Set<string>()

  return Object.entries(acceptedInputs).flatMap(([key, value]) => {
    const token = JSON.stringify(value)
    if (seen.has(token)) {
      return []
    }
    seen.add(token)
    return [{ key, value }]
  })
}

export function FieldEditor({ field, value, persistedAnswer, error, onChange }: FieldEditorProps) {
  if (field.type === 'text') {
    return (
      <article className="setup-field-card setup-input-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">Your Answer</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
        {helperText(field) ? <p className="setup-field-help">{helperText(field)}</p> : null}
        <input
          className="setup-input"
          type="text"
          value={typeof value === 'string' ? value : ''}
          onChange={(event) => onChange(event.target.value)}
        />
        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  if (field.type === 'confirm') {
    const options = uniqueConfirmOptions(field)
    const optionValues = options.map((option) => option.value)
    const isBoolean = optionValues.every((option) => typeof option === 'boolean')

    if (isBoolean) {
      return (
        <article className="setup-field-card setup-input-card">
          <div className="setup-field-header">
            <div>
              <p className="section-label">Decision</p>
              <h2>{fieldLabel(field)}</h2>
            </div>
          </div>
          {helperText(field) ? <p className="setup-field-help">{helperText(field)}</p> : null}
          <div className="setup-choice-grid setup-choice-grid-compact">
            {[true, false].map((option) => (
              <button
                key={String(option)}
                type="button"
                className={`setup-choice-card${value === option ? ' is-selected' : ''}`}
                onClick={() => onChange(option)}
              >
                <span className="setup-choice-dot" aria-hidden="true" />
                <strong>{friendlyValue(option)}</strong>
              </button>
            ))}
          </div>
          {error ? <p className="setup-field-error">{error}</p> : null}
        </article>
      )
    }

    return (
      <article className="setup-field-card setup-input-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">Decision</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
        {helperText(field) ? <p className="setup-field-help">{helperText(field)}</p> : null}
        <div className="setup-choice-grid setup-choice-grid-compact">
          {options.map((option) => (
            <button
              key={String(option.value)}
              type="button"
              className={`setup-choice-card${value === option.value ? ' is-selected' : ''}`}
              onClick={() => onChange(option.value)}
            >
              <span className="setup-choice-dot" aria-hidden="true" />
              <strong>{friendlyValue(option.value)}</strong>
            </button>
          ))}
        </div>
        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  if (field.type === 'single_select') {
    return (
      <article className="setup-field-card setup-input-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">Choose One</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
        {helperText(field) ? <p className="setup-field-help">{helperText(field)}</p> : null}
        <div className="setup-choice-grid setup-choice-grid-compact">
          {(field.canonical_values ?? []).map((option) => (
            <button
              key={option}
              type="button"
              className={`setup-choice-card${value === option ? ' is-selected' : ''}`}
              onClick={() => onChange(option)}
            >
              <span className="setup-choice-dot" aria-hidden="true" />
              <strong>{friendlyValue(option)}</strong>
            </button>
          ))}
        </div>
        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  if (field.type === 'multi_select') {
    const selected = Array.isArray(value) ? value.map((item) => String(item)) : []

    return (
      <article className="setup-field-card setup-input-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">Choose Any</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>

        <div className="setup-choice-grid">
          {(field.canonical_values ?? []).map((option) => {
            const checked = selected.includes(option)

            return (
              <button
                key={option}
                type="button"
                className={`setup-choice-card${checked ? ' is-selected' : ''}`}
                onClick={() => {
                  if (checked) {
                    onChange(selected.filter((item) => item !== option))
                    return
                  }

                  onChange([...selected, option])
                }}
              >
                <span className="setup-choice-dot" aria-hidden="true" />
                <strong>{friendlyValue(option)}</strong>
              </button>
            )
          })}
        </div>

        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  if (field.type === 'secret_group') {
    const persistedValues = typeof persistedAnswer === 'object' && persistedAnswer !== null ? (persistedAnswer as Record<string, unknown>) : {}
    const draftValues = typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {}

    return (
      <article className="setup-field-card setup-input-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">Private Values</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
        {helperText(field) ? <p className="setup-field-help">{helperText(field)}</p> : null}

        <div className="setup-secret-list">
          {(field.entries ?? []).map((entry) => {
            const key = entry.key ?? ''
            const savedValue = persistedValues[key]
            const currentValue = typeof draftValues[key] === 'string' ? String(draftValues[key]) : ''

            return (
              <label key={key} className="setup-secret-row">
                <span>{friendlyValue(key)}</span>
                <input
                  className="setup-input"
                  type="password"
                  value={currentValue}
                  placeholder={savedValue === '[redacted]' ? 'Saved value kept unless replaced' : ''}
                  onChange={(event) => onChange({ ...draftValues, [key]: event.target.value })}
                />
              </label>
            )
          })}
        </div>

        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  return null
}
