import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { expect, it } from 'vitest'

const referencedAssets = [
  'assets/popup-test.js', 'assets/popup-test.css',
  'assets/options-test.js', 'assets/options-test.css',
]
const required = [
  'popup.html', 'options.html', 'icon-192.png',
  'readability.js', 'readability-LICENSE.md', ...referencedAssets,
]

it.each(required)(
  'rejects an unpacked build missing %s', missing => {
    const root = mkdtempSync(join(tmpdir(), 'catchup-extension-build-'))
    const dist = join(root, 'dist')
    mkdirSync(dist)
    try {
      copyFileSync(resolve('public/manifest.json'), join(dist, 'manifest.json'))
      mkdirSync(join(dist, 'assets'))
      writeFileSync(join(dist, 'popup.html'), `<link rel="stylesheet" href="/assets/popup-test.css">
        <script type="module" src="/assets/popup-test.js"></script>`)
      writeFileSync(join(dist, 'options.html'), `<link rel="stylesheet" href="/assets/options-test.css">
        <script type="module" src="/assets/options-test.js"></script>`)
      for (const name of required) {
        if (name === 'popup.html' || name === 'options.html') continue
        writeFileSync(join(dist, name), 'test fixture')
      }
      const check = () => execFileSync(process.execPath, [resolve('scripts/check-build.mjs')], {
        cwd: root, stdio: 'pipe',
      })
      expect(check).not.toThrow()
      rmSync(join(dist, missing))
      expect(check).toThrow()
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  },
)
