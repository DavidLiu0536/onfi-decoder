"""Command-line interface for ONFI decoder."""
import argparse
import sys
import json
from .decoder import OnfiDecoder


def main():
    p = argparse.ArgumentParser(
        prog='onfi-decode',
        description='Decode logic-analyzer captures of ONFI bus traffic into commands.',
    )
    p.add_argument('csv', help='Path to logic analyzer CSV (Saleae Logic 2 format)')
    p.add_argument('-o', '--output', help='Output file (default: stdout)')
    p.add_argument('-f', '--format', choices=['text', 'json'], default='text',
                   help='Output format (default: text)')
    p.add_argument('--stats', action='store_true', help='Print decode statistics only')
    args = p.parse_args()

    dec = OnfiDecoder()
    try:
        dec.decode_csv(args.csv)
    except FileNotFoundError:
        print(f"Error: file not found: {args.csv}", file=sys.stderr); sys.exit(1)
    except ValueError as e:
        print(f"Error parsing CSV: {e}", file=sys.stderr); sys.exit(2)

    if args.stats:
        out = json.dumps(dec.stats(), indent=2, ensure_ascii=False)
    elif args.format == 'json':
        out = json.dumps([{
            'time_us': e.time_us, 'kind': e.kind, **e.raw
        } for e in dec.events], indent=2, ensure_ascii=False, default=str)
    else:
        out = dec.report_text()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(out)
        print(f"Written: {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == '__main__':
    main()
