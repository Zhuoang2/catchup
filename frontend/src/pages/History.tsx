import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../api/client'
import { longDate, plural, shortTime } from '../components/format'
import { Icon } from '../components/Icon'
import { PageHead, Rail, buttonClass } from '../components/ui'

type DigestEntry = {
  id: number; created_at: string; item_count: number; source_count: number
  topics: string[]; language: string | null; creator_updates_only: boolean
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
        if (mounted) setDigests(entries)
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
                {digest.topics.length ? digest.topics.join(' · ') :
                  digest.creator_updates_only ? 'Creator updates only' : 'No topics'}
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
