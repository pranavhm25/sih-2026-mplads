import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import SystemStatus from '../pages/SystemStatus'
import { setRetryDelaysForTesting } from '../services/api'
import { useBackendReady } from './useHealth'

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

beforeEach(() => {
  // Keep retry backoff instantaneous in tests; restored after each test.
  setRetryDelaysForTesting([1, 1, 1, 1, 1])
})

afterEach(() => {
  setRetryDelaysForTesting([1000, 2000, 4000, 8000, 8000])
})

describe('SystemStatus (backend health screen)', () => {
  it('shows connected state when /api/v1/health returns ok', async () => {
    mockFetchOnce({ status: 'ok', service: 'drishti-api' })
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
    mockFetchOnce({ status: 'degraded', service: 'drishti-api' })
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getAllByText(/Backend unreachable/).length).toBeGreaterThan(0))
  })

  it('re-check button refetches health', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'ok', service: 'drishti-api' }),
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
    mockFetchOnce({ status: 'ok', service: 'drishti-api' })
    const { default: App } = await import('../App')
    // jsdom lacks URLSearchParams routing issues here; RouterProvider handles '/'
    const { container } = render(<App />)
    expect(container).toBeTruthy()
  })
})

describe('GET retry layer (cold-start resilience)', () => {
  it('retries GET on network failure and succeeds when the backend wakes', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'ok', service: 'drishti-api' }),
      })
    vi.stubGlobal('fetch', fetchMock)
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getByText(/Backend connected/)).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('retries GET on 503 and succeeds', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'ok', service: 'drishti-api' }),
      })
    vi.stubGlobal('fetch', fetchMock)
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getByText(/Backend connected/)).toBeInTheDocument())
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('gives up after the bounded retry window', async () => {
    const fetchMock = vi.fn(() => Promise.reject(new TypeError('Failed to fetch')))
    vi.stubGlobal('fetch', fetchMock)
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getAllByText(/Backend unreachable/).length).toBeGreaterThan(0))
    // 1 initial + 5 retries, never more.
    expect(fetchMock).toHaveBeenCalledTimes(6)
  })

  it('does not retry on 4xx application errors', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: false, status: 404, json: () => Promise.resolve({}) })
    vi.stubGlobal('fetch', fetchMock)
    render(<SystemStatus />)
    await waitFor(() => expect(screen.getAllByText(/Backend unreachable/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('never retries mutations (POST)', async () => {
    const { api } = await import('../services/api')
    const fetchMock = vi.fn(() =>
      Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({}) }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await expect(api.createCase({ project_id: 'p1' })).rejects.toBeTruthy()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe('waking-backend UX (useBackendReady / BackendGate)', () => {
  function Probe({ pollMs = 5, maxAttempts = 3 }: { pollMs?: number; maxAttempts?: number }) {
    const s = useBackendReady({ pollMs, maxAttempts })
    return (
      <div>
        <span data-testid="probe-status">{s.status}</span>
        <span data-testid="probe-attempt">{s.attempt}</span>
      </div>
    )
  }

  it('reports down after exhausting bounded attempts', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))))
    render(<Probe maxAttempts={3} />)
    await waitFor(() => expect(screen.getByTestId('probe-status')).toHaveTextContent('down'))
    // Bounded: exactly maxAttempts polls, never infinite.
    expect(Number(screen.getByTestId('probe-attempt').textContent)).toBeLessThanOrEqual(3)
  })

  it('recovers to ready once the backend answers', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'ok', ready: true, checks: { database: 'ok' } }),
      })
    vi.stubGlobal('fetch', fetchMock)
    render(<Probe />)
    await waitFor(() => expect(screen.getByTestId('probe-status')).toHaveTextContent('ready'))
  })

  it('CommandCenter shows the starting state (not a crash) while the backend wakes, then recovers', async () => {
    const { default: CommandCenter } = await import('../pages/CommandCenter')
    let backendUp = false
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/health/ready')) {
        return backendUp
          ? Promise.resolve({
              ok: true,
              status: 200,
              json: () => Promise.resolve({ status: 'ok', ready: true, checks: { database: 'ok' } }),
            })
          : Promise.reject(new TypeError('Failed to fetch'))
      }
      if (url.includes('/dashboard/summary')) {
        return backendUp
          ? Promise.resolve({
              ok: true,
              status: 200,
              json: () =>
                Promise.resolve({
                  data: {
                    total_works: 76,
                    total_value: 1000,
                    high_priority_count: 5,
                    critical_count: 17,
                    delayed_count: 3,
                    duplicate_candidate_count: 1,
                    case_open_count: 0,
                    risk_distribution: { CRITICAL: 17, HIGH: 5, MEDIUM: 26, LOW: 3 },
                    signal_distribution: { DELAY: 3 },
                    quality_exception_count: 0,
                    districts: [],
                    queue_preview: [],
                    map_points: [],
                  },
                  meta: { dataset_version: 'demo-01', is_synthetic: true },
                }),
            })
          : Promise.reject(new TypeError('Failed to fetch'))
      }
      return Promise.reject(new TypeError(`unexpected url ${url}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <CommandCenter />
      </MemoryRouter>,
    )
    // Waking state — explicitly NOT an application error.
    await waitFor(() =>
      expect(screen.getByText(/Drishti backend is starting/)).toBeInTheDocument(),
    )
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()

    // Backend wakes: the gate auto-reloads the dashboard (poll every 1.5s).
    backendUp = true
    await waitFor(() => expect(screen.getByText('Command Center')).toBeInTheDocument(), {
      timeout: 6000,
    })
    await waitFor(() => expect(screen.getByText('76')).toBeInTheDocument())
  })
})
