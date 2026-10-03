import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGreenness } from '@/core/queries';
import type { GreennessRow } from '@/core/api';
import { fmt } from '@/core/format';
import { Card, Empty, ErrorBox, Loading, Select, Table } from '@/shared/ui';
import { Histogram, SectorBars } from './Charts';

const COLS = [
  {
    key: 'id',
    label: 'Ticker',
    render: (r: GreennessRow) => <span className="font-mono text-xs text-accent">{r.firm_id}</span>,
  },
  { key: 'name', label: 'Name', render: (r: GreennessRow) => r.name ?? '' },
  {
    key: 'sector',
    label: 'Sector',
    render: (r: GreennessRow) => <span className="text-xs text-ink2">{r.sector ?? ''}</span>,
  },
  {
    key: 'e',
    label: 'E score',
    align: 'right' as const,
    render: (r: GreennessRow) => fmt.num(r.e_score),
  },
  {
    key: 'w',
    label: 'E weight',
    align: 'right' as const,
    render: (r: GreennessRow) => fmt.num(r.e_weight, 0),
  },
  { key: 'g', label: 'g', align: 'right' as const, render: (r: GreennessRow) => fmt.num(r.g) },
];

export function GreennessPage() {
  const [year, setYear] = useState<number | undefined>();
  const [provider, setProvider] = useState<string | undefined>();
  const q = useGreenness(year, provider);
  const navigate = useNavigate();
  if (q.isError) return <ErrorBox error={q.error} />;
  if (q.isLoading || !q.data) return <Loading />;
  const d = q.data;
  if (!d.firms.length)
    return (
      <Empty>
        No greenness table yet. Run <code>scripts/phase0_replicate.py</code>.
      </Empty>
    );
  const open = (r: GreennessRow) => navigate(`/firms/${r.firm_id}`);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Greenness</h1>
          <p className="mt-1 max-w-3xl text-sm text-ink2">
            g = −(10 − E score) · E weight / 100 (Pástor, Stambaugh & Taylor 2022). 0 is perfectly
            green; brown firms in E-material industries are strongly negative. Provider{' '}
            <code>carbon_proxy</code> derives the score from within-industry scope-1 intensity ranks
            and the weight from sector intensity.
          </p>
        </div>
        <div className="flex gap-3">
          <Select
            label="Provider"
            value={d.provider ?? ''}
            onChange={setProvider}
            options={d.providers.map((p) => ({ value: p, label: p }))}
          />
          <Select
            label="Year"
            value={d.year ?? 0}
            onChange={setYear}
            options={d.years.map((y) => ({ value: y, label: String(y) }))}
          />
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <SectorBars sectors={d.sectors.filter((s) => s.sector)} />
        <Histogram
          values={d.firms.map((f) => f.g)}
          subtitle={`${d.firms.length} firms, ${d.year}, provider ${d.provider}`}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Brownest 15">
          <Table
            rows={d.firms.slice(0, 15)}
            rowKey={(r) => r.firm_id}
            columns={COLS}
            onRowClick={open}
          />
        </Card>
        <Card
          title="Greenest 15"
          subtitle="Ties at g = 0 are firms with no matched GHGRP facilities, treated as cleanest in their sector"
        >
          <Table
            rows={[...d.firms].reverse().slice(0, 15)}
            rowKey={(r) => r.firm_id}
            columns={COLS}
            onRowClick={open}
          />
        </Card>
      </div>
    </div>
  );
}
