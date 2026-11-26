import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../api/client'
import { longDate, plural, shortDateTime, shortTime, tokenTotals } from './format'
import { Icon } from './Icon'
import { digestLang } from './lang'
import { Button, PageHead, SectionRow, SummaryText, KindIcon, ReasonLabel,
  reasons, type Reason, type SourceKind } from './ui'
import { useJump } from './useJump'

type DigestItem = {
  id: number; bookmarked: boolean; liked: boolean; rating: 'good' | 'poor' | null; note: string | null
  title: string; link: string; source_name: string; source_kind?: SourceKind | null
  published_at: string | null; summary: string | null; summary_unavailable: boolean
  also_read?: { title: string; url: string; kind: string }[]
  images?: { url: string; alt: string }[]
}
type Topic = { title: string; overview: string; items: DigestItem[] }
type CreatorUpdate = {
  source_name: string; source_kind?: SourceKind | null
  items: { title: string; link: string; published_at: string | null;
    reason: string; source_kind?: SourceKind | null }[]
}
export type Digest = {
  id: number; created_at: string; model_id: string; language?: string | null; topics: Topic[]
  item_count: number; source_count: number
  creator_updates?: CreatorUpdate[]; transcript_wait_days?: number
  prompt_tokens?: number | null; completion_tokens?: number | null
}

export type Marks = {
  id: number; bookmarked: boolean; liked: boolean; rating: 'good' | 'poor' | null; note: string | null
}

export function ItemActions({ item, title, announce, onChange }: {
  item: DigestItem; title: string; announce: (message: string) => void; onChange?: (marks: Marks) => void
}) {
  const [marks, setMarks] = useState<Marks>(item)
  const [busy, setBusy] = useState({ bookmark: false, like: false })
  const [error, setError] = useState('')
  async function toggle(kind: 'bookmark' | 'like') {
    if (busy[kind]) return
    const pressed = kind === 'bookmark' ? marks.bookmarked : marks.liked
    setBusy(previous => ({ ...previous, [kind]: true }))
    setError('')
    announce('')
    try {
      const saved = await request<Marks>(`/digest-items/${item.id}/${kind}`, { method: pressed ? 'DELETE' : 'PUT' })
      setMarks(saved)
      onChange?.(saved)
      announce(kind === 'bookmark'
        ? pressed ? 'Bookmark removed.' : 'Bookmarked.'
        : pressed ? 'Like removed.' : 'Liked.')
    } catch (error) {
      setError((error as Error).message)
    } finally {
      setBusy(previous => ({ ...previous, [kind]: false }))
    }
  }
  return <div className="item-actions">
    <Button variant="ghost" size="sm" aria-pressed={!!marks.bookmarked}
      aria-disabled={busy.bookmark || undefined} onClick={() => void toggle('bookmark')}>
      {marks.bookmarked && <Icon name="check" className="icon icon-xs"/>}Bookmark<span className="sr-only"> {title}</span>
    </Button>
    <Button variant="ghost" size="sm" aria-pressed={!!marks.liked}
      aria-disabled={busy.like || undefined} onClick={() => void toggle('like')}>
      {marks.liked && <Icon name="check" className="icon icon-xs"/>}Like<span className="sr-only"> {title}</span>
    </Button>
    {!!item.summary && !item.summary_unavailable && <>
      <Button variant="ghost" size="sm" aria-expanded={false}>Feedback<span className="sr-only"> on {title}</span></Button>
      {marks.rating && <span className="feedback-state">Rated {marks.rating}</span>}
    </>}
    {error && <p role="alert" className="item-error">{error}</p>}
  </div>
}

function IndexLink({ id, title, lang }: { id: string; title: string; lang?: string | null }) {
  const jump = useJump(id)
  return <a href={`#${id}`} lang={lang || undefined} onClick={jump}>{title}</a>
}

function SourceTime({ value }: { value: string | null }) {
  return value && <><span aria-hidden="true">·</span><time dateTime={value}>{shortDateTime(value)}</time></>
}

function ItemImages({ images, lang }: { images: { url: string; alt: string }[]; lang?: string }) {
  const [failed, setFailed] = useState<Set<number>>(() => new Set())
  const visible = images.map((image, index) => ({ image, index }))
    .filter(({ image, index }) => typeof image.alt === 'string' && image.alt.trim() && !failed.has(index))
  if (!visible.length) return null
  return <div className="item-images">
    {visible.map(({ image, index }) => <figure key={`${image.url}-${index}`}>
      <img src={image.url} alt="" loading="lazy" decoding="async"
        referrerPolicy="no-referrer" onError={() => setFailed(previous => new Set(previous).add(index))}/>
      <figcaption lang={lang || undefined}>{image.alt}</figcaption>
    </figure>)}
  </div>
}

