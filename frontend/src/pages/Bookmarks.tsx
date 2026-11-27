import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../api/client'
import { ItemActions, ItemContent, type DigestItem, type Marks } from '../components/DigestArticle'
import { shortDate } from '../components/format'
import { digestLang } from '../components/lang'
import { PageHead, buttonClass } from '../components/ui'
import { useDocumentTitle } from '../components/useDocumentTitle'

type BookmarkEntry = DigestItem & {
  bookmarked_at: string
  digest: { id: number; created_at: string; language: string | null }
}

export default function Bookmarks() {
  useDocumentTitle('Bookmarks')
  const [entries, setEntries] = useState<BookmarkEntry[]>([])
  const [showImages, setShowImages] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, announce] = useState('')
  useEffect(() => {
    let mounted = true
    Promise.all([
      request<BookmarkEntry[]>('/bookmarks'),
      request<{ show_images: boolean }>('/settings/preferences').catch(() => ({ show_images: true })),
    ])
      .then(([result, preferences]) => { if (mounted) {
        setEntries(result)
        setShowImages(preferences.show_images !== false)
      } })
      .catch((reason: Error) => { if (mounted) setError(reason.message) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])
  function updateEntry(marks: Marks) {
    setEntries(previous => previous.map(entry => entry.id === marks.id ? { ...entry, ...marks } : entry))
  }
  return <section className="page page-bookmarks">
    <PageHead title="Bookmarks" lede="Items you bookmarked, newest first. They stay when their source is deleted.">
      <p className="back-link"><Link to="/digests">← All digests</Link></p>
    </PageHead>
    <p className="sr-only" role="status">{message}</p>
    {loading && <p>Loading bookmarks…</p>}
    {error && <p role="alert">{error}</p>}
    {!loading && !error && !entries.length && <div className="empty-state">
      <h2>No bookmarks yet</h2>
      <p>Bookmark an item in a digest to keep it here.</p>
      <Link to="/" className={buttonClass('primary')}>Open the latest digest</Link>
    </div>}
    {!!entries.length && <ol className="bookmark-list">
      {entries.map(entry => <li key={entry.id}>
        <article className="item">
          <ItemContent item={entry} lang={digestLang(entry.digest.language)} showImages={showImages}
            imageKey={`${entry.digest.id}-${entry.id}`} headingLevel={2}/>
          <p className="bookmark-from"><Link to={`/digests/${entry.digest.id}`}>
            From No. {entry.digest.id} · {shortDate(entry.digest.created_at)}
          </Link></p>
          <ItemActions item={entry} title={entry.title} announce={announce} onChange={updateEntry}/>
        </article>
      </li>)}
    </ol>}
  </section>
}
