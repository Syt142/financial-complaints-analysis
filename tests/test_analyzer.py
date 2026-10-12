import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from complaints_analyzer.core import COLUMNS, DataError, ExactIdTracker, analyze_csv, export_results, safe_rate

def record(**updates):
    row = {c: '' for c in COLUMNS}
    row.update({'Date received': '2024-01-01T10:00:00Z', 'Product': 'Checking or savings account',
        'Issue': 'Managing an account', 'Company': 'SYNTHETIC BANK', 'Submitted via': 'Web',
        'Date sent to company': '2024-01-01T11:00:00Z', 'Company response to consumer': 'Closed with explanation',
        'Timely response?': 'Yes', 'Complaint ID': '1'})
    row.update(updates)
    return row

class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, rows, columns=COLUMNS):
        path = self.root/'input.csv'
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_manual_counts_and_reconciliation(self):
        path = self.source([record(), record(**{'Complaint ID':'2','Product':'Mortgage','Timely response?':'No'})])
        r = analyze_csv(path)
        self.assertEqual(r['rows'], 2)
        self.assertEqual(r['frequencies']['Product'], {'Checking or savings account':1,'Mortgage':1})
        self.assertEqual(r['metrics']['timely_response']['rate'], .5)
        self.assertTrue(all(r['checks'].values()))

    def test_quoted_comma_and_multiline_are_one_record(self):
        r = analyze_csv(self.source([record(**{'Company':'BANK, TEST','Consumer complaint narrative':'Line one, detail\nLine two'})]))
        self.assertEqual(r['rows'], 1)
        self.assertEqual(r['frequencies']['Company']['BANK, TEST'], 1)
        self.assertEqual(r['metrics']['narrative_coverage']['rate'], 1)

    def test_empty_value_is_not_literal_na_or_zero(self):
        r = analyze_csv(self.source([record(**{'State':''}),record(**{'Complaint ID':'2','State':'NA'}),record(**{'Complaint ID':'3','State':'0'})]))
        self.assertEqual(r['missing']['State'], 1)
        self.assertEqual(len(r['frequencies']['State']), 3)

    def test_reordered_header_is_supported(self):
        r = analyze_csv(self.source([record()], tuple(reversed(COLUMNS))))
        self.assertEqual(r['rows'],1)
        self.assertEqual(r['quality']['unique_numeric_ids'],1)

    def test_missing_required_column_fails(self):
        with self.assertRaises(DataError):
            analyze_csv(self.source([record()], COLUMNS[:-1]))

    def test_duplicate_header_fails(self):
        p=self.root/'bad.csv'
        p.write_text(','.join(COLUMNS+('Company',))+'\n',encoding='utf-8')
        with self.assertRaises(DataError): analyze_csv(p)

    def test_empty_file_and_header_only_are_distinguished(self):
        p=self.root/'empty.csv';p.write_text('',encoding='utf-8')
        with self.assertRaises(DataError): analyze_csv(p)
        r=analyze_csv(self.source([]))
        self.assertEqual(r['rows'],0)
        self.assertIsNone(r['metrics']['timely_response']['rate'])
        self.assertIsNone(r['min_received'])

    def test_short_record_fails_instead_of_silent_fill(self):
        p=self.source([])
        with p.open('a',encoding='utf-8') as f:f.write('only,two\n')
        with self.assertRaises(DataError):analyze_csv(p)

    def test_unclosed_quoted_record_fails(self):
        p=self.source([])
        with p.open('a',encoding='utf-8') as f:f.write('"unclosed\n')
        with self.assertRaises(DataError):analyze_csv(p)

    def test_invalid_date_is_reported_and_not_dropped(self):
        r=analyze_csv(self.source([record(**{'Date received':'2024-02-30'})]))
        self.assertEqual(r['quality']['invalid_received'],1)
        self.assertEqual(r['rows'],1)
        self.assertIsNone(r['min_received'])

    def test_timezone_uses_utc_year(self):
        r=analyze_csv(self.source([record(**{'Date received':'2025-01-01T00:30:00+02:00'})]))
        self.assertEqual(r['frequencies']['year'],{'2024':1})

    def test_negative_forwarding_and_same_day_order(self):
        r=analyze_csv(self.source([record(**{'Date sent to company':'2024-01-01T09:00:00Z'}),record(**{'Complaint ID':'2','Date sent to company':'2023-12-31T10:00:00Z'})]))
        self.assertEqual(r['quality']['negative_forwarding_timestamp'],2)
        self.assertEqual(r['quality']['negative_forwarding_calendar_day'],1)

    def test_duplicate_numeric_id_across_progress_batches(self):
        r=analyze_csv(self.source([record(),record(**{'Complaint ID':'2'}),record(**{'Complaint ID':'001'})]),batch_size=1)
        self.assertEqual(r['quality']['unique_numeric_ids'],2)
        self.assertEqual(r['quality']['duplicate_id_extra_rows'],1)
        self.assertEqual(r['rows'],3)  # diagnostic, not automatic deletion

    def test_missing_invalid_and_zero_ids(self):
        r=analyze_csv(self.source([record(**{'Complaint ID':''}),record(**{'Complaint ID':'abc'}),record(**{'Complaint ID':'0'})]))
        self.assertEqual(r['quality']['missing_id'],1)
        self.assertEqual(r['quality']['invalid_id'],1)
        self.assertEqual(r['quality']['unique_numeric_ids'],1)

    def test_tracker_cap_is_explicit(self):
        tracker=ExactIdTracker(max_blocks=1)
        tracker.add('0')
        with self.assertRaises(DataError):tracker.add(str(1<<20))

    def test_unknown_timeliness_is_not_in_rate_denominator(self):
        r=analyze_csv(self.source([record(),record(**{'Complaint ID':'2','Timely response?':'Unknown'})]))
        self.assertEqual(r['metrics']['timely_response']['denominator'],1)
        self.assertEqual(r['metrics']['timely_response']['rate'],1)

    def test_limit_is_labeled_and_exact_eof_is_complete(self):
        p=self.source([record(),record(**{'Complaint ID':'2'})])
        self.assertFalse(analyze_csv(p,limit=1)['run']['complete_file'])
        self.assertTrue(analyze_csv(p,limit=2)['run']['complete_file'])

    def test_export_privacy_input_integrity_and_checksums(self):
        p=self.source([record(**{'Consumer complaint narrative':'PRIVATE_SENTINEL_TEXT'})])
        before=p.read_bytes();out=self.root/'out'
        export_results(analyze_csv(p),out)
        self.assertEqual(p.read_bytes(),before)
        self.assertNotIn('PRIVATE_SENTINEL_TEXT',(out/'summary.json').read_text(encoding='utf-8'))
        hashes=json.loads((out/'manifest.json').read_text())
        for name,expected in hashes.items():
            self.assertEqual(hashlib.sha256((out/name).read_bytes()).hexdigest(),expected)

    def test_cli_end_to_end(self):
        p=self.source([record()]);out=self.root/'cli'
        proc=subprocess.run([sys.executable,'-m','complaints_analyzer',str(p),'--outdir',str(out),'--quiet'],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(json.loads((out/'summary.json').read_text())['rows'],1)

    def test_cli_rejects_overwriting_input(self):
        p=self.source([record()]);renamed=self.root/'frequencies.csv';p.rename(renamed)
        before=renamed.read_bytes()
        proc=subprocess.run([sys.executable,'-m','complaints_analyzer',str(renamed),'--outdir',str(self.root)],capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertEqual(renamed.read_bytes(),before)

if __name__=='__main__':unittest.main()
