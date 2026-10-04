import { useEffect, useState } from 'react'
import { ApiError, request } from '../api/client'

type Entry = { title: string; link: string; published_at: string | null }
type Preview = {
  feed_url: string; site_url: string; title: string;
  follows_site_feed_notice: boolean; entries: Entry[]
}
type Source = {
  id: number; title: string; feed_url: string; site_url: string;
  last_check_at: string | null; last_check_status: string | null; possible_gap: boolean
}

const messages: Record<string, string> = {
  invalid_url: 'Enter a valid HTTP or HTTPS URL.',
  blocked_address: 'This address is not allowed.',
  fetch_failed: 'Could not fetch the source. Check the URL and try again.',
  no_feed: 'No supported feed was found at this URL.',
  not_a_feed: 'The URL did not return a parsable feed.',
}

function describeError(error: unknown) {
  if (error instanceof ApiError) return messages[error.code] ?? error.message
  return 'Could not connect to CatchUp.'
}

export default function Sources() {
  const [url, setUrl] = useState('')
  const [preview, setPreview] = useState<Preview | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function refresh() {
    setSources(await request<Source[]>('/sources'))
  }

  useEffect(() => {
    refresh().catch((err: unknown) => setError(describeError(err)))
      .finally(() => setLoading(false))
  }, [])

  async function previewSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPreview(null)
    setError('')
    setMessage('')
    try {
      setPreview(await request<Preview>('/sources/preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      }))
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function confirmSource() {
    if (!preview) return
    setError('')
    try {
      await request<Source>('/sources', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feed_url: preview.feed_url }),
      })
      setPreview(null)
      setUrl('')
      await refresh()
      setMessage('Source saved.')
    } catch (err) {
      setError(describeError(err))
    }
  }

  async function deleteSource(source: Source) {
    if (!window.confirm(`Delete ${source.title}? Saved digests will remain available.`)) return
    setError('')
    try {
      await request<void>(`/sources/${source.id}`, { method: 'DELETE' })
      await refresh()
    } catch (err) {
      setError(describeError(err))
    }
  }

  return (
    <section>
      <h2>Sources</h2>
      <form onSubmit={previewSource}>
        <label>Website or feed URL <input type="url" value={url} required
          onChange={event => { setUrl(event.target.value); setPreview(null) }}
          placeholder="https://example.com" /></label>
        <button type="submit">Preview</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {preview && (
        <section aria-label="Source preview">
          <h3>{preview.title}</h3>
          <p>Feed: <a href={preview.feed_url}>{preview.feed_url}</a></p>
          <p>Site: <a href={preview.site_url}>{preview.site_url}</a></p>
          {preview.follows_site_feed_notice && (
            <p>CatchUp will follow the whole site's feed, not only this page.</p>
          )}
          <ul>{preview.entries.map((entry, index) => (
            <li key={`${entry.link}-${index}`}>
              <a href={entry.link}>{entry.title}</a>
              {entry.published_at && <> ({new Date(entry.published_at).toLocaleDateString()})</>}
            </li>
          ))}</ul>
          <button type="button" onClick={confirmSource}>Confirm source</button>
        </section>
      )}
      <h3>Saved sources</h3>
      {loading ? <p>Loading sources…</p> : sources.length === 0 ? <p>No sources added yet.</p> : (
        <ul>{sources.map(source => (
          <li key={source.id}>
            <strong>{source.title}</strong> <a href={source.feed_url}>{source.feed_url}</a>
            <span> Last check: {source.last_check_status ?? 'Never checked'}
              {source.last_check_at ? ` (${new Date(source.last_check_at).toLocaleString()})` : ''}
            </span>
            {source.possible_gap && <span> Possible gap</span>}
            <button type="button" onClick={() => deleteSource(source)}>Delete {source.title}</button>
          </li>
        ))}</ul>
      )}
    </section>
  )
}
