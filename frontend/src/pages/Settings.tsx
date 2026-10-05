import { useEffect, useState } from 'react'
import { ApiError, request } from '../api/client'

type ModelSettings = { base_url: string; model_id: string; key_set: boolean; api_key_last4: string | null }
type Preferences = {
  digest_language: string
  youtube_captions: boolean
  youtube_skip_shorts: boolean
}
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

export default function Settings() {
  const [baseUrl, setBaseUrl] = useState('https://api.deepseek.com')
  const [key, setKey] = useState('')
  const [last4, setLast4] = useState<string | null>(null)
  const [model, setModel] = useState('')
  const [models, setModels] = useState<string[]>([])
  const [language, setLanguage] = useState('en')
  const [otherLanguage, setOtherLanguage] = useState('')
  const [youtubeCaptions, setYoutubeCaptions] = useState(false)
  const [skipShorts, setSkipShorts] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      request<ModelSettings>('/settings/model'),
      request<Preferences>('/settings/preferences'),
    ]).then(([settings, preferences]) => {
      setBaseUrl(settings.base_url)
      setModel(settings.model_id)
      setModels(settings.model_id ? [settings.model_id] : [])
      setLast4(settings.key_set ? settings.api_key_last4 : null)
      const selected = preferences.digest_language
      setLanguage(languageOptions.includes(selected) ? selected : 'other')
      if (!languageOptions.includes(selected)) setOtherLanguage(selected)
      setYoutubeCaptions(preferences.youtube_captions)
      setSkipShorts(preferences.youtube_skip_shorts)
    }).catch((err: unknown) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  async function testConnection() {
    setError('')
    setMessage('')
    try {
      const result = await request<TestResult>('/settings/model/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, api_key: key || undefined }),
      })
      setModels(result.models)
      if (!result.models.includes(model)) setModel(result.models[0] ?? '')
      setMessage('Connection succeeded. Choose a model and save.')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const saved = await request<ModelSettings>('/settings/model', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url: baseUrl, model_id: model, api_key: key }),
      })
      await request<Preferences>('/settings/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          digest_language: language === 'other' ? otherLanguage : language,
          youtube_captions: youtubeCaptions, youtube_skip_shorts: skipShorts,
        }),
      })
      setLast4(saved.api_key_last4)
      setKey('')
      setMessage('Settings saved.')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <section>
      <h2>Settings</h2>
      {loading ? <p>Loading settings…</p> : (
        <form onSubmit={save}>
          <p>Content will be sent to your configured model provider.</p>
          <p><label>Provider base URL <input value={baseUrl} onChange={event => setBaseUrl(event.target.value)} required /></label></p>
          <p><label>API key <input type="password" value={key} placeholder={last4 ? `•••• ${last4}` : ''}
            onChange={event => setKey(event.target.value)} autoComplete="new-password" /></label></p>
          <p><button type="button" onClick={testConnection}>Test connection</button></p>
          <p><label>Model <select value={model} onChange={event => setModel(event.target.value)} required>
            {!model && <option value="">Choose a model</option>}
            {models.map(id => <option key={id} value={id}>{id}</option>)}
          </select></label></p>
          <p><label>Digest language <select value={language} onChange={event => setLanguage(event.target.value)}>
            <option value="en">English</option>
            <option value="zh-Hans">简体中文</option>
            <option value="original">Same as original</option>
            <option value="other">Other</option>
          </select></label></p>
          {language === 'other' && <p><label>Other language <input value={otherLanguage} maxLength={40}
            onChange={event => setOtherLanguage(event.target.value)} required /></label></p>}
          <p><label><input type="checkbox" checked={youtubeCaptions}
            onChange={event => setYoutubeCaptions(event.target.checked)} /> Fetch captions locally</label></p>
          <p>Fetches captions from YouTube from this computer. YouTube's Terms of Service do not allow automated access, so turn this on only if you accept that risk. When off, new videos are listed under Creator updates without a summary.</p>
          <p><label><input type="checkbox" checked={skipShorts}
            onChange={event => setSkipShorts(event.target.checked)} /> Skip Shorts</label></p>
          <button type="submit">Save</button>
        </form>
      )}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </section>
  )
}
