import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, it } from 'vitest'

it('asks only for user-initiated page access and the local CatchUp server', () => {
  const manifest = JSON.parse(readFileSync(resolve('public/manifest.json'), 'utf8'))
  expect(manifest.manifest_version).toBe(3)
  expect(manifest.permissions).toEqual(['activeTab', 'scripting', 'storage'])
  expect(manifest.host_permissions).toEqual(['http://127.0.0.1/*', 'http://localhost/*'])
  for (const forbidden of ['background', 'content_scripts', 'externally_connectable']) {
    expect(manifest).not.toHaveProperty(forbidden)
  }
  expect(manifest.action.default_popup).toBe('popup.html')
  expect(manifest.options_ui.page).toBe('options.html')
  expect(manifest.icons['192']).toBe('icon-192.png')
})
