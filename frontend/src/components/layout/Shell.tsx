import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Command Center', end: true },
  { to: '/queue', label: 'Investigation Queue' },
  { to: '/cases', label: 'Cases' },
  { to: '/data', label: 'Data' },
  { to: '/stakeholders', label: 'Stakeholder views' },
  { to: '/validation', label: 'Evidence & Validation' },
  { to: '/system', label: 'System status' },
]

export default function Shell() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Mobile top bar (hidden on desktop) */}
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-ink/70 bg-paper px-4 py-3 lg:hidden">
        <div>
          <p className="font-serif text-[19px] font-semibold leading-none">Drishti</p>
          <p className="mt-1 text-meta text-ink-faint">MPLADS Risk Intelligence</p>
        </div>
        <button
          type="button"
          className="btn px-2.5 py-1.5"
          aria-expanded={menuOpen}
          aria-controls="mobile-nav"
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <span aria-hidden className="flex flex-col gap-[3px]">
            <span className="block h-[1.5px] w-4 bg-current" />
            <span className="block h-[1.5px] w-4 bg-current" />
            <span className="block h-[1.5px] w-4 bg-current" />
          </span>
          <span className="text-[11.5px]">{menuOpen ? 'Close' : 'Menu'}</span>
        </button>
      </div>

      {/* Sidebar: static column on desktop, collapsible panel on mobile */}
      <nav
        id="mobile-nav"
        aria-label="Primary"
        className={`${
          menuOpen ? 'block' : 'hidden'
        } w-full shrink-0 border-b border-ink/70 bg-paper lg:sticky lg:top-0 lg:block lg:h-screen lg:w-52 lg:border-b-0 lg:border-r`}
      >
        <div className="hidden border-b border-ink/70 px-4 py-4 lg:block">
          <p className="font-serif text-[19px] font-semibold leading-none">Drishti</p>
          <p className="mt-1 text-meta text-ink-faint">MPLADS Risk Intelligence</p>
        </div>
        <ul className="space-y-px px-2 py-2 lg:mt-3 lg:py-0">
          {NAV.map((n) => (
            <li key={n.to}>
              <NavLink
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `block px-2 py-1.5 font-plex text-[13px] ${
                    isActive
                      ? 'border-l-2 border-accent bg-accent-soft font-semibold text-accent'
                      : 'border-l-2 border-transparent text-ink-soft hover:bg-accent-soft/50'
                  }`
                }
                onClick={() => setMenuOpen(false)}
              >
                {n.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="hidden border-t border-rule px-4 py-3 text-meta text-ink-faint lg:mt-auto lg:block">
          <p>Decision support only.</p>
          <p>Signals are not findings.</p>
        </div>
      </nav>

      <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
