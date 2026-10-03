export const fmt = {
  num: (v: number | null | undefined, d = 2) =>
    v === null || v === undefined || Number.isNaN(v)
      ? '–'
      : v.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d }),
  int: (v: number | null | undefined) =>
    v === null || v === undefined || Number.isNaN(v) ? '–' : Math.round(v).toLocaleString('en-US'),
  pct: (v: number | null | undefined, d = 1) =>
    v === null || v === undefined || Number.isNaN(v) ? '–' : `${(v * 100).toFixed(d)} %`,
  bps: (v: number | null | undefined) =>
    v === null || v === undefined ? '–' : `${v.toFixed(0)} bps`,
  compact: (v: number | null | undefined) =>
    v === null || v === undefined || Number.isNaN(v)
      ? '–'
      : Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(v),
};
