import { useParams } from 'react-router-dom';
import { useFirm } from '@/core/queries';
import { fmt } from '@/core/format';
import { Card, Empty, ErrorBox, Loading, StatTile } from '@/shared/ui';
import { Badge } from '@/shared/Layout';
import { color } from '@/shared/charts';
import { ScoredDocumentsTable } from '@/shared/ScoredDocumentsTable';
import { SeriesChart } from './SeriesChart';

export function FirmPage() {
  const { firmId } = useParams();
  const q = useFirm(firmId);
  if (q.isError) return <ErrorBox error={q.error} />;
  if (q.isLoading || !q.data) return <Loading />;
  const f = q.data;
  const em = f.emissions.filter((e) => e.matched);
  const gr = f.greenness.filter((g) => g.provider === (f.greenness[0]?.provider ?? 'carbon_proxy'));
  const latestEm = em[em.length - 1];
  const latestTw = f.talkwalk[f.talkwalk.length - 1];
  const latestG = gr[gr.length - 1];
  const one = (key: string, name: string) => [{ key, name, swatch: color.s1 }];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline gap-3">
        <h1 className="text-xl font-semibold">{f.name}</h1>
        <span className="font-mono text-sm text-ink2">{f.firm_id}</span>
        <span className="text-sm text-ink2">
          {f.sector}
          {f.industry ? ` · ${f.industry}` : ''}
        </span>
        {f.has_emissions && <Badge>emissions</Badge>}
        {f.has_talkwalk && <Badge>talk/walk</Badge>}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile
          label={`Scope 1${latestEm ? `, ${latestEm.year}` : ''}`}
          value={latestEm ? `${fmt.compact(latestEm.scope1)} t` : '–'}
          hint={latestEm?.source}
        />
        <StatTile
          label="Intensity"
          value={latestEm?.intensity ? fmt.num(latestEm.intensity, 1) : '–'}
          hint="tCO2e per USD m revenue"
        />
        <StatTile
          label={`Greenness g${latestG ? `, ${latestG.year}` : ''}`}
          value={fmt.num(latestG?.g)}
          hint={
            latestG
              ? `E ${fmt.num(latestG.e_score, 1)} · weight ${fmt.num(latestG.e_weight, 0)}`
              : 'no score'
          }
        />
        <StatTile
          label={`Talk / walk${latestTw ? `, ${latestTw.year}` : ''}`}
          value={latestTw ? `${fmt.num(latestTw.talk, 1)} / ${fmt.num(latestTw.walk, 1)}` : '–'}
          hint={latestTw ? `gap ${fmt.num(latestTw.gap, 1)}` : 'not scored'}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Scope 1 emissions" subtitle="tCO2e per year, matched facilities">
          {em.length ? (
            <SeriesChart
              data={em}
              x="year"
              series={one('scope1', 'Scope 1')}
              format={(v) => `${fmt.compact(v)} t`}
              tickFormat={fmt.compact}
            />
          ) : (
            <Empty>No matched emissions.</Empty>
          )}
        </Card>
        <Card title="Carbon intensity" subtitle="Scope 1 / revenue (tCO2e per USD million)">
          {em.some((e) => e.intensity) ? (
            <SeriesChart
              data={em}
              x="year"
              series={one('intensity', 'Intensity')}
              format={(v) => fmt.num(v, 1)}
              tickFormat={(v) => fmt.num(v, 0)}
            />
          ) : (
            <Empty>No revenue data to scale by.</Empty>
          )}
        </Card>
        <Card title="Greenness g" subtitle={gr[0] ? `provider ${gr[0].provider}` : ''}>
          {gr.length ? (
            <SeriesChart
              data={gr}
              x="year"
              series={one('g', 'g')}
              format={(v) => fmt.num(v)}
              tickFormat={(v) => fmt.num(v, 1)}
              domain={[-5, 0]}
            />
          ) : (
            <Empty>No greenness score.</Empty>
          )}
        </Card>
        <Card title="Talk and walk" subtitle="LLM rubric, firm-year">
          {f.talkwalk.length ? (
            <SeriesChart
              data={f.talkwalk}
              x="year"
              series={[
                { key: 'talk', name: 'Talk', swatch: color.s1 },
                { key: 'walk', name: 'Walk', swatch: color.s2 },
              ]}
              format={(v) => fmt.num(v)}
              tickFormat={(v) => String(v)}
              domain={[0, 10]}
            />
          ) : (
            <Empty>
              Not scored. Run <code>scripts/score_talkwalk.py --tickers {f.firm_id}</code>.
            </Empty>
          )}
        </Card>
      </div>
      {f.documents.length > 0 && (
        <Card title="Scored documents">
          <ScoredDocumentsTable rows={f.documents} variant="commitments" />
        </Card>
      )}
    </div>
  );
}
