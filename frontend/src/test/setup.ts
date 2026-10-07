import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import 'vitest-axe/extend-expect'

afterEach(cleanup)

// axe probes canvas font rendering; jsdom does not implement a canvas context.
HTMLCanvasElement.prototype.getContext = () => null

// vite.config.ts pins TZ for the date tests; fail loudly if a pool or runner ignores it.
const zone = Intl.DateTimeFormat().resolvedOptions().timeZone
if (zone !== 'America/Los_Angeles') {
  throw new Error(`Tests must run in America/Los_Angeles (got ${zone}); see test.env in vite.config.ts.`)
}
