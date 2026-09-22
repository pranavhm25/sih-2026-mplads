import { afterEach, beforeEach, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'

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
