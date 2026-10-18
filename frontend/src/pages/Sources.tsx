import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, request } from '../api/client'
import { parseDate, shortDateTime } from '../components/format'
import { Icon } from '../components/Icon'
import { useDocumentTitle } from '../components/useDocumentTitle'
import { Button, Chip, KindBadge, PageHead, Rail, type SourceKind } from '../components/ui'

type Entry = { title: string; link: string; published_at: string | null }
type Preview = {
  feed_url: string; site_url: string; title: string
  follows_site_feed_notice: boolean; entries: Entry[]
  kind: SourceKind; captions_enabled: boolean
}
type Source = {
  id: number; title: string; feed_url: string; site_url: string; kind: SourceKind
  last_check_at: string | null; last_check_status: string | null; possible_gap: boolean
  http_status: number | null; rate_limited: boolean
}

const messages: Record<string, string> = {
  invalid_url: 'Enter a valid HTTP or HTTPS URL.',
  blocked_address: 'This address is not allowed.',
  fetch_failed: 'Could not fetch the source. Check the URL and try again.',
  no_feed: 'No supported feed was found at this URL.',
  not_a_feed: 'The URL did not return a parsable feed.',
}

function describeError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.code === 'rate_limited') {
      return `Rate limited — try again later${error.retryAfter !== null ? ` (about ${error.retryAfter} seconds)` : ''}.`
    }
    if (error.code === 'fetch_failed' && error.httpStatus !== null) {
      const status = error.httpStatus
      if (status === 401 || status === 403) {
        return `The site refused the request (HTTP ${status}). If you know its feed URL, paste that instead.`
      }
      if (status === 404 || status === 410) {
        return `The page was not found (HTTP ${status}). Check the URL, or paste the site's feed URL.`
      }
      if (status >= 500 && status <= 599) {
        return `The site is not responding (HTTP ${status}). Try again later.`
      }
      return `The site answered HTTP ${status}. Check the URL, or paste the site's feed URL.`
    }
    if (error.code === 'feed_unavailable') {
      return `The site's feed is temporarily unavailable${error.httpStatus !== null ? ` (HTTP ${error.httpStatus})` : ''}. Try again later.`
    }
    return messages[error.code] ?? error.message
  }
  return 'Could not connect to CatchUp.'
}

function SourcePreview({ preview, onConfirm, onCancel }: {
  preview: Preview; onConfirm: () => void; onCancel: () => void
}) {
  const method = preview.kind === 'podcast' ? 'Transcripts published by the show'
    : preview.kind === 'youtube' ? preview.captions_enabled
      ? 'Captions fetched from YouTube on this computer'
      : 'Caption fetching is off; videos will be listed without summaries'
      : 'Article text from the feed and linked pages'
  return <section className="preview-card" aria-label="Source preview">
    <div className="preview-head"><h2 className="preview-title">{preview.title}</h2>
      <KindBadge kind={preview.kind}/></div>
    <dl className="preview-urls"><dt>Feed</dt><dd><a href={preview.feed_url}>{preview.feed_url}</a></dd>
      <dt>Site</dt><dd><a href={preview.site_url}>{preview.site_url}</a></dd></dl>
    <p className="preview-method"><Icon name={preview.kind === 'youtube' && !preview.captions_enabled ? 'info' : 'check'}/>
      {method}{preview.kind === 'youtube' && !preview.captions_enabled && <>
        {' '}<Link to="/settings">Change in Settings</Link></>}
    </p>
    {preview.follows_site_feed_notice && <p className="notice"><Icon name="info"/>
      {preview.kind === 'podcast'
        ? 'CatchUp will follow the whole show, not only this episode.'
        : "CatchUp will follow the whole site's feed, not only this page."}</p>}
    <h3 className="section-label">Recent entries</h3>
    <ul className="entry-list">{preview.entries.map((entry, index) => <li key={`${entry.link}-${index}`}>
      <a href={entry.link}>{entry.title}</a>
      {entry.published_at && <time dateTime={entry.published_at}>
        {new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(parseDate(entry.published_at))}
      </time>}
    </li>)}</ul>
    <div className="actions"><Button variant="primary" type="button" onClick={onConfirm}>Confirm source</Button>
      <Button variant="ghost" type="button" onClick={onCancel}>Cancel</Button></div>
  </section>
}

