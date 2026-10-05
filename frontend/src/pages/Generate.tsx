import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, request } from '../api/client'

type Check = {
  source_id: number
  source_title: string
  status: string
  possible_gap: boolean
  error: string | null
  http_status: number | null
  rate_limited: boolean
}
type Run = {
  id: number
  status: string
  items_total: number
  items_done: number
  sources_total: number
  source_checks: Check[]
  error_kind: string | null
  error_message: string | null
  digest_id: number | null
  waiting_count: number
  deferred_count: number
}

const active = (run: Run) => ['queued', 'collecting', 'summarizing', 'grouping'].includes(run.status)

export default function Generate() {
  const [run, setRun] = useState<Run | null>(null)
  const [error, setError] = useState('')
  const [needsModel, setNeedsModel] = useState(false)

  useEffect(() => {
    let mounted = true
    request<Run | null>('/digest-runs/active')
      .then((result) => { if (mounted) setRun(result) })
      .catch((reason: Error) => { if (mounted) setError(reason.message) })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    if (!run || !active(run)) return
    const timer = window.setInterval(() => {
      request<Run>(`/digest-runs/${run.id}`)
        .then((result) => { setRun(result); setError('') })
        .catch((reason: Error) => setError(reason.message))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [run?.id, run?.status])

  async function generate() {
    setError('')
    setNeedsModel(false)
    try {
      setRun(await request<Run>('/digest-runs', { method: 'POST' }))
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === 'run_active') {
        try {
          setRun(await request<Run | null>('/digest-runs/active'))
        } catch (refreshError) {
          setError((refreshError as Error).message)
        }
      } else if (reason instanceof ApiError && reason.code === 'model_not_configured') {
        setNeedsModel(true)
      } else {
        setError((reason as Error).message)
      }
    }
  }

  return (
    <section>
      <h2>Generate digest</h2>
      <button type="button" onClick={generate} disabled={!!run && active(run)}>Generate Digest</button>
      {needsModel && <p role="alert">Set up your model in <Link to="/settings">Settings</Link> first.</p>}
      {error && <p role="alert">{error}</p>}
      {run && (
        <section aria-label="Digest run">
          <p>Stage: {run.status}</p>
          {run.status === 'collecting'
            ? <p>Sources checked: {run.source_checks.length} of {run.sources_total}</p>
            : <p>Items summarized: {run.items_done} of {run.items_total}</p>}
          {run.status === 'no_new_content' && <p>No new content.</p>}
          {!!run.waiting_count && <p>{run.waiting_count} items waiting for transcripts or captions</p>}
          {!!run.deferred_count && <p>{run.deferred_count} videos deferred to the next run</p>}
          {run.status === 'failed' && <p role="alert">{run.error_message || 'Digest generation failed.'}</p>}
          {run.status === 'succeeded' && run.digest_id && (
            <Link to={`/digests/${run.digest_id}`}>View digest</Link>
          )}
          <h3>Source checks</h3>
          <ul>
            {run.source_checks.map((check) => (
              <li key={check.source_id}>
                {check.source_title}: {check.rate_limited ? 'rate limited (try later)' : check.status}
                {check.possible_gap && ' (possible gap)'}
                {!check.rate_limited && check.error && `: ${check.error}`}
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  )
}
