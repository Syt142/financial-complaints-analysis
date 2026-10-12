import argparse
import json
import sys
from pathlib import Path
from .core import analyze_csv, export_results, DataError

def main():
    parser = argparse.ArgumentParser(description='Stream a CFPB-style CSV into auditable aggregate tables.')
    parser.add_argument('input', type=Path)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--batch-size', type=int, default=100000)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--max-id-blocks', type=int, default=1024)
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    # Prevent replacing the source even when a user names it like an output.
    outputs = {'summary.json', 'frequencies.csv', 'cross_tables.csv', 'quality.csv', 'manifest.json', 'analysis.md'}
    if args.input.resolve() in {(args.outdir/name).resolve() for name in outputs}:
        parser.error('Output would overwrite the input file')
    progress = None if args.quiet else lambda x: print(json.dumps(x), flush=True)
    try:
        result = analyze_csv(args.input, batch_size=args.batch_size, limit=args.limit,
                             max_id_blocks=args.max_id_blocks, progress=progress)
        path = export_results(result, args.outdir)
    except (DataError, ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2
    print(json.dumps({'rows': result['rows'], 'complete_file': result['run']['complete_file'],
                      'summary': str(path), 'all_checks_pass': all(result['checks'].values())}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
