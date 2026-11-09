import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError, request } from '../api/client'
import { shortDateTime } from '../components/format'
import { Icon } from '../components/Icon'
import { useDocumentTitle } from '../components/useDocumentTitle'
import { Button, PageHead, Switch } from '../components/ui'

type ModelSettings = { base_url: string; model_id: string; key_set: boolean; api_key_last4: string | null }
type ModelSave = { base_url: string; model_id: string; api_key: string }
type Preferences = { digest_language: string; youtube_captions: boolean; youtube_skip_shorts: boolean;
  show_images: boolean }
type TestResult = { ok: true; models: string[] }
type Browser = { id: number; name: string; created_at: string; last_used_at: string | null }
type ConnectedBrowser = Omit<Browser, 'last_used_at'> & { token: string }
type XSettings = { token_set: boolean; token_last4: string | null }
const languageOptions = ['en', 'zh-Hans', 'original']

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const messages: Record<string, string> = {
      auth_failed: 'The provider rejected the API key.',
      connection_failed: 'Could not reach the model provider. Check the base URL.',
      insufficient_balance: 'The provider account has insufficient balance.',
      rate_limited: 'The provider is rate limiting requests. Try again later.',
      provider_error: 'The model provider returned an error.',
      secret_not_configured: 'Set CATCHUP_SECRET_KEY on the server before saving an API key.',
    }
    return messages[error.code] ?? error.message
  }
  return 'Could not connect to CatchUp.'
}

function SettingsSection({ number, title, children }: {
  number: number; title: string; children: ReactNode
}) {
  return <section className="settings-section">
    <h2 className="settings-title"><span className="step-num" aria-hidden="true">{number}</span>
      <span className="sr-only">Step {number}: </span>{title}</h2>{children}
  </section>
}

