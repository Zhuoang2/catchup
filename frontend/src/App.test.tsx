import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('navigation', () => {
  it('shows links to all main pages', () => {
    render(<App />)
    expect(screen.getByRole('link', { name: 'Generate' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('link', { name: 'Sources' })).toHaveAttribute('href', '/sources')
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/settings')
    expect(screen.getByRole('link', { name: 'History' })).toHaveAttribute('href', '/digests')
  })
})
