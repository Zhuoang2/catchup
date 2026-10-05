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
type CreatorUpdate = {
  source_name: string
  items: { title: string; link: string; published_at: string | null; reason: string }[]
}
type Digest = {
  id: number; created_at: string; model_id: string; topics: Topic[]
  creator_updates?: CreatorUpdate[]; transcript_wait_days?: number
  prompt_tokens?: number | null; completion_tokens?: number | null
}

function reasonLabel(reason: string, days: number) {
  const labels: Record<string, string> = {
    captions_off: 'Caption fetching is off',
    no_captions: 'This video has no captions',
    blocked: 'Blocked by YouTube',
    captions_failed: 'Captions could not be fetched',
    no_transcript: `No transcript within ${days} days`,
  }
  return labels[reason] ?? reason
}

function SummaryText({ text }: { text: string | null }) {
  if (!text) return null
  const lines = text.split('\n')
  const firstPoint = lines.findIndex(line => line.startsWith('- '))
  if (firstPoint < 0) return <p>{text}</p>
  return <>
    {lines.slice(0, firstPoint).join('\n').trim() && <p>{lines.slice(0, firstPoint).join('\n').trim()}</p>}
    <ul>{lines.slice(firstPoint).filter(line => line.startsWith('- '))
      .map((line, index) => <li key={index}>{line.slice(2)}</li>)}</ul>
  </>
}

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
          <p>{digest.prompt_tokens != null && digest.completion_tokens != null
            ? `Tokens: ${digest.prompt_tokens} in / ${digest.completion_tokens} out`
            : 'Tokens: not reported'}</p>
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
                    {item.summary_unavailable ? <p>Summary unavailable</p> : <SummaryText text={item.summary} />}
                  </li>
                ))}
              </ul>
            </section>
          ))}
          {!!digest.creator_updates?.length && (
            <section aria-label="Creator updates">
              <h3>Creator updates</h3>
              {digest.creator_updates.map(group => (
                <section key={group.source_name} aria-label={group.source_name}>
                  <h4>{group.source_name}</h4>
                  <ul>{group.items.map((item, index) => (
                    <li key={index}>
                      <a href={item.link} target="_blank" rel="noopener noreferrer">{item.title}</a>
                      {item.published_at && <> · <time dateTime={item.published_at}>
                        {new Date(item.published_at).toLocaleString()}
                      </time></>}
                      <p>{reasonLabel(item.reason, digest.transcript_wait_days ?? 7)}</p>
                    </li>
                  ))}</ul>
                </section>
              ))}
            </section>
          )}
        </>
      )}
    </section>
  )
}
