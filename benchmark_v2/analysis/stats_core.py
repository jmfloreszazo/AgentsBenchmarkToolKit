"""Statistical helpers for stratified policy comparisons and paired case-level tests.

Choose the experimental unit explicitly; repeated calls are not independent cases."""
from __future__ import annotations
import itertools, math
import numpy as np
from scipy import stats


def cell_arrays(df, model_col, arm_col, y_col, arm_a, arm_b):
    out = []
    for m, g in df.groupby(model_col):
        a = g.loc[g[arm_col] == arm_a, y_col].to_numpy(float)
        b = g.loc[g[arm_col] == arm_b, y_col].to_numpy(float)
        if len(a) and len(b):
            out.append((m, a, b))
    return out


def stratified_estimate(cells, margin=0.10):
    """Average within-model mean difference with pooled within-cell variance.
    Return the estimate, t interval and reference-prior posterior probabilities."""
    M = len(cells)
    d = np.mean([a.mean() - b.mean() for _, a, b in cells])
    ss = sum(((x - x.mean()) ** 2).sum() for _, a, b in cells for x in (a, b))
    df = sum(len(x) - 1 for _, a, b in cells for x in (a, b))
    s2 = ss / df if df > 0 else float('nan')
    var = sum(s2 * (1 / len(a) + 1 / len(b)) for _, a, b in cells) / M ** 2
    se = math.sqrt(var)
    t = stats.t(df, loc=d, scale=se)
    lo, hi = t.ppf(0.025), t.ppf(0.975)
    return {
        'd': d, 'se': se, 'df': df, 'ci95': (lo, hi),
        'p_gt_margin': float(1 - t.cdf(margin)),          # Probability that A exceeds B by more than the margin
        'p_equiv': float(t.cdf(margin) - t.cdf(-margin)),  # Probability that the absolute difference lies within the margin
        'p_lt_margin': float(t.cdf(-margin)),              # Probability that B exceeds A by more than the margin
    }


def stratified_permutation_p(cells):
    """Exact permutation of policy labels within each model through complete enumeration."""
    per_model = []
    obs = []
    for _, a, b in cells:
        x = np.concatenate([a, b]); na = len(a)
        obs.append(a.mean() - b.mean())
        vals = []
        for idx in itertools.combinations(range(len(x)), na):
            mask = np.zeros(len(x), bool); mask[list(idx)] = True
            vals.append(x[mask].mean() - x[~mask].mean())
        per_model.append(np.array(vals))
    d_obs = np.mean(obs)
    total = 0; hit = 0
    # Exact Cartesian-product convolution; cost grows with the number of combinations
    grids = np.meshgrid(*[np.arange(len(v)) for v in per_model], indexing='ij')
    stat = np.mean([v[g] for v, g in zip(per_model, grids)], axis=0)
    p = float(np.mean(np.abs(stat) >= abs(d_obs) - 1e-12))
    return p, int(stat.size)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items); out = {}; running = 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def decision(est, thr=0.95):
    """Decision rule using a prespecified relevance margin."""
    if est['p_gt_margin'] >= thr:
        return 'A better than B (above margin)'
    if est['p_lt_margin'] >= thr:
        return 'B better than A (above margin)'
    if est['p_equiv'] >= thr:
        return 'Equivalent within the margin'
    return 'Inconclusive'


def paired_signflip_p(diffs):
    d = np.array(diffs, float)
    obs = abs(d.mean())
    n = len(d)
    cnt = 0
    for signs in itertools.product((-1, 1), repeat=n):
        cnt += abs((d * np.array(signs)).mean()) >= obs - 1e-12
    return cnt / 2 ** n


def exact_upper_no_failure(n, conf=0.95):
    return 1 - (1 - conf) ** (1 / n)
