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
