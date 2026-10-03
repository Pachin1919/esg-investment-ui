import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTalkWalkDocuments, useTalkWalkFirmYears } from '@/core/queries';
import { Card, Empty, ErrorBox, Loading, Select } from '@/shared/ui';
import { color } from '@/shared/charts';
import { ScoredDocumentsTable } from '@/shared/ScoredDocumentsTable';
import { GapBars, PillarLines, SubscoreBars } from './PillarCharts';
import { DictionaryScatter, type DictAxis } from './DictionaryScatter';

const TALK_SUB = [
  'ambition',
  'specificity',
  'forward_looking_share',
  'hedging',
  'promotional_tone',
];
const WALK_SUB = [
  'realised_reductions',
  'capital_deployed',
  'verification',
  'governance',
  'hard_data_consistency',
  'implementation_share',
];

export function TalkWalkPage() {
  const fy = useTalkWalkFirmYears();
  const firmIds = useMemo(
    () => Array.from(new Set((fy.data ?? []).map((r) => r.firm_id))).sort(),
    [fy.data],
  );
  const [firm, setFirm] = useState('');
  const selected = firm || firmIds[0] || '';
  const docs = useTalkWalkDocuments(selected || undefined);
  const [axis, setAxis] = useState<DictAxis>('glossiness');
  const navigate = useNavigate();

  if (fy.isError) return <ErrorBox error={fy.error} />;
  if (fy.isLoading) return <Loading />;
  if (!firmIds.length)
    return (
      <Empty>
        No talk / walk scores yet. Run <code>scripts/score_talkwalk.py --tickers XOM</code> with an
        API key.
      </Empty>
    );

  const years = (fy.data ?? [])
    .filter((r) => r.firm_id === selected)
    .sort((a, b) => a.year - b.year);
  const latest = years[years.length - 1];
  const docRows = (docs.data ?? []).filter((d) => !d.skipped);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Talk vs walk</h1>
          <p className="mt-1 max-w-3xl text-sm text-ink2">
            Talk is what the firm says (ambition, forward-looking share, promotional tone); walk is
            what it demonstrably does (realised reductions, capital, verification, governance,
            hard-data consistency, implementation share). Both on 0–10, reported separately. Gap =
            talk − walk, high = greenwashing risk.
          </p>
        </div>
        <Select
          label="Firm"
          value={selected}
          onChange={setFirm}
          options={firmIds.map((f) => ({ value: f, label: f }))}
        />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <PillarLines years={years} />
        <GapBars years={years} />
      </div>
      {latest && (
        <div className="grid gap-4 lg:grid-cols-2">
          <SubscoreBars
            title={`Talk sub-scores, ${latest.year}`}
            row={latest}
            prefix="talk_"
            keys={TALK_SUB}
            fill={color.s1}
          />
          <SubscoreBars
            title={`Walk sub-scores, ${latest.year}`}
            row={latest}
            prefix="walk_"
            keys={WALK_SUB}
            fill={color.s2}
          />
        </div>
      )}
      <DictionaryScatter docs={docRows} axis={axis} setAxis={setAxis} loading={docs.isLoading} />
      <Card
        title="Documents"
        subtitle="One row per scored filing section. Click a row to open the firm page."
      >
        {docRows.length === 0 ? (
          <Empty>No documents.</Empty>
        ) : (
          <ScoredDocumentsTable
            rows={docRows}
            variant="dictionary"
            onRowClick={(d) => navigate(`/firms/${d.firm_id}`)}
          />
        )}
      </Card>
    </div>
  );
}