export function DigestArticle({ digest, className = '', before, headEnd, showImages = true }: {
  digest: Digest; className?: string; before?: ReactNode; headEnd?: ReactNode; showImages?: boolean
}) {
  const [message, announce] = useState('')
  const lang = digestLang(digest.language)
  const groups = digest.creator_updates ?? []
  const sectionCount = digest.topics.length + (groups.length ? 1 : 0)
  return <section className={`page page-digest${className ? ` ${className}` : ''}`}>
    {before}
    <p className="sr-only" role="status">{message}</p>
    <PageHead className="digest-head" eyebrow={`Digest · No. ${digest.id}`} title={<>{longDate(digest.created_at)}
      <span className="title-time"> · {shortTime(digest.created_at)}</span></>}>
      <p className="digest-meta">{plural(digest.item_count, 'item')} · {plural(digest.source_count, 'source')}
        {' · '}{digest.model_id} · <span className="tokens">{tokenTotals(digest.prompt_tokens, digest.completion_tokens)}</span></p>
      {!digest.topics.length && groups.length > 0 && <p className="digest-note">
        Nothing could be summarized this time. Here is what your sources published.
      </p>}
      {headEnd}
    </PageHead>
    <div className="digest-layout">
      {sectionCount > 1 && <nav className="toc" aria-label="In this digest">
        <p className="toc-title">In this digest</p><ol>
          {digest.topics.map((topic, index) =>
            <li key={index}><IndexLink id={`t${index}`} title={topic.title} lang={lang}/>
              {' '}<span className="toc-count">{topic.items.length}</span></li>)}
          {groups.length > 0 && <li className="toc-creator"><IndexLink id="creator" title="Creator updates"/>
            {' '}<span className="toc-count">{groups.reduce((count, group) => count + group.items.length, 0)}</span></li>}
        </ol>
      </nav>}
      <div className="digest-body">
        {digest.topics.map((topic, index) =>
          <SectionRow key={index} id={`t${index}`} title={topic.title} overview={topic.overview} lang={lang}>
            <div className="items">{topic.items.map((item, position) =>
              <article key={position} className="item">
                <p className="item-meta"><KindIcon kind={item.source_kind}/><span>{item.source_name}</span>
                  <SourceTime value={item.published_at}/></p>
                <h3 className="item-title"><a href={item.link} target="_blank" rel="noopener noreferrer">
                  {item.title}<Icon name="external" className="icon icon-xs"/>
                  <span className="sr-only"> (opens the original)</span>
                </a></h3>
                {item.summary_unavailable
                  ? <p className="summary-unavailable">Summary unavailable</p>
                  : item.summary && <div className="item-body">
                    <SummaryText text={item.summary} lang={lang}/>
                    {showImages && !!item.images?.length && <ItemImages
                      key={`${digest.id}-${index}-${position}`} images={item.images} lang={lang}/>}
                    {!!item.also_read?.length && <p className="also-read">Also read: {' '}
                      {item.also_read.map((part, index) => <span key={`${part.url}-${index}`}>
                        {index > 0 && ' · '}
                        <a href={part.url} target="_blank" rel="noopener noreferrer">{part.title}</a>
                      </span>)}
                    </p>}
                  </div>}
                <ItemActions key={`${digest.id}-${item.id}`} item={item} title={item.title} announce={announce}/>
              </article>
            )}</div>
          </SectionRow>)}
        {groups.length > 0 && <section className={`creator ${!digest.topics.length ? 'creator-only' : ''}`}
          id="creator" tabIndex={-1} aria-labelledby="creator-heading">
          <h2 className="creator-title" id="creator-heading">Creator updates</h2>
          <p className="creator-lede">New from sources you follow, listed without a summary because no transcript or captions were available.</p>
          {groups.map((group, index) => <section className="creator-group" key={index} aria-label={group.source_name}>
            <h3 className="creator-source"><KindIcon kind={group.source_kind}/>{group.source_name}</h3>
            <ul className="creator-list">{group.items.map((item, position) =>
              <li className="creator-item" key={position}>
                <a href={item.link} target="_blank" rel="noopener noreferrer">{item.title}
                  <Icon name="external" className="icon icon-xs"/>
                  <span className="sr-only"> (opens the original)</span></a>
                <span className="creator-meta">
                  {item.published_at && <time dateTime={item.published_at}>{shortDateTime(item.published_at)}</time>}
                  {item.reason in reasons ? <ReasonLabel reason={item.reason as Reason}
                    waitDays={digest.transcript_wait_days ?? 7}/> : item.reason}
                </span>
              </li>)}</ul>
          </section>)}
        </section>}
      </div>
    </div>
  </section>
}
