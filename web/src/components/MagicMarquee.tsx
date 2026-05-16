import type { ComponentPropsWithoutRef, ReactNode } from 'react'

type MarqueeProps = ComponentPropsWithoutRef<'div'> & {
  children: ReactNode
  reverse?: boolean
  pauseOnHover?: boolean
  vertical?: boolean
  repeat?: number
}

export function Marquee({
  className,
  children,
  reverse = false,
  pauseOnHover = false,
  vertical = false,
  repeat = 4,
  ...props
}: MarqueeProps) {
  const classes = [
    'magic-marquee',
    vertical ? 'magic-marquee-vertical' : 'magic-marquee-horizontal',
    reverse ? 'magic-marquee-reverse' : '',
    pauseOnHover ? 'magic-marquee-pause-hover' : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div {...props} className={classes}>
      {Array.from({ length: repeat }, (_, index) => (
        <div key={index} className="magic-marquee-track" aria-hidden={index > 0 ? true : undefined}>
          {children}
        </div>
      ))}
    </div>
  )
}
