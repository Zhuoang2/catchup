// Chrome serializes this function into the tab after readability.js is injected there.
export function extractReadable() {
  const Reader = (globalThis as {
    Readability?: new (doc: Document) => { parse(): {
      title?: string | null; content?: string | null; textContent?: string | null
      byline?: string | null; siteName?: string | null; publishedTime?: string | null
    } | null }
  }).Readability
  if (!Reader) return null
  const article = new Reader(document.cloneNode(true) as Document).parse()
  if (!article?.content || (article.textContent ?? '').trim().length < 200) return null

  function httpUrl(value: string | null | undefined): string | null {
    if (!value) return null
    try {
      const parsed = new URL(value, location.href)
      return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : null
    } catch { return null }
  }
  function meta(selector: string): string | null {
    return document.querySelector<HTMLMetaElement>(selector)?.content.trim() || null
  }
  const url = httpUrl(document.querySelector<HTMLLinkElement>('link[rel~=canonical]')?.href)
    ?? httpUrl(meta('meta[property="og:url"]')) ?? httpUrl(location.href) ?? ''
  const parsed = new DOMParser().parseFromString(article.content, 'text/html')
  const root = parsed.body
  function excluded(element: Element): boolean {
    for (let current: Element | null = element; current && current !== root; current = current.parentElement) {
      if (current.matches('nav,aside,footer,header,form,script,style,noscript')) return true
    }
    return false
  }
  let text = ''
  let previousBlock: Element | null = null
  const walker = parsed.createTreeWalker(root, NodeFilter.SHOW_TEXT)
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
  const images: { url: string; alt: string }[] = []
  for (const image of root.querySelectorAll('img')) {
    if (excluded(image)) continue
    const src = httpUrl(image.currentSrc || image.getAttribute('src') || image.src)
    if (src) images.push({ url: src, alt: image.alt.slice(0, 500) })
    if (images.length >= 8) break
  }
  const links: { url: string; text: string }[] = []
  for (const anchor of root.querySelectorAll<HTMLAnchorElement>('a[href]')) {
    if (excluded(anchor)) continue
    const href = httpUrl(anchor.getAttribute('href'))
    if (href) links.push({ url: href, text: (anchor.textContent ?? '').trim().slice(0, 500) })
    if (links.length >= 50) break
  }
  return {
    url,
    title: article.title || meta('meta[property="og:title"]') || document.title,
    site_name: article.siteName || meta('meta[property="og:site_name"]') || location.hostname,
    author: article.byline || meta('meta[name="author"]') || meta('meta[property="article:author"]'),
    published_at: article.publishedTime || meta('meta[property="article:published_time"]'),
    content_text: text.slice(0, 16000).trim(), images, links, replies: [] as string[],
  }
}
