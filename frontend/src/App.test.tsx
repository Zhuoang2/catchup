import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from './components/AppShell'
import { expectAccessible } from './test/accessibility'
import Generate from './pages/Generate'
import Sources from './pages/Sources'
import Settings from './pages/Settings'
import History from './pages/History'

it.each([
  ['/', 'Generate · CatchUp', <Generate/>],
  ['/sources', 'Sources · CatchUp', <Sources/>],
  ['/digests', 'History · CatchUp', <History/>],
  ['/settings', 'Settings · CatchUp', <Settings/>],
])('titles the %s screen', (path, title, page) => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => [] })))
  render(<MemoryRouter initialEntries={[path]}><Routes><Route path={path} element={page}/></Routes></MemoryRouter>)
  expect(document.title).toBe(title)
  vi.unstubAllGlobals()
})

function shell(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><AppShell><h1>Content</h1><a href="/digests">Read more</a></AppShell></MemoryRouter>)
}

afterEach(() => vi.useRealTimers())

describe('navigation', () => {
  it('uses the browser local calendar date in the masthead', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-06T23:30:00-07:00'))
    shell()
    const time = document.querySelector('.masthead-line time')
    expect(time).toHaveAttribute('dateTime', '2026-10-06')
    expect(time).toHaveTextContent('Tuesday, 6 October 2026')
  })
  it('shows links to all main pages and marks the current route', () => {
    shell('/digests/1')
    expect(screen.getByRole('link', { name: 'Generate' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'Sources' })).toHaveAttribute('href', '/sources')
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings')
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('href', '/digests')
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Generate' })).not.toHaveAttribute('aria-current')
  })

  it('moves keyboard focus to main when the skip link is activated', () => {
    shell()
    fireEvent.click(screen.getByRole('link', { name: 'Skip to content' }))
    expect(document.activeElement).toBe(screen.getByRole('main'))
    const main = screen.getByRole('main')
    const firstFocusable = main.querySelector('a[href], button:not([disabled]), input:not([disabled])')
    expect(firstFocusable).toBe(screen.getByRole('link', { name: 'Read more' }))
    expect(main.contains(firstFocusable)).toBe(true)
  })

  it('has no accessibility violations', async () => {
    const { container } = shell('/sources')
    await expectAccessible(container)
  })
})
