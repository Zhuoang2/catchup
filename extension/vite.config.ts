import { defineConfig } from 'vitest/config'
import { resolve } from 'node:path'
import { readFile } from 'node:fs/promises'

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        popup: resolve(import.meta.dirname, 'popup.html'),
        options: resolve(import.meta.dirname, 'options.html'),
      },
    },
  },
  plugins: [{
    name: 'catchup-png-icon',
    async generateBundle() {
      this.emitFile({
        type: 'asset', fileName: 'icon-192.png',
        source: await readFile(resolve(import.meta.dirname, '../frontend/public/icon-192.png')),
      })
    },
  }],
  test: {
    environment: 'jsdom', setupFiles: ['./src/test/setup.ts'],
    environmentOptions: { jsdom: { url: 'https://x.com/alice/status/123' } },
  },
})
