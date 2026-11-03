import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, it } from 'vitest'

it('runs the extension install, tests and build in CI', () => {
  const ci = readFileSync(resolve('../.github/workflows/ci.yml'), 'utf8')
  const job = ci.split(/^  extension:\s*$/m)[1]?.split(/^  [a-z]+:\s*$/m)[0]
  expect(job).toContain('working-directory: extension')
  expect(job).toContain('run: npm ci')
  expect(job).toContain('run: npm test -- --run')
  expect(job).toContain('run: npm run build')
})

it('documents loading, connection, permissions, and the X risk', () => {
  const readme = readFileSync(resolve('../README.md'), 'utf8')
  const section = readme.split('## Browser extension')[1]?.split(/^## /m)[0]
  for (const text of ['npm ci', 'npm run build', 'Developer mode', 'Chrome', 'Edge',
    'Load unpacked', 'Settings', 'Browser extension', 'activeTab', 'scripting',
    'storage', '127.0.0.1', 'localhost', 'X', 'terms', 'own risk']) {
    expect(section, text).toContain(text)
  }
})

it('documents collection boundaries, reader license and the context-pass limit', () => {
  const readme = readFileSync(resolve('../README.md'), 'utf8')
  const extension = readme.split('## Browser extension')[1]?.split(/^## /m)[0]
  for (const text of ['cookies', 'saved passwords', 'site storage', 'background reading',
    'scroll', 'click', 'open pages', 'Mozilla Readability', 'Apache-2.0',
    'context pass', 'summary without links', 'without your cookies', 'sponsor text']) {
    expect(extension, text).toContain(text)
  }
})

it('documents X accounts, costs, limits and account ownership without old no-follow claim', () => {
  const readme = readFileSync(resolve('../README.md'), 'utf8')
  expect(readme).toContain('## X accounts')
  expect(readme).toContain('](#x-accounts)')
  const section = readme.split('## X accounts')[1]?.split(/^## /m)[0]
  for (const text of ['console.x.com', 'Bearer token', 'spending limit',
    '2026-10-24', 'CATCHUP_X_READS_PER_RUN', 'Waits for the next run',
    'Delete all X data', '24 hours', 'model provider', 'thread']) {
    expect(section, text).toContain(text)
  }
  expect(readme).not.toContain('CatchUp does not follow X accounts')
})