export default function Settings() {
  useDocumentTitle('Settings')
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com')
  const [key, setKey] = useState('')
  const [last4, setLast4] = useState<string | null>(null)
  const [model, setModel] = useState('')
  const [models, setModels] = useState<string[]>([])
  const [language, setLanguage] = useState('en')
  const [otherLanguage, setOtherLanguage] = useState('')
  const [youtubeCaptions, setYoutubeCaptions] = useState(false)
  const [skipShorts, setSkipShorts] = useState(true)
  const [showImages, setShowImages] = useState(true)
  const [error, setError] = useState('')
  const [errorField, setErrorField] = useState<'key' | 'base' | null>(null)
  const [message, setMessage] = useState('')
  const [modelStatus, setModelStatus] = useState('')
  const [modelError, setModelError] = useState('')
  const [savedBaseUrl, setSavedBaseUrl] = useState<string | null>(null)
  const modelSaveQueue = useRef(Promise.resolve())
  const [loading, setLoading] = useState(true)
  const [browserName, setBrowserName] = useState('Chrome')
  const [browsers, setBrowsers] = useState<Browser[]>([])
  const [connectedBrowser, setConnectedBrowser] = useState<ConnectedBrowser | null>(null)
  const [browserError, setBrowserError] = useState('')
  const [browserMessage, setBrowserMessage] = useState('')
  const [copyMessage, setCopyMessage] = useState('')
  const [xToken, setXToken] = useState('')
  const [xLast4, setXLast4] = useState<string | null>(null)
  const [xError, setXError] = useState('')
  const [xErrorOnToken, setXErrorOnToken] = useState(false)
  const [xMessage, setXMessage] = useState('')
  const [xDeleteConfirm, setXDeleteConfirm] = useState(false)
  const tokenRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    let mounted = true
    Promise.all([
      request<ModelSettings>('/settings/model'),
      request<Preferences>('/settings/preferences'),
    ]).then(([settings, preferences]) => {
      if (!mounted) return
      setBaseUrl(settings.base_url)
      setModel(settings.model_id)
      setModels(settings.model_id ? [settings.model_id] : [])
      setLast4(settings.key_set ? settings.api_key_last4 : null)
      setSavedBaseUrl(settings.key_set ? settings.base_url : null)
      const selected = preferences.digest_language
      setLanguage(languageOptions.includes(selected) ? selected : 'other')
      if (!languageOptions.includes(selected)) setOtherLanguage(selected)
      setYoutubeCaptions(preferences.youtube_captions)
      setSkipShorts(preferences.youtube_skip_shorts)
      setShowImages(preferences.show_images !== false)
    }).catch((err: unknown) => { if (mounted) setError(errorMessage(err)) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    let mounted = true
    request<Browser[]>('/settings/extension-tokens')
      .then(rows => { if (mounted && Array.isArray(rows)) setBrowsers(rows) })
      .catch((err: unknown) => { if (mounted) setBrowserError(errorMessage(err)) })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    let mounted = true
    request<XSettings>('/settings/x')
      .then(saved => { if (mounted) setXLast4(saved.token_set ? saved.token_last4 : null) })
      .catch((err: unknown) => { if (mounted) setXError(errorMessage(err)) })
    return () => { mounted = false }
  }, [])

  async function saveX(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setXError(''); setXErrorOnToken(false); setXMessage('')
    try {
      const saved = await request<XSettings>('/settings/x', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: xToken }),
      })
      setXLast4(saved.token_last4)
      setXToken('')
      setXMessage('X token saved.')
    } catch (err) { setXError(errorMessage(err)); setXErrorOnToken(true) }
  }

  async function testX() {
    setXError(''); setXErrorOnToken(false); setXMessage('')
    try {
      await request<{ ok: true }>('/settings/x/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: xToken || undefined }),
      })
      setXMessage('X token works.')
    } catch (err) { setXError(errorMessage(err)); setXErrorOnToken(true) }
  }

  async function removeX() {
    setXError(''); setXErrorOnToken(false); setXMessage('')
    try {
      await request<void>('/settings/x', { method: 'DELETE' })
      setXLast4(null)
      setXToken('')
      setXMessage('X token removed.')
    } catch (err) { setXError(errorMessage(err)) }
  }

  async function deleteAllX() {
    setXError(''); setXErrorOnToken(false); setXMessage('')
    try {
      const removed = await request<{ digest_items: number; digests: number; accounts: number }>(
        '/settings/x/delete-all', { method: 'POST' })
      setXLast4(null)
      setXToken('')
      setXDeleteConfirm(false)
      setXMessage(`Deleted ${removed.digest_items} X digest ${removed.digest_items === 1 ? 'item' : 'items'}, ` +
        `${removed.digests} ${removed.digests === 1 ? 'digest' : 'digests'}, and ` +
        `${removed.accounts} X ${removed.accounts === 1 ? 'account' : 'accounts'}.`)
    } catch (err) { setXError(errorMessage(err)) }
  }

  async function connectBrowser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBrowserError(''); setBrowserMessage(''); setConnectedBrowser(null); setCopyMessage('')
    try {
      const created = await request<ConnectedBrowser>('/settings/extension-tokens', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: browserName }),
      })
      setConnectedBrowser(created)
      setBrowsers(previous => [{ id: created.id, name: created.name,
        created_at: created.created_at, last_used_at: null },
      ...previous.filter(row => row.id !== created.id)])
      setBrowserMessage(`${created.name} connected.`)
    } catch (err) { setBrowserError(errorMessage(err)) }
  }

  async function copyToken() {
    if (!connectedBrowser) return
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(connectedBrowser.token)
      setCopyMessage('Copied.')
    } catch {
      tokenRef.current?.focus()
      tokenRef.current?.select()
      setCopyMessage('Copy failed. Select the token and copy it.')
    }
  }

  async function disconnectBrowser(browser: Browser) {
    setBrowserError(''); setBrowserMessage('')
    try {
      await request<void>(`/settings/extension-tokens/${browser.id}`, { method: 'DELETE' })
      setBrowsers(previous => previous.filter(row => row.id !== browser.id))
      if (connectedBrowser?.id === browser.id) setConnectedBrowser(null)
      setBrowserMessage(`${browser.name} disconnected.`)
    } catch (err) { setBrowserError(errorMessage(err)) }
  }

  function showError(err: unknown, inModelGroup = false) {
    const field = err instanceof ApiError
      ? err.code === 'connection_failed' ? 'base'
        : ['auth_failed', 'insufficient_balance', 'api_key_required', 'missing_api_key'].includes(err.code)
          ? 'key' : null
      : null
    if (inModelGroup && !field) setModelError(errorMessage(err))
    else {
      setError(errorMessage(err))
      setErrorField(field)
    }
  }

  function queueModelSave(values: ModelSave, success: (saved: ModelSettings) => string, failure: string) {
    const saveModel = async () => {
      setModelStatus(''); setModelError('')
      try {
        const saved = await request<ModelSettings>('/settings/model', {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(values),
        })
        setLast4(saved.api_key_last4)
        setSavedBaseUrl(saved.base_url)
        setKey(current => current === values.api_key ? '' : current)
        setModelStatus(success(saved))
      } catch (err) { setModelError(failure + errorMessage(err)) }
    }
    modelSaveQueue.current = modelSaveQueue.current.then(saveModel, saveModel)
    return modelSaveQueue.current
  }

  async function testConnection() {
    setError(''); setErrorField(null); setMessage('')
    setModelStatus(''); setModelError('')
    const testedBaseUrl = baseUrl
    const testedKey = key
    try {
      const result = await request<TestResult>('/settings/model/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: testedBaseUrl, api_key: testedKey || undefined }),
      })
      setModels(result.models)
      const replaced = !result.models.includes(model)
      const chosen = replaced ? result.models[0] : model
      setModel(chosen ?? '')
      if (!chosen) {
        setModelStatus('Connection succeeded, but the provider listed no models. Nothing was saved.')
        return
      }
      await queueModelSave({ base_url: testedBaseUrl, model_id: chosen, api_key: testedKey },
        saved => (testedKey
          ? `Connection succeeded. Saved key ending in ${saved.api_key_last4} with model ${chosen}.`
          : `Connection succeeded. Saved model ${chosen}.`) +
          (replaced && result.models.length > 1 ? ' Choose another model to change it.' : ''),
        'Connection succeeded, but nothing was saved. ')
    } catch (err) { showError(err, true) }
  }

  function chooseModel(choice: string) {
    setModel(choice)
    if (!key && baseUrl.trim() === savedBaseUrl) {
      void queueModelSave({ base_url: savedBaseUrl, model_id: choice, api_key: '' },
        () => `Saved model ${choice}.`, 'The model was not saved. ')
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(''); setErrorField(null); setMessage('')
    setModelStatus(''); setModelError('')
    try {
      const saved = await request<ModelSettings>('/settings/model', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, model_id: model, api_key: key }),
      })
      setSavedBaseUrl(saved.base_url)
      await request<Preferences>('/settings/preferences', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          digest_language: language === 'other' ? otherLanguage : language,
          youtube_captions: youtubeCaptions, youtube_skip_shorts: skipShorts,
          show_images: showImages,
        }),
      })
      setLast4(saved.api_key_last4)
      setKey('')
      setMessage('Settings saved.')
    } catch (err) { showError(err) }
  }

  const keyDescription = [last4 ? 'key-saved' : null, 'key-hint',
    error && errorField === 'key' ? 'key-error' : null].filter(Boolean).join(' ')

  return <section className="page page-settings">
    <PageHead title="Settings" lede={last4
      ? 'Your model, digest language, YouTube options, browser extension, and X accounts.'
      : 'Three quick steps, plus optional X accounts and a browser extension. Your key stays on this computer, encrypted.'}/>
    {loading ? <p>Loading settings…</p> : <form className="settings-form" onSubmit={event => void save(event)}>
      <SettingsSection number={1} title="Model provider">
        <p className="note"><Icon name="info"/>Content will be sent to your configured model provider.</p>
        <div className="field"><label className="field-label" htmlFor="base">Base URL</label>
          <input className="input" id="base" value={baseUrl} onChange={event => setBaseUrl(event.target.value)}
            aria-invalid={errorField === 'base' || undefined}
            aria-describedby={errorField === 'base' ? 'base-error' : undefined} required/></div>
        <div className="field"><label className="field-label" htmlFor="key">API key</label>
          {last4 && <p className="key-saved" id="key-saved"><Icon name="check"/>
            Saved key ending in <code>{last4}</code></p>}
          <input className="input" id="key" type="password" value={key}
            placeholder={last4 ? 'Paste a new key to replace it' : 'Paste your API key'}
            onChange={event => setKey(event.target.value)} autoComplete="new-password"
            aria-invalid={errorField === 'key' || undefined} aria-describedby={keyDescription}/>
          <p className="field-hint" id="key-hint">{last4
            ? 'Leave empty to keep the saved key. Testing a new key saves it.'
            : 'Stored encrypted on this computer. It is never shown again.'}</p>
        </div>
        <div className="field-row"><Button type="button" onClick={() => void testConnection()}>
          Test connection</Button>
          <p className="inline-msg msg-ok" role="status">
            {modelStatus && <Icon name="check"/>}{modelStatus}</p>
        </div>
        {error && errorField && <p className="field-error" id={errorField === 'base' ? 'base-error' : 'key-error'}
          role="alert"><Icon name="alert"/>{error}</p>}
        {modelError && <p className="field-error" role="alert" id="model-error">
          <Icon name="alert"/>{modelError}</p>}
        <div className="field"><label className="field-label" htmlFor="model">Model</label>
          <select className="input select" id="model" value={model}
            onChange={event => chooseModel(event.target.value)} disabled={!models.length} required>
            {!model && <option value="">Test the connection to list models</option>}
            {models.map(id => <option key={id} value={id}>{id}</option>)}
          </select></div>
      </SettingsSection>
      <SettingsSection number={2} title="Digest">
        <div className="field"><label className="field-label" htmlFor="lang">Digest language</label>
          <select className="input select" id="lang" value={language} onChange={event => setLanguage(event.target.value)}
            aria-describedby="lang-hint">
            <option value="en">English</option><option value="zh-Hans" lang="zh-Hans">简体中文</option>
            <option value="original">Same as original</option><option value="other">Other</option>
          </select>
          <p className="field-hint" id="lang-hint">Topic titles and summaries are written in this language. Item titles stay as published.</p>
        </div>
        {language === 'other' && <div className="field"><label className="field-label" htmlFor="other">Other language</label>
          <input className="input" id="other" value={otherLanguage} maxLength={40}
            onChange={event => setOtherLanguage(event.target.value)} required/></div>}
        <Switch label="Show images from source sites" checked={showImages}
          onChange={event => setShowImages(event.target.checked)} describedBy="images-note"/>
        <p className="field-hint" id="images-note">
          Opening a digest loads its images from the sites that published them.
        </p>
      </SettingsSection>
      <SettingsSection number={3} title="YouTube">
        <Switch label="Fetch captions locally" checked={youtubeCaptions}
          onChange={event => setYoutubeCaptions(event.target.checked)} describedBy="captions-risk"/>
        <p className="risk" id="captions-risk"><Icon name="alert"/>
          <span>Fetches captions from YouTube from this computer. YouTube's Terms of Service do not allow automated access,
            so turn this on only if you accept that risk. When off, new videos are listed under Creator updates without a summary.</span>
        </p>
        <Switch label="Skip Shorts" checked={skipShorts} onChange={event => setSkipShorts(event.target.checked)}/>
      </SettingsSection>
      <div className="save-bar"><Button variant="primary" type="submit">Save</Button>
        {message === 'Settings saved.' && <p className="inline-msg msg-ok" role="status">
          <Icon name="check"/>{message}</p>}</div>
    </form>}
    {!loading && <SettingsSection number={4} title="Browser extension">
      <form onSubmit={event => void connectBrowser(event)}>
        <div className="field"><label className="field-label" htmlFor="browser-name">Browser name</label>
          <input className="input" id="browser-name" value={browserName} maxLength={60} required
            onChange={event => setBrowserName(event.target.value)}/></div>
        <Button type="submit">Connect a browser</Button>
      </form>
      {connectedBrowser && <div className="field">
        <label className="field-label" htmlFor="browser-token">Connection token</label>
        <div className="input-row"><input ref={tokenRef} className="input" id="browser-token"
          value={connectedBrowser.token} readOnly aria-describedby="browser-token-note"/>
          <Button type="button" onClick={() => void copyToken()}>Copy</Button></div>
        <p className="field-hint" id="browser-token-note">
          Paste this into the CatchUp extension's options. It is shown only once.
        </p>
      </div>}
      <p role="status" aria-label="Copy result">{copyMessage}</p>
      {browserError && <p role="alert" className="field-error">{browserError}</p>}
      {browserMessage && <p role="status">{browserMessage}</p>}
      <h3 className="section-label">Connected browsers</h3>
      <ul>{browsers.map(browser => <li key={browser.id}>
        <strong>{browser.name}</strong>{' '}<span>Connected <time dateTime={browser.created_at}>
          {shortDateTime(browser.created_at)}</time></span>{' '}<span>Last used:{' '}
          {browser.last_used_at ? <time dateTime={browser.last_used_at}>
            {shortDateTime(browser.last_used_at)}</time> : 'Never'}</span>{' '}
        <Button type="button" variant="ghost" aria-label={`Disconnect ${browser.name}`}
          onClick={() => void disconnectBrowser(browser)}>Disconnect</Button>
      </li>)}</ul>
    </SettingsSection>}
    {!loading && <SettingsSection number={5} title="X accounts">
      <form onSubmit={event => void saveX(event)}>
        <div className="field"><label className="field-label" htmlFor="x-token">X API token</label>
          {xLast4 && <p className="key-saved" id="x-token-saved"><Icon name="check"/>
            Saved token ending in <code>{xLast4}</code></p>}
          <input className="input" id="x-token" type="password" value={xToken}
            autoComplete="new-password" aria-invalid={xError && xErrorOnToken ? true : undefined}
            aria-describedby={[xLast4 ? 'x-token-saved' : null, 'x-token-note',
              xError && xErrorOnToken ? 'x-token-error' : null].filter(Boolean).join(' ')}
            onChange={event => setXToken(event.target.value)}/>
          <p className="field-hint" id="x-token-note">
            Your own X developer App's Bearer token is stored encrypted on this computer.
          </p>
        </div>
        <div className="field-row">
          <Button type="submit">Save X token</Button>
          <Button type="button" onClick={() => void testX()}>Test X token</Button>
          <Button type="button" variant="ghost" onClick={() => void removeX()}>Remove X token</Button>
        </div>
      </form>
      <p className="note"><Icon name="info"/><span>X API reads are billed to your X developer account. You can set a{' '}
        <a href="https://github.com/Zhuoang2/catchup#x-accounts">spending limit in the X console</a>.</span></p>
      {xDeleteConfirm ? <div role="group" aria-label="Confirm X data deletion">
        <p>Delete all X data? This removes your X token, followed X accounts, and their items in saved digests.
          {' '}Pages saved from X with the extension stay.</p>
        <div className="actions">
          <Button type="button" variant="danger-solid" onClick={() => void deleteAllX()}>Delete X data</Button>
          <Button type="button" variant="ghost" onClick={() => setXDeleteConfirm(false)}>Cancel</Button>
        </div>
      </div> : <Button type="button" variant="danger"
        onClick={() => { setXError(''); setXErrorOnToken(false); setXMessage(''); setXDeleteConfirm(true) }}>Delete all X data</Button>}
      {xError && <p className="field-error" id="x-token-error" role="alert"><Icon name="alert"/>{xError}</p>}
      {xMessage && <p className="inline-msg msg-ok" role="status"><Icon name="check"/>{xMessage}</p>}
    </SettingsSection>}
    {error && !errorField && <p className="field-error" role="alert"><Icon name="alert"/>{error}</p>}
  </section>
}
