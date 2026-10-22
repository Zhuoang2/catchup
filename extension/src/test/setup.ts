import '@testing-library/jest-dom/vitest'
import 'vitest-axe/extend-expect'

HTMLCanvasElement.prototype.getContext = () => null
