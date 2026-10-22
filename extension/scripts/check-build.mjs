import { existsSync, readFileSync } from 'node:fs'
import { resolve, join } from 'node:path'

export function checkBuild(dist = resolve('dist')) {
  const manifestPath = join(dist, 'manifest.json')
  if (!existsSync(manifestPath)) throw new Error('Missing manifest.json from extension build')
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
  const paths = [
    manifest.action.default_popup, manifest.options_ui.page, ...Object.values(manifest.icons),
  ]
  for (const path of paths) {
    if (typeof path !== 'string' || path.startsWith('/') || path.includes('..')
        || !existsSync(join(dist, path))) {
      throw new Error(`Missing extension build file: ${path}`)
    }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)) checkBuild()
