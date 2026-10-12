"""Compare a new analyzer result with saved independent aggregate controls."""
import argparse
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('summary',type=Path)
parser.add_argument('--reference',type=Path,default=Path('evidence/reference_control.json'))
parser.add_argument('--output',type=Path,default=Path('results/reference_comparison.json'))
args=parser.parse_args()
actual=json.loads(args.summary.read_text(encoding='utf-8'))
reference=json.loads(args.reference.read_text(encoding='utf-8'))
checks={'rows':actual['rows']==reference['rows'],
        'missing':actual['missing']==reference['missing'],
        'min_received':actual['min_received']==reference['min_received'],
        'max_received':actual['max_received']==reference['max_received']}
for name,expected in reference['frequencies'].items():
    checks['frequency:'+name]=actual['frequencies'][name]==expected
for name,expected in reference['quality'].items():
    checks['quality:'+name]=actual['quality'][name]==expected
for name,expected in reference['cross'].items():
    def keyed(rows):return {tuple(row['keys']):row['n'] for row in rows}
    checks['cross:'+name]=keyed(actual['cross'][name])==keyed(expected)
result={'all_pass':all(checks.values()),'checks':checks,
        'reference_method':'previous independent full-file pandas chunk analysis; source hash in source_fingerprint.json'}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['all_pass'] else 1)
