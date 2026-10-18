"""Analyze case-level policy contrasts, completed-round estimates and failure-as-zero sensitivity."""
from __future__ import annotations
import csv, json, math, sys, itertools
from pathlib import Path
import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import scorer_v2 as S
import stats_core as sc

PRIMARY = dict(max_extra_refs=3, one_to_one=False, min_keywords=1)   # v2_cap3, prespecified


def clopper_pearson(k, n, conf=0.95):
    if n == 0:
        return (float('nan'), float('nan'))
    a = 1 - conf
    lo = 0.0 if k == 0 else stats.beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - a / 2, k + 1, n - k)
    return (float(lo), float(hi))


def decide(d_c, delta, alpha_family):
    d_c = np.asarray(d_c, float); C = len(d_c)
    if C < 3:
        return dict(n_cases=C, decision='Insufficient data (<3 cases)')
    m = d_c.mean(); se = d_c.std(ddof=1) / math.sqrt(C); df = C - 1
    t1 = stats.t.ppf(1 - alpha_family / 2, df); t2 = stats.t.ppf(1 - alpha_family, df)
    ci = (m - t1 * se, m + t1 * se); ci_eq = (m - t2 * se, m + t2 * se)
    if ci[0] > delta: dec = 'A better than B by more than the margin'
    elif ci[1] < -delta: dec = 'B better than A by more than the margin'
    elif ci_eq[0] > -delta and ci_eq[1] < delta: dec = 'Equivalent within the margin'
    elif ci[0] > 0 or ci[1] < 0: dec = 'Detectable difference, uncertain magnitude'
    else: dec = 'Inconclusive'
    if C <= 14:
        cnt = sum(abs((d_c * np.array(s)).mean()) >= abs(m) - 1e-12 for s in itertools.product((-1, 1), repeat=C)); p = cnt / 2 ** C
    else:
        rng = np.random.default_rng(1); sg = rng.choice([-1, 1], size=(100000, C)); p = float(np.mean(np.abs((sg * d_c).mean(1)) >= abs(m) - 1e-12))
    return dict(n_cases=C, d=float(m), se=float(se), df=df, ci=[float(ci[0]), float(ci[1])], ci_equiv=[float(ci_eq[0]), float(ci_eq[1])],
                p_signflip=float(p), decision=dec)


def load_scores(results_csv, case_pack, sealed_dir, rfp_dir):
    import bench
    pack = {c['id']: c for c in json.loads(Path(case_pack).read_text(encoding='utf-8'))['cases']}
    keys, ids = {}, {}
    rows = []
    for r in csv.DictReader(open(results_csv, encoding='utf-8')):
        cid = r['case_id']
        if pack[cid].get('role', 'test') != 'test':
            continue
        if cid not in keys:
            keys[cid] = json.loads((Path(sealed_dir) / Path(pack[cid]['answer_key']).name).read_text(encoding='utf-8'))
            ids[cid] = set(bench.REF_RX.findall((Path(rfp_dir) / Path(pack[cid]['rfp']).name).read_text(encoding='utf-8')))
        row = dict(case_id=cid, model=r['model'], round=int(r['round']), arm=r['arm'], status=r['status'], failure_type=r.get('failure_type', ''))
        row['ok'] = r['status'] == 'ok'
        if row['ok']:
            rep = json.loads(Path(r['report_path']).read_text(encoding='utf-8'))
            s = S.score(rep, keys[cid], **PRIMARY)
            crit = [m for m in keys[cid]['mutants'] if m.get('severity') == 'critical']
            row.update(recall=s['recall'], recall_crit=(sum(m['id'] in s['mutants_found'] for m in crit) / len(crit)) if crit else float('nan'),
                       v1=S.score(rep, keys[cid], **S.VARIANTS['v1_original'])['recall'], strict=S.score(rep, keys[cid], **S.VARIANTS['v2_strict'])['recall'],
                       false_alarms=s['false_alarm_n'], lfr=s['linked_finding_rate'], controls_ok=int(s['controls_ok']),
                       gate=int(bench.gate(rep, ids[cid])['pass']))
        rows.append(row)
    return rows


