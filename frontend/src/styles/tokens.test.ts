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
