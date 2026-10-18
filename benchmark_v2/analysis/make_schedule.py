"""Create a randomized block schedule as a planning artifact; does not execute provider calls.

The default runner uses its own rotating policy order, not this CSV schedule."""
from __future__ import annotations
import argparse, csv, json, random
from pathlib import Path

CALLS = {'fixed': 3, 'dynamic': 4, 'frozen_heldout': 3, 'frozen': 3, 'fleet_free': None, 'fleet_method': None,
         'fixed_len_matched': 3, 'dynamic_budget_matched': 3}
NEEDS_HARNESS_CHANGE = {'frozen_heldout', 'fixed_len_matched', 'dynamic_budget_matched'}


def build(pack: dict, models: list[str], rounds: int, arms: list[str], seed: int, timeout: int):
    rng = random.Random(seed)
    tests = [c for c in pack['cases'] if c.get('role', 'test') == 'test']
    blocks = [(c['id'], m, r) for c in tests for m in models for r in range(1, rounds + 1)]
    rng.shuffle(blocks)
    rows, n = [], 0
    # Frozen-profile design jobs use calibration only, once per model.
    calib = next((c for c in pack['cases'] if c.get('role') == 'calibration'), None)
    if calib and 'frozen_heldout' in arms:
        for m in models:
            n += 1
            rows.append(dict(run_id=f'J{n:04d}', block='design', order=0, case_id=calib['id'], model=m, round=0,
                             arm='frozen_design_job', planned_calls=1, timeout_s=timeout, needs_harness_change=True))
    for (cid, m, r) in blocks:
        order = arms[:]; rng.shuffle(order)
        for i, arm in enumerate(order, 1):
            n += 1
            rows.append(dict(run_id=f'R{n:04d}', block=f'{cid}|{m}|{r}', order=i, case_id=cid, model=m, round=r, arm=arm,
                             planned_calls=CALLS.get(arm), timeout_s=timeout, needs_harness_change=arm in NEEDS_HARNESS_CHANGE))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case-pack', required=True); ap.add_argument('--models', required=True)
    ap.add_argument('--rounds', type=int, default=2); ap.add_argument('--arms', default='fixed,dynamic,frozen_heldout')
    ap.add_argument('--seed', type=int, required=True); ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--out', default='run_schedule.csv')
    a = ap.parse_args()
    pack = json.loads(Path(a.case_pack).read_text(encoding='utf-8'))
    rows = build(pack, a.models.split(','), a.rounds, a.arms.split(','), a.seed, a.timeout)
    with open(a.out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    calls = sum(r['planned_calls'] or 0 for r in rows)
    print(f'{len(rows)} jobs, {calls} minimum planned calls (excluding Fleet) -> {a.out}')


if __name__ == '__main__':
    main()
