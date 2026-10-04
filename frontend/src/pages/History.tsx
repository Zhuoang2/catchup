import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../api/client'

type DigestEntry = {
  id: number
  created_at: string
  item_count: number
  source_count: number
}

export default function History() {
  const [digests, setDigests] = useState<DigestEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    request<DigestEntry[]>('/digests')
      .then((entries) => { if (mounted) setDigests(entries) })
      .catch((reason: Error) => { if (mounted) setError(reason.message) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  return (
    <section>
      <h2>Digest history</h2>
      {loading && <p>Loading digests…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && digests.length === 0 && <p>No saved digests yet.</p>}
      <ul>
        {digests.map((digest) => (
          <li key={digest.id}>
            <Link to={`/digests/${digest.id}`}>
              <time dateTime={digest.created_at}>{new Date(digest.created_at).toLocaleString()}</time>
            </Link>
            {' · '}{digest.item_count} {digest.item_count === 1 ? 'item' : 'items'}
            {' · '}{digest.source_count} {digest.source_count === 1 ? 'source' : 'sources'}
          </li>
        ))}
      </ul>
    </section>
  )
}
