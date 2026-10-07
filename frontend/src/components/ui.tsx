import { useId, type ComponentProps, type ReactNode } from 'react'
import { Icon } from './Icon'

export function PageHead({ title, lede, children, className = '', eyebrow }: {
  title: ReactNode; lede?: ReactNode; children?: ReactNode; className?: string; eyebrow?: ReactNode
}) {
  return <header className={`page-head ${className}`}>{eyebrow && <p className="eyebrow">{eyebrow}</p>}
    <h1 className="page-title">{title}</h1>
    {lede && <p className="lede">{lede}</p>}{children}</header>
}

export function SectionRow({ title, overview, note, children, className = '', id, lang }: {
  title: ReactNode; overview?: ReactNode; note?: ReactNode; children: ReactNode
  className?: string; id?: string; lang?: string | null
}) {
  return <section className={`topic ${className}`} id={id} tabIndex={id ? -1 : undefined}
    aria-labelledby={id ? `${id}-heading` : undefined}
    aria-label={!id && typeof title === 'string' ? title : undefined}>
    <h2 className="topic-title" id={id ? `${id}-heading` : undefined} lang={lang || undefined}>{title}</h2>
    {overview && <p className="topic-overview" lang={lang || undefined}>{overview}</p>}
    {children}{note && <aside className="note">{note}</aside>}
  </section>
}

export function Rail({ children }: { children: ReactNode }) {
  return <aside className="rail" aria-label="About this page">{children}</aside>
}

export function Button({ variant = 'secondary', size, className = '', children, ...props }:
  ComponentProps<'button'> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-solid'; size?: 'sm' | 'lg' }) {
  return <button className={`btn btn-${variant}${size ? ` btn-${size}` : ''} ${className}`} {...props}>{children}</button>
}
export function buttonClass(variant: 'primary' | 'secondary' | 'ghost' = 'secondary', size?: 'sm' | 'lg') {
  return `btn btn-${variant}${size ? ` btn-${size}` : ''}`
}

export function Chip({ children, tone = 'neutral', title }: {
  children: ReactNode; tone?: 'ok' | 'neutral' | 'warn' | 'error'; title?: string
}) {
  return <span className={`chip chip-${tone}`} title={title}>{children}</span>
}

export type SourceKind = 'feed' | 'podcast' | 'youtube'
export const kindNames: Record<SourceKind, string> = {
  feed: 'Website feed', podcast: 'Podcast', youtube: 'YouTube channel',
}
export function KindBadge({ kind }: { kind: SourceKind }) {
  return <span className={`badge badge-kind kind-${kind}`}><Icon name={kind} className="icon icon-sm"/>{kindNames[kind]}</span>
}
export function KindIcon({ kind }: { kind: SourceKind | null | undefined }) {
  return kind && kind in kindNames
    ? <><Icon name={kind} className="icon icon-sm"/><span className="sr-only">{kindNames[kind]}: </span></>
    : null
}

export type Reason = 'captions_off' | 'no_captions' | 'blocked' | 'captions_failed' | 'no_transcript'
export const reasons: Record<Reason, string> = {
  captions_off: 'Caption fetching is off', no_captions: 'This video has no captions',
  blocked: 'Blocked by YouTube', captions_failed: 'Captions could not be fetched',
  no_transcript: 'No transcript within 7 days',
}
export function ReasonLabel({ reason, waitDays = 7 }: { reason: Reason; waitDays?: number }) {
  return <span className={`reason reason-${reason}`}>
    {reason === 'no_transcript' ? `No transcript within ${waitDays} days` : reasons[reason]}
  </span>
}

export function Alert({ tone = 'info', title, children, actions }: {
  tone?: 'info' | 'error'; title: string; children: ReactNode; actions?: ReactNode
}) {
  return <div className={`alert alert-${tone}`} role="alert"><Icon name={tone === 'error' ? 'alert' : 'info'}/>
    <div><strong>{title}</strong><p>{children}</p>{actions && <div className="alert-actions">{actions}</div>}</div>
  </div>
}

export function Switch({ label, checked, onChange, describedBy, disabled }: {
  label: string; checked: boolean; onChange: ComponentProps<'input'>['onChange']
  describedBy?: string; disabled?: boolean
}) {
  return <label className="switch">
    <input type="checkbox" role="switch" checked={checked} onChange={onChange}
      aria-describedby={describedBy} disabled={disabled}/>
    <span className="switch-track" aria-hidden="true"/><span className="switch-label">{label}</span>
  </label>
}

export function Stepper({ current }: { current: 'collecting' | 'summarizing' | 'grouping' }) {
  const steps = [['collecting', 'Checking sources'], ['summarizing', 'Summarizing'], ['grouping', 'Grouping topics']] as const
  const at = steps.findIndex(([name]) => name === current)
  return <ol className="stepper" aria-label="Run progress">{steps.map(([name, label], index) => {
    const state = index < at ? 'done' : index === at ? 'in progress' : 'next'
    return <li className={`step ${index < at ? 'is-done' : index === at ? 'is-current' : ''}`}
      aria-current={index === at ? 'step' : undefined} key={name}>
      <span className="step-dot" aria-hidden="true">{index < at ? <Icon name="check"/> : index + 1}</span>
      {label}<span className="sr-only"> ({state})</span>
    </li>
  })}</ol>
}

export function Progress({ label, value, max }: { label: string; value: number; max: number }) {
  const id = useId()
  return <div className="progress-row"><progress className="progress" value={value} max={max || 1} aria-labelledby={id}/>
    <span className="progress-label" id={id}>{label}</span></div>
}

export function StatusRegion({ children }: { children?: ReactNode }) {
  return <p className="sr-only" role="status" id="run-status">{children}</p>
}

export function SummaryText({ text, lang }: { text: string; lang?: string | null }) {
  const lines = text.split('\n')
  const blocks: { kind: 'paragraph' | 'list'; lines: string[] }[] = []
  for (const raw of lines) {
    const line = raw.trim()
    if (!line) continue
    const list = line.startsWith('- ')
    const kind = list ? 'list' : 'paragraph'
    if (blocks.at(-1)?.kind === kind) blocks.at(-1)!.lines.push(list ? line.slice(2) : line)
    else blocks.push({ kind, lines: [list ? line.slice(2) : line] })
  }
  return <div className="summary" lang={lang || undefined}>{blocks.map((block, index) =>
    block.kind === 'list'
      ? <ul className="points" key={index}>{block.lines.map((line, i) => <li key={i}>{line}</li>)}</ul>
      : <p key={index} style={{ whiteSpace: 'pre-line' }}>{block.lines.join('\n')}</p>)}</div>
}
