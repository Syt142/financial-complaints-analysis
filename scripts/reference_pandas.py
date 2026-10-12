import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('input', type=Path)
parser.add_argument('--outdir', type=Path, required=True)
args = parser.parse_args()
SOURCE = args.input
WORK = args.outdir
WORK.mkdir(exist_ok=True, parents=True)
start = time.perf_counter()
counts = {}
cross = {}
missing = Counter()
quality = Counter()
lag_days = Counter()
narrative_lengths = Counter()
id_arrays = []
total = 0
min_date = None
max_date = None
columns = None
single = ['Product', 'Sub-product', 'Issue', 'Sub-issue', 'Company public response', 'Company', 'State', 'Tags', 'Submitted via', 'Company response to consumer', 'Timely response?']
group_specs = {
    'year_product': ['year', 'Product'],
    'month_product': ['month', 'Product'],
    'year_issue': ['year', 'Issue'],
    'year_company': ['year', 'Company'],
    'year_response': ['year', 'Company response to consumer'],
    'year_timely': ['year', 'Timely response?'],
    'year_channel': ['year', 'Submitted via'],
    'year_narrative': ['year', 'has_narrative'],
    'product_issue': ['Product', 'Issue'],
    'product_response': ['Product', 'Company response to consumer'],
    'product_timely': ['Product', 'Timely response?'],
    'company_response': ['Company', 'Company response to consumer'],
    'company_timely': ['Company', 'Timely response?'],
    'issue_response': ['Issue', 'Company response to consumer'],
    'issue_timely': ['Issue', 'Timely response?'],
    'product_narrative': ['Product', 'has_narrative'],
}
for chunk_no, frame in enumerate(pd.read_csv(SOURCE, dtype=str, keep_default_na=False, encoding='utf-8-sig', chunksize=100_000, on_bad_lines='error'), 1):
    if columns is None:
        columns = list(frame.columns)
    total += len(frame)
    for col in columns:
        missing[col] += int(frame[col].eq('').sum())
    for col in single:
        counts.setdefault(col, Counter()).update(frame[col].value_counts(dropna=False).to_dict())

    received = pd.to_datetime(frame['Date received'], format='ISO8601', utc=True, errors='coerce')
    sent = pd.to_datetime(frame['Date sent to company'], format='ISO8601', utc=True, errors='coerce')
    quality['invalid_received'] += int((received.isna() & frame['Date received'].ne('')).sum())
    quality['invalid_sent'] += int((sent.isna() & frame['Date sent to company'].ne('')).sum())
    if received.notna().any():
        cmin, cmax = received.min().isoformat(), received.max().isoformat()
        min_date = cmin if min_date is None else min(min_date, cmin)
        max_date = cmax if max_date is None else max(max_date, cmax)
    frame['day'] = received.dt.strftime('%Y-%m-%d').fillna('INVALID')
    frame['month'] = frame['day'].str[:7]
    frame['year'] = frame['day'].str[:4]
    frame['has_narrative'] = np.where(frame['Consumer complaint narrative'].ne(''), 'Yes', 'No')
    for col in ['day', 'month', 'year']:
        counts.setdefault(col, Counter()).update(frame[col].value_counts(dropna=False).to_dict())
    for name, keys in group_specs.items():
        cross.setdefault(name, Counter()).update(frame.groupby(keys, sort=False, dropna=False).size().to_dict())

    calendar_days = (sent.dt.normalize() - received.dt.normalize()).dt.days
    quality['sent_before_received_timestamp'] += int(((sent - received).dt.total_seconds() < 0).sum())
    quality['sent_before_received_calendar_day'] += int(calendar_days.lt(0).sum())
    lag_days.update({int(k): int(v) for k, v in calendar_days.value_counts().items()})
    lengths = frame['Consumer complaint narrative'].str.len()
    narrative_lengths.update({int(k): int(v) for k, v in lengths[lengths.gt(0)].value_counts().items()})

    numeric = frame['Complaint ID'].str.fullmatch(r'\d+')
    quality['nonnumeric_nonblank_ids'] += int((~numeric & frame['Complaint ID'].ne('')).sum())
    id_arrays.append(frame.loc[numeric, 'Complaint ID'].astype('int64').to_numpy())
    progress = {'rows': total, 'chunks': chunk_no, 'elapsed_seconds': round(time.perf_counter() - start, 1), 'min_received': min_date, 'max_received': max_date}
    (WORK / 'profile_progress.json').write_text(json.dumps(progress), encoding='utf-8')
    if chunk_no % 5 == 0:
        print(json.dumps(progress), flush=True)

ids = np.concatenate(id_arrays)
del id_arrays
unique, id_freqs = np.unique(ids, return_counts=True)
quality['unique_numeric_ids'] = int(len(unique))
quality['duplicate_id_extra_rows'] = int((id_freqs - 1).sum())
quality['ids_appearing_more_than_once'] = int((id_freqs > 1).sum())
quality['min_id'] = int(ids.min())
quality['max_id'] = int(ids.max())

checks = {}
for name, counter in counts.items():
    checks['total_' + name] = sum(counter.values()) == total
for name, counter in cross.items():
    checks['total_' + name] = sum(counter.values()) == total
checks['date_partition'] = sum(lag_days.values()) + missing['Date received'] + missing['Date sent to company'] + quality['invalid_received'] + quality['invalid_sent'] == total if not (missing['Date received'] or quality['invalid_received']) else None
if not all(v for v in checks.values() if v is not None):
    raise RuntimeError(checks)

result = {
    'source': str(SOURCE), 'source_bytes': SOURCE.stat().st_size,
    'total_rows': total, 'columns': columns, 'min_received': min_date, 'max_received': max_date,
    'missing': dict(missing), 'quality': dict(quality), 'checks': checks,
    'counts': {name: dict(counter.most_common()) for name, counter in counts.items()},
    'cross': {name: [{'keys': list(keys), 'n': int(n)} for keys, n in counter.most_common()] for name, counter in cross.items()},
    'forwarding_calendar_days': {str(k): int(v) for k, v in sorted(lag_days.items())},
    'narrative_characters': {str(k): int(v) for k, v in sorted(narrative_lengths.items())},
    'elapsed_seconds': round(time.perf_counter() - start, 1),
}
(WORK / 'complaints_profile.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ['total_rows', 'min_received', 'max_received', 'missing', 'quality', 'elapsed_seconds']}, ensure_ascii=False), flush=True)
print('PROFILE_COMPLETE', flush=True)
