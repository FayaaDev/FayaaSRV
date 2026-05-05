import type { SetupQuestionField } from '../api/types'

type FieldEditorProps = {
  field: SetupQuestionField
  value: unknown
  persistedAnswer: unknown
  error?: string
  onChange: (value: unknown) => void
}

function fieldLabel(field: SetupQuestionField) {
  return field.prompt?.trim() || field.prompt_template?.trim() || field.id
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
      <article className="setup-field-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">{field.type}</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
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
        <article className="setup-field-card">
          <div className="setup-field-header">
            <div>
              <p className="section-label">{field.type}</p>
              <h2>{fieldLabel(field)}</h2>
            </div>
          </div>
          <label className="setup-checkbox-row">
            <input type="checkbox" checked={value === true} onChange={(event) => onChange(event.target.checked)} />
            <span>{value === true ? 'Yes' : 'No'}</span>
          </label>
          {error ? <p className="setup-field-error">{error}</p> : null}
        </article>
      )
    }

    return (
      <article className="setup-field-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">{field.type}</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
        <select className="setup-input" value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(event.target.value)}>
          <option value="">Choose one</option>
          {options.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {String(option.value)}
            </option>
          ))}
        </select>
        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  if (field.type === 'single_select') {
    return (
      <article className="setup-field-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">{field.type}</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>
        <select className="setup-input" value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(event.target.value)}>
          <option value="">Choose one</option>
          {(field.canonical_values ?? []).map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        {error ? <p className="setup-field-error">{error}</p> : null}
      </article>
    )
  }

  if (field.type === 'multi_select') {
    const selected = Array.isArray(value) ? value.map((item) => String(item)) : []

    return (
      <article className="setup-field-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">{field.type}</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>

        <div className="setup-checkbox-list">
          {(field.canonical_values ?? []).map((option) => {
            const checked = selected.includes(option)

            return (
              <label key={option} className="setup-checkbox-row">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    if (event.target.checked) {
                      onChange([...selected, option])
                      return
                    }

                    onChange(selected.filter((item) => item !== option))
                  }}
                />
                <span>{option}</span>
              </label>
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
      <article className="setup-field-card">
        <div className="setup-field-header">
          <div>
            <p className="section-label">{field.type}</p>
            <h2>{fieldLabel(field)}</h2>
          </div>
        </div>

        <div className="setup-secret-list">
          {(field.entries ?? []).map((entry) => {
            const key = entry.key ?? ''
            const savedValue = persistedValues[key]
            const currentValue = typeof draftValues[key] === 'string' ? String(draftValues[key]) : ''

            return (
              <label key={key} className="setup-secret-row">
                <span>{key}</span>
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
