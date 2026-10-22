import { DEFAULT_SERVER, validServer } from './options'

type Tab = { id?: number; url?: string; title?: string }
type Preview = {
  title: string; kind: string; feed_url: string; site_url: string
  follows_site_feed_notice: boolean
  entries: { title: string; link: string; published_at: string | null }[]
}
type ApiError = { status: number; code: string; message: string; http_status: number | null }

function element<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag)
  if (text !== undefined) node.textContent = text
  return node
}

function button(label: string, action: () => void): HTMLButtonElement {
  const node = element('button', label)
  node.type = 'button'
  node.addEventListener('click', action)
  return node
}

// Copy of the error wording in frontend/src/pages/Sources.tsx (describeError).
function sourceError(error: ApiError): string {
  if (error.code === 'fetch_failed' && error.http_status !== null && error.http_status >= 400) {
    const status = error.http_status
    if (status === 401 || status === 403)
      return `The site refused the request (HTTP ${status}). If you know its feed URL, paste that instead.`
    if (status === 404 || status === 410)
      return `The page was not found (HTTP ${status}). Check the URL, or paste the site's feed URL.`
    if (status >= 500 && status <= 599)
      return `The site is not responding (HTTP ${status}). Try again later.`
    return `The site answered HTTP ${status}. Check the URL, or paste the site's feed URL.`
  }
  const messages: Record<string, string> = {
    invalid_url: 'Enter a valid HTTP or HTTPS URL.',
    blocked_address: 'This address is not allowed.',
    fetch_failed: 'Could not fetch the source. Check the URL and try again.',
    no_feed: 'No supported feed was found at this URL.',
    not_a_feed: 'The URL did not return a parsable feed.',
  }
  return messages[error.code] ?? error.message
}

export async function initPopup(): Promise<void> {
  const root = document.querySelector<HTMLElement>('#popup')!
  const saved = await chrome.storage.local.get(['server', 'token'])
  const server = typeof saved.server === 'string' ? saved.server : DEFAULT_SERVER
  const token = typeof saved.token === 'string' ? saved.token : ''

  function disconnected() {
    root.replaceChildren(
      element('p', 'Connect this browser in CatchUp → Settings → Browser extension.'),
      button('Open options', () => chrome.runtime.openOptionsPage()),
    )
  }
  if (!token || !validServer(server)) { disconnected(); return }
  root.textContent = 'Connecting to CatchUp…'

  async function api<T>(path: string, body?: object): Promise<T> {
    const response = await fetch(`${server}/api${path}`, {
      ...(body ? { method: 'POST', body: JSON.stringify(body) } : {}),
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
    })
    const result = await response.json() as T & { error?: Partial<ApiError> }
    if (!response.ok) {
      throw {
        status: response.status, code: result.error?.code ?? '',
        message: result.error?.message ?? 'Could not connect to CatchUp.',
        http_status: result.error?.http_status ?? null,
      } satisfies ApiError
    }
    return result
  }

  let tab: Tab
  let waiting: number
  try {
    const status = await api<{ name: string; waiting: number }>('/extension/status')
    waiting = status.waiting
    tab = (await chrome.tabs.query({ active: true, currentWindow: true }))[0] ?? {}
  } catch (error) {
    if ((error as ApiError).status === 401) disconnected()
    else root.replaceChildren(element('p', 'Could not connect to CatchUp.'),
      button('Open options', () => chrome.runtime.openOptionsPage()))
    return
  }

  const statusText = element('p')
  statusText.setAttribute('role', 'status')
  statusText.setAttribute('aria-live', 'polite')
  const host = (() => { try { return new URL(tab.url ?? '').hostname } catch { return '' } })()
  const isX = host === 'x.com' || host === 'twitter.com'

  function connected() {
    const follow = button('Follow this site', () => { void previewSite() })
    root.replaceChildren(
      element('h2', tab.title || 'Current tab'),
      element('p', host),
      element('p', `${waiting} pages waiting`),
      ...(isX
        ? [element('p', 'X accounts cannot be followed. You can save an individual post instead.')]
        : tab.url?.startsWith('http') ? [follow] : []),
      button('Open CatchUp', () => { void chrome.tabs.create({ url: server }) }),
      statusText,
    )
  }

  async function previewSite() {
    statusText.textContent = ''
    try {
      const preview = await api<Preview>('/sources/preview', { url: tab.url })
      const section = element('section')
      section.setAttribute('aria-label', 'Source preview')
      const entries = element('ul')
      for (const entry of preview.entries.slice(0, 5)) entries.append(element('li', entry.title))
      section.append(
        element('h2', preview.title),
        element('p', preview.kind),
        element('p', preview.feed_url),
        ...(preview.follows_site_feed_notice
          ? [element('p', preview.kind === 'podcast'
            ? 'CatchUp will follow the whole show, not only this episode.'
            : "CatchUp will follow the whole site's feed, not only this page.")] : []),
        entries,
        button('Confirm', () => { void confirmSite(preview) }),
        button('Cancel', connected),
      )
      root.replaceChildren(section, statusText)
    } catch (error) {
      if ((error as ApiError).status === 401) disconnected()
      else statusText.textContent = sourceError(error as ApiError)
    }
  }

  async function confirmSite(preview: Preview) {
    try {
      await api('/sources', { feed_url: preview.feed_url })
      connected()
      statusText.textContent = 'Source saved.'
    } catch (error) {
      if ((error as ApiError).status === 401) disconnected()
      else statusText.textContent = sourceError(error as ApiError)
    }
  }

  connected()
}

if (document.querySelector('#popup')) void initPopup()
