export function LayerDiagram() {
  const box = (x: number, label: string, sub: string, fill: string) => (
    <g key={label}>
      <rect x={x} y={20} width={200} height={64} rx={8} fill={fill} stroke="var(--border)" />
      <text
        x={x + 100}
        y={46}
        textAnchor="middle"
        fontSize={13}
        fontWeight={600}
        fill="var(--text-primary)"
      >
        {label}
      </text>
      <text x={x + 100} y={66} textAnchor="middle" fontSize={11} fill="var(--text-secondary)">
        {sub}
      </text>
    </g>
  );
  const arrow = (x: number) => (
    <path
      key={x}
      d={`M${x} 52 h34 l-8 -6 m8 6 l-8 6`}
      stroke="var(--text-muted)"
      strokeWidth={1.5}
      fill="none"
    />
  );
  const rows = [
    ['carbon (GHGRP, HKEX)', 'shock catalogue', 'tilt / hedge / long-short'],
    ['greenness (PST)', 'firm network', 'factor backtests (FF5 + GMB)'],
    ['talk / walk (LLM agents)', 'diffusion models', 'Fama–MacBeth robustness'],
    ['attention / news', 'I/O pass-through', 'scenario ΔV distributions'],
  ];
  return (
    <svg
      viewBox="0 0 700 220"
      className="w-full max-w-3xl"
      role="img"
      aria-label="Three layers: measurement, shocks and diffusion, investing"
    >
      {box(
        10,
        'A. Measurement',
        'built',
        'color-mix(in srgb, var(--series-1) 14%, var(--surface-1))',
      )}
      {arrow(216)}
      {box(256, 'B. Shocks & diffusion', 'planned', 'var(--page)')}
      {arrow(462)}
      {box(500, 'C. Investing', 'planned', 'var(--page)')}
      {rows.map((r, i) =>
        r.map((t, j) => (
          <text
            key={`${i}${j}`}
            x={[110, 356, 600][j]}
            y={110 + i * 22}
            textAnchor="middle"
            fontSize={11}
            fill="var(--text-secondary)"
          >
            {t}
          </text>
        )),
      )}
    </svg>
  );
}
