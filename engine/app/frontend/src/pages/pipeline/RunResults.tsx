import type { RunDetail } from '@/core/api';
import { fmt } from '@/core/format';
import { Card, Table } from '@/shared/ui';

export function RunResults({ run }: { run: RunDetail }) {
  const fy = run.results?.firm_years ?? [];
  const memos = run.results?.memos ?? [];
  return (
    <>
      {fy.length > 0 && (
        <Card title="Result: firm-years" subtitle={`Written to ${run.results.dir}`}>
          <Table
            rows={fy}
            rowKey={(r) => `${r.firm_id}-${r.year}`}
            columns={[
              {
                key: 'f',
                label: 'Firm',
                render: (r) => <span className="font-mono text-xs">{r.firm_id}</span>,
              },
              { key: 'y', label: 'Year', render: (r) => String(r.year) },
              { key: 't', label: 'Talk', align: 'right', render: (r) => fmt.num(r.talk) },
              { key: 'w', label: 'Walk', align: 'right', render: (r) => fmt.num(r.walk) },
              { key: 'g', label: 'Gap', align: 'right', render: (r) => fmt.num(r.gap) },
              { key: 'n', label: 'Docs', align: 'right', render: (r) => String(r.n_docs) },
            ]}
          />
        </Card>
      )}
      {memos.length > 0 && (
        <Card title="Reviewer memos" subtitle="One per firm-year from the reviewer agent">
          <ul className="space-y-2">
            {memos.map((m) => (
              <li
                key={`${m.firm_id}-${m.year}`}
                className="rounded-md border border-line p-3 text-sm"
              >
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-xs">{m.firm_id}</span>
                  <span className="font-medium">{m.year}</span>
                  <span className="text-xs text-muted">{m.model}</span>
                </div>
                <p className="mt-1 text-ink2">{m.memo}</p>
                <ul className="mt-1 flex flex-wrap gap-1">
                  {m.flags.map((f) => (
                    <li
                      key={f}
                      className="rounded border border-line px-1.5 py-0.5 text-[11px] text-ink2"
                    >
                      {f}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
