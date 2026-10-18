"""Prepare and seal an English synthetic study without calling an AI provider."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sys
from datetime import datetime, timezone

V2 = Path(__file__).resolve().parent
REPO = V2.parent
for folder in (REPO, V2 / "generator", V2 / "analysis"):
    sys.path.insert(0, str(folder))
import bench
import independence_audit as audit
import rfp_generator as generator
import scorer_v2 as scorer


def stuffed(key, ids):
    words = " ".join(w for m in key["mutants"] for w in m["keywords_any"])
    return dict(requirements=[], findings=[
        dict(kind=kind, summary=words, impact=words, recommendation=words, source_refs=list(ids))
        for kind in sorted({m["kind"] for m in key["mutants"]})])


def self_check(cases):
    rows = []
    for case in cases:
        key, ids = case["key"], set(case["source_ids"])
        expected = generator.oracle_report(case)
        score = scorer.score(expected, key)
        row = dict(id=case["id"], anchors=len(ids), oracle_recall=score["recall"],
                   oracle_controls=score["controls_ok"], oracle_false_alarms=score["false_alarm_n"],
                   stuffed_recall=scorer.score(stuffed(key, ids), key)["recall"],
                   oracle_gate=bench.gate(expected, ids)["pass"],
                   valid_refs=all(set(m["refs"]) <= ids for m in key["mutants"] + key["decoys"])
                   and all(c["ref"] in ids for c in key["controls"]),
                   anchored_conditions=key["covariates"]["conditions_anchor"] in ids)
        row["ok"] = (row["oracle_recall"] == 1 and row["oracle_controls"] and row["oracle_false_alarms"] == 0
                     and row["stuffed_recall"] == 0 and row["oracle_gate"] and row["valid_refs"]
                     and row["anchored_conditions"] and 20 <= row["anchors"] <= 99)
        rows.append(row)
    return rows


def quote(value) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", choices=["copilot", "claude", "codex"], default="copilot")
    parser.add_argument("--models", required=True, help="Comma-separated exact native model identifiers")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--out", type=Path, default=Path("study_new"))
    args = parser.parse_args()
    models = [m.strip() for m in args.models.split(",")]
    if not models or any(not bench.MODEL_RX.fullmatch(m) or m in (".", "..") for m in models):
        parser.error("Use valid native model identifiers, separated by commas.")
    if not 1 <= args.n <= 100 or not 1 <= args.rounds <= 30 or args.timeout < 10:
        parser.error("Require 1..100 cases, 1..30 rounds and timeout >=10 seconds.")
    out = args.out if args.out.is_absolute() else REPO / args.out
    if out.exists() and any(out.iterdir()):
        parser.error(f"Refusing to overwrite a nonempty study: {out}")
    seed = args.seed if args.seed is not None else secrets.randbelow(2 ** 62)
    (out / "private").mkdir(parents=True)
    (out / "private" / "seed.txt").write_text(f"{seed}\n", encoding="utf-8")
    cases = generator.write_batch(seed, args.n, out / "generated", out / "sealed")
    metrics = audit.audit(cases)
    failures = audit.check(metrics)
    generator.save_json(out / "diversity_audit.json", dict(metrics=metrics, failures=failures))
    if failures:
        raise SystemExit("Diversity thresholds failed; study NOT sealed: " + "; ".join(failures))
    checks = self_check(cases)
    generator.save_json(out / "instrument_self_check.json", checks)
    if not all(c["ok"] for c in checks):
        raise SystemExit("Instrument self-check failed; study NOT sealed.")
    tests = [c for c in cases if c["role"] == "test"]
    calls = len(tests) * args.rounds * 10 + 1
    plan = dict(created_utc=datetime.now(timezone.utc).isoformat(), cli=args.cli, models=models,
                test_cases=len(tests), rounds=args.rounds, timeout_seconds=args.timeout,
                calls_per_model=calls, planned_calls=calls * len(models),
                policies=["fixed", "dynamic", "frozen_heldout"],
                limitations=["Synthetic inputs, not independently reviewed.",
                             "Do not infer expected cost or active compute time from historical campaigns."])
    generator.save_json(out / "study_plan.json", plan)
    files = {}
    for base, prefix in ((V2, "benchmark_v2"), (out / "generated", "generated"), (out / "sealed", "sealed"),
                         (REPO / ".github", ".github"), (REPO / ".claude", ".claude"), (REPO / ".codex", ".codex")):
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                files[f"{prefix}/{path.relative_to(base).as_posix()}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (REPO / "bench.py", out / "study_plan.json"):
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    commitment = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    generator.save_json(out / "seal_manifest.json", dict(files=files, commitment_sha256=commitment))
    (out / "COMMITMENT.txt").write_text(commitment + "\n", encoding="utf-8")
    head = "$ErrorActionPreference = 'Stop'\nSet-Location -LiteralPath " + quote(REPO) + "\n"
    common = (f"--cli {args.cli} --case-pack {quote(out / 'generated' / 'case_pack.json')} "
              f"--sealed {quote(out / 'sealed')} --timeout {args.timeout}")
    runner = "python benchmark_v2\\run_cases_with_bench.py"
    smoke = out / "smoke"
    (out / "1_smoke_test.ps1").write_text(
        head + f"# Paid calls: approximately {11 * len(models)}. Review before execution.\n"
        f"{args.cli} --version\n{runner} {common} --models {quote(','.join(models))} "
        f"--runs 1 --only {tests[0]['id']} --out {quote(smoke)}\n", encoding="utf-8")
    for model in models:
        (out / f"2_run_{model}.ps1").write_text(
            head + f"# Paid calls: approximately {calls}.\n{runner} {common} --models {quote(model)} "
            f"--runs {args.rounds} --out {quote(out / 'results_cases')}\n", encoding="utf-8")
    (out / "3_analyze.ps1").write_text(
        head + f"python benchmark_v2\\collect_results.py {quote(out / 'results_cases')} {quote(out / 'results_long.csv')}\n"
        f"python benchmark_v2\\analysis\\analyze_study.py --results {quote(out / 'results_long.csv')} "
        f"--case-pack {quote(out / 'generated' / 'case_pack.json')} --sealed {quote(out / 'sealed')} "
        f"--rfp-dir {quote(out / 'generated' / 'rfp')} --out {quote(out / 'study_analysis.json')}\n", encoding="utf-8")
    print(f"Study prepared without provider calls: {out}\nCommitment: {commitment}\nPlanned paid calls: {calls * len(models)}")


if __name__ == "__main__":
    main()
