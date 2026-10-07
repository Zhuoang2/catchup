import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import 'vitest-axe/extend-expect'

afterEach(cleanup)

// axe probes canvas font rendering; jsdom does not implement a canvas context.
HTMLCanvasElement.prototype.getContext = () => null
