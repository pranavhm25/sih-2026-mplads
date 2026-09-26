import { afterEach, beforeEach, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'

// jsdom lacks ResizeObserver; recharts' ResponsiveContainer needs it.
// (Discovered when a CommandCenter waking-state test recovered to full render.)
if (typeof globalThis.ResizeObserver === 'undefined') {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver
}

// Ensure tests never hit the network; api.ts uses relative /api paths.
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(new Error('fetch not mocked in this test'))),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})
