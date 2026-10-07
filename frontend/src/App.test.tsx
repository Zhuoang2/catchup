import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppShell } from './components/AppShell'
import { expectAccessible } from './test/accessibility'

function shell(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><AppShell><h1>Content</h1></AppShell></MemoryRouter>)
}

describe('navigation', () => {
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
  })

  it('has no accessibility violations', async () => {
    const { container } = shell('/sources')
    await expectAccessible(container)
  })
})
