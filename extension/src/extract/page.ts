// Passed directly to chrome.scripting.executeScript; keep all runtime dependencies inside.
export type CapturedPage = {
  url: string
  title: string
  site_name: string
  author: string | null
  published_at: string | null
  content_text: string
  images: { url: string; alt: string }[]
  links: { url: string; text: string }[]
  replies: string[]
}

export function extractPage(): CapturedPage {
  type ReadArticle = {
    title?: string | null; content?: string | null; textContent?: string | null
    byline?: string | null; siteName?: string | null; publishedTime?: string | null
  }
  const Reader = (globalThis as {
    Readability?: new (doc: Document, options?: {
      charThreshold: number; linkDensityModifier: number
    }) => { parse(): ReadArticle | null }
  }).Readability

  const shown = document.cloneNode(true) as Document
  const removed: Element[] = []
  function copyShown(live: Element, copy: Element) {
    if (live.matches('script,style,template,noscript')) return
    const style = getComputedStyle(live)
    if (style.display === 'none') { removed.push(copy); return }
    if (style.visibility === 'hidden' || style.visibility === 'collapse') {
      if (!live.children.length) { removed.push(copy); return }
      for (const node of [...copy.childNodes]) {
        if (node.nodeType === Node.TEXT_NODE) node.remove()
      }
    }
    if (live.tagName === 'IMG' && (live as HTMLImageElement).currentSrc) {
      copy.setAttribute('src', (live as HTMLImageElement).currentSrc)
    }
    for (let i = 0; i < live.children.length; ++i) {
      copyShown(live.children[i], copy.children[i])
    }
  }
  copyShown(document.body, shown.body)
  for (const element of removed) element.remove()

  let article: ReadArticle | null = null
  if (Reader) {
    try {
      article = new Reader(shown.cloneNode(true) as Document, {
        charThreshold: 1, linkDensityModifier: 0.3,
      }).parse()
    } catch { /* Read the visible main region instead. */ }
  }
  const region = shown.querySelector('article') ?? shown.querySelector('main')
    ?? shown.querySelector('[role="main"]')
  const root = article?.content && article.textContent?.trim()
    ? new DOMParser().parseFromString(article.content, 'text/html').body
    : region ?? shown.body

  function httpUrl(value: string | null | undefined): string | null {
    if (!value) return null
    try {
      const parsed = new URL(value, document.baseURI)
      return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null
    } catch { return null }
  }
  function meta(selector: string): string | null {
    return document.querySelector<HTMLMetaElement>(selector)?.content.trim() || null
  }
  const url = httpUrl(document.querySelector<HTMLLinkElement>('link[rel~=canonical]')?.href)
    ?? httpUrl(meta('meta[property="og:url"]')) ?? httpUrl(location.href) ?? ''
  const title = article?.title?.trim() || meta('meta[property="og:title"]') || document.title

  function excluded(element: Element): boolean {
    for (let current: Element | null = element; current && current !== root; current = current.parentElement) {
      if (current.matches('nav,aside,footer,header,form,script,style,noscript')) return true
    }
    return false
  }
  let text = ''
  let previousBlock: Element | null = null
  const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  while (walker.nextNode()) {
    const node = walker.currentNode
    const parent = node.parentElement
    if (!parent || excluded(parent)) continue
    const value = (node.nodeValue ?? '').replace(/\s+/g, ' ').trim()
    if (!value) continue
    const block = parent.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre,div,section,article,main,body')
    if (text && block !== previousBlock) text += '\n'
    else if (text && !/[\s]$/.test(text) && !/^[.,!?;:)\]]/.test(value)) text += ' '
    text += value
    previousBlock = block
    if (text.length >= 16000) break
  }
  const images: CapturedPage['images'] = []
  for (const image of root.querySelectorAll('img')) {
    if (excluded(image)) continue
    const src = httpUrl(image.getAttribute('src'))
    if (src) images.push({ url: src, alt: image.alt.slice(0, 500) })
    if (images.length >= 8) break
  }

  const links: CapturedPage['links'] = []
  const seen = new Set<string>()
  function addLink(anchor: Element) {
    const href = httpUrl(anchor.getAttribute('href'))
    if (href && !seen.has(href) && links.length < 50) {
      seen.add(href)
      links.push({ url: href, text: (anchor.textContent ?? '').trim().slice(0, 500) })
    }
  }
  const collapse = (value: string) => value.replace(/\s+/g, ' ').trim().toLowerCase()
  function withoutSite(value: string): string {
    const cut = Math.max(...[' | ', ' - ', ' – ', ' — ', ' · '].map(separator => value.lastIndexOf(separator)))
    return cut < 0 ? value : value.slice(0, cut)
  }
  function withoutLabel(value: string): string {
    const cut = value.indexOf(': ')
    return cut < 0 ? value : value.slice(cut + 2)
  }
  function withoutFragment(value: string): string {
    const parsed = new URL(value)
    parsed.hash = ''
    return parsed.href
  }
  const t = collapse(title)
  const wanted = new Set([t, withoutLabel(t), withoutSite(t), withoutSite(withoutLabel(t))])
  for (const anchor of shown.body.querySelectorAll('a[href]')) {
    if (anchor.closest('nav,aside,footer,header,form')) continue
    const href = httpUrl(anchor.getAttribute('href'))
    if (!href || withoutFragment(href) === withoutFragment(location.href)
        || (url && withoutFragment(href) === withoutFragment(url))) continue
    if (!wanted.has(collapse(anchor.textContent ?? ''))) continue
    addLink(anchor)
    break
  }
  for (const anchor of root.querySelectorAll('a[href]')) {
    if (excluded(anchor)) continue
    addLink(anchor)
    if (links.length >= 50) break
  }
  return {
    url, title,
    site_name: article?.siteName?.trim() || meta('meta[property="og:site_name"]') || location.hostname,
    author: article?.byline?.trim() || meta('meta[name="author"]') || meta('meta[property="article:author"]'),
    published_at: article?.publishedTime?.trim() || meta('meta[property="article:published_time"]')
      || root.querySelector('time[datetime]')?.getAttribute('datetime')
      || region?.querySelector('time[datetime]')?.getAttribute('datetime') || null,
    content_text: text.slice(0, 16000).trim(),
    images, links, replies: [],
  }
}
