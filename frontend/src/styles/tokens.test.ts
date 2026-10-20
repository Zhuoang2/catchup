import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const css = readFileSync('src/styles/tokens.css', 'utf8')

function tokens(text: string): Record<string, string> {
  return Object.fromEntries([...text.matchAll(/(--[\w-]+):\s*(#[\da-f]{6})\s*;/gi)]
    .map(([, key, value]) => [key, value.toLowerCase()]))
}

function themes(text: string) {
  const dark = text.indexOf('@media (prefers-color-scheme: dark)')
  return { light: tokens(text.slice(0, dark)), dark: tokens(text.slice(dark)) }
}

function rgb(hex: string): number[] {
  return [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16) / 255)
}

function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map(value =>
    value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
  return .2126 * r + .7152 * g + .0722 * b
}

function contrast(a: string, b: string): number {
  const [lighter, darker] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (lighter + .05) / (darker + .05)
}

function hue(hex: string): number {
  const [r, g, b] = rgb(hex)
  const high = Math.max(r, g, b)
  const low = Math.min(r, g, b)
  const range = high - low
  if (!range) return 0
  const sector = high === r ? ((g - b) / range) % 6
    : high === g ? (b - r) / range + 2 : (r - g) / range + 4
  return (sector * 60 + 360) % 360
}

export function validateTokens(text: string): string[] {
  const failures: string[] = []
  for (const [theme, values] of Object.entries(themes(text))) {
    const pairs: [string, string, number][] = [
      ...['--bg', '--surface'].flatMap(bg =>
        ['--fg', '--muted', '--subtle', '--accent', '--link']
          .map(fg => [fg, bg, 4.5] as [string, string, number])),
      ['--accent-fg', '--accent', 4.5],
      ...['ok', 'warn', 'error'].map(tone =>
        [`--${tone}`, `--${tone}-soft`, 4.5] as [string, string, number]),
      ['--muted', '--neutral-soft', 4.5],
      ['--muted', '--hover', 4.5],
      ['--fg', '--hover', 4.5],
      ['--muted', '--disabled', 3],
    ]
    for (const [fg, bg, minimum] of pairs) {
      if (!values[fg] || !values[bg] || contrast(values[fg], values[bg]) < minimum) {
        failures.push(`${theme}: ${fg} on ${bg} must be at least ${minimum}:1`)
      }
    }
    for (const [a, b] of [['--error', '--warn'], ['--error', '--accent'], ['--warn', '--accent']]) {
      if (!values[a] || !values[b]) {
        failures.push(`${theme}: missing hue ${a} or ${b}`)
      } else {
        const delta = Math.abs(hue(values[a]) - hue(values[b]))
        if (Math.min(delta, 360 - delta) < 20) failures.push(`${theme}: ${a} and ${b} are too similar`)
      }
    }
    if (values['--error-border'] !== values['--error']) failures.push(`${theme}: error border differs`)
  }
  return failures
}

describe('C7 theme tokens', () => {
  it('meets text, control boundary, and hue requirements in both themes', () => {
    expect(validateTokens(css)).toEqual([])
  })

  it('rejects the earlier low-contrast subtle text', () => {
    expect(validateTokens(css.replace('--subtle: #66625a', '--subtle: #77736a')))
      .toContain('light: --subtle on --bg must be at least 4.5:1')
  })
})

it('shows the full feed URL without a line clamp', () => {
  const components = readFileSync('src/styles/components.css', 'utf8')
  const feed = components.match(/\.source-feed\s*\{([^}]+)\}/)?.[1]
  expect(feed).toBeDefined()
  expect(feed).toMatch(/overflow-wrap:\s*anywhere/)
  expect(feed).not.toMatch(/(?:line-clamp|overflow:\s*hidden)/)
})

it('keeps secondary History text readable when a row is hovered', () => {
  const components = readFileSync('src/styles/components.css', 'utf8')
  const hoverRules = [...components.matchAll(/([^{}]*:hover[^{}]*)\{([^{}]+)\}/g)]
  expect(hoverRules.some(([, selector, body]) =>
    selector.includes('.history-link:hover .history-counts') && /color:\s*var\(--muted\)/.test(body))).toBe(true)
  expect(hoverRules.every(([, , body]) => !/color:\s*var\(--subtle\)/.test(body))).toBe(true)
})

it('styles disabled secondary buttons with the disabled and muted tokens', () => {
  const components = readFileSync('src/styles/components.css', 'utf8')
  const disabled = components.match(/\.btn:disabled\s*\{([^}]+)\}/)?.[1]
  expect(disabled).toMatch(/background:\s*var\(--disabled\)/)
  expect(disabled).toMatch(/color:\s*var\(--muted\)/)
})

it('does not restyle disabled buttons on hover', () => {
  const components = readFileSync('src/styles/components.css', 'utf8')
  const hoverRules = [...components.matchAll(/([^{}]*\.btn[^{}]*:hover[^{}]*)\{([^{}]+)\}/g)]
  expect(hoverRules.length).toBeGreaterThan(0)
  for (const [, selector] of hoverRules) {
    for (const part of selector.split(',')) expect(part).toMatch(/:not\(:disabled\)/)
  }
})

