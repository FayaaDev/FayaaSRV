import type { ReactNode } from 'react'
import type { SetupQuestionField } from '../api/types'

type FieldRendererProps = {
  field: SetupQuestionField
  answer: unknown
}

function renderValue(value: unknown): ReactNode {
  if (value === null || value === undefined || value === '') {
    return <span className="setup-empty-value">Not set yet</span>
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="setup-empty-value">None selected</span>
    }

    return (
      <ul className="setup-value-list">
        {value.map((item) => (
          <li key={String(item)}>{String(item)}</li>
        ))}
      </ul>
    )
  }

  if (typeof value === 'object') {
    return (
      <dl className="setup-value-map">
        {Object.entries(value as Record<string, unknown>).map(([key, entryValue]) => (
          <div key={key} className="setup-value-map-row">
            <dt>{key}</dt>
            <dd>{renderValue(entryValue)}</dd>
          </div>
        ))}
      </dl>
    )
  }

  return String(value)
}

function fieldLabel(field: SetupQuestionField) {
  return field.prompt?.trim() || field.prompt_template?.trim() || field.id
}

export function FieldRenderer({ field, answer }: FieldRendererProps) {
  return (
    <article className="setup-field-card">
      <div className="setup-field-header">
        <div>
          <p className="section-label">{field.type}</p>
          <h2>{fieldLabel(field)}</h2>
        </div>
        {field.required === false ? <span className="badge">Optional</span> : null}
      </div>

      {field.records.length > 0 ? <p className="setup-field-records">Records: {field.records.join(', ')}</p> : null}

      <div className="setup-field-value">{renderValue(answer)}</div>
    </article>
  )
}
