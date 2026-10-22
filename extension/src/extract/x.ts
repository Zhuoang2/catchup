// Passed directly to chrome.scripting.executeScript; Chrome drops module scope.
export function extractX() {
  const path = /^\/[^/]+\/status\/(\d+)(?:\/|$)/.exec(location.pathname)
  if (!['x.com', 'twitter.com'].includes(location.hostname) || !path) return null
  function hasStatusId(article: Element, id: string): boolean {
    for (const anchor of article.querySelectorAll<HTMLAnchorElement>('a[href]')) {
      try {
        const url = new URL(anchor.href)
        if (url.hostname === 'x.com' || url.hostname === 'twitter.com') {
          const match = /^\/[^/]+\/status\/(\d+)(?:\/|$)/.exec(url.pathname)
          if (match?.[1] === id) return true
        }
      } catch { /* Ignore invalid page links. */ }
    }
    return false
  }
  function identity(article: Element): { name: string; handle: string } {
    const label = article.querySelector('[data-testid="User-Name"]')?.textContent?.replace(/\s+/g, ' ').trim() ?? ''
    const handle = /@[\w_]+/.exec(label)?.[0] ?? ''
    const name = label.split(handle)[0].trim() || handle
    return { name, handle }
  }
  const articles = Array.from(document.querySelectorAll('article[data-testid="tweet"]'))
  const index = articles.findIndex(article => hasStatusId(article, path[1]))
  if (index < 0) return null
  const article = articles[index]
  const author = identity(article)
  const text = article.querySelector('[data-testid="tweetText"]')?.textContent?.replace(/\s+/g, ' ').trim() ?? ''
  const replies: string[] = []
  for (const reply of articles.slice(index + 1)) {
    if (!author.handle || identity(reply).handle.toLowerCase() !== author.handle.toLowerCase()) continue
    const value = reply.querySelector('[data-testid="tweetText"]')?.textContent?.replace(/\s+/g, ' ').trim()
    if (!value) continue
    const remaining = 4000 - replies.join('\n\n').length - (replies.length ? 2 : 0)
    if (remaining <= 0 || replies.length >= 10) break
    replies.push(value.slice(0, remaining))
  }
  const images: { url: string; alt: string }[] = []
  for (const image of article.querySelectorAll<HTMLImageElement>('[data-testid="tweetPhoto"] img')) {
    try {
      const url = new URL(image.currentSrc || image.src)
      if (['http:', 'https:'].includes(url.protocol)) images.push({ url: url.href, alt: image.alt.slice(0, 500) })
    } catch { /* Ignore invalid page images. */ }
    if (images.length >= 8) break
  }
  const links: { url: string; text: string }[] = []
  for (const anchor of article.querySelectorAll<HTMLAnchorElement>('a[href]')) {
    try {
      let url = new URL(anchor.href)
      const label = (anchor.textContent ?? '').trim()
      if (url.hostname === 't.co') {
        if (!/^https?:\/\/\S+$/.test(label) || label.endsWith('…')) continue
        url = new URL(label)
      }
      if (['http:', 'https:'].includes(url.protocol)) links.push({ url: url.href, text: label.slice(0, 500) })
    } catch { /* Ignore invalid page links. */ }
    if (links.length >= 50) break
  }
  return {
    url: location.href, title: `${author.name} on X`, site_name: `X · ${author.name}`,
    author: `${author.name} ${author.handle}`.trim(),
    published_at: article.querySelector('time[datetime]')?.getAttribute('datetime') ?? null,
    content_text: text.slice(0, 16000),
    images, links, replies,
  }
}
