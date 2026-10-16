import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, request } from '../api/client'
import { DigestArticle } from '../components/DigestArticle'
import { plural, tokenTotals } from '../components/format'
import type { Digest } from '../components/DigestArticle'
import { Icon } from '../components/Icon'
import { useDocumentTitle } from '../components/useDocumentTitle'
import { Alert, Button, Chip, PageHead, Progress, Rail, StatusRegion, Stepper, buttonClass } from '../components/ui'

type Check = {
  source_id: number; source_title: string; status: string; possible_gap: boolean
  error: string | null; http_status: number | null; rate_limited: boolean
}
type Run = {
  id: number; status: string; items_total: number; items_done: number; sources_total: number
  digest_item_count: number | null; digest_update_count: number | null
  source_checks: Check[]; error_kind: string | null; error_message: string | null; digest_id: number | null
  waiting_count: number; deferred_count: number; prompt_tokens: number | null; completion_tokens: number | null
}
type Source = { kind: string }
// "16 items (14 summarized, 2 in Creator updates)": the saved total, split when Creator updates are part of it.
function savedItems(run: Run) {
  const total = run.digest_item_count ?? run.items_total
  const updates = run.digest_update_count ?? 0
  if (!updates) return plural(total, 'item')
  if (updates >= total) return `${plural(total, 'item')} in Creator updates`
  return `${plural(total, 'item')} (${total - updates} summarized, ${updates} in Creator updates)`
}
const active = (run: Run) => ['queued', 'collecting', 'summarizing', 'grouping'].includes(run.status)
const configErrors = ['auth_failed', 'insufficient_balance', 'model_not_configured', 'connection_failed']

function SourceChecks({ checks, compact = false }: { checks: Check[]; compact?: boolean }) {
  return <>{compact ? <p className="section-label">Sources</p> : <h2 className="section-label">Sources</h2>}<ul className="check-list">{checks.map(check =>
    <li className="check-row" key={check.source_id}>
      <span className="check-title">{check.source_title}</span><span className="check-status">
        <Chip tone={check.rate_limited ? 'warn' : check.status === 'failed' ? 'error'
          : check.status === 'new_items' ? 'ok' : 'neutral'}>
          {check.rate_limited ? 'Rate limited · try later' : ({
            failed: 'Failed', new_items: 'New items', no_new_items: 'No new items',
          } as Record<string, string>)[check.status] ?? check.status}
        </Chip>
        {check.possible_gap && <Chip tone="warn"
          title="Older items may have dropped off the feed between checks.">Possible gap</Chip>}
      </span>
      {!check.rate_limited && check.error && <span className="check-error">{check.error}</span>}
    </li>)}</ul></>
}

function HeldNotes({ run }: { run: Run }) {
  return run.waiting_count || run.deferred_count ? <ul className="held-notes">
    {!!run.waiting_count && <li>{plural(run.waiting_count, 'item')} waiting for transcripts or captions</li>}
    {!!run.deferred_count && <li>{plural(run.deferred_count, 'video')} deferred to the next run</li>}
  </ul> : null
}