it('keeps the Settings save bar visible at the bottom of the window', () => {
  const layout = readFileSync('src/styles/layout.css', 'utf8')
  const rule = layout.match(/\.save-bar\s*\{([^}]+)\}/)?.[1]
  expect(rule).toMatch(/position:\s*sticky/)
  expect(rule).toMatch(/bottom:\s*0/)
  expect(rule).toMatch(/background:\s*var\(--bg\)/)
})

it('keeps focused fields clear of the sticky save bar', () => {
  const layout = readFileSync('src/styles/layout.css', 'utf8')
  const rule = layout.match(/:root:has\(\.save-bar\)\s*\{([^}]+)\}/)?.[1]
  expect(rule).toMatch(/scroll-padding-bottom:\s*\d/)
})

it('spans and separates the Home run bar with one-row ready controls at all widths', () => {
  const layout = readFileSync('src/styles/layout.css', 'utf8')
  const components = readFileSync('src/styles/components.css', 'utf8')
  const wide = layout.match(/\.page-home\s*>\s*\.run-bar\s*\{([^}]+)\}/)?.[1]
  expect(wide).toMatch(/grid-column:\s*1\s*\/\s*-1/)
  const narrow = layout.slice(layout.indexOf('@container (max-width: 900px)'))
  expect(narrow).toMatch(/\.page\s*>\s*\*[^{}]*\{[^}]*grid-column:\s*1\s*\/\s*-1/)
  expect(narrow).not.toMatch(/\.page-home\s*>\s*\.run-bar\s*\{/)
  const bar = components.match(/\.run-bar\s*\{([^}]+)\}/)?.[1]
  expect(bar).toMatch(/border-bottom:\s*1px solid var\(--border-strong\)/)
  expect(components).toMatch(/\.run-bar\s+\.check-row:last-child\s*\{[^}]*border-bottom:\s*0/)
  expect(components).not.toMatch(/\.hero-last\b/)
  const actions = components.match(/\.run-bar-actions\s*\{([^}]+)\}/)?.[1]
  expect(actions).toMatch(/display:\s*flex/)
  expect(actions).toMatch(/align-items:\s*center/)
})

type LayoutRule = { selector: string; body: string; container: string | null }

function layoutRules(text: string, container: string | null = null): LayoutRule[] {
  const css = text.replace(/\/\*[\s\S]*?\*\//g, '')
  const rules: LayoutRule[] = []
  let start = 0
  while (start < css.length) {
    const open = css.indexOf('{', start)
    if (open < 0) break
    const selector = css.slice(start, open).trim()
    let close = open + 1
    let depth = 1
    while (depth && close < css.length) {
      if (css[close] === '{') depth++
      if (css[close] === '}') depth--
      close++
    }
    const body = css.slice(open + 1, close - 1)
    if (selector.startsWith('@')) rules.push(...layoutRules(body,
      selector.startsWith('@container') ? selector : container))
    else rules.push({ selector, body, container })
    start = close
  }
  return rules
}

function ownedLayoutRules(): (LayoutRule & { file: string })[] {
  return ['base', 'layout', 'components'].flatMap(name => {
    const file = `src/styles/${name}.css`
    return layoutRules(readFileSync(file, 'utf8')).map(rule => ({ ...rule, file }))
  })
}

function splitSelectors(selector: string): string[] {
  const parts: string[] = []
  let depth = 0
  let start = 0
  for (let i = 0; i < selector.length; i++) {
    if (selector[i] === '(' || selector[i] === '[') depth++
    else if (selector[i] === ')' || selector[i] === ']') depth--
    else if (selector[i] === ',' && depth === 0) {
      parts.push(selector.slice(start, i).trim())
      start = i + 1
    }
  }
  parts.push(selector.slice(start).trim())
  return parts
}

function rightmostCompound(selector: string): string {
  let compound = ''
  let depth = 0
  for (const char of selector.trim()) {
    if (char === '(' || char === '[') depth++
    else if (char === ')' || char === ']') depth--
    if (depth === 0 && /[\s>+~]/.test(char)) compound = ''
    else compound += char
  }
  return compound
}

function hasTargetClass(compound: string, classes: string[]): boolean {
  const direct = compound.replace(/\[[^\]]*\]|:[\w-]+\([^()]*\)/g, '')
  if ([...direct.matchAll(/\.([\w-]+)/g)].some(([, name]) => classes.includes(name))) return true
  return [...compound.matchAll(/:(?:is|where)\(([^()]*)\)/g)].some(([, options]) =>
    splitSelectors(options).some(option => hasTargetClass(rightmostCompound(option), classes)))
}

function targetsItemChild(selector: string): boolean {
  return splitSelectors(selector).some(part => {
    const compound = rightmostCompound(part)
    return hasTargetClass(compound, ['item-meta', 'item-title', 'item-body', 'summary', 'summary-unavailable'])
      || (compound === '*' && /\.items\s*>\s*\.item\s*>\s*\*$/.test(part))
  })
}

