"""Heuristic scoring with optional citation caps, one-to-one matching and keyword thresholds.

This instrument does not replace human review. Valid decoy clauses measure false alarms."""
from __future__ import annotations
import unicodedata

TEXT_FIELDS = ('summary', 'impact', 'recommendation')


def norm(s: str) -> str:
    x = unicodedata.normalize('NFKD', str(s).casefold())
    return ''.join(ch for ch in x if not unicodedata.combining(ch))


def _strs(v):
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def _kw_hits(text: str, words: list[str]) -> int:
    t = norm(text)
    return sum(1 for w in set(words) if norm(w) in t)


def _eligible(item: dict, entry: dict, max_extra_refs, min_keywords, kind_must_match=True) -> bool:
    if not isinstance(item, dict):
        return False
    if kind_must_match and item.get('kind') != entry['kind']:
        return False
    refs = set(_strs(item.get('source_refs')))
    need = set(entry['refs'])
    if not need.issubset(refs):
        return False
    if max_extra_refs is not None and len(refs) > len(need) + max_extra_refs:
        return False
    text = ' '.join(str(item.get(k, '')) for k in TEXT_FIELDS)
    return _kw_hits(text, entry['keywords_any']) >= min_keywords


def _max_matching(adj: dict[str, list[int]]) -> dict[str, int]:
    """Maximum bipartite matching through augmenting paths: mutant -> candidate findings."""
    owner: dict[int, str] = {}

    def try_assign(m, seen):
        for f in adj[m]:
            if f in seen:
                continue
            seen.add(f)
            if f not in owner or try_assign(owner[f], seen):
                owner[f] = m
                return True
        return False

    for m in adj:
        try_assign(m, set())
    return {m: f for f, m in owner.items()}


def score(report: dict, key: dict, *, max_extra_refs: int | None = 3, one_to_one: bool = False,
          min_keywords: int = 1) -> dict:
    findings = report.get('findings') if isinstance(report.get('findings'), list) else []
    requirements = report.get('requirements') if isinstance(report.get('requirements'), list) else []
    adj = {m['id']: [i for i, f in enumerate(findings) if _eligible(f, m, max_extra_refs, min_keywords)]
           for m in key['mutants']}
    if one_to_one:
        match = _max_matching(adj)
    else:
        match = {m: c[0] for m, c in adj.items() if c}
    found = [m['id'] for m in key['mutants'] if m['id'] in match]
    controls = []
    for c in key.get('controls', []):
        hit = any(isinstance(r, dict) and c['ref'] in _strs(r.get('source_refs'))
                  and _kw_hits(str(r.get('description', '')), c['keywords_any']) >= 1 for r in requirements)
        controls.append({'id': c['id'], 'found': hit})
    # False alarms flag valid decoy clauses as defects when the key defines decoys.
    # A finding linked to a real mutant is not also counted as a false alarm.
    linked = set(match.values())
    decoy_hits = []
    for d in key.get('decoys', []):
        for i, f in enumerate(findings):
            if i in linked:
                continue
            if _eligible(f, d, max_extra_refs, 1, kind_must_match=True):
                decoy_hits.append({'decoy': d['id'], 'finding': i})
    false_alarm_findings = sorted({h['finding'] for h in decoy_hits})
    n_f = len(findings)
    return {
        'mutants_found': found,
        'recall': round(len(found) / len(key['mutants']), 4) if key['mutants'] else 0.0,
        'controls_ok': all(c['found'] for c in controls) if controls else True,
        'n_findings': n_f,
        'linked_findings': len(linked),
        'linked_finding_rate': round(len(linked) / n_f, 4) if n_f else 0.0,
        'false_alarm_findings': false_alarm_findings,
        'false_alarm_n': len(false_alarm_findings),
    }


VARIANTS = {
    'v1_original':        dict(max_extra_refs=None, one_to_one=False, min_keywords=1),
    'v2_cap3':            dict(max_extra_refs=3,    one_to_one=False, min_keywords=1),
    'v2_cap2':            dict(max_extra_refs=2,    one_to_one=False, min_keywords=1),
    'v2_cap3_1to1':       dict(max_extra_refs=3,    one_to_one=True,  min_keywords=1),
    'v2_cap3_kw2':        dict(max_extra_refs=3,    one_to_one=False, min_keywords=2),
    'v2_strict':          dict(max_extra_refs=2,    one_to_one=True,  min_keywords=2),
}
