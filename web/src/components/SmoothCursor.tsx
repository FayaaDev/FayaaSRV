import { useEffect, useRef, useState } from 'react'

type Position = {
  x: number
  y: number
}

const desktopPointerQuery = '(any-hover: hover) and (any-pointer: fine)'

function isTrackablePointer(pointerType: string) {
  return pointerType !== 'touch'
}

function CursorMark() {
  return (
    <svg className="smooth-cursor-mark" viewBox="0 0 50 54" fill="none" aria-hidden="true">
      <path
        d="M42.68 41.15 27.51 6.8c-.78-1.77-3.3-1.77-4.12 0L7.6 41.15c-.84 1.83.93 3.74 2.81 3.05l13.97-5.15c.5-.19 1.06-.19 1.56 0l13.87 5.15c1.87.69 3.68-1.22 2.87-3.05Z"
        fill="currentColor"
      />
      <path
        d="M43.71 40.69 28.54 6.34c-1.19-2.69-4.96-2.65-6.17-.01L6.57 40.68c-1.26 2.74 1.4 5.62 4.23 4.58l13.97-5.15c.25-.09.53-.09.78 0l13.87 5.14c2.81 1.04 5.51-1.82 4.3-4.56Z"
        stroke="rgba(255,255,255,.92)"
        strokeWidth="2.25"
      />
    </svg>
  )
}

export function SmoothCursor() {
  const target = useRef<Position>({ x: 0, y: 0 })
  const current = useRef<Position>({ x: 0, y: 0 })
  const previous = useRef<Position>({ x: 0, y: 0 })
  const cursorRef = useRef<HTMLDivElement | null>(null)
  const frameRef = useRef<number | null>(null)
  const [enabled, setEnabled] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia(desktopPointerQuery)
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')

    const updateEnabled = () => {
      const nextEnabled = mediaQuery.matches && !motionQuery.matches
      setEnabled(nextEnabled)
      if (!nextEnabled) setVisible(false)
    }

    updateEnabled()
    mediaQuery.addEventListener('change', updateEnabled)
    motionQuery.addEventListener('change', updateEnabled)

    return () => {
      mediaQuery.removeEventListener('change', updateEnabled)
      motionQuery.removeEventListener('change', updateEnabled)
    }
  }, [])

  useEffect(() => {
    if (!enabled) return

    const handlePointerMove = (event: PointerEvent) => {
      if (!isTrackablePointer(event.pointerType)) return
      target.current = { x: event.clientX, y: event.clientY }
      setVisible(true)
    }

    const animate = () => {
      const nextX = current.current.x + (target.current.x - current.current.x) * 0.22
      const nextY = current.current.y + (target.current.y - current.current.y) * 0.22
      const velocityX = nextX - previous.current.x
      const velocityY = nextY - previous.current.y
      const speed = Math.hypot(velocityX, velocityY)
      const angle = speed > 0.08 ? Math.atan2(velocityY, velocityX) * (180 / Math.PI) + 90 : 0
      const scale = speed > 0.08 ? 0.92 : 1

      current.current = { x: nextX, y: nextY }
      previous.current = { x: nextX, y: nextY }

      if (cursorRef.current) {
        cursorRef.current.style.transform = `translate3d(${nextX}px, ${nextY}px, 0) translate(-50%, -50%) rotate(${angle}deg) scale(${scale})`
      }

      frameRef.current = requestAnimationFrame(animate)
    }

    document.body.classList.add('has-smooth-cursor')
    window.addEventListener('pointermove', handlePointerMove, { passive: true })
    frameRef.current = requestAnimationFrame(animate)

    return () => {
      document.body.classList.remove('has-smooth-cursor')
      window.removeEventListener('pointermove', handlePointerMove)
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    }
  }, [enabled])

  if (!enabled) return null

  return (
    <div ref={cursorRef} className={`smooth-cursor${visible ? ' is-visible' : ''}`}>
      <CursorMark />
    </div>
  )
}
