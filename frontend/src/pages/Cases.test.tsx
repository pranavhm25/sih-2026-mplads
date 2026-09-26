import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { CaseDetail } from './Cases'
import type { Case } from '../types/types'

const baseCase: Case = {
  id: 'case-1',
  case_number: 'DRSHY-C-1001',
  project_id: 'p-1',
  priority: 'HIGH',
  status: 'FIELD_VERIFICATION',
  assigned_officer_id: 'o-1',
  opened_at: '2026-09-26T10:00:00Z',
  updated_at: '2026-09-26T10:00:00Z',
  closed_at: null,
  resolution_type: null,
  resolution_reason: null,
  resolution_summary: null,
  project: {
    id: 'p-1',
    work_id: 'MPL-10281',
    description: 'Anganwadi building works',
    district: 'Bengaluru Rural',
    state: 'Karnataka',
    category: 'Education',
    status: 'ONGOING',
    sanctioned_cost: 1000000,
    latitude: null,
    longitude: null,
    priority: null,
    primary_signals: ['DUPLICATE'],
    case_status: 'FIELD_VERIFICATION',
  },
  assigned_officer: {
    id: 'o-1',
    name: 'Officer A. Sharma',
    role: 'INVESTIGATOR',
    email: 'sharma@drishti.demo',
    district: null,
    is_active: true,
  },
  events: [],
  notes: [],
  evidence: [],
}

function mockFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(String(input), init)),
  )
}

function renderCase() {
  return render(
    <MemoryRouter initialEntries={['/cases/case-1']}>
      <Routes>
        <Route path="/cases/:id" element={<CaseDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CaseDetail outcome UI (AI FLAG ≠ FRAUD)', () => {
  it('shows the AI-flag disclaimer banner', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch((url) => {
        if (url.includes('/api/v1/cases/case-1')) {
          return Response.json({ data: baseCase, meta: {} })
        }
        if (url.includes('/api/v1/officers')) {
          return Response.json({ data: [{ id: 'o-1', name: 'Officer A. Sharma', role: 'INVESTIGATOR' }], meta: {} })
        }
        return Response.json({ data: [], meta: {} })
      }),
    )
    renderCase()
    await waitFor(() =>
      expect(
        screen.getByText(/AI-generated risk flags require human verification/),
      ).toBeInTheDocument(),
    )
  })

  it('offers the neutral not-substantiated close action and requires reason + explanation', async () => {
    const updateSpy = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/api/v1/cases/case-1')) {
        if (init?.method === 'PATCH' && init.body) {
          const payload = JSON.parse(String(init.body))
          return Response.json({ data: { ...baseCase, ...payload }, meta: {} })
        }
        return Response.json({ data: baseCase, meta: {} })
      }
      if (url.includes('/officers')) {
        return Response.json({ data: [{ id: 'o-1', name: 'Officer A. Sharma', role: 'INVESTIGATOR', email: 'sharma@drishti.demo', district: null, is_active: true }], meta: {} })
      }
      return Response.json({ data: [], meta: {} })
    })
    vi.stubGlobal('fetch', updateSpy)
    const user = userEvent.setup()

    renderCase()
    const closeBtn = await screen.findByRole('button', { name: /not substantiated \(close case\)/i })
    await user.click(closeBtn)

    // Neutral outcome form appears; submit is disabled until reason + text.
    const reasonSelect = await screen.findByLabelText(/Reason category/i)
    const explanation = screen.getByLabelText(/Short explanation/i)
    const submit = screen.getByRole('button', { name: /Record outcome/i })
    expect(submit).toBeDisabled()

    await user.selectOptions(reasonSelect, 'FALSE_DUPLICATE_CANDIDATE')
    await user.type(explanation, 'Documents verified; separate sanctioned works.')
    expect(submit).toBeEnabled()

    await user.click(submit)
    await waitFor(() => {
      const call = updateSpy.mock.calls.find(([u, i]) =>
        String(u).includes('/api/v1/cases/case-1') && i?.method === 'PATCH' && !!i?.body
          ? String(JSON.parse(String(i.body)).status) === 'CLOSED'
          : false,
      )
      if (!call) throw new Error('no CLOSED patch recorded')
      const body = JSON.parse(String(call[1]?.body))
      expect(body.status).toBe('CLOSED')
      expect(body.resolution_type).toBe('NOT_SUBSTANTIATED')
      expect(body.resolution_reason).toBe('FALSE_DUPLICATE_CANDIDATE')
    })
  })

  it('shows the closed outcome and reason on a cleared case', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch((url) => {
        if (url.includes('/api/v1/cases/case-1')) {
          return Response.json({
            data: {
              ...baseCase,
              status: 'CLOSED',
              resolution_type: 'NOT_SUBSTANTIATED',
              resolution_reason: 'FALSE_DUPLICATE_CANDIDATE',
              resolution_summary: 'Verified with the district office.',
              closed_at: '2026-09-26T11:00:00Z',
            },
            meta: {},
          })
        }
        if (url.includes('/api/v1/officers')) {
          return Response.json({ data: [{ id: 'o-1', name: 'Officer A. Sharma', role: 'INVESTIGATOR' }], meta: {} })
        }
        return Response.json({ data: [], meta: {} })
      }),
    )
    renderCase()
    await waitFor(() => expect(screen.getByText(/Closed — not substantiated/)).toBeInTheDocument())
    expect(screen.getByText(/Reason: Separate works \(duplicate flag not upheld\)/)).toBeInTheDocument()
  })
})
