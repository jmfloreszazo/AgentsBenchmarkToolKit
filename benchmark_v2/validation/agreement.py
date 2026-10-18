"""Compare two reviewer label sheets and optional scorer predictions against human consensus."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd

def cohen_kappa(a, b):
    a, b = np.asarray(a, int), np.asarray(b, int)
    po = float(np.mean(a == b))
    pe = float(np.mean(a) * np.mean(b) + (1 - np.mean(a)) * (1 - np.mean(b)))
    return float((po - pe) / (1 - pe)) if pe < 1 else float('nan')


def compute(r1: pd.DataFrame, r2: pd.DataFrame, scorer: pd.DataFrame | None = None, consensus: pd.DataFrame | None = None):
    k = ['vid', 'item_id']
    d = r1[k + ['found_0_1', 'kind']].merge(r2[k + ['found_0_1']], on=k, suffixes=('_1', '_2')).dropna()
    d = d[d.item_id.str.startswith(('M', 'H', 'T', 'D'))] if False else d
    out = {'n_items': int(len(d)), 'raw_agreement': round(float(np.mean(d.found_0_1_1 == d.found_0_1_2)), 4),
           'kappa': round(cohen_kappa(d.found_0_1_1, d.found_0_1_2), 4),
           'kappa_by_kind': {kd: round(cohen_kappa(g.found_0_1_1, g.found_0_1_2), 3) for kd, g in d.groupby('kind') if len(g) >= 8}}
    d['disagrees'] = (d.found_0_1_1 != d.found_0_1_2)
    if consensus is None:  # Exclude unresolved disagreements from scorer-versus-consensus comparisons.
        agree = d[~d.disagrees].copy(); agree['consensus'] = agree.found_0_1_1
    else:
        agree = d.merge(consensus[k + ['consensus']], on=k)
    out['items_to_adjudicate'] = int(d.disagrees.sum())
    if scorer is not None:
        res = {}
        for vn, g in scorer.groupby('variant'):
            m = agree.merge(g[k + ['scorer']], on=k)
            tp = int(((m.scorer == 1) & (m.consensus == 1)).sum()); fp = int(((m.scorer == 1) & (m.consensus == 0)).sum())
            fn = int(((m.scorer == 0) & (m.consensus == 1)).sum()); tn = int(((m.scorer == 0) & (m.consensus == 0)).sum())
            prec = tp / (tp + fp) if tp + fp else float('nan'); rec = tp / (tp + fn) if tp + fn else float('nan')
            res[vn] = dict(n=len(m), tp=tp, fp=fp, fn=fn, tn=tn, precision=round(prec, 3), recall=round(rec, 3),
                           f1=round(2 * prec * rec / (prec + rec), 3) if prec + rec else float('nan'), accuracy=round((tp + tn) / len(m), 3),
                           kappa_vs_human=round(cohen_kappa(m.scorer, m.consensus), 3))
        out['scorer_vs_human'] = res
    return out, d[d.disagrees]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewer1', required=True, type=Path)
    parser.add_argument('--reviewer2', required=True, type=Path)
    parser.add_argument('--scorer', type=Path, help='CSV: vid,item_id,variant,scorer')
    parser.add_argument('--consensus', type=Path, help='CSV: vid,item_id,consensus')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    r1 = pd.read_csv(args.reviewer1); r2 = pd.read_csv(args.reviewer2)
    if r1.found_0_1.isna().all() or r2.found_0_1.isna().all():
        parser.error('Label sheets are empty; two reviewers must complete them.')
    scorer = pd.read_csv(args.scorer) if args.scorer else None
    consensus = pd.read_csv(args.consensus) if args.consensus else None
    res, disc = compute(r1, r2, scorer, consensus)
    args.out.mkdir(parents=True, exist_ok=True)
    disc.to_csv(args.out / 'adjudication_needed.csv', index=False)
    (args.out / 'agreement_report.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=2))
