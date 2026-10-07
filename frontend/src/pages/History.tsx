import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../api/client'
import { longDate, plural, shortTime } from '../components/format'
import { Icon } from '../components/Icon'
import { PageHead, Rail, buttonClass } from '../components/ui'

type DigestEntry = {
  id: number; created_at: string; item_count: number; source_count: number
  topics?: { title: string }[]; language?: string | null
}

export default function History() {
  const [digests, setDigests] = useState<DigestEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    async function load() {
      try {
        const entries = await request<DigestEntry[]>('/digests')
        // The list API contains counts but not titles; use the saved detail
        // snapshots for previews without changing the endpoint.
        const withTopics = await Promise.all(entries.map(async entry => {
          const detail = await request<Pick<DigestEntry, 'topics' | 'language'>>(`/digests/${entry.id}`)
          return { ...entry, topics: detail.topics, language: detail.language }
        }))
        if (mounted) setDigests(withTopics)
      } catch (reason) {
        if (mounted) setError((reason as Error).message)
      } finally {
        if (mounted) setLoading(false)
      }
    }
    void load()
    return () => { mounted = false }
  }, [])

  return <section className="page page-history">
    <PageHead title="History" lede="Every digest you have generated, newest first."/>
    {loading && <p>Loading digests…</p>}
    {error && <p role="alert">{error}</p>}
    {!loading && !error && !digests.length &&
      <div className="empty-state"><Icon name="history" className="icon icon-empty"/>
        <h2>No saved digests yet</h2><p>Generate your first digest and it will appear here.</p>
        <Link to="/" className={buttonClass('primary')}>Generate a digest</Link>
      </div>}
    {!!digests.length && <ol className="history-list">
      {digests.map(digest => {
        const date = new Date(digest.created_at)
        return <li className="history-row" key={digest.id}>
          <Link className="history-link" to={`/digests/${digest.id}`}>
            <span className="history-date" aria-hidden="true"><span className="history-day">{date.getDate()}</span>
              <span className="history-month">{new Intl.DateTimeFormat('en-GB', { month: 'short' }).format(date)}</span>
            </span>
            <span className="history-main"><span className="history-title">No. {digest.id} ·{' '}
              <time dateTime={digest.created_at}>{longDate(digest.created_at)} · {shortTime(digest.created_at)}</time></span>
              <span className="history-topics" lang={digest.language || undefined}>
                {digest.topics?.length ? digest.topics.map(topic => topic.title).join(' · ') : 'Creator updates only'}
              </span>
            </span>
            <span className="history-counts">{plural(digest.item_count, 'item')} · {plural(digest.source_count, 'source')}</span>
          </Link>
        </li>
      })}</ol>}
    {!loading && !error && <Rail>
      {!!digests.length && <section className="rail-box"><h2 className="rail-title">Archive</h2>
        <p className="rail-big">{digests.length}</p>
        <p className="rail-meta">digests · {digests.reduce((n, digest) => n + digest.item_count, 0)} items in total</p>
      </section>}
      <section className="rail-box"><h2 className="rail-title">Kept as saved</h2>
        <p className="rail-meta">A saved digest never changes, even if a source is deleted later.</p>
      </section>
    </Rail>}
  </section>
}
