import { Link } from 'react-router-dom';
import { useFirms, useGmb, useHealth, useTalkWalkFirmYears } from '@/core/queries';
import { fmt } from '@/core/format';
import { Card, ErrorBox, Loading, StatTile, Table } from '@/shared/ui';
import { Badge } from '@/shared/Layout';

export function OverviewPage() {
  const health = useHealth();
  const firms = useFirms();
  const tw = useTalkWalkFirmYears();
  const gmb = useGmb();
  if (health.isError) return <ErrorBox error={health.error} />;
  if (health.isLoading || firms.isLoading) return <Loading />;

  const f = firms.data ?? [];
  const withEmissions = f.filter((x) => x.has_emissions).length;
  const withTw = new Set((tw.data ?? []).map((x) => x.firm_id));
  const datasets = Object.entries(health.data?.datasets ?? {}).map(([name, d]) => ({ name, ...d }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Measurement layer</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink2">
          What the pipeline has produced so far: carbon data, greenness à la
          Pástor–Stambaugh–Taylor, the green-minus-brown factor, and LLM-scored talk vs walk on SEC
          filings. Everything here is read from <code>outputs/</code> and{' '}
          <code>data/processed/</code>; nothing is computed in the UI.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Firms in universe" value={fmt.int(f.length)} hint="S&P 500 + Hang Seng" />
        <StatTile
          label="Firms with emissions"
          value={fmt.int(withEmissions)}
          hint="EPA GHGRP match or HKEX report"
        />
        <StatTile
          label="Talk / walk firm-years"
          value={fmt.int(tw.data?.length ?? 0)}
          hint={`${withTw.size} firm(s) scored`}
        />
        <StatTile
          label="GMB, value-weighted"
          value={fmt.bps(gmb.data?.summary.gmb?.mean_bps)}
          hint={
            gmb.data?.summary.gmb
              ? `per month, t = ${fmt.num(gmb.data.summary.gmb.t_stat, 1)}`
              : 'not built yet'
          }
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Datasets" subtitle="Availability of each table the dashboard reads">
          <Table
            rows={datasets}
            rowKey={(r) => r.name}
            columns={[
              {
                key: 'name',
                label: 'Table',
                render: (r) => <span className="font-mono text-xs">{r.name}</span>,
              },
              {
                key: 'ok',
                label: '',
                render: (r) =>
                  r.available ? (
                    <Badge>ready</Badge>
                  ) : (
                    <span className="text-xs text-muted">missing</span>
                  ),
              },
              {
                key: 'rows',
                label: 'Rows',
                align: 'right',
                render: (r) => (r.rows === null ? '' : fmt.int(r.rows)),
              },
              {
                key: 'updated',
                label: 'Updated',
                render: (r) => (
                  <span className="text-xs text-ink2">{r.updated?.replace('T', ' ') ?? ''}</span>
                ),
              },
            ]}
          />
        </Card>
        <Card
          title="Scored firms"
          subtitle="Firms with LLM talk / walk scores. Click to open the firm page."
        >
          {withTw.size === 0 ? (
            <p className="text-sm text-ink2">
              No talk / walk scores yet. Run <code>scripts/score_talkwalk.py</code> first.
            </p>
          ) : (
            <ul className="divide-y divide-grid">
              {f
                .filter((x) => withTw.has(x.firm_id))
                .map((x) => (
                  <li key={x.firm_id} className="flex items-center gap-3 py-2">
                    <Link to={`/firms/${x.firm_id}`} className="w-20 font-mono text-xs text-accent">
                      {x.firm_id}
                    </Link>
                    <span className="flex-1">{x.name}</span>
                    <span className="text-xs text-ink2">{x.sector}</span>
                  </li>
                ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
