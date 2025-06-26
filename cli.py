"""Read-only deterministic evaluator. No server or model required."""
import argparse
from pathlib import Path
import sys
from contracts import parse_json
from decision import evaluate
from exports import comparison_export

def main(argv=None,stdin=None,stdout=None,stderr=None):
    stdin,stdout,stderr=stdin or sys.stdin,stdout or sys.stdout,stderr or sys.stderr
    if hasattr(stdout,'reconfigure'):stdout.reconfigure(encoding='utf-8')
    if hasattr(stderr,'reconfigure'):stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Evaluate synthetic or user-provided USD rental listings')
    parser.add_argument('--input',default=str(Path(__file__).with_name('data.json')),help='Listing JSON file, or - for stdin')
    parser.add_argument('--budget',default='1000000')
    parser.add_argument('--kind',choices=['all','room','whole'],default='all')
    parser.add_argument('--months',type=int,default=12)
    parser.add_argument('--optional',action='store_true')
    parser.add_argument('--known-only',action='store_true')
    parser.add_argument('--format',choices=['json','csv'],default='json')
    parser.add_argument('--sort',choices=['total','monthly','effective','completeness'],default='total')
    args=parser.parse_args(argv)
    try:
        if args.input=='-':raw=stdin.read(100001)
        else:
            with Path(args.input).open('rb') as source:raw=source.read(100001).decode('utf-8')
        if len(raw.encode('utf-8'))>100000:raise ValueError('Input exceeds 100 KB')
        listing_data=parse_json(raw)
        result=evaluate(listing_data,{'budget':args.budget,'kind':args.kind,'months':args.months,'optional':args.optional,'known_only':args.known_only,'sort':args.sort})
        stdout.write(comparison_export(result['results'],args.format)+'\n')
        return 0
    except (OSError,ValueError,TypeError,UnicodeError) as exc:
        stderr.write('Rentwise: '+str(exc)+'\n')
        return 2

if __name__=='__main__':sys.exit(main())