export default function Home() {
  const [run, setRun] = useState<Run | null>(null)
  const [modelReady, setModelReady] = useState<boolean | null>(null)
  const [sources, setSources] = useState<Source[] | null>(null)
  const [digest, setDigest] = useState<Digest | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<{ title: string; message: string } | null>(null)
  const [error, setError] = useState<{ title: string; message: string; source?: 'poll' } | null>(null)
  const [newDigestError, setNewDigestError] = useState<{ id: number; message: string } | null>(null)
  useDocumentTitle(digest ? `Latest · No. ${digest.id}` : 'Latest')

  useEffect(() => {
    let mounted = true
    Promise.allSettled([
      request<{ key_set: boolean }>('/settings/model'),
      request<Source[]>('/sources'),
      request<Digest | null>('/digests/latest'),
      request<Run | null>('/digest-runs/active'),
    ] as const).then(([settings, savedSources, history, current]) => {
      if (!mounted) return
      setModelReady(settings.status === 'fulfilled' ? settings.value.key_set : true)
      if (savedSources.status === 'fulfilled') setSources(savedSources.value)
      if (history.status === 'fulfilled') setDigest(history.value)
      if (current.status === 'fulfilled') setRun(current.value)
      const failure = [settings, savedSources, history, current].find(result => result.status === 'rejected')
      if (failure?.status === 'rejected') {
        setLoadError({ title: history.status === 'rejected'
          ? 'Could not load the latest digest' : 'Could not load some page details',
        message: (failure.reason as Error).message })
      }
      setLoading(false)
    })
    return () => { mounted = false }
  }, [])

  useEffect(() => {
    if (!run || !active(run)) return
    let mounted = true
    const timer = window.setInterval(() => {
      request<Run>(`/digest-runs/${run.id}`)
        .then(result => { if (mounted) {
          setRun(result)
          setError(previous => previous?.source === 'poll' ? null : previous)
        } })
        .catch((reason: Error) => { if (mounted) setError({
          title: 'Could not check digest progress', message: reason.message, source: 'poll',
        }) })
    }, 1000)
    return () => { mounted = false; window.clearInterval(timer) }
  }, [run?.id, run?.status])

  useEffect(() => {
    if (run?.status !== 'succeeded' || !run.digest_id || digest?.id === run.digest_id) return
    let mounted = true
    request<Digest>(`/digests/${run.digest_id}`)
      .then(result => { if (mounted) {
        setDigest(result)
        setNewDigestError(null)
      } })
      .catch((reason: Error) => { if (mounted) setNewDigestError({
        id: run.digest_id!, message: reason.message,
      }) })
    return () => { mounted = false }
  }, [run?.id, run?.status, run?.digest_id, digest?.id])

  async function generate() {
    setError(null)
    try {
      setRun(await request<Run>('/digest-runs', { method: 'POST' }))
    } catch (reason) {
      if (reason instanceof ApiError && reason.code === 'run_active') {
        try { setRun(await request<Run | null>('/digest-runs/active')) }
        catch (refreshError) { setError({
          title: 'Could not resume digest run', message: (refreshError as Error).message,
        }) }
      } else if (reason instanceof ApiError && reason.code === 'model_not_configured') {
        setModelReady(false)
      } else setError({ title: 'Could not start digest', message: (reason as Error).message })
    }
  }

  const firstRun = modelReady === false
  const running = !!run && active(run)
  const noSources = modelReady === true && sources?.length === 0 && !run
  const state = firstRun ? 'first-run' : run?.status ?? 'idle'
  const configurationError = state === 'failed' && configErrors.includes(run?.error_kind ?? '')
  const status = run?.status === 'collecting' || run?.status === 'queued'
    ? `Checking sources, ${run.source_checks.length} of ${run.sources_total}`
    : run?.status === 'summarizing' || run?.status === 'grouping'
      ? `Summarizing, ${run.items_done} of ${run.items_total}`
      : run?.status === 'succeeded' ? `Digest ready: ${savedItems(run)}`
        : run?.status === 'no_new_content' ? 'No new content'
          : run?.status === 'failed' ? `Digest generation failed: ${run.error_message || 'Digest generation failed. Try again.'}` : ''

  return <>
  {loading ? <section className="page page-generate"><PageHead title="Loading…"/></section>
    : digest ? <DigestArticle digest={digest} className="page-home" before={
      <section className="run-bar" aria-label="Digest run">
        <div className="run-bar-actions">
          {firstRun ? <>
            <Link className={buttonClass('primary', 'lg')} to="/settings">Set up your model</Link>
            <Button disabled aria-describedby="home-model-why">Generate digest</Button>
            <p className="hero-meta" id="home-model-why">Available once a model is set up and a source is added.</p>
          </> : noSources ? <>
            <Link className={buttonClass('primary', 'lg')} to="/sources">Add sources</Link>
            <Button disabled aria-describedby="home-sources-why">Generate digest</Button>
            <p className="hero-meta" id="home-sources-why">Available once a source is added.</p>
          </> : <>
            {configurationError && <Link className={buttonClass('primary')} to="/settings">Check settings</Link>}
            <Button variant={running || state === 'idle' || state === 'failed' && !configurationError ? 'primary' : 'secondary'}
              size="lg" type="button" onClick={() => void generate()} disabled={running || modelReady === null}>
              {running ? 'Generating…' : state === 'failed' ? 'Try again' : 'Generate digest'}
            </Button>
          </>}
          {sources !== null && <p className="hero-meta">{plural(sources.length, 'source')} ·{' '}
            <Link to="/sources">Manage sources</Link></p>}
        </div>
        {loadError && <Alert tone="error" title={loadError.title}>{loadError.message}</Alert>}
        {error && <Alert tone="error" title={error.title}>{error.message}</Alert>}
        {newDigestError && <Alert tone="error" title="Could not load the new digest"
          actions={<Link to={`/digests/${newDigestError.id}`}>View digest</Link>}>
          {newDigestError.message}
        </Alert>}
        {running && run && <>
          <Stepper current={run.status === 'queued' ? 'collecting'
            : run.status === 'grouping' ? 'grouping' : run.status as 'collecting' | 'summarizing'}/>
          <Progress label={run.status === 'collecting' || run.status === 'queued'
            ? `Sources checked: ${run.source_checks.length} of ${run.sources_total}`
            : `Items summarized: ${run.items_done} of ${run.items_total}`}
            value={run.status === 'collecting' || run.status === 'queued'
              ? run.source_checks.length : run.items_done}
            max={run.status === 'collecting' || run.status === 'queued' ? run.sources_total : run.items_total}/>
          <SourceChecks checks={run.source_checks} compact/>
        </>}
        {state === 'succeeded' && run && <>
          <p className="result-meta">Your digest is ready · {savedItems(run)} · {plural(run.sources_total, 'source')}
            {' · '}{tokenTotals(run.prompt_tokens, run.completion_tokens)}</p>
          <HeldNotes run={run}/><SourceChecks checks={run.source_checks} compact/>
        </>}
        {state === 'no_new_content' && run && <>
          <p className="result-meta">No new content · Nothing new since your last digest ·{' '}
            {tokenTotals(run.prompt_tokens, run.completion_tokens)}</p>
          <HeldNotes run={run}/><SourceChecks checks={run.source_checks} compact/>
        </>}
        {state === 'failed' && run && <>
          <Alert tone="error" announce={false} title="Digest generation failed">
            {run.error_message || 'Digest generation failed. Try again.'}
          </Alert>
          <p className="result-meta">{run.items_total > 0
            ? <>{run.items_done} of {run.items_total} items were summarized before the error.
              {' '}No digest was saved; all {run.items_total} items stay pending and those summaries are reused next time.</>
            : 'No digest was saved.'}
            {' · '}{tokenTotals(run.prompt_tokens, run.completion_tokens)}</p>
          <SourceChecks checks={run.source_checks} compact/>
        </>}
      </section>
    }/>
    : <section className="page page-generate">
    <PageHead title="Generate digest" lede={firstRun
      ? 'Check the sources you follow and summarize what is new since your last digest.'
      : sources === null ? 'Check your sources and summarize everything new since your last digest.'
        : `Check your ${plural(sources.length, 'source')} and summarize everything new since your last digest.`}
      className="hero">
      <div className="hero-actions">
        {firstRun ? <>
          <Link className={buttonClass('primary', 'lg')} to="/settings">Set up your model</Link>
          <Button disabled aria-describedby="generate-why">Generate digest</Button>
          <p className="hero-meta" id="generate-why">Available once a model is set up and a source is added.</p>
        </> : noSources ? <>
          <Link className={buttonClass('primary', 'lg')} to="/sources">Add sources</Link>
          <Button disabled aria-describedby="generate-sources-why">Generate digest</Button>
          <p className="hero-meta" id="generate-sources-why">Available once a source is added.</p>
        </> : <>
          <Button variant={running || state === 'idle' || state === 'failed' && !configurationError ? 'primary' : 'secondary'}
            size="lg" type="button" onClick={() => void generate()} disabled={running || modelReady === null}>
            {running ? 'Generating…' : state === 'failed' ? 'Try again' : 'Generate digest'}
          </Button>
        </>}
      </div>
    </PageHead>
    {loadError && <Alert tone="error" title={loadError.title}
      actions={loadError.title === 'Could not load the latest digest' && <Link to="/digests">View History</Link>}>
      {loadError.message}</Alert>}
    {error && <Alert tone="error" title={error.title}>{error.message}</Alert>}
    {newDigestError && <Alert tone="error" title="Could not load the new digest"
      actions={<Link to={`/digests/${newDigestError.id}`}>View digest</Link>}>
      {newDigestError.message}</Alert>}
    {firstRun && <Alert title="Set up your model first." actions={<Link className={buttonClass('ghost')} to="/sources">Add sources</Link>}>
      CatchUp summarizes with your own AI model. Add a provider and key in Settings, then add a few sources.
    </Alert>}
    {running && run && <section className="card run-card" aria-label="Digest run">
      <Stepper current={run.status === 'queued' ? 'collecting'
        : run.status === 'grouping' ? 'grouping' : run.status as 'collecting' | 'summarizing'}/>
      <Progress label={run.status === 'collecting' || run.status === 'queued'
        ? `Sources checked: ${run.source_checks.length} of ${run.sources_total}`
        : `Items summarized: ${run.items_done} of ${run.items_total}`}
        value={run.status === 'collecting' || run.status === 'queued'
          ? run.source_checks.length : run.items_done}
        max={run.status === 'collecting' || run.status === 'queued' ? run.sources_total : run.items_total}/>
      <SourceChecks checks={run.source_checks}/>
    </section>}
    {state === 'succeeded' && run && <section className="card result-card result-ok" aria-label="Digest run">
      <div className="result-head"><Icon name="check" className="icon icon-result"/>
        <div><h2 className="result-title">Your digest is ready</h2>
          <p className="result-meta">{savedItems(run)} · {plural(run.sources_total, 'source')}
            {' · '}{tokenTotals(run.prompt_tokens, run.completion_tokens)}</p>
        </div>
        {run.digest_id && <Link className={buttonClass('primary')} to={`/digests/${run.digest_id}`}>View digest</Link>}
      </div>
      <HeldNotes run={run}/><SourceChecks checks={run.source_checks}/>
    </section>}
    {state === 'no_new_content' && run && <section className="card result-card result-none" aria-label="Digest run">
      <div className="result-head"><Icon name="info" className="icon icon-result"/>
        <div><h2 className="result-title">No new content</h2>
          <p className="result-meta">Nothing new since your last digest · {tokenTotals(run.prompt_tokens, run.completion_tokens)}</p>
        </div></div>
      <HeldNotes run={run}/><SourceChecks checks={run.source_checks}/>
    </section>}
    {state === 'failed' && run && <>
      <Alert tone="error" announce={false} title="Digest generation failed"
        actions={configurationError && <Link className={buttonClass('primary')} to="/settings">Check settings</Link>}>
        {run.error_message || 'Digest generation failed. Try again.'}
      </Alert>
      <section className="card result-card" aria-label="Digest run">
        <p className="result-meta">{run.items_total > 0
          ? <>{run.items_done} of {run.items_total} items were summarized before the error.
            {' '}No digest was saved; all {run.items_total} items stay pending and those summaries are reused next time.</>
          : 'No digest was saved.'}
          {' · '}{tokenTotals(run.prompt_tokens, run.completion_tokens)}</p>
        <SourceChecks checks={run.source_checks}/>
      </section>
    </>}
    <Rail>{firstRun ? <>
      <section className="rail-box"><h2 className="rail-title">Getting started</h2>
        <ol className="rail-steps"><li><Link to="/settings">Set up your model</Link></li>
          <li><Link to="/sources">Add a few sources</Link></li><li>Generate your first digest</li></ol>
      </section>
    </> : <>
      {sources !== null && <section className="rail-box"><h2 className="rail-title">Your sources</h2>
        <p className="rail-big">{sources.length}</p>
        <p className="rail-meta">{plural(sources.filter(s => s.kind === 'podcast').length, 'podcast')} ·{' '}
          {sources.filter(s => s.kind === 'youtube').length} YouTube ·{' '}
          {plural(sources.filter(s => s.kind === 'feed').length, 'website')}</p>
        <p><Link to="/sources">Manage sources</Link></p>
      </section>}
    </>}
      <section className="rail-box"><h2 className="rail-title">How it works</h2>
        <p className="rail-meta">Each digest covers everything new since the previous one. Podcasts and videos are summarized only from transcripts or captions.</p>
      </section>
    </Rail>
  </section>}
  <StatusRegion>{status}</StatusRegion>
  </>
}
