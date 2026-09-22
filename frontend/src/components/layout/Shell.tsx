import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Command Center', end: true },
  { to: '/queue', label: 'Investigation Queue' },
  { to: '/cases', label: 'Cases' },
  { to: '/data', label: 'Data' },
]

export default function Shell() {
  return (
    <div className="flex min-h-screen">
      <nav className="flex w-52 shrink-0 flex-col border-r border-ink/70 bg-paper" aria-label="Primary">
        <div className="border-b border-ink/70 px-4 py-4">
          <p className="font-serif text-[19px] font-semibold leading-none">Drishti</p>
          <p className="mt-1 text-meta text-ink-faint">MPLADS Risk Intelligence</p>
        </div>
        <ul className="mt-3 space-y-px px-2">
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
              >
                {n.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="mt-auto border-t border-rule px-4 py-3 text-meta text-ink-faint">
          <p>Decision support only.</p>
          <p>Signals are not findings.</p>
        </div>
      </nav>
      <main className="min-w-0 flex-1 px-8 py-6">
        <Outlet />
      </main>
    </div>
  )
}
