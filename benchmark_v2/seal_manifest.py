"""Hash protocol, instrument, input documents and keys before execution.

Publish the SHA-256 commitment with a verifiable timestamp. Keep seeds private
until study closure; modifying any sealed file changes the commitment."""
from __future__ import annotations
import argparse, hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = ['PROTOCOL.md', 'analysis/scorer_v2.py', 'analysis/stats_core.py', 'analysis/analyze_study.py', 'analysis/make_schedule.py',
        'generator/rfp_generator.py', 'validation/agreement.py']


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--generated', required=True); ap.add_argument('--sealed', required=True)
    ap.add_argument('--schedule', default=''); ap.add_argument('--out', default='seal_manifest.json')
    a = ap.parse_args()
    files = {}
    for rel in CORE:
        files[rel] = sha(HERE / rel)
    gen, sealed = Path(a.generated), Path(a.sealed)
    for p in sorted(gen.rglob('*')):
        if p.is_file():
            files['generated/' + p.relative_to(gen).as_posix()] = sha(p)
    for p in sorted(sealed.glob('*')):
        if p.is_file():
            files['sealed/' + p.name] = sha(p)
    if a.schedule:
        files['schedule/' + Path(a.schedule).name] = sha(Path(a.schedule))
    commit = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    m = {'created_utc': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(), 'files': files, 'commitment_sha256': commit}
    Path(a.out).write_text(json.dumps(m, indent=2), encoding='utf-8')
    print('SHA-256 commitment (publish before execution):', commit)


if __name__ == '__main__':
    main()
