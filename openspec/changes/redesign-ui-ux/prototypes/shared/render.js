// Renders every CatchUp screen and state from window.SAMPLE into semantic markup.
// Each direction styles the same markup with its own CSS (and may set window.DIRECTION.nav / .rail).
(function () {
  const S = window.SAMPLE
  const D = window.DIRECTION || { id: 'x', name: 'Prototype', nav: 'top' }
  const DIRECTIONS = [
    ['a', 'A · Quiet reader'], ['b', 'B · Focused workspace'], ['c', 'C · Morning briefing'], ['c2', 'C2 · Briefing, sans body'], ['c3', 'C3 · Broadsheet'], ['c3b', 'C3b · Broadsheet, revised'], ['c4', 'C4 · Salmon paper'], ['c5', 'C5 · Tabloid'], ['c6', 'C6 · Swiss grid'], ['c7', 'C7 · Front page grid'],
    ['d', 'D · Soft cards'], ['e', 'E · Native desktop'],
  ]
  const SCREENS = {
    generate: ['first-run', 'idle', 'collecting', 'summarizing', 'succeeded', 'no-new-content', 'failed'],
    digest: ['zh', 'en', 'creator-only'],
    sources: ['list', 'preview-podcast', 'preview-youtube', 'error', 'confirm-delete', 'empty'],
    settings: ['saved', 'first-run', 'tested', 'error'],
    history: ['list', 'empty'],
    offline: ['default'],
  }
  const TODAY = '2026-10-06T09:00:00'

  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
  const fmt = (iso, opts) => new Intl.DateTimeFormat('en-GB', opts || { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
  const longDate = (iso) => fmt(iso, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const time = (iso) => fmt(iso, { hour: '2-digit', minute: '2-digit' })
  const num = (n) => n.toLocaleString('en-US')
  const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`
  const sr = (text) => `<span class="sr-only">${text}</span>`

  const ICON = {
    generate: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>',
    sources: '<path d="M5 19a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/>',
    history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>',
    settings: '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    podcast: '<path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zM19 11a7 7 0 0 1-14 0M12 18v3"/>',
    youtube: '<rect x="3" y="6" width="18" height="12" rx="3"/><path d="M10 9.5v5l4-2.5z"/>',
    feed: '<path d="M4 6h16M4 12h16M4 18h10"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    check: '<path d="M5 12l4 4 10-10"/>',
    alert: '<path d="M12 9v4M12 17h.01M10.3 3.9L2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  }
  const icon = (name, cls = 'icon') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICON[name]}</svg>`

  const KIND = { podcast: 'Podcast', youtube: 'YouTube channel', feed: 'Website feed' }
  const kindBadge = (kind) => `<span class="badge badge-kind kind-${kind}">${icon(kind, 'icon icon-sm')}${KIND[kind]}</span>`
  const STATUS = {
    new_items: ['New items', 'ok'], no_new_items: ['No new items', 'neutral'], failed: ['Failed', 'error'],
    rate_limited: ['Rate limited · try later', 'warn'], null: ['Never checked', 'neutral'],
  }
  const statusChip = (status) => { const [label, tone] = STATUS[status] || STATUS.null; return `<span class="chip chip-${tone}">${label}</span>` }
  const gapChip = '<span class="chip chip-warn" title="Older items may have dropped off the feed between checks.">Possible gap</span>'
  const REASON = {
    captions_off: 'Caption fetching is off', no_captions: 'This video has no captions', blocked: 'Blocked by YouTube',
    captions_failed: 'Captions could not be fetched', no_transcript: 'No transcript within 7 days',
  }

  // Optional right rail (newspaper-site pattern); only directions with DIRECTION.rail render it. Content follows the state.
  function rail(screen, state) {
    if (!D.rail) return ''
    const kinds = S.sources.reduce((m, s) => ({ ...m, [s.kind]: (m[s.kind] || 0) + 1 }), {})
    const L = S.lastDigest
    const box = (title, body) => `<section class="rail-box"><h2 class="rail-title">${title}</h2>${body}</section>`
    let boxes = ''
    if (screen === 'generate' && state === 'first-run') {
      boxes = box('Getting started', '<ol class="rail-steps"><li><a href="#settings/first-run">Set up your model</a></li><li><a href="#sources/empty">Add a few sources</a></li><li>Generate your first digest</li></ol>')
        + box('How it works', '<p class="rail-meta">Each digest covers everything new since the previous one. Podcasts and videos are summarized only from transcripts or captions.</p>')
    } else if (screen === 'generate') {
      boxes = box('Last digest', `<p><a href="#digest/zh">No. ${L.id} · ${longDate(L.created)}, ${time(L.created)}</a></p><p class="rail-meta">${plural(L.items, 'item')} · ${plural(L.sources, 'source')}</p>`)
        + box('Your sources', `<p class="rail-big">${S.sources.length}</p><p class="rail-meta">${plural(kinds.podcast || 0, 'podcast')} · ${kinds.youtube || 0} YouTube · ${plural(kinds.feed || 0, 'website')}</p><p><a href="#sources/list">Manage sources</a></p>`)
        + box('How it works', '<p class="rail-meta">Each digest covers everything new since the previous one. Podcasts and videos are summarized only from transcripts or captions.</p>')
    } else if (screen === 'sources') {
      boxes = box('What you can add', '<ul class="rail-list"><li>Blogs and news sites with a feed</li><li>Podcasts — summarized from published transcripts</li><li>YouTube channels — captions are opt-in in Settings</li><li>Bluesky and Mastodon profiles</li></ul><p class="rail-meta">Apple Podcasts links work too; CatchUp finds the show’s feed.</p>')
        + (state === 'empty' ? '' : box('Checks', '<p class="rail-meta">Sources are checked when you generate a digest. “Possible gap” means older items may have dropped off the feed between checks.</p>'))
    } else if (screen === 'history') {
      boxes = (state === 'empty' ? '' : box('Archive', `<p class="rail-big">${S.history.length}</p><p class="rail-meta">digests · ${S.history.reduce((n, h) => n + h.items, 0)} items in total</p>`))
        + box('Kept as saved', '<p class="rail-meta">A saved digest never changes, even if a source is deleted later.</p>')
    }
    return boxes ? `<aside class="rail" aria-label="About this page">${boxes}</aside>` : ''
  }

  // ---------- Screens ----------
  function checksList(checks) {
    return `<ul class="check-list">${checks.map((c) => `
      <li class="check-row"><span class="check-title">${esc(c.title)}</span>
        <span class="check-status">${statusChip(c.status)}${c.possible_gap ? gapChip : ''}</span>
        ${c.error ? `<span class="check-error">${esc(c.error)}</span>` : ''}</li>`).join('')}</ul>`
  }
  function stepper(status) {
    const steps = [['collecting', 'Checking sources'], ['summarizing', 'Summarizing'], ['grouping', 'Grouping topics']]
    const at = steps.findIndex(([s]) => s === status)
    return `<ol class="stepper" aria-label="Run progress">${steps.map(([s, label], i) => `<li class="step ${i < at ? 'is-done' : i === at ? 'is-current' : ''}" ${i === at ? 'aria-current="step"' : ''}><span class="step-dot" aria-hidden="true">${i < at ? icon('check', 'icon icon-xs') : i + 1}</span>${label}${sr(i < at ? ' (done)' : i === at ? ' (in progress)' : ' (next)')}</li>`).join('')}</ol>`
  }
  function heldNotes(r) {
    const notes = []
    if (r.waiting) notes.push(`${icon('clock', 'icon icon-sm')} ${plural(r.waiting, 'item')} waiting for transcripts or captions`)
    if (r.deferred) notes.push(`${icon('youtube', 'icon icon-sm')} ${plural(r.deferred, 'video')} deferred to the next run`)
    return notes.length ? `<ul class="held-notes">${notes.map((n) => `<li>${n}</li>`).join('')}</ul>` : ''
  }
  const tokens = (t) => `<span class="tokens">Tokens: ${num(t[0])} in / ${num(t[1])} out</span>`

  function generate(state) {
    const firstRun = state === 'first-run'
    const r = { collecting: S.run.collecting, summarizing: S.run.summarizing, succeeded: S.run.succeeded, 'no-new-content': S.run.none, failed: S.run.failed }[state]
    const running = r && ['collecting', 'summarizing'].includes(r.status)
    const L = S.lastDigest
    let body = ''
    let status = ''
    if (firstRun) {
      body = `<div class="alert alert-info">${icon('info')}<div><strong>Set up your model first.</strong>
        <p>CatchUp summarizes with your own AI model. Add a provider and key in Settings, then add a few sources.</p>
        <p class="alert-actions"><a class="btn btn-ghost" href="#sources/empty">Add sources</a></p></div></div>`
    } else if (running) {
      const progress = r.status === 'collecting'
        ? { label: `Sources checked: ${r.checks.length} of ${r.sources_total}`, value: r.checks.length, max: r.sources_total }
        : { label: `Items summarized: ${r.items_done} of ${r.items_total}`, value: r.items_done, max: r.items_total }
      status = r.status === 'collecting' ? `Checking sources, ${r.checks.length} of ${r.sources_total}` : `Summarizing, ${r.items_done} of ${r.items_total}`
      body = `<section class="card run-card" aria-label="Digest run">
        ${stepper(r.status)}
        <div class="progress-row"><progress class="progress" value="${progress.value}" max="${progress.max}" aria-labelledby="progress-label"></progress><span class="progress-label" id="progress-label">${progress.label}</span></div>
        <h2 class="section-label">Sources</h2>${checksList(r.checks)}</section>`
    } else if (r && r.status === 'succeeded') {
      status = `Digest ready: ${plural(r.items_total, 'item')}`
      body = `<section class="card result-card result-ok" aria-label="Digest run">
        <div class="result-head">${icon('check', 'icon icon-result')}<div><h2 class="result-title">Your digest is ready</h2>
        <p class="result-meta">${plural(r.items_total, 'item')} · ${plural(r.sources_total, 'source')} · ${tokens(r.tokens)}</p></div>
        <a class="btn btn-primary" href="#digest/zh">View digest</a></div>
        ${heldNotes(r)}<h2 class="section-label">Sources</h2>${checksList(r.checks)}</section>`
    } else if (r && r.status === 'no_new_content') {
      status = 'No new content'
      body = `<section class="card result-card result-none" aria-label="Digest run">
        <div class="result-head">${icon('info', 'icon icon-result')}<div><h2 class="result-title">No new content</h2>
        <p class="result-meta">Nothing new since your last digest · ${tokens(r.tokens)}</p></div></div>
        ${heldNotes(r)}<h2 class="section-label">Sources</h2>${checksList(r.checks)}</section>`
    } else if (r && r.status === 'failed') {
      body = `<div class="alert alert-error" role="alert">${icon('alert')}<div><strong>Digest generation failed</strong><p>${esc(r.error)}</p>
        <p class="alert-actions"><a class="btn btn-primary" href="#settings/saved">Check settings</a></p></div></div>
        <section class="card result-card" aria-label="Digest run"><p class="result-meta">${r.items_done} of ${r.items_total} items were summarized before the error. No digest was saved; all ${r.items_total} items stay pending and those summaries are reused next time. · ${tokens(r.tokens)}</p>
        <h2 class="section-label">Sources</h2>${checksList(r.checks)}</section>`
    }
    const lede = firstRun ? 'Check the sources you follow and summarize what is new since your last digest.'
      : `Check your ${S.sources.length} sources and summarize everything new since your last digest.`
    // One primary action per state: setup on first run, the digest after success, settings after a configuration error.
    const generateClass = firstRun || state === 'succeeded' || state === 'no-new-content' || state === 'failed' ? 'btn-secondary' : 'btn-primary'
    const actions = firstRun
      ? `<a class="btn btn-primary btn-lg" href="#settings/first-run">Set up your model</a>
         <button class="btn btn-secondary" type="button" disabled aria-describedby="generate-why">Generate digest</button>
         <p class="hero-meta" id="generate-why">Available once a model is set up and a source is added.</p>`
      : `<button class="btn ${generateClass} btn-lg" type="button" ${running ? 'disabled' : ''}>${running ? 'Generating…' : state === 'failed' ? 'Try again' : 'Generate digest'}</button>
         <p class="hero-meta hero-last">Last digest: <a href="#digest/zh">No. ${L.id} · ${fmt(L.created)}</a> · ${plural(L.items, 'item')}</p>`
    return `<section class="page page-generate">
      <header class="page-head hero">
        <h1 class="page-title">Generate digest</h1><p class="lede">${lede}</p>
        <div class="hero-actions">${actions}</div>
      </header>${body}<p class="sr-only" role="status" id="run-status">${status}</p>${rail('generate', state)}</section>`
  }

  function summary(item, lang) {
    if (item.unavailable) return '<p class="summary-unavailable">Summary unavailable</p>'
    return `<div class="summary" lang="${lang}"><p>${esc(item.summary)}</p>${item.points ? `<ul class="points">${item.points.map((p) => `<li>${esc(p)}</li>`).join('')}</ul>` : ''}</div>`
  }
  // Long items (key points or a long summary) get the wide column; size never depends on position.
  const isLong = (it) => !!it.points || (it.summary || '').length > 140
  function digest(state) {
    const d = { zh: S.digests.zh, en: S.digests.en, 'creator-only': S.digests.creatorOnly }[state]
    const sections = d.topics.length + (d.creator.length ? 1 : 0)
    const toc = sections > 1 ? `<nav class="toc" aria-label="In this digest"><p class="toc-title">In this digest</p><ol>${d.topics.map((t, i) => `<li><a href="#t${i}" lang="${d.lang}">${esc(t.title)}</a> <span class="toc-count">${t.items.length}</span></li>`).join('')}${d.creator.length ? `<li class="toc-creator"><a href="#creator">Creator updates</a> <span class="toc-count">${d.creator.reduce((n, g) => n + g.items.length, 0)}</span></li>` : ''}</ol></nav>` : ''
    const topics = d.topics.map((t, i) => `<section class="topic" id="t${i}" tabindex="-1" aria-labelledby="t${i}h">
      <h2 class="topic-title" id="t${i}h" lang="${d.lang}">${esc(t.title)}</h2><p class="topic-overview" lang="${d.lang}">${esc(t.overview)}</p>
      <div class="items">${t.items.map((it) => `<article class="item ${isLong(it) ? 'item-long' : 'item-short'}">
        <p class="item-meta">${icon(it.kind, 'icon icon-sm')}${sr(KIND[it.kind] + ': ')}<span class="item-source">${esc(it.source)}</span><span class="dot" aria-hidden="true">·</span><time>${fmt(it.published)}</time></p>
        <h3 class="item-title"><a href="#" target="_blank" rel="noopener noreferrer">${esc(it.title)}${icon('external', 'icon icon-xs')}${sr(' (opens the original)')}</a></h3>
        ${summary(it, d.lang)}</article>`).join('')}</div></section>`).join('')
    const creator = d.creator.length ? `<section class="creator ${d.topics.length ? '' : 'creator-only'}" id="creator" tabindex="-1" aria-labelledby="creatorh">
      <h2 class="creator-title" id="creatorh">Creator updates</h2>
      <p class="creator-lede">New from sources you follow, listed without a summary because no transcript or captions were available.</p>
      ${d.creator.map((g) => `<section class="creator-group" aria-label="${esc(g.source)}"><h3 class="creator-source">${icon(g.kind, 'icon icon-sm')}${sr(KIND[g.kind] + ': ')}${esc(g.source)}</h3>
        <ul class="creator-list">${g.items.map((it) => `<li class="creator-item"><a href="#" target="_blank" rel="noopener noreferrer">${esc(it.title)}${icon('external', 'icon icon-xs')}</a>
          <span class="creator-meta"><time>${fmt(it.published)}</time><span class="reason reason-${it.reason}">${REASON[it.reason]}</span></span></li>`).join('')}</ul></section>`).join('')}</section>` : ''
    const onlyCreator = !d.topics.length ? '<p class="digest-note">Nothing could be summarized this time. Here is what your sources published.</p>' : ''
    return `<section class="page page-digest">
      <header class="page-head digest-head"><p class="eyebrow">Digest<span class="edition"> · No. ${d.id}</span></p><h1 class="page-title">${longDate(d.created)}<span class="title-time"> · ${time(d.created)}</span></h1>
        <p class="digest-meta">${plural(d.items, 'item')} · ${plural(d.sources, 'source')} · ${esc(d.model)} · ${tokens(d.tokens)}</p>
        ${onlyCreator}<p class="back-link"><a href="#history/list">← All digests</a></p></header>
      <div class="digest-layout">${toc}<div class="digest-body">${topics}${creator}</div></div></section>`
  }

  function preview(p) {
    const method = p.kind === 'podcast' ? 'Transcripts published by the show'
      : p.kind === 'youtube' ? (p.captions ? 'Captions fetched from YouTube on this computer' : 'Caption fetching is off; videos will be listed without summaries') : 'Article text from the feed and linked pages'
    return `<section class="card preview-card" aria-label="Source preview">
      <div class="preview-head"><h2 class="preview-title">${esc(p.title)}</h2>${kindBadge(p.kind)}</div>
      <dl class="preview-urls"><dt>Feed</dt><dd><a href="#">${esc(p.feed)}</a></dd><dt>Site</dt><dd><a href="#">${esc(p.site)}</a></dd></dl>
      <p class="preview-method ${p.kind === 'youtube' && !p.captions ? 'is-muted' : ''}">${icon(p.kind === 'youtube' && !p.captions ? 'info' : 'check', 'icon icon-sm')}${method}${p.kind === 'youtube' && !p.captions ? ' <a href="#settings/saved">Change in Settings</a>' : ''}</p>
      ${p.notice ? `<p class="notice">${icon('info', 'icon icon-sm')}CatchUp will follow the whole show, not only this episode.</p>` : ''}
      <h3 class="section-label">Recent entries</h3><ul class="entry-list">${p.entries.map((e) => `<li><a href="#">${esc(e.title)}</a><time>${fmt(e.published, { day: 'numeric', month: 'short' })}</time></li>`).join('')}</ul>
      <div class="actions"><button class="btn btn-primary" type="button">Confirm source</button><button class="btn btn-ghost" type="button">Cancel</button></div></section>`
  }
  function sources(state) {
    const value = { 'preview-podcast': 'https://podcasts.apple.com/us/podcast/the-daily/id1200361736?i=1000793081178', 'preview-youtube': 'https://www.youtube.com/@GoogleDevelopers', error: 'https://example.com/about' }[state] || ''
    const previewing = state.startsWith('preview')
    const error = state === 'error'
    const row = (s, i) => state === 'confirm-delete' && i === 0
      ? `<li class="source-row source-confirm" role="group" aria-label="Confirm deletion"><p class="confirm-text"><strong>Delete ${esc(s.title)}?</strong> Saved digests will remain available.</p>
         <div class="actions"><button class="btn btn-danger-solid btn-sm" type="button">Delete</button><button class="btn btn-ghost btn-sm" type="button">Cancel</button></div></li>`
      : `<li class="source-row">
        <span class="source-icon">${icon(s.kind)}</span>
        <div class="source-main"><p class="source-title">${esc(s.title)} ${kindBadge(s.kind)}</p><p class="source-feed" title="${esc(s.feed)}">${esc(s.feed)}</p></div>
        <div class="source-status">${statusChip(s.status)}${s.possible_gap ? gapChip : ''}<span class="source-time">${s.checked ? fmt(s.checked) : ''}</span></div>
        <button class="btn btn-ghost btn-danger btn-sm" type="button" aria-label="Delete ${esc(s.title)}">Delete</button></li>`
    const list = state === 'empty' ? `<div class="empty-state">${icon('sources', 'icon icon-empty')}<h2>No sources yet</h2>
        <p>Paste the address of something you follow. CatchUp finds its feed for you.</p>
        <ul class="examples"><li>A blog or news site</li><li>A podcast feed or Apple Podcasts link</li><li>A YouTube channel</li><li>A Bluesky or Mastodon profile</li></ul></div>`
      : `<h2 class="section-label">Your sources <span class="count">${S.sources.length}</span></h2><ul class="source-list">${S.sources.map(row).join('')}</ul>`
    return `<section class="page page-sources">
      <header class="page-head"><h1 class="page-title">Sources</h1><p class="lede">Blogs, podcasts, YouTube channels, and social profiles you follow.</p></header>
      <form class="add-form card" onsubmit="return false"><label class="field-label" for="url">Website or feed URL</label>
        <div class="input-row"><input class="input" id="url" type="url" placeholder="https://example.com" value="${esc(value)}" aria-describedby="${error ? 'url-error ' : ''}url-hint" ${error ? 'aria-invalid="true"' : ''}><button class="btn ${previewing ? 'btn-secondary' : 'btn-primary'}" type="submit">Preview</button></div>
        ${error ? `<p class="field-error" id="url-error" role="alert">${icon('alert', 'icon icon-sm')}No supported feed was found at this URL.</p>` : ''}
        <p class="field-hint" id="url-hint">Paste a page address. CatchUp looks for its feed and shows a preview before saving.</p>
      </form>
      ${state === 'preview-podcast' ? preview(S.previews.podcast) : state === 'preview-youtube' ? preview(S.previews.youtube) : ''}
      ${list}${rail('sources', state)}</section>`
  }

  function settings(state) {
    const first = state === 'first-run'
    const msg = state === 'tested' ? `<p class="inline-msg msg-ok" role="status">${icon('check', 'icon icon-sm')}Connection succeeded. Choose a model and save.</p>`
      : state === 'error' ? `<p class="inline-msg msg-error" id="key-error" role="alert">${icon('alert', 'icon icon-sm')}The provider rejected the API key.</p>` : ''
    const step = (n, title) => `<h2 class="settings-title"><span class="step-num" aria-hidden="true">${n}</span>${sr(`Step ${n}: `)}${title}</h2>`
    const keyField = first
      ? `<input class="input" id="key" type="password" placeholder="Paste your API key" aria-describedby="key-hint">
         <p class="field-hint" id="key-hint">Stored encrypted on this computer. It is never shown again.</p>`
      : `<p class="key-saved" id="key-saved">${icon('check', 'icon icon-sm')}Saved key ending in <code>3f9a</code></p>
         <input class="input" id="key" type="password" placeholder="Paste a new key to replace it" aria-describedby="key-saved key-hint${state === 'error' ? ' key-error' : ''}" ${state === 'error' ? 'aria-invalid="true"' : ''}>
         <p class="field-hint" id="key-hint">Leave empty to keep the saved key.</p>`
    return `<section class="page page-settings">
      <header class="page-head"><h1 class="page-title">Settings</h1><p class="lede">${first ? 'Three quick steps. Your key stays on this computer, encrypted.' : 'Your model, digest language, and YouTube options.'}</p></header>
      <form class="settings-form" onsubmit="return false">
      <section class="card settings-section">${step(1, 'Model provider')}
        <p class="note">${icon('info', 'icon icon-sm')}Content will be sent to your configured model provider.</p>
        <div class="field"><label class="field-label" for="base">Base URL</label><input class="input" id="base" value="https://api.deepseek.com"></div>
        <div class="field"><label class="field-label" for="key">API key</label>${keyField}</div>
        <div class="field-row"><button class="btn btn-secondary" type="button">Test connection</button>${msg}</div>
        <div class="field"><label class="field-label" for="model">Model</label><select class="input select" id="model" ${first ? 'disabled' : ''}>${first ? '<option>Test the connection to list models</option>' : S.models.map((m) => `<option>${m}</option>`).join('')}</select></div>
      </section>
      <section class="card settings-section">${step(2, 'Digest')}
        <div class="field"><label class="field-label" for="lang">Language</label><select class="input select" id="lang" aria-describedby="lang-hint"><option>English</option><option selected lang="zh-Hans">简体中文</option><option>Same as original</option><option>Other…</option></select>
        <p class="field-hint" id="lang-hint">Topic titles and summaries are written in this language. Item titles stay as published.</p></div>
      </section>
      <section class="card settings-section">${step(3, 'YouTube')}
        <label class="switch"><input type="checkbox" role="switch" aria-describedby="captions-risk" ${state === 'saved' || state === 'tested' ? 'checked' : ''}><span class="switch-track" aria-hidden="true"></span><span class="switch-label">Fetch captions locally</span></label>
        <p class="risk" id="captions-risk">${icon('alert', 'icon icon-sm')}<span>Fetches captions from YouTube from this computer. YouTube's Terms of Service do not allow automated access, so turn this on only if you accept that risk. When off, new videos are listed under Creator updates without a summary.</span></p>
        <label class="switch"><input type="checkbox" role="switch" checked><span class="switch-track" aria-hidden="true"></span><span class="switch-label">Skip Shorts</span></label>
      </section>
      <div class="save-bar"><button class="btn btn-primary" type="submit">Save</button>${state === 'saved' ? `<p class="inline-msg msg-ok" role="status">${icon('check', 'icon icon-sm')}Settings saved.</p>` : ''}</div>
      </form></section>`
  }

  function history(state) {
    const body = state === 'empty' ? `<div class="empty-state">${icon('history', 'icon icon-empty')}<h2>No saved digests yet</h2><p>Generate your first digest and it will appear here.</p><a class="btn btn-primary" href="#generate/idle">Generate a digest</a></div>`
      : `<ol class="history-list">${S.history.map((h) => `<li class="history-row"><a class="history-link" href="#digest/zh">
          <span class="history-date" aria-hidden="true"><span class="history-day">${fmt(h.created, { day: 'numeric' })}</span><span class="history-month">${fmt(h.created, { month: 'short' })}</span></span>
          <span class="history-main"><span class="history-title"><span class="edition">No. ${h.id} · </span>${longDate(h.created)} · ${time(h.created)}</span>
          <span class="history-topics" lang="zh-Hans">${h.topics.map(esc).join(' · ')}</span></span>
          <span class="history-counts">${plural(h.items, 'item')} · ${plural(h.sources, 'source')}</span></a></li>`).join('')}</ol>`
    return `<section class="page page-history"><header class="page-head"><h1 class="page-title">History</h1><p class="lede">Every digest you have generated, newest first.</p></header>${body}${rail('history', state)}</section>`
  }

  function offline() {
    return `<section class="page page-offline"><div class="offline-card card"><span class="logo logo-lg" aria-hidden="true"></span><p class="offline-brand">CatchUp</p>
      <h1 class="page-title">CatchUp isn't running</h1><p class="lede">Start it, then reload this window.</p>
      <pre class="code"><code>docker compose up -d</code></pre><p class="field-hint">Or, from a source checkout: <code>uv run catchup serve</code></p>
      <button class="btn btn-primary" type="button">Reload</button></div></section>`
  }

  // ---------- Shell and prototype controls ----------
  function parse() {
    const [path, query] = location.hash.replace(/^#/, '').split('?')
    let [screen, state] = (path || 'generate/idle').split('/')
    if (!SCREENS[screen]) screen = 'generate'
    if (!SCREENS[screen].includes(state)) state = SCREENS[screen][0]
    const q = new URLSearchParams(query || '')
    return { screen, state, theme: q.get('theme') || localStorage.getItem('proto-theme') || 'light', width: q.get('w') || localStorage.getItem('proto-width') || 'desktop' }
  }
  function nav(screen) {
    const items = [['generate', 'Generate', 'generate/idle'], ['sources', 'Sources', 'sources/list'], ['history', 'History', 'history/list'], ['settings', 'Settings', 'settings/saved']]
    const current = screen === 'digest' ? 'history' : screen
    return `<nav class="app-nav" aria-label="Main">${items.map(([id, label, href]) => `<a class="nav-link" href="#${href}" ${id === current ? 'aria-current="page"' : ''}>${icon(id)}<span>${label}</span></a>`).join('')}</nav>`
  }
  const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
  // Scroll to an in-page target and move keyboard focus there (skip link, digest index).
  function jump(id) {
    const target = document.getElementById(id)
    if (!target) return
    target.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth' })
    target.focus({ preventScroll: true })
  }
  function render() {
    const st = parse()
    localStorage.setItem('proto-theme', st.theme); localStorage.setItem('proto-width', st.width)
    const screens = { generate, digest, sources, settings, history, offline: () => offline() }
    const page = screens[st.screen](st.state)
    const shell = st.screen === 'offline' ? `<main class="app-main" id="main">${page}</main>`
      : `<a class="skip-link" href="#main">Skip to content</a><header class="app-header"><a class="brand" href="#generate/idle"><span class="logo" aria-hidden="true"></span><span class="brand-name">CatchUp</span></a><p class="masthead-line"><time datetime="${TODAY.slice(0, 10)}">${longDate(TODAY)}</time></p>${nav(st.screen)}</header><main class="app-main" id="main" tabindex="-1">${page}</main>`
    const q = (o) => { const p = new URLSearchParams({ theme: o.theme ?? st.theme, w: o.width ?? st.width }); return `#${o.screen ?? st.screen}/${o.state ?? st.state}?${p}` }
    document.body.innerHTML = `
      <div class="proto-bar" role="toolbar" aria-label="Prototype controls">
        <span class="proto-name">CatchUp prototype</span>
        <label>Direction <select id="p-dir">${DIRECTIONS.map(([id, name]) => `<option value="${id}" ${id === D.id ? 'selected' : ''}>${name}</option>`).join('')}</select></label>
        <label>Screen <select id="p-screen">${Object.keys(SCREENS).map((s) => `<option ${s === st.screen ? 'selected' : ''}>${s}</option>`).join('')}</select></label>
        <label>State <select id="p-state">${SCREENS[st.screen].map((s) => `<option ${s === st.state ? 'selected' : ''}>${s}</option>`).join('')}</select></label>
        <a class="proto-btn" href="${q({ theme: st.theme === 'dark' ? 'light' : 'dark' })}">${st.theme === 'dark' ? 'Light' : 'Dark'}</a>
        <a class="proto-btn" href="${q({ width: st.width === 'narrow' ? 'desktop' : 'narrow' })}">${st.width === 'narrow' ? 'Desktop width' : 'Narrow 420px'}</a>
        <a class="proto-btn" href="../index.html">All directions</a>
      </div>
      <div class="proto-stage" data-width="${st.width}">
        <div class="app" data-theme="${st.theme}" data-nav="${D.nav || 'top'}" data-screen="${st.screen}" data-state="${st.state}">${shell}</div>
      </div>`
    document.getElementById('p-dir').onchange = (e) => { location.href = `${e.target.value}.html${location.hash}` }
    document.getElementById('p-screen').onchange = (e) => { location.hash = q({ screen: e.target.value, state: SCREENS[e.target.value][0] }) }
    document.getElementById('p-state').onchange = (e) => { location.hash = q({ state: e.target.value }) }
    document.title = `CatchUp · ${D.name} · ${st.screen}/${st.state}`
    document.querySelectorAll('.app a[href="#"]').forEach((a) => a.addEventListener('click', (e) => e.preventDefault()))
    document.querySelectorAll('.app a[href^="#t"], .app a[href="#creator"], .skip-link').forEach((a) => a.addEventListener('click', (e) => {
      e.preventDefault(); jump(a.getAttribute('href').slice(1))
    }))
  }
  window.addEventListener('hashchange', render)
  document.addEventListener('DOMContentLoaded', render)
})()
