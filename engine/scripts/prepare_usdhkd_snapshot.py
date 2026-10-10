"""Add monthly ECB USD/HKD observations to a COPY of an existing FX snapshot.

Download the daily JSON from the URL in ../../docs/fx-snapshot-provenance.json.
Run: python engine/scripts/prepare_usdhkd_snapshot.py daily.json existing.parquet new.parquet
This offline helper refuses to replace existing USDHKD observations or its input file.
"""
import argparse
import json
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('daily', type=Path)
    parser.add_argument('existing', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.existing.resolve():
        parser.error('Choose a new output file; original snapshots are never overwritten.')
    existing = pd.read_parquet(args.existing)
    if existing['pair'].eq('USDHKD').any():
        parser.error('Input already contains USDHKD; create a deliberately versioned update instead.')
    daily = pd.DataFrame(json.loads(args.daily.read_text(encoding='utf-8')))
    if not daily['base'].eq('USD').all() or not daily['quote'].eq('HKD').all():
        parser.error('Expected only USD base and HKD quote observations.')
    daily['date'] = pd.to_datetime(daily['date'], errors='raise')
    daily['month'] = daily['date'].dt.to_period('M')
    daily = daily[(daily['date'] >= '2009-11-01') & (daily['date'] <= '2026-09-30')]
    if daily.empty or not daily['rate'].gt(0).all() or daily['date'].duplicated().any():
        parser.error('Empty, non-positive or duplicate daily rates.')
    monthly = daily.sort_values('date').groupby('month', as_index=False).tail(1).copy()
    monthly['month'] = monthly['month'].astype(str)
    monthly['observation_date'] = monthly['date'].dt.strftime('%Y-%m-%d')
    monthly['pair'] = 'USDHKD'
    monthly['source'] = 'ECB reference rates via Frankfurter (USD/HKD cross), last observation per month'
    merged = pd.concat([existing, monthly[['month', 'pair', 'rate', 'observation_date', 'source']]], ignore_index=True)
    if merged.duplicated(['month', 'pair']).any():
        parser.error('Duplicate pair/month observations.')
    merged.to_parquet(args.output, index=False)
    print(f'Wrote {len(monthly)} USDHKD months to {args.output}')


if __name__ == '__main__':
    main()
