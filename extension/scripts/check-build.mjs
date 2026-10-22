import { existsSync, readFileSync } from 'node:fs'
import { resolve, join } from 'node:path'

export function checkBuild(dist = resolve('dist')) {
  const manifestPath = join(dist, 'manifest.json')
  if (!existsSync(manifestPath)) throw new Error('Missing manifest.json from extension build')
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
  const paths = [
    manifest.action.default_popup, manifest.options_ui.page, ...Object.values(manifest.icons),
    'readability.js', 'readability-LICENSE.md',
  ]
  for (const html of [manifest.action.default_popup, manifest.options_ui.page]) {
    if (typeof html !== 'string' || !existsSync(join(dist, html))) continue
    const markup = readFileSync(join(dist, html), 'utf8')
    for (const match of markup.matchAll(/\b(?:src|href)=["'](\/assets\/[^"'?#]+)["']/g)) {
      paths.push(match[1].slice(1))
    }
  }
  for (const path of paths) {
    if (typeof path !== 'string' || path.startsWith('/') || path.includes('..')
        || !existsSync(join(dist, path))) {
      throw new Error(`Missing extension build file: ${path}`)
    }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(import.meta.filename)) checkBuild()
