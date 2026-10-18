# RFP Agent Team Benchmark

Compare fixed specialist profiles, dynamically designed teams and teams frozen
after a held-out calibration task. Run the same explicit pipeline through
**GitHub Copilot CLI**, **Claude Code CLI** or **OpenAI Codex CLI**.

This is a standalone source package. It contains **synthetic inputs, evaluation
keys and offline tests**, not model responses, execution logs, historical
results, invoices or the blog article.

## Start here: the 100 English RFPs

Open **[rfp/](rfp/)**: it contains exactly **100 English RFP Markdown files**,
not just the three former pilot documents. Each file describes a different
project. The additional calibration document is in [calibration/](calibration/),
outside the 100 test cases.

- **100 distinct projects**, covering **20 sectors**, five projects per sector.
- **20 presentation styles**: formal tenders, outcome briefs, engineering
  specifications, service charters, legal schedules, product backlogs, supplier
  questionnaires, decision memos, work orders, operating instructions, compliance
  matrices, risk dossiers, dialogue records, milestone plans, interface contracts,
  assurance cases, field notes, board papers, user stories and migration playbooks.
- Varied narrative, clause numbering, tables, lists, questions and work-item
  layouts, all stored as UTF-8 Markdown that the runner can read directly.
  These are different document structures, **not PDF/DOCX ingestion support**.
- Scenarios include pathology samples, ferry berths, seed certification,
  telescope time, wildfire resources, museum loans and many other workflows.

Examples:

- [Hospital bed coordination](rfp/RFP_001-healthcare-81d945.md)
- [Bus depot charging](rfp/RFP_002-transport-4c0e37.md)
- [District heat balancing](rfp/RFP_003-energy-b69506.md)

[case_pack.json](case_pack.json) lists every case and its role.
[public_manifest.json](public_manifest.json) records document hashes, projects
and styles. The generation seed is `20261018`.

### Diversity evidence and limitations

[diversity_audit.json](diversity_audit.json) covers all **5,050 pairs** of the
101 documents, including calibration:

| Measure | Observed | Acceptance threshold |
|---|---:|---:|
| Identical heading sequences | 0 | 0 |
| Identical defect-kind sequences | 0 | 0 |
| Identical defect-template sets | 0 | 0 |
| Mean word-five-gram Jaccard similarity | 0.0586 | <= 0.06 |
| Maximum pairwise similarity | 0.1907 | <= 0.20 |

The generator varies project workflows, selected issues, wording and document
layout. However, it uses shared synthetic templates. These are **not 100
independent human authors**, and the audit does not establish statistical
independence, realism or external validity. Independent domain review is pending.

**This English v3 corpus is new and has not been evaluated with paid models.**
It replaces the Spanish public fixtures in this source package. It must not be
presented as the corpus or results used in the historical blog study. That
study's article and evidence remain outside this directory and were not changed.

## Generic agents, equivalent across providers

The same four domain-neutral profiles are provided for all backends:

| Role | Purpose |
|---|---|
| `discovery` | Extract requirements, conflicts, dependencies and unknowns |
| `architecture` | Propose provisional, evidence-grounded solution options |
| `audit` | Challenge earlier drafts and produce the final report |
| `team-designer` | Design the three specialists from the supplied RFP |

They assume **no particular product, client, industry, legacy stack or preferred
architecture**. Applicable constraints come from the supplied RFP.

- Copilot: [.github/agents/](.github/agents/) (`*.agent.md`).
- Claude Code: [.claude/agents/](.claude/agents/) (Markdown with YAML frontmatter).
- Codex: [.codex/agents/](.codex/agents/) (TOML).

[sync_agents.py](sync_agents.py) holds the shared English instructions and
regenerates the three equivalent sets:

```powershell
python sync_agents.py
```

Published profiles do not pin models. Select a native model ID at execution
time. The runner controls the stages explicitly; this is **not a comparison of
each provider's automatic native subagent routing**. For Codex, the runner
loads the TOML instructions into each `codex exec` stage; it does not invent
an `exec --agent` flag or spawn an extra layer of subagents.

## Installation

