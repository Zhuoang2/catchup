import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { execFileSync } from 'node:child_process'
import { expect, it } from 'vitest'

it.each(['popup.html', 'options.html', 'icon-192.png'])(
  'rejects an unpacked build missing %s', missing => {
    const root = mkdtempSync(join(tmpdir(), 'catchup-extension-build-'))
    const dist = join(root, 'dist')
    mkdirSync(dist)
    try {
      copyFileSync(resolve('public/manifest.json'), join(dist, 'manifest.json'))
      for (const name of ['popup.html', 'options.html', 'icon-192.png']) {
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
