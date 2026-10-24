export const DEFAULT_SERVER = 'http://127.0.0.1:8000'

export function validServer(value: string): boolean {
  const match = /^http:\/\/(127\.0\.0\.1|localhost):(\d{1,5})$/.exec(value)
  return match !== null && Number(match[2]) >= 1 && Number(match[2]) <= 65535
}

export function initOptions(): void {
  const server = document.querySelector<HTMLInputElement>('#server')!
  const token = document.querySelector<HTMLInputElement>('#token')!
  const feedback = document.querySelector<HTMLElement>('#feedback')!
  server.value = DEFAULT_SERVER
  void chrome.storage.local.get(['server', 'token']).then(values => {
    server.value = typeof values.server === 'string' ? values.server : DEFAULT_SERVER
    token.value = typeof values.token === 'string' ? values.token : ''
  })

  function connectedSettings(): { server: string; token: string } | null {
    const settings = { server: server.value.trim(), token: token.value.trim() }
    if (!validServer(settings.server)) {
      feedback.textContent = 'Use http://127.0.0.1:<port> or http://localhost:<port>. Only these local addresses are permitted.'
      return null
    }
    if (!settings.token) {
      feedback.textContent = 'Paste the connection token from CatchUp Settings.'
      return null
    }
    return settings
  }

  document.querySelector<HTMLFormElement>('#options-form')!.addEventListener('submit', event => {
    event.preventDefault()
    const settings = connectedSettings()
    if (!settings) return
    void chrome.storage.local.set(settings).then(() => {
      feedback.textContent = 'Saved.'
    }).catch(() => { feedback.textContent = 'Could not save options.' })
  })
  document.querySelector<HTMLButtonElement>('#test-connection')!.addEventListener('click', () => {
    const settings = connectedSettings()
    if (!settings) return
    void fetch(`${settings.server}/api/extension/status`, {
      headers: { Authorization: `Bearer ${settings.token}` },
    }).then(async response => {
      const body = await response.json() as { name?: string; error?: { message?: string } }
      feedback.textContent = response.ok ? `Connected as ${body.name ?? 'browser'}.`
        : body.error?.message ?? 'Could not connect to CatchUp.'
    }).catch(() => { feedback.textContent = 'Could not connect to CatchUp.' })
  })
}

if (document.querySelector('#options-form')) initOptions()
