import { useState } from 'react'

type ServiceMarkProps = {
  slug: string
  label: string
}

function serviceInitials(label: string) {
  const words = label.replace(/\.[a-z]+$/i, '').split(/\s+|-/).filter(Boolean)
  const initials = words.length > 1 ? `${words[0][0]}${words[1][0]}` : label.slice(0, 2)
  return initials.toUpperCase()
}

export function ServiceMark({ slug, label }: ServiceMarkProps) {
  const [missing, setMissing] = useState(false)

  return (
    <span className="setup-service-mark" aria-hidden="true">
      {missing ? (
        <span className="setup-service-mark-fallback">{serviceInitials(label)}</span>
      ) : (
        <img
          className="setup-service-mark-image"
          src={`/service-icons/${slug}.png`}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setMissing(true)}
        />
      )}
    </span>
  )
}
