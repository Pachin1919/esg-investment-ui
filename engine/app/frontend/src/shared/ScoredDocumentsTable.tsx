import type { TalkWalkDocument } from '@/core/api';
import { fmt } from '@/core/format';
import { Table } from './ui';

type Col = {
  key: string;
  label: string;
  render: (d: TalkWalkDocument) => React.ReactNode;
  align?: 'left' | 'right';
  width?: string;
};

const BASE: Col[] = [
  { key: 'form', label: 'Form', render: (d) => d.form },
  {
    key: 'section',
    label: 'Section',
    render: (d) => <span className="font-mono text-xs">{d.section}</span>,
  },
  { key: 'period', label: 'Period', render: (d) => d.period ?? d.filing_date },
  { key: 'talk', label: 'Talk', align: 'right', render: (d) => fmt.num(d.talk) },
  { key: 'walk', label: 'Walk', align: 'right', render: (d) => fmt.num(d.walk) },
  { key: 'gap', label: 'Gap', align: 'right', render: (d) => fmt.num(d.gap) },
];
const DICT: Col[] = [
  {
    key: 'rel',
    label: 'Climate rel.',
    align: 'right',
    render: (d) => fmt.num(d.climate_relevance, 1),
  },
  {
    key: 'gloss',
    label: 'Glossiness',
    align: 'right',
    render: (d) => fmt.num(d.glossiness ?? null),
  },
  { key: 'sent', label: 'Env. sentiment', align: 'right', render: (d) => fmt.num(d.env_sentiment) },
  {
    key: 'sim',
    label: 'Climate sim.',
    align: 'right',
    render: (d) => fmt.num(d.climate_similarity, 3),
  },
];
const COMMIT: Col = {
  key: 'q',
  label: 'Commitments (quantified)',
  align: 'right',
  render: (d) => `${d.n_commitments ?? 0} (${d.n_quantified ?? 0})`,
};
const SUMMARY: Col = {
  key: 'summary',
  label: 'Summary',
  width: '36%',
  render: (d) => <span className="text-xs text-ink2">{d.summary}</span>,
};

export function ScoredDocumentsTable({
  rows,
  variant,
  onRowClick,
}: {
  rows: TalkWalkDocument[];
  variant: 'dictionary' | 'commitments';
  onRowClick?: (d: TalkWalkDocument) => void;
}) {
  const columns =
    variant === 'dictionary'
      ? [...BASE.slice(0, 3), DICT[0], ...BASE.slice(3), ...DICT.slice(1), SUMMARY]
      : [...BASE, COMMIT, SUMMARY];
  return (
    <Table
      rows={rows.filter((d) => !d.skipped)}
      rowKey={(d) => `${d.accession}-${d.section}`}
      columns={columns}
      onRowClick={onRowClick}
    />
  );
}