Use **Python 3.11 or newer** (`tomllib` is required). Local validation used
Python 3.13 on Windows. From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s benchmark_v2\tests -v
python -m unittest discover -s tests -v
```

Install and authenticate the official CLI you intend to use:

- [GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli)
- [Claude Code](https://code.claude.com/docs/en/overview)
- [OpenAI Codex CLI](https://developers.openai.com/codex/cli/)

Check `copilot --version`, `claude --version` or `codex --version`, and confirm
the exact model identifier available to your account. Models and pricing are
not interchangeable between providers.

Claude uses `--bare` with explicit profiles, no tools, hooks or ambient MCP
configuration. This mode needs provider credentials such as
`ANTHROPIC_API_KEY`; subscription OAuth login must not be assumed sufficient.
Codex uses non-interactive JSONL output, stdin for long prompts, a read-only
sandbox, no interactive approval, disabled shell/web/memory/multiagent features,
and ignores user configuration. These are risk-reduction controls, **not an
OS-level isolation guarantee**. Observed tool calls invalidate an invocation.
Missing model metadata is recorded as unverified, never inferred from the request.

## Verify without paying for model calls

```powershell
python benchmark_v2\generator\independence_audit.py . oracle
python bench.py --cli copilot --demo --runs 1 --arm all --out results\synthetic-check
```

`--demo` constructs expected output from the key. Its output is explicitly
labelled synthetic and must never be reported as model performance.
The offline backend tests use local subprocess fixtures, not provider calls.
Live Claude Code and Codex compatibility still requires an authenticated smoke
test with your installed CLI versions.

## Run a paid smoke test: one case first

**The following commands make paid provider calls.** Replace the model
placeholder with an available native ID and choose one backend:

```powershell
$case = (Get-Content case_pack.json -Raw | ConvertFrom-Json).cases |
    Where-Object role -eq 'test' | Select-Object -First 1

python benchmark_v2\run_cases_with_bench.py --cli copilot --models YOUR_COPILOT_MODEL --case-pack case_pack.json --sealed oracle --runs 1 --only $case.id --out results\copilot-smoke

python benchmark_v2\run_cases_with_bench.py --cli claude --models YOUR_CLAUDE_MODEL --case-pack case_pack.json --sealed oracle --runs 1 --only $case.id --out results\claude-smoke

python benchmark_v2\run_cases_with_bench.py --cli codex --models YOUR_CODEX_MODEL --case-pack case_pack.json --sealed oracle --runs 1 --only $case.id --out results\codex-smoke
```

Policies:

- **fixed**: three predefined specialists, three calls per case/round.
- **dynamic**: design a team per case/round, then run its specialists: four calls.
- **frozen held-out**: one calibration design per backend/model/campaign,
  then three calls per case/round without redesign.

One case with all policies and one round needs approximately **11 calls**.
For all 100 cases, remove `--only $case.id` and choose a fresh output directory.
One model needs **1,001 planned calls for one round**, or **2,001 for two**.
Do not run all cases automatically before reviewing your budget. No reliable
monetary estimate is possible without actual usage, current tariffs and cache
accounting. CLI-internal retries may add consumption.

Use separate output roots for different backends. Do not silently replace an
unavailable model or overwrite earlier attempts.

## Collect and analyze your execution

```powershell
python benchmark_v2\collect_results.py results\copilot-smoke results\copilot-smoke.csv
python benchmark_v2\analysis\analyze_study.py --results results\copilot-smoke.csv --case-pack case_pack.json --sealed oracle --rfp-dir rfp --out results\copilot-smoke-analysis.json
```

A smoke test checks wiring, **not statistical superiority or equivalence**.
The primary automatic score checks defect kind, source anchors and keywords,
with a cap on extra references. The analysis contrasts case-level averages and
reports both completed-round estimates and failure-as-zero sensitivity.
See [benchmark_v2/PROTOCOL.md](benchmark_v2/PROTOCOL.md) for assumptions,
human-review requirements and limitations.

### Evaluation keys are not model results

[oracle/](oracle/) contains synthetic ground truth: 15 injected issues,
two positive compliance controls and three valid decoy clauses per case.
These fixtures support scoring and instrument tests; **they are not answers
generated by an AI model**. The runner does not copy keys to the agent workspace.

The public corpus is not a secret test set: it may be memorized or contaminated.
For a new blind study, generate and seal a fresh private corpus and arrange
independent human review before executing.

## Generate a new English study

Generation itself does not contact providers:

```powershell
python benchmark_v2\generator\rfp_generator.py --seed 12345 --n 100 --out generated_new --sealed generated_new\oracle

python benchmark_v2\prepare_study.py --cli copilot --models YOUR_COPILOT_MODEL --n 20 --rounds 2 --out study_new
# Alternatives: --cli claude --models YOUR_CLAUDE_MODEL
#               --cli codex --models YOUR_CODEX_MODEL
```

The preparation command audits the batch, checks the scorer and source
anchors, records configuration and seals hashes. It refuses to seal a batch
that fails diversity or instrument checks. Not every seed passes, especially
for small samples. The generated PowerShell scripts **do** call providers.
Keep `private/` and `sealed/` unpublished until study closure.

The catalogue supports up to 100 test projects plus calibration. Changing the
seed changes issue selection and phrasing, not the catalogue of project themes.
The optional [schedule generator](benchmark_v2/analysis/make_schedule.py) is a
planning utility; the default runner does not consume that schedule.

## Publish the source

Publish **this directory's contents**, not the parent workspace. Review staged
files; [.gitignore](.gitignore) excludes common outputs, environments and logs
but is not a substitute for checking credentials and execution artifacts.
The code does not create or push a remote repository. The copyright holder
must choose a license before offering explicit reuse permissions.
