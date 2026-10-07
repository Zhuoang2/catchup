import { useCallback, type MouseEvent } from 'react'

export function useJump(id: string) {
  return useCallback((event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    const target = document.getElementById(id)
    if (!target) return
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    target.scrollIntoView?.({ behavior: reduced ? 'auto' : 'smooth' })
    target.focus({ preventScroll: true })
  }, [id])
}
