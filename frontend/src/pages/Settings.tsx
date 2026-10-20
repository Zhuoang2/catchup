import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { ApiError, request } from '../api/client'
import { Icon } from '../components/Icon'
import { useDocumentTitle } from '../components/useDocumentTitle'
import { Button, PageHead, Switch } from '../components/ui'

type ModelSettings = { base_url: string; model_id: string; key_set: boolean; api_key_last4: string | null }
type Preferences = { digest_language: string; youtube_captions: boolean; youtube_skip_shorts: boolean;
  show_images: boolean }
type TestResult = { ok: true; models: string[] }
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
  const [loading, setLoading] = useState(true)

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

  function showError(err: unknown) {
    setError(errorMessage(err))
    setErrorField(err instanceof ApiError
      ? err.code === 'connection_failed' ? 'base'
        : ['auth_failed', 'insufficient_balance', 'api_key_required', 'missing_api_key'].includes(err.code)
          ? 'key' : null
      : null)
  }

  async function testConnection() {
    setError(''); setErrorField(null); setMessage('')
    try {
      const result = await request<TestResult>('/settings/model/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, api_key: key || undefined }),
      })
      setModels(result.models)
      if (!result.models.includes(model)) setModel(result.models[0] ?? '')
      setMessage('Connection succeeded. Choose a model, then click Save.')
    } catch (err) { showError(err) }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(''); setErrorField(null); setMessage('')
    try {
      const saved = await request<ModelSettings>('/settings/model', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, model_id: model, api_key: key }),
      })
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
      ? 'Your model, digest language, and YouTube options.'
      : 'Three quick steps. Your key stays on this computer, encrypted.'}/>
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
            ? 'Leave empty to keep the saved key.'
            : 'Stored encrypted on this computer. It is never shown again.'}</p>
        </div>
        <div className="field-row"><Button type="button" onClick={() => void testConnection()}>
          Test connection</Button>
          {message.startsWith('Connection') && <p className="inline-msg msg-ok" role="status">
            <Icon name="check"/>{message}</p>}
        </div>
        {error && errorField && <p className="field-error" id={errorField === 'base' ? 'base-error' : 'key-error'}
          role="alert"><Icon name="alert"/>{error}</p>}
        <div className="field"><label className="field-label" htmlFor="model">Model</label>
          <select className="input select" id="model" value={model}
            onChange={event => setModel(event.target.value)} disabled={!models.length} required>
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
    {error && !errorField && <p className="field-error" role="alert"><Icon name="alert"/>{error}</p>}
  </section>
}
