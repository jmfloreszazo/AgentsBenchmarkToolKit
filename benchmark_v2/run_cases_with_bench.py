"""Run the benchmark for each test RFP with a separate held-out calibration design.

The generated bench_multicase module isolates case-specific input paths from
the single-case runner. Provider calls are paid unless --demo is selected.
"""
from __future__ import annotations
import argparse, importlib, json, os, shutil, sys, uuid, hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def make_patched_bench(repo: Path = REPO) -> Path:
    src = (repo / 'bench.py').read_text(encoding='utf-8')
    dst = repo / 'bench_multicase.py'
    tmp = repo / f'.bench_multicase.{os.getpid()}.tmp'
    tmp.write_text(src, encoding='utf-8'); os.replace(tmp, dst)
    return dst


def design_frozen_heldout(bm, model: str, rfp_text: str, timeout: int, outdir: Path,
                          cli: str = 'copilot') -> Path:
    """Design once per backend/model on calibration; reject incompatible cached designs."""
    outdir.mkdir(parents=True, exist_ok=True); path = outdir / 'frozen_design.json'
    identity = dict(cli=cli, model_requested=model,
                    calibration_sha256=hashlib.sha256(rfp_text.encode('utf-8')).hexdigest())
    if path.exists():
        saved = json.loads((outdir / 'design_record.json').read_text(encoding='utf-8'))
        if any(saved.get(k) != v for k, v in identity.items()):
            raise ValueError('Held-out cache CLI/model/calibration mismatch; use a fresh output directory')
        return path
    with bm.isolated_workspace() as wd:
        (wd / 'RFP.md').write_text(rfp_text, encoding='utf-8')
        directory, suffix = bm.agent_location(cli)
        agents_dir = wd / directory; agents_dir.mkdir(parents=True)
        designer_id = f'heldout-{uuid.uuid4().hex[:10]}-designer'
        src = bm.fixed_agent('team-designer', model, cli, designer_id)
        (agents_dir / f'{designer_id}{suffix}').write_text(src, encoding='utf-8')
        res = bm.invoke(designer_id, bm.design_prompt(rfp_text), model, wd, outdir, '00_designer_heldout', timeout, cli=cli)
    record = {**bm.call_record('design', res), **identity}
    bm.write_json(outdir / 'design_record.json', record)
    if res['exit'] != 0:
        raise RuntimeError(f'Held-out design failed for {model}: ' + str(res.get('stderr', ''))[-300:])
    design = bm.extract_json(res['answer']); agents = design.get('agents')
    if not isinstance(agents, list) or [a.get('stage') for a in agents if isinstance(a, dict)] != list(bm.STAGES):
        raise ValueError('Held-out designer did not preserve three ordered stages')
    bm.write_json(path, design)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cli', choices=['copilot', 'claude', 'codex'], default='copilot')
    ap.add_argument('--case-pack', required=True); ap.add_argument('--models', required=True)
    ap.add_argument('--runs', type=int, default=2); ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--arm', choices=['fixed', 'dynamic', 'frozen', 'both', 'all'], default='all')
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--out', default='results_cases'); ap.add_argument('--only', default='', help='Comma-separated test-case IDs')
    ap.add_argument('--sealed', default='', help='Scoring-key directory (default: sealed sibling of the case-pack directory)')
    ap.add_argument('--frozen', choices=['heldout', 'percase'], default='heldout')
    a = ap.parse_args()
    failures = 0
    models = [m.strip() for m in a.models.split(',')]
    if any(not bm_model_valid(m) for m in models):
        ap.error('--models requires valid comma-separated native model identifiers')
    if not 1 <= a.runs <= 30 or a.timeout < 10:
        ap.error('Require runs between 1 and 30 and timeout >=10')
    make_patched_bench()
    sys.path.insert(0, str(REPO))
    bm = importlib.import_module('bench_multicase')
    pack = json.loads(Path(a.case_pack).read_text(encoding='utf-8'))
    base = Path(a.case_pack).resolve().parent
    only = set(filter(None, a.only.split(',')))
    test_ids = {c['id'] for c in pack['cases'] if c.get('role', 'test') == 'test'}
    if only - test_ids:
        ap.error('--only contains unknown test cases: ' + ', '.join(sorted(only - test_ids)))
    if not test_ids:
        ap.error('The case pack contains no test cases')
    heldout = {}
    if a.frozen == 'heldout' and not a.demo and a.arm in ('all', 'frozen'):
        calib = next((c for c in pack['cases'] if c.get('role') == 'calibration'), None)
        if calib is None:
            raise SystemExit('Held-out frozen policy requires one calibration case in the case pack.')
        for model in models:
            heldout[model] = design_frozen_heldout(bm, model, (base / calib['rfp']).read_text(encoding='utf-8'), a.timeout,
                                                   Path(a.out) / '_frozen_heldout' / a.cli / model, cli=a.cli)
            print(f'== held-out frozen design for {model}: {heldout[model]}', flush=True)
    for c in pack['cases']:
        if c.get('role', 'test') != 'test' or (only and c['id'] not in only):
            continue
        sealed = Path(a.sealed).resolve() if a.sealed else (base.parent / 'sealed')
        # Scoring inputs stay outside the agent workspace; temporary paths keep
        # source fingerprints relative to this package root.
        stage = REPO / '.multicase_stage' / f"{c['id']}__{os.getpid()}"; stage.mkdir(parents=True, exist_ok=True)
        shutil.copy2((base / c['rfp']).resolve(), stage / 'RFP.md')
        shutil.copy2((sealed / Path(c['answer_key']).name).resolve(), stage / 'answer_key.json')
        bm.RFP = stage / 'RFP.md'; bm.KEY = stage / 'answer_key.json'
        try:
            for model in models:
                argv = ['bench', '--cli', a.cli, '--runs', str(a.runs), '--model', model, '--arm', a.arm, '--timeout', str(a.timeout),
                        '--out', str(Path(a.out) / c['id'] / model)] + (['--demo'] if a.demo else [])
                print(f"== case {c['id']} | CLI {a.cli} | model {model}", flush=True)
                old_argv = sys.argv
                old_frozen = os.environ.pop('BENCH_FROZEN_DESIGN', None)
                sys.argv = argv
                if model in heldout:
                    os.environ['BENCH_FROZEN_DESIGN'] = str(heldout[model].resolve())
                try:
                    if bm.main() != 0:
                        failures += 1
                finally:
                    sys.argv = old_argv
                    os.environ.pop('BENCH_FROZEN_DESIGN', None)
                    if old_frozen is not None:
                        os.environ['BENCH_FROZEN_DESIGN'] = old_frozen
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    return 1 if failures else 0


def bm_model_valid(model):
    import re
    return bool(re.fullmatch(r'[A-Za-z0-9_.-]+', model)) and model not in ('.', '..')


if __name__ == '__main__':
    raise SystemExit(main())
