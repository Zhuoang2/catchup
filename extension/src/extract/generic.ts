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

// Passed directly to chrome.scripting.executeScript. Keep all runtime dependencies inside.
export function extractGeneric(): CapturedPage {
  function httpUrl(value: string | null | undefined): string | null {
    if (!value) return null
    try {
      const parsed = new URL(value, location.href)
      return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.href : null
    } catch { return null }
  }
  function meta(selector: string): string | null {
    return document.querySelector<HTMLMetaElement>(selector)?.content.trim() || null
  }
  const url = httpUrl(document.querySelector<HTMLLinkElement>('link[rel~=canonical]')?.href)
    ?? httpUrl(meta('meta[property="og:url"]')) ?? httpUrl(location.href) ?? ''
  const root = document.querySelector('article') ?? document.querySelector('main')
    ?? document.querySelector('[role="main"]') ?? document.body
  let text = ''
  let previousBlock: Element | null = null
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  while (walker.nextNode()) {
    const node = walker.currentNode
    const parent = node.parentElement
    if (!parent || parent.closest('nav,aside,footer,script,style,noscript,form')) continue
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
    const src = httpUrl(image.currentSrc || image.src)
    if (src) images.push({ url: src, alt: image.alt.slice(0, 500) })
    if (images.length >= 8) break
  }
  const links: CapturedPage['links'] = []
  for (const anchor of root.querySelectorAll<HTMLAnchorElement>('a[href]')) {
    const href = httpUrl(anchor.href)
    if (href) links.push({ url: href, text: (anchor.textContent ?? '').trim().slice(0, 500) })
    if (links.length >= 50) break
  }
  return {
    url,
    title: meta('meta[property="og:title"]') ?? document.title,
    site_name: meta('meta[property="og:site_name"]') ?? location.hostname,
    author: meta('meta[name="author"]') ?? meta('meta[property="article:author"]'),
    published_at: meta('meta[property="article:published_time"]')
      ?? root.querySelector('time[datetime]')?.getAttribute('datetime') ?? null,
    content_text: text.slice(0, 16000).trim(),
    images, links, replies: [],
  }
}