function SourceStatus({ source }: { source: Source }) {
  const status = source.rate_limited ? 'Rate limited · try later' : ({
    new_items: 'New items', no_new_items: 'No new items', failed: 'Failed',
  } as Record<string, string>)[source.last_check_status ?? ''] ?? 'Never checked'
  const tone = source.rate_limited ? 'warn' : source.last_check_status === 'failed' ? 'error'
    : source.last_check_status === 'new_items' ? 'ok' : 'neutral'
  return <div className="source-status"><Chip tone={tone}>{status}</Chip>
    {source.possible_gap && <Chip tone="warn"
      title="Older items may have dropped off the feed between checks.">Possible gap</Chip>}
    {source.last_check_at && <time className="source-time" dateTime={source.last_check_at}>
      {shortDateTime(source.last_check_at)}</time>}
  </div>
}

export default function Sources() {
  useDocumentTitle('Sources')
  const [url, setUrl] = useState('')
  const [preview, setPreview] = useState<Preview | null>(null)
  const [sources, setSources] = useState<Source[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [fieldError, setFieldError] = useState('')
  const [pageError, setPageError] = useState('')
  const [message, setMessage] = useState('')
  const [confirmId, setConfirmId] = useState<number | null>(null)
  const [restoreFocusId, setRestoreFocusId] = useState<number | null>(null)
  const [focusAfterDelete, setFocusAfterDelete] = useState(false)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const emptyHeadingRef = useRef<HTMLHeadingElement>(null)
  const deleteRefs = useRef(new Map<number, HTMLButtonElement>())

  useEffect(() => {
    if (confirmId !== null) cancelRef.current?.focus()
    else if (restoreFocusId !== null) {
      deleteRefs.current.get(restoreFocusId)?.focus()
      setRestoreFocusId(null)
    }
  }, [confirmId, restoreFocusId])

  useEffect(() => {
    if (focusAfterDelete) {
      (sources?.length ? headingRef : emptyHeadingRef).current?.focus()
      setFocusAfterDelete(false)
    }
  }, [focusAfterDelete, sources])

  async function refresh() { setSources(await request<Source[]>('/sources')) }

  useEffect(() => {
    let mounted = true
    request<Source[]>('/sources')
      .then(result => { if (mounted) setSources(result) })
      .catch((err: unknown) => { if (mounted) setPageError(describeError(err)) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  async function previewSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPreview(null); setFieldError(''); setPageError(''); setMessage('')
    try {
      setPreview(await request<Preview>('/sources/preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      }))
    } catch (err) { setFieldError(describeError(err)) }
  }

  async function confirmSource() {
    if (!preview) return
    setFieldError('')
    try {
      await request<Source>('/sources', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feed_url: preview.feed_url }),
      })
      setPreview(null); setUrl('')
      await refresh()
      setMessage('Source saved.')
    } catch (err) { setFieldError(describeError(err)) }
  }

  async function deleteSource(source: Source) {
    setPageError('')
    try {
      await request<void>(`/sources/${source.id}`, { method: 'DELETE' })
    } catch (err) { setPageError(describeError(err)); return }
    setSources(previous => previous?.filter(entry => entry.id !== source.id) ?? null)
    setConfirmId(null)
    setFocusAfterDelete(true)
    try { await refresh() }
    catch (err) { setPageError(`Could not refresh sources. ${describeError(err)}`) }
  }

  return <section className="page page-sources">
    <PageHead title="Sources" lede="Blogs, podcasts, YouTube channels, and social profiles you follow."/>
    <form className="add-form card" onSubmit={event => void previewSource(event)} noValidate>
      <label className="field-label" htmlFor="url">Website or feed URL</label>
      <div className="input-row"><input className="input" id="url" type="url" value={url}
        onChange={event => { setUrl(event.target.value); setPreview(null); setFieldError('') }}
        placeholder="https://example.com" required aria-invalid={fieldError ? true : undefined}
        aria-describedby={`${fieldError ? 'url-error ' : ''}url-hint`}/>
        <Button variant={preview ? 'secondary' : 'primary'} type="submit">Preview</Button></div>
      {fieldError && <p className="field-error" id="url-error" role="alert"><Icon name="alert"/>{fieldError}</p>}
      <p className="field-hint" id="url-hint">Paste a page address. CatchUp looks for its feed and shows a preview before saving.</p>
    </form>
    {pageError && <p className="field-error" role="alert"><Icon name="alert"/>{pageError}</p>}
    {message && <p role="status">{message}</p>}
    {preview && <SourcePreview preview={preview} onConfirm={() => void confirmSource()}
      onCancel={() => setPreview(null)}/>}
    {!loading && sources !== null && sources.length > 0 && <h2 ref={headingRef} tabIndex={-1} className="section-label">
      Your sources <span className="count">{sources.length}</span>
    </h2>}
    {loading ? <p>Loading sources…</p> : sources === null ? null : !sources.length ? <div className="empty-state">
      <Icon name="sources" className="icon icon-empty"/>
      <h2 ref={emptyHeadingRef} tabIndex={-1}>No sources yet</h2>
      <p>Paste the address of something you follow. CatchUp finds its feed for you.</p>
      <ul className="examples"><li>A blog or news site</li><li>A podcast feed or Apple Podcasts link</li>
        <li>A YouTube channel</li><li>A Bluesky or Mastodon profile</li></ul>
    </div> : <>
      <ul className="source-list">{sources.map(source => confirmId === source.id
        ? <li className="source-row source-confirm" key={source.id}>
          <div role="group" aria-label="Confirm deletion">
            <p className="confirm-text"><strong>Delete {source.title}?</strong> Saved digests will remain available.</p>
            <div className="actions"><Button variant="danger-solid" size="sm" type="button"
              onClick={() => void deleteSource(source)}>Delete</Button>
              <Button ref={cancelRef} variant="ghost" size="sm" type="button" onClick={() => {
                setRestoreFocusId(source.id); setConfirmId(null)
              }}>Cancel</Button></div>
          </div>
        </li>
        : <li className="source-row" key={source.id}>
          <span className="source-icon"><Icon name={source.kind}/></span>
          <div className="source-main"><p className="source-title">{source.title} <KindBadge kind={source.kind}/></p>
            <p className="source-feed" title={source.feed_url}>{source.feed_url}</p></div>
          <SourceStatus source={source}/>
          <Button variant="ghost" size="sm" className="btn-danger" type="button"
            ref={node => { if (node) deleteRefs.current.set(source.id, node)
              else deleteRefs.current.delete(source.id) }}
            aria-label={`Delete ${source.title}`} onClick={() => setConfirmId(source.id)}>Delete</Button>
        </li>)}</ul>
    </>}
    <Rail>
      <section className="rail-box"><h2 className="rail-title">What you can add</h2>
        <ul className="rail-list"><li>Blogs and news sites with a feed</li>
          <li>Podcasts — summarized from published transcripts</li>
          <li>YouTube channels — captions are opt-in in Settings</li>
          <li>Bluesky and Mastodon profiles</li></ul>
        <p className="rail-meta">Apple Podcasts links work too; CatchUp finds the show’s feed.</p>
      </section>
      {!!sources?.length && <section className="rail-box"><h2 className="rail-title">Checks</h2>
        <p className="rail-meta">Sources are checked when you generate a digest. “Possible gap” means older items may have dropped off the feed between checks.</p>
      </section>}
    </Rail>
  </section>
}
