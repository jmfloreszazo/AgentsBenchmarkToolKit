# Protocol for a new RFP agent-team experiment

This document describes the public English v3 instrument. It is **not** the
sealed protocol or dataset of the earlier blog study.

## Question and experimental unit

Does issue detection differ between predefined specialists, specialists
designed for each RFP, and specialists frozen after one held-out calibration?
The **case**, not a finding or invocation, is the comparison unit.

Fix model IDs, backend, case count, rounds, timeout, stopping rule and analysis
before execution. Report budget-driven reductions and retain failed attempts.
Do not select cases according to performance.

## Three policies

- `fixed`: discovery, architecture and audit with predefined generic profiles.
- `dynamic`: one design invocation followed by the three generated specialists.
- `frozen`: profiles designed once per backend/model on calibration, then reused
  without modification on test cases.

The policies do not equalize invocation counts or profile length. Observed
differences concern the complete policy, not specialization alone.
Provider-native automatic subagent routing is not the experimental variable.

## Corpus and diversity

The package has 100 English test projects in 20 sectors with 20 presentation
styles, plus one calibration document. All are synthetic and use shared
issue templates and editorial variants. They are not independent human authors
and have not undergone independent domain review.

Diversity limits: no duplicate heading sequences, defect-kind sequences or
template sets; mean word-five-gram Jaccard similarity <=0.06 and pairwise maximum
<=0.20. These limits do not prove statistical independence or external validity.
Do not relax them silently when a generated seed fails.

Public keys enable reproduction but prevent treating the corpus as secret.
Use new private inputs and independent review for blind confirmatory research.
Changing the seed does not change the catalogue's project themes.

## Automatic instrument and human validation

Primary automatic score: recall of 15 planted issues using `v2_cap3`
(matching kind, expected anchors and at least one keyword; at most three
additional anchors per finding). Sensitivity variants tighten matching.

Instrument checks require an oracle report to obtain recall 1, all positive
controls, no decoy false alarms and a valid output contract. An all-keywords,
all-anchors stuffing response must obtain recall 0 with the hardened scorer.
These checks are not evidence of semantic understanding.

The gate checks output structure, citation validity and coverage, not quality.
Report decoy false alarms, positive controls, completion rates, invocation counts
and durations alongside recall.

Two reviewers independent of the author should label a blinded sample.
Suggested acceptance criteria: precision >=0.85, recall >=0.80 and reviewer
kappa >=0.70 against adjudicated consensus. Without validation, automatic
results remain exploratory.

Reviewer CSVs: `vid,item_id,kind,found_0_1`. Optional scorer CSV:
`vid,item_id,variant,scorer`. Optional adjudicated CSV: `vid,item_id,consensus`.

```powershell
python benchmark_v2\validation\agreement.py --reviewer1 reviewer1.csv --reviewer2 reviewer2.csv --scorer scorer.csv --out results\human-review
```

## Analysis

- Average completed rounds within each case and policy across models.
- Compare three policy pairs; relevance margin: recall difference 0.10.
- Use t intervals with Bonferroni alpha 0.05/3.
- Declare equivalence only when the corresponding interval lies inside
  the prespecified margin.
- Report case-level sign-flip tests as a secondary analysis.
- Report completed-round estimates and failure-as-zero ITT sensitivity.
- Report clustering from shared domains/templates as a limitation.

The default runner rotates policy order; it does not consume the optional
randomized schedule CSV. Do not claim full randomization unless a separately
verified execution process actually used that schedule.

## Backend controls and provenance

Record CLI, CLI version, requested model, explicitly reported model, exit status,
timeout, duration and per-invocation artifacts. Missing model metadata stays
unverified. Never infer served weights or equate models across providers.

The runner creates a disposable workspace without keys and restricts tools.
These controls are not an OS sandbox guarantee. Any observed tool invocation
invalidates a response. Claude print JSON does not expose a complete tool trace;
document that observation limit.

Keep errors explicit, do not silently retry rounds, and preserve original
attempts. Wall-clock invocation durations can include machine suspension:
do not call them active compute hours.

Planned invocation count per model: `cases * rounds * 10 + 1`, excluding extra
smoke tests and provider-internal retries. Costs require verified counters and
tariffs. Do not sum overlapping prompt/cache counters or equate estimated
consumption with money invoiced.

## Sealing and publication

Seal code, agent profiles, inputs, keys and configuration before execution.
Publish the commitment with a verifiable timestamp. Do not change sealed
materials or silently substitute models. Record any deviation.

Keep source, historical model responses and derived results as separate
publication packages. Expected-answer fixtures are not model execution evidence.
