import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useState, type ReactNode } from 'react';
import { Search } from 'lucide-react';
import clsx from 'clsx';
import { api, type Firm } from '@/core/api';

const links = [
  { to: '/', label: 'Overview' },
  { to: '/talkwalk', label: 'Talk vs walk' },
  { to: '/greenness', label: 'Greenness' },
  { to: '/gmb', label: 'GMB factor' },
  { to: '/method', label: 'How it works' },
  { to: '/pipeline', label: 'Pipeline' },
];

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <NavLink to="/" className="text-base font-semibold tracking-tight">
            ESG Exposure Engine
          </NavLink>
          <nav className="flex gap-1">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.to === '/'}
                className={({ isActive }) =>
                  clsx(
                    'rounded-md px-3 py-1.5 text-sm',
                    isActive ? 'bg-accent/10 font-medium text-ink' : 'text-ink2 hover:text-ink',
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto">
            <FirmSearch />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </div>
  );
}

function FirmSearch() {
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Firm[]>([]);
  const navigate = useNavigate();
  useEffect(() => {
    if (q.trim().length < 1) return setHits([]);
    const t = setTimeout(
      () =>
        api
          .search(q)
          .then(setHits)
          .catch(() => setHits([])),
      150,
    );
    return () => clearTimeout(t);
  }, [q]);
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-2 top-2 h-4 w-4 text-muted" />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Find a firm (ticker or name)"
        className="w-64 rounded-md border border-line bg-surface py-1.5 pl-8 pr-2 text-sm outline-none focus:border-accent"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && hits[0]) {
            navigate(`/firms/${hits[0].firm_id}`);
            setQ('');
          }
        }}
      />
      {hits.length > 0 && (
        <ul className="absolute right-0 mt-1 w-80 overflow-hidden rounded-md border border-line bg-surface shadow-lg">
          {hits.slice(0, 8).map((h) => (
            <li key={h.firm_id}>
              <button
                className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-accent/10"
                onClick={() => {
                  navigate(`/firms/${h.firm_id}`);
                  setQ('');
                }}
              >
                <span className="w-16 font-mono text-xs text-ink2">{h.firm_id}</span>
                <span className="flex-1 truncate">{h.name}</span>
                {h.has_talkwalk && <Badge>talk/walk</Badge>}
                {h.has_emissions && <Badge>emissions</Badge>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="rounded border border-line px-1.5 py-0.5 text-[11px] text-ink2">
      {children}
    </span>
  );
}
