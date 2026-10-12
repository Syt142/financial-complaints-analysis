"""Streaming counters. Raw complaint narratives are never written to outputs."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

COLUMNS = (
    'Date received', 'Product', 'Sub-product', 'Issue', 'Sub-issue',
    'Consumer complaint narrative', 'Company public response', 'Company',
    'State', 'ZIP code', 'Tags', 'Submitted via', 'Date sent to company',
    'Company response to consumer', 'Timely response?', 'Complaint ID',
)
CATEGORICAL = ('Product', 'Sub-product', 'Issue', 'Sub-issue', 'Company', 'State',
               'Submitted via', 'Company response to consumer', 'Timely response?')
FINAL_RESPONSES = {'Closed with explanation', 'Closed with monetary relief',
                   'Closed with non-monetary relief'}

class DataError(ValueError):
    """Invalid file structure, not a silently discarded observation."""

class ExactIdTracker:
    """Exact numeric-ID membership in lazily allocated bit blocks.

    A block represents 2**20 numeric IDs and uses 128 KiB. Leading zeros are
    canonicalized, so '001' and '1' identify the same numeric ID. A hard block
    limit fails explicitly rather than returning approximate duplicate counts.
    """
    BITS = 20
    BYTES = 1 << (BITS - 3)

    def __init__(self, max_blocks=1024):
        self.blocks = {}
        self.max_blocks = max_blocks
        self.unique = 0

    def add(self, text):
        if not text or not text.isascii() or not text.isdecimal():
            raise DataError('Complaint ID must contain ASCII digits')
        value = int(text)
        key, offset = value >> self.BITS, value & ((1 << self.BITS) - 1)
        if key not in self.blocks:
            if len(self.blocks) >= self.max_blocks:
                raise DataError('Exact ID tracker memory cap exceeded; increase --max-id-blocks')
            self.blocks[key] = bytearray(self.BYTES)
        block = self.blocks[key]
        byte, bit = offset >> 3, 1 << (offset & 7)
        duplicate = bool(block[byte] & bit)
        block[byte] |= bit
        self.unique += not duplicate
        return duplicate

def parse_timestamp(text):
    if not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace('Z', '+00:00'))
        # Date-only and naive input are explicitly interpreted as UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None

def safe_rate(numerator, denominator):
    return numerator / denominator if denominator else None

def peak_memory_bytes():
    """Peak resident/working-set size when the OS exposes it; not total machine RAM."""
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)] + [
                (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
                    'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            return counters.PeakWorkingSetSize
        return None
    try:
        import resource
        value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value if sys.platform=='darwin' else value*1024
    except (ImportError,AttributeError):
        return None

def analyze_csv(path, *, batch_size=100000, limit=None, max_id_blocks=1024,
                progress=None, max_field_chars=10_000_000):
    """Read logical CSV records once; retain aggregates, never the full table.

    Counts always describe records, including duplicate IDs. Duplicates are
    diagnostics and are not silently removed. Malformed CSV/schema fails fast.
    Blank means exactly an empty string, not arbitrary whitespace or 'NA'.
    """
    if batch_size < 1 or max_id_blocks < 1 or (limit is not None and limit < 1):
        raise ValueError('batch_size, max_id_blocks and an optional limit must be positive')
    path = Path(path)
    stat_before = path.stat()
    started = time.perf_counter()
    missing = Counter({c: 0 for c in COLUMNS})
    frequencies = {c: Counter() for c in CATEGORICAL}
    frequencies.update(year=Counter(), month=Counter())
    dimensions = {
        'year_product': ('year', 'Product'), 'month_product': ('month', 'Product'),
        'year_response': ('year', 'Company response to consumer'),
        'year_timely': ('year', 'Timely response?'),
        'year_narrative': ('year', 'has_narrative'),
        'product_response': ('Product', 'Company response to consumer'),
        'product_narrative': ('Product', 'has_narrative'),
        'company_response': ('Company', 'Company response to consumer'),
        'narrative_response': ('has_narrative', 'Company response to consumer'),
    }
    crosses = {k: Counter() for k in dimensions}
    quality = Counter({k: 0 for k in ['invalid_received', 'invalid_sent',
        'negative_forwarding_timestamp', 'negative_forwarding_calendar_day',
        'missing_id', 'invalid_id', 'duplicate_id_extra_rows']})
    tracker = ExactIdTracker(max_id_blocks)
    lags = Counter()
    n = 0
    earliest = latest = None
    complete = True
    old_limit = csv.field_size_limit(max_field_chars)
    try:
        with path.open('r', encoding='utf-8-sig', newline='', buffering=4*1024*1024) as stream:
            reader = csv.reader(stream, strict=True)
            try:
                header = next(reader)
            except StopIteration:
                raise DataError('Empty file: required CSV header is absent') from None
            if len(header) != len(set(header)):
                raise DataError('Duplicate column names')
            absent = set(COLUMNS) - set(header)
            if absent:
                raise DataError('Missing required columns: ' + ', '.join(sorted(absent)))
            index = {c: header.index(c) for c in COLUMNS}
            slots = [(c, index[c]) for c in COLUMNS]
            cat_slots = [(c, index[c]) for c in CATEGORICAL]
            for row in reader:
                if limit is not None and n >= limit:
                    complete = False
                    break
                if len(row) != len(header):
                    raise DataError(f'Logical record {n+1} has {len(row)} fields; expected {len(header)} (physical line {reader.line_num})')
                n += 1
                for col, i in slots:
                    missing[col] += row[i] == ''
                for col, i in cat_slots:
                    frequencies[col][row[i]] += 1
                received_raw = row[index['Date received']]
                sent_raw = row[index['Date sent to company']]
                received = parse_timestamp(received_raw)
                sent = parse_timestamp(sent_raw)
                quality['invalid_received'] += bool(received_raw) and received is None
                quality['invalid_sent'] += bool(sent_raw) and sent is None
                if received is not None:
                    earliest = received if earliest is None else min(earliest, received)
                    latest = received if latest is None else max(latest, received)
                    year, month = received.strftime('%Y'), received.strftime('%Y-%m')
                else:
                    year = month = '(invalid or missing date)'
                frequencies['year'][year] += 1
                frequencies['month'][month] += 1
                if received is not None and sent is not None:
                    lag = (sent.date() - received.date()).days
                    lags[lag] += 1
                    quality['negative_forwarding_timestamp'] += sent < received
                    quality['negative_forwarding_calendar_day'] += lag < 0
                narrative = 'Yes' if row[index['Consumer complaint narrative']] else 'No'
                derived = {'year': year, 'month': month, 'has_narrative': narrative}
                for name, fields in dimensions.items():
                    key = tuple(derived[field] if field in derived else row[index[field]] for field in fields)
                    crosses[name][key] += 1
                complaint_id = row[index['Complaint ID']]
                if not complaint_id:
                    quality['missing_id'] += 1
                elif not complaint_id.isascii() or not complaint_id.isdecimal():
                    quality['invalid_id'] += 1
                else:
                    quality['duplicate_id_extra_rows'] += tracker.add(complaint_id)
                if progress is not None and n % batch_size == 0:
                    progress({'rows': n, 'elapsed_seconds': round(time.perf_counter()-started, 2)})
    except (csv.Error, UnicodeError) as exc:
        raise DataError(f'CSV decoding/parsing failed after {n} records: {exc}') from exc
    finally:
        csv.field_size_limit(old_limit)
    stat_after = path.stat()
    if (stat_before.st_size, stat_before.st_mtime_ns) != (stat_after.st_size, stat_after.st_mtime_ns):
        raise DataError('Input file changed during analysis; results were not accepted')
    checks = {f'frequency:{k}': sum(v.values()) == n for k, v in frequencies.items()}
    checks.update({f'cross:{k}': sum(v.values()) == n for k, v in crosses.items()})
    checks['id_partition'] = tracker.unique + quality['duplicate_id_extra_rows'] + quality['missing_id'] + quality['invalid_id'] == n
    if not all(checks.values()):
        raise AssertionError('Aggregation reconciliation failed')
    timely = frequencies['Timely response?']
    narrative_count = n - missing['Consumer complaint narrative']
    return {
        'schema_version': 1, 'program_version': '0.1.0',
        'source': {'file_name': path.name, 'bytes': stat_before.st_size,
                   'mtime_ns': stat_before.st_mtime_ns, 'input_unchanged_size_mtime': True},
        'run': {'complete_file': complete, 'row_limit': limit, 'batch_size': batch_size,
                'python': platform.python_version(), 'platform': platform.platform(),
                'elapsed_seconds': round(time.perf_counter()-started, 3),
                'peak_process_memory_bytes': peak_memory_bytes(),
                'id_tracker_bytes': len(tracker.blocks)*tracker.BYTES,
                'method': 'stdlib CSV logical-record streaming with exact numeric-ID bit blocks'},
        'rows': n, 'columns': header,
        'min_received': earliest.isoformat() if earliest else None,
        'max_received': latest.isoformat() if latest else None,
        'missing': dict(missing), 'quality': dict(quality, unique_numeric_ids=tracker.unique),
        'frequencies': {k: dict(v.most_common()) for k, v in frequencies.items()},
        'cross_dimensions': dimensions,
        'cross': {k: [{'keys': list(keys), 'n': value} for keys, value in v.most_common()] for k, v in crosses.items()},
        'forwarding_calendar_days': {str(k): v for k, v in sorted(lags.items())},
        'metrics': {
            'timely_response': {'numerator': timely.get('Yes', 0),
                'denominator': timely.get('Yes', 0)+timely.get('No', 0),
                'rate': safe_rate(timely.get('Yes', 0), timely.get('Yes', 0)+timely.get('No', 0)),
                'definition': 'Yes / (Yes + No); not a resolution rate'},
            'narrative_coverage': {'numerator': narrative_count, 'denominator': n,
                'rate': safe_rate(narrative_count, n), 'definition': 'nonempty narrative / all records'},
        },
        'checks': checks,
        'definitions': {'missing': 'exact empty string only; literal NA and whitespace are retained',
            'record_unit': 'complaint record, not unique consumer',
            'duplicates': 'numeric ID duplicates diagnosed, rows retained in aggregate counts',
            'time': 'UTC; date-only and naive timestamps are interpreted as UTC',
            'lag': 'calendar days from receipt to forwarding; not company response duration',
            'category': 'original labels; no historical taxonomy harmonization',
            'narrative': 'only presence is aggregated; raw text is not exported'},
    }

def export_results(result, outdir):
    from .reporting import make_markdown
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir/'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    (outdir/'analysis.md').write_text(make_markdown(result), encoding='utf-8')
    with (outdir/'frequencies.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['dimension', 'value', 'count', 'denominator', 'share'])
        for dimension, values in result['frequencies'].items():
            for value, n in values.items():
                writer.writerow([dimension, value, n, result['rows'], safe_rate(n, result['rows'])])
    with (outdir/'cross_tables.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['table', 'key_1', 'key_2', 'count'])
        for table, rows in result['cross'].items():
            writer.writerows([table, *row['keys'], row['n']] for row in rows)
    with (outdir/'quality.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['type', 'metric', 'count'])
        writer.writerows(['missing', c, n] for c,n in result['missing'].items())
        writer.writerows(['quality', c, n] for c,n in result['quality'].items())
    manifest = {}
    for name in ['summary.json', 'frequencies.csv', 'cross_tables.csv', 'quality.csv', 'analysis.md']:
        manifest[name] = hashlib.sha256((outdir/name).read_bytes()).hexdigest()
    (outdir/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return outdir/'summary.json'
