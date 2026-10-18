"""Collect benchmark records and report paths into a long-format CSV.
Expected layout: <out>/<case_id>/<model>/<campaign>/NN_<policy>/."""
from __future__ import annotations
import csv, json, re, sys
from pathlib import Path


def collect(root: Path, rows_out: Path):
    rows = []
    for rec_path in sorted(root.glob('*/*/*/[0-9][0-9]_*/record.json')):
        d = rec_path.parent
        case_id, model = rec_path.parents[3].name, rec_path.parents[2].name
        m = re.match(r'(\d+)_(fixed|dynamic|frozen)$', d.name)
        if not m:
            continue
        rec = json.loads(rec_path.read_text(encoding='utf-8'))
        ok = rec.get('status') == 'ok'
        err = rec.get('error', '') or ''
        calls = rec.get('calls', [])
        ft = '' if ok else ('timeout' if calls and calls[-1].get('exit') is None else 'json_empty' if 'JSONDecodeError' in err else 'other')
        rows.append(dict(case_id=case_id, model=model, cli=rec['cli'], round=int(m.group(1)), arm=m.group(2), status='ok' if ok else 'error',
                         failure_type=ft, report_path=str(d / 'final_report.json') if ok else ''))
    if not rows:
        raise SystemExit('No rounds found. Expected layout: <root>/<case>/<model>/<campaign>/NN_<policy>/record.json')
    with open(rows_out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return rows


if __name__ == '__main__':
    rows = collect(Path(sys.argv[1]), Path(sys.argv[2]))
    print(len(rows), 'rows ->', sys.argv[2])
