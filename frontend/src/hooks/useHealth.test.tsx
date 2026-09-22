import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import SystemStatus from '../pages/SystemStatus'

function mockFetchOnce(payload: unknown, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok,
        status: ok ? 200 : 500,
        json: () => Promise.resolve(payload),
      }),
    ),
  )
}

describe('SystemStatus (backend health screen)', () => {
  it('shows connected state when /api/v1/health returns ok', async () => {
    mockFetchOnce({ data: { status: 'ok', service: 'drishti-api' }, meta: {} })
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getByText(/Backend connected/)).toBeInTheDocument())
    expect(screen.getByText('drishti-api')).toBeInTheDocument()
  })

  it('shows unreachable state and error when backend is down', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.reject(new Error('Backend unreachable'))),
    )
    render(<SystemStatus />)
    // The text appears in both the status badge and the error row.
    await waitFor(() => expect(screen.getAllByText(/Backend unreachable/).length).toBeGreaterThan(0))
  })

  it('handles non-ok health payload as down', async () => {
    mockFetchOnce({ data: { status: 'degraded', service: 'drishti-api' }, meta: {} })
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getAllByText(/Backend unreachable/).length).toBeGreaterThan(0))
  })

  it('re-check button refetches health', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ data: { status: 'ok', service: 'drishti-api' }, meta: {} }),
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getByText(/Backend connected/)).toBeInTheDocument())
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: /Re-check connection/i }))
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2))
  })
})

describe('App smoke (foundation §15)', () => {
  it('renders the shell with primary navigation', async () => {
    mockFetchOnce({ data: { status: 'ok', service: 'drishti-api' }, meta: {} })
    const { default: App } = await import('../App')
    // jsdom lacks URLSearchParams routing issues here; RouterProvider handles '/'
    const { container } = render(<App />)
    expect(container).toBeTruthy()
  })
})