function targetsItem(selector: string): boolean {
  return splitSelectors(selector).some(part => hasTargetClass(rightmostCompound(part), ['item']))
}

function properties(body: string): string[] {
  return [...body.matchAll(/(?:^|;)\s*([\w-]+)\s*:/g)].map(([, name]) => name.toLowerCase())
}

it('places digest headings beside summaries only above 1100px', () => {
  const rules = ownedLayoutRules()
  const wide = rules.filter(rule =>
    rule.file === 'src/styles/layout.css' && rule.container === '@container (width > 1100px)')
  const outside = rules.filter(rule =>
    rule.file === 'src/styles/layout.css' && rule.container !== '@container (width > 1100px)')
  const wideRule = (selector: string) => wide.find(rule => rule.selector.split(',').map(part => part.trim()).includes(selector))?.body

  const misplaced = rules.filter(rule => rule.container !== '@container (width > 1100px)' &&
    properties(rule.body).some(property =>
      (targetsItemChild(rule.selector) && /^grid-(?:area|column(?:-(?:start|end))?|row(?:-(?:start|end))?)$/.test(property))
      || (targetsItem(rule.selector) && /^grid(?:-template(?:-(?:columns|rows|areas))?)?$/.test(property))))
  expect(misplaced.map(rule => `${rule.file}: ${rule.selector}`)).toEqual([])

  const item = wideRule('.items > .item')
  expect(item).toMatch(/grid-template-columns:\s*subgrid/)
  expect(item).toMatch(/column-gap:\s*var\(--gutter\)/)
  expect(item).toMatch(/grid-template-rows:\s*auto\s+auto\s+1fr/)
  for (const [selector, row] of [
    ['.items > .item > .item-meta', '1'],
    ['.items > .item > .item-title', '2'],
  ]) {
    expect(wideRule(selector)).toMatch(/grid-column:\s*1\s*\/\s*span\s+3/)
    expect(wideRule(selector)).toMatch(new RegExp(`grid-row:\\s*${row}\\s*;`))
  }
  for (const selector of ['.items > .item > .item-body', '.items > .item > .summary-unavailable']) {
    expect(wideRule(selector)).toMatch(/grid-column:\s*4\s*\/\s*-1/)
    expect(wideRule(selector)).toMatch(/grid-row:\s*1\s*\/\s*-1/)
  }

  const outsideItems = outside.filter(rule => rule.selector.startsWith('.items > .item'))
  expect(outsideItems.map(rule => rule.selector)).toEqual([
    '.items > .item', '.items > .item + .item',
  ])
  expect(outsideItems.every(rule => rule.container === null)).toBe(true)
  expect(outsideItems[0].body).toMatch(/grid-column:\s*1\s*\/\s*-1/)
  expect(outsideItems[0].body).not.toMatch(/grid-template-columns|grid-template-rows|column-gap/)
  expect(outsideItems[1].body).toMatch(/border-top:\s*1px solid var\(--border\)/)
  expect(outside.map(rule => rule.body).join(' ')).not.toMatch(/grid-template-rows:\s*auto\s+auto\s+1fr/)
})

it('keeps digest items and their headings and summaries free of vertical rules', () => {
  const rulesWithVerticalBorders = ownedLayoutRules().filter(rule =>
    (targetsItemChild(rule.selector) || targetsItem(rule.selector))
    && properties(rule.body).some(property =>
      property.startsWith('border') && !/^border-(?:top|bottom)(?:-|$)/.test(property)
      && property !== 'border-radius'))
  expect(rulesWithVerticalBorders.map(rule => `${rule.file}: ${rule.selector}`)).toEqual([])
})

it('does not size items by length or separate them with a vertical rule', () => {
  const rules = layoutRules(readFileSync('src/styles/layout.css', 'utf8'))
  expect(rules.some(rule => /\.item-(?:long|short)\b|\.item:only-child\b/.test(rule.selector))).toBe(false)
  const separators = rules.filter(rule => rule.selector.split(',').some(selector =>
    selector.trim() === '.items > .item + .item'))
  expect(separators).toHaveLength(1)
  expect(separators[0].body).not.toMatch(/border-left\s*:/)
})

it('keeps image figures inside the summary cell, bounded and wrapping without grid rules', () => {
  const components = readFileSync('src/styles/components.css', 'utf8')
  const block = components.match(/\.item-images\s*\{([^}]+)\}/)?.[1]
  const image = components.match(/\.item-images img\s*\{([^}]+)\}/)?.[1]
  expect(block).toMatch(/display:\s*flex/)
  expect(block).toMatch(/flex-wrap:\s*wrap/)
  expect(block).not.toMatch(/grid-column|grid-row/)
  expect(image).toMatch(/max-height:\s*320px/)
  expect(image).toMatch(/max-width:\s*100%/)
  expect(image).toMatch(/object-fit:\s*contain/)
  expect(image).toMatch(/border:\s*1px solid var\(--border\)/)
})
