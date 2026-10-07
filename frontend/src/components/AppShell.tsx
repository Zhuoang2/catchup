import { Link, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Icon } from './Icon'
import { useJump } from './useJump'

const navigation = [
  { to: '/', label: 'Generate', icon: 'generate' },
  { to: '/sources', label: 'Sources', icon: 'sources' },
  { to: '/digests', label: 'History', icon: 'history' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
] as const

export function AppShell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const jump = useJump('main')
  const screen = /^\/digests\/[^/]+$/.test(pathname) ? 'digest' :
    pathname === '/digests' ? 'history' : pathname === '/sources' ? 'sources' :
      pathname === '/settings' ? 'settings' : 'generate'
  const today = new Date()
  return <div className="app" data-screen={screen}>
    <a className="skip-link" href="#main" onClick={jump}>Skip to content</a>
    <header className="app-header page-frame">
      <Link className="brand" to="/">CatchUp</Link>
      <p className="masthead-line"><time dateTime={today.toISOString().slice(0, 10)}>
        {new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(today)}
      </time></p>
      <nav className="app-nav" aria-label="Main">
        {navigation.map(({ to, label, icon }) =>
          <Link key={to} to={to} className="nav-link"
            aria-current={screen === icon || (screen === 'digest' && icon === 'history') ? 'page' : undefined}>
            <Icon name={icon}/><span>{label}</span>
          </Link>)}
      </nav>
    </header>
    <main className="app-main page-frame" id="main" tabIndex={-1}>{children}</main>
  </div>
}
