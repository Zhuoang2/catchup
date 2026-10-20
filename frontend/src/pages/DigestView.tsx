import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { request } from '../api/client'
import { shortDate } from '../components/format'
import { DigestArticle, type Digest } from '../components/DigestArticle'
import { PageHead } from '../components/ui'
import { useDocumentTitle } from '../components/useDocumentTitle'

export default function DigestView() {
  const { id } = useParams()
  const [digest, setDigest] = useState<Digest | null>(null)
  const [showImages, setShowImages] = useState(true)
  const [error, setError] = useState('')
  useDocumentTitle(!error && digest?.id === Number(id)
    ? `No. ${digest.id} · ${shortDate(digest.created_at)}` : 'Digest')
  useEffect(() => {
    let mounted = true
    setDigest(null)
    setError('')
    Promise.all([
      request<Digest>(`/digests/${id}`),
      request<{ show_images: boolean }>('/settings/preferences').catch(() => ({ show_images: true })),
    ])
      .then(([result, preferences]) => { if (mounted) {
        setShowImages(preferences.show_images !== false)
        setDigest(result)
      } })
      .catch((reason: Error) => { if (mounted) setError(reason.message) })
    return () => { mounted = false }
  }, [id])
  if (error) return <section className="page page-digest">
    <PageHead title="Could not load digest"/>
    <p role="alert">{error}</p><p className="back-link"><Link to="/digests">← All digests</Link></p>
  </section>
  if (!digest) return <section className="page page-digest"><PageHead title="Loading digest…"/></section>
  return <DigestArticle digest={digest} showImages={showImages}
    headEnd={<p className="back-link"><Link to="/digests">← All digests</Link></p>}/>
}