def case_level(rows, arm_a, arm_b, col, itt=False):
    out = {}
    for cid in sorted({r['case_id'] for r in rows}):
        def avg(arm):
            v = [(r[col] if r['ok'] else (0.0 if itt else None)) for r in rows if r['case_id'] == cid and r['arm'] == arm]
            v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
            return np.mean(v) if v else None
        a, b = avg(arm_a), avg(arm_b)
        if a is not None and b is not None:
            out[cid] = a - b
    return np.array(list(out.values()))


def analyze(results_csv, case_pack, sealed_dir, rfp_dir, arms, delta=0.10, families=None):
    rows = load_scores(results_csv, case_pack, sealed_dir, rfp_dir)
    res = {'n_rows': len(rows), 'delta': delta}
    # 1. Reliability
    rel = {}
    for arm in arms:
        rr = [r for r in rows if r['arm'] == arm]; k = sum(r['ok'] for r in rr)
        rel[arm] = dict(n=len(rr), completed=k, rate=round(k / len(rr), 4) if rr else None,
                        ci95_clopper_pearson=[round(x, 4) for x in clopper_pearson(k, len(rr))],
                        errors=dict(sorted({t: sum(1 for r in rr if not r['ok'] and r['failure_type'] == t) for t in {r['failure_type'] for r in rr if not r['ok']}}.items())))
    res['reliability'] = rel
    # 2. Contrasts
    families = families or [[(a, b) for a, b in itertools.combinations(arms, 2)]]
    res['contrasts'] = {}
    for fam in families:
        alpha_fam = 0.05 / len(fam)
        for a, b in fam:
            key = f'{a}_vs_{b}'
            res['contrasts'][key] = {
                'primary_PP_recall': decide(case_level(rows, a, b, 'recall'), delta, alpha_fam),
                'sens_ITT_recall': decide(case_level(rows, a, b, 'recall', itt=True), delta, alpha_fam),
                'sensitivity_critical_recall': decide(case_level(rows, a, b, 'recall_crit'), delta, alpha_fam),
                'sensitivity_original_scorer': decide(case_level(rows, a, b, 'v1'), delta, alpha_fam),
                'sensitivity_strict_scorer': decide(case_level(rows, a, b, 'strict'), delta, alpha_fam),
                'secondary_false_alarms_per_round': decide(case_level(rows, a, b, 'false_alarms'), delta=1.0, alpha_family=alpha_fam),
                'family_alpha': round(alpha_fam, 5)}
    # 3. Observed variance components (descriptive)
    okr = [r for r in rows if r['ok']]
    cells = {}
    for r in okr:
        cells.setdefault((r['case_id'], r['model'], r['arm']), []).append(r['recall'])
    w = [np.var(v, ddof=1) for v in cells.values() if len(v) > 1]
    res['observed_residual_sigma'] = round(float(np.sqrt(np.mean(w))), 4) if w else None
    res['mean_recall_by_policy'] = {arm: round(float(np.mean([r['recall'] for r in okr if r['arm'] == arm])), 4) for arm in arms if any(r['arm'] == arm for r in okr)}
    return res


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', required=True); ap.add_argument('--case-pack', required=True)
    ap.add_argument('--sealed', required=True); ap.add_argument('--rfp-dir', required=True)
    ap.add_argument('--arms', default='fixed,dynamic,frozen'); ap.add_argument('--delta', type=float, default=0.10)
    ap.add_argument('--out', default='study_analysis.json')
    a = ap.parse_args()
    out = analyze(a.results, a.case_pack, a.sealed, a.rfp_dir, a.arms.split(','), a.delta)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8'); print('->', a.out)
