"""Measure structural duplication and word-five-gram overlap in a synthetic corpus."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import re
import unicodedata

MAX_MEAN_SIM = 0.06
MAX_PAIR_SIM = 0.20


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\[[pa]-\d{2}\]", " ", text)
    text = re.sub(r"\d+", "#", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z# ]+", " ", text)).strip()


def author_text(text: str) -> str:
    return "\n".join(line for line in text.splitlines()
                     if not line.startswith("> **SYNTHETIC EVALUATION INPUT.**"))


def shingles(text: str, k: int = 5) -> set[str]:
    words = norm(author_text(text)).split()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def heading_skeleton(text: str) -> tuple[str, ...]:
    return tuple(norm(re.sub(r"^#+\s*", "", line)) for line in text.splitlines()
                 if line.startswith("#") and not line.startswith("# "))


def kind_sequence(key: dict) -> tuple[str, ...]:
    def first(entry):
        return min((0 if ref.startswith("P") else 100) + int(ref[2:]) for ref in entry["refs"])
    return tuple(m["kind"] for m in sorted(key["mutants"], key=first))


def jacc(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def audit(docs: list[dict]) -> dict:
    if len(docs) < 2:
        raise ValueError("At least two documents are required for pairwise auditing.")
    pairs = list(itertools.combinations(range(len(docs)), 2))
    texts = [shingles(d["rfp"]) for d in docs]
    headings = [heading_skeleton(d["rfp"]) for d in docs]
    kinds = [kind_sequence(d["key"]) for d in docs]
    templates = [frozenset(m["template"] for m in d["key"]["mutants"]) for d in docs]
    scores = [jacc(texts[i], texts[j]) for i, j in pairs]
    worst = pairs[scores.index(max(scores))]
    return dict(documents=len(docs), pairs=len(pairs),
                identical_heading_pairs=sum(headings[i] == headings[j] for i, j in pairs),
                identical_kind_sequence_pairs=sum(kinds[i] == kinds[j] for i, j in pairs),
                identical_template_set_pairs=sum(templates[i] == templates[j] for i, j in pairs),
                five_gram_similarity=dict(min=round(min(scores), 4),
                                         mean=round(sum(scores) / len(scores), 4),
                                         max=round(max(scores), 4)),
                most_similar_pair=[docs[i]["id"] for i in worst])


def check(metrics: dict, baseline: dict | None = None) -> list[str]:
    failures = []
    for field in ("identical_heading_pairs", "identical_kind_sequence_pairs", "identical_template_set_pairs"):
        if metrics[field]:
            failures.append(f"{field} must be zero; observed {metrics[field]}")
    for field, limit in (("mean", MAX_MEAN_SIM), ("max", MAX_PAIR_SIM)):
        value = metrics["five_gram_similarity"][field]
        if value > limit:
            failures.append(f"Five-gram {field} similarity {value} exceeds {limit}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("generated", type=Path)
    parser.add_argument("keys", type=Path)
    args = parser.parse_args()
    pack = json.loads((args.generated / "case_pack.json").read_text(encoding="utf-8"))
    docs = [dict(id=c["id"], rfp=(args.generated / c["rfp"]).read_text(encoding="utf-8"),
                 key=json.loads((args.keys / Path(c["answer_key"]).name).read_text(encoding="utf-8")))
            for c in pack["cases"]]
    metrics = audit(docs)
    failures = check(metrics)
    print(json.dumps(dict(metrics=metrics, thresholds_passed=not failures, failures=failures), indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
