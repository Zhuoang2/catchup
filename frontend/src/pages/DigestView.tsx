import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { request } from '../api/client'

type DigestItem = {
  title: string
  link: string
  source_name: string
  published_at: string | null
  summary: string | null
  summary_unavailable: boolean
}
type Topic = { title: string; overview: string; items: DigestItem[] }
type Digest = { id: number; created_at: string; model_id: string; topics: Topic[] }

export default function DigestView() {
  const { id } = useParams()
  const [digest, setDigest] = useState<Digest | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let mounted = true
    request<Digest>(`/digests/${id}`)
      .then((result) => { if (mounted) setDigest(result) })
      .catch((reason: Error) => { if (mounted) setError(reason.message) })
    return () => { mounted = false }
  }, [id])

  return (
    <section>
      <h2>Digest</h2>
      {error && <p role="alert">{error}</p>}
      {digest && (
        <>
          <p>Created <time dateTime={digest.created_at}>
            {new Date(digest.created_at).toLocaleString()}
          </time></p>
          {digest.topics.map((topic, index) => (
            <section key={index} aria-label={topic.title}>
              <h3>{topic.title}</h3>
              <p>{topic.overview}</p>
              <ul>
                {topic.items.map((item, position) => (
                  <li key={position}>
                    <a href={item.link} target="_blank" rel="noopener noreferrer">{item.title}</a>
                    <p>{item.source_name}
                      {item.published_at && <> · <time dateTime={item.published_at}>
                        {new Date(item.published_at).toLocaleString()}
                      </time></>}
                    </p>
                    <p>{item.summary_unavailable ? 'Summary unavailable' : item.summary}</p>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </>
      )}
    </section>
  )
}
