"""Verify exact English corpus size, diversity, integrity and scorer compatibility."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / "benchmark_v2", ROOT / "benchmark_v2" / "generator"):
    sys.path.insert(0, str(folder))
import independence_audit as audit
import prepare_study
import rfp_generator as generator


class PublicCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads((ROOT / "case_pack.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "public_manifest.json").read_text(encoding="utf-8"))
        cls.documents = []
        for entry in cls.pack["cases"]:
            text = (ROOT / entry["rfp"]).read_text(encoding="utf-8")
            key = json.loads((ROOT / entry["answer_key"]).read_text(encoding="utf-8"))
            cls.documents.append(dict(id=entry["id"], rfp=text, key=key,
                                      source_ids=sorted(set(re.findall(r"\[([PA]-\d{2})\]", text)))))

    def test_exact_count_and_location(self):
        self.assertEqual(100, len(list((ROOT / "rfp").glob("*.md"))))
        self.assertEqual(1, len(list((ROOT / "calibration").glob("*.md"))))
        self.assertEqual(100, sum(c["role"] == "test" for c in self.pack["cases"]))
        self.assertEqual(1, sum(c["role"] == "calibration" for c in self.pack["cases"]))
        self.assertEqual(101, len({c["id"] for c in self.pack["cases"]}))
        self.assertTrue(all(c["rfp"].startswith("rfp/") for c in self.pack["cases"] if c["role"] == "test"))

    def test_distinct_projects_and_presentation_styles(self):
        tests = [d for d in self.documents if d["key"]["generator"]["role"] == "test"]
        self.assertEqual(100, len({d["key"]["covariates"]["project"] for d in tests}))
        self.assertEqual(20, len({d["key"]["covariates"]["domain"] for d in tests}))
        self.assertEqual(20, len({d["key"]["covariates"]["persona"] for d in tests}))
        self.assertEqual(100, len({d["rfp"] for d in tests}))
        self.assertTrue(any("| Reference |" in d["rfp"] for d in tests))
        self.assertTrue(any("SHALL-" in d["rfp"] for d in tests))
        self.assertTrue(any("Article 1." in d["rfp"] for d in tests))
        self.assertTrue(any("How will your proposal" in d["rfp"] for d in tests))

    def test_english_content_and_integrity(self):
        hashes = {c["id"]: c["rfp_sha256"] for c in self.manifest["cases"]}
        self.assertEqual("en", self.manifest["language"])
        for document in self.documents:
            self.assertTrue(document["rfp"].isascii())
            self.assertIn("SYNTHETIC EVALUATION INPUT", document["rfp"])
            self.assertEqual(hashes[document["id"]],
                             hashlib.sha256(document["rfp"].encode()).hexdigest())
            for prefix in ("P", "A"):
                numbers = [int(value) for value in re.findall(rf"\[{prefix}-(\d{{2}})\]", document["rfp"])]
                self.assertEqual(list(range(1, len(numbers) + 1)), numbers)

    def test_diversity_thresholds_and_recorded_metrics(self):
        metrics = audit.audit(self.documents)
        self.assertEqual([], audit.check(metrics))
        stored = json.loads((ROOT / "diversity_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["metrics"], metrics)
        self.assertTrue(stored["thresholds_passed"])
        self.assertEqual(5050, metrics["pairs"])

    def test_all_keys_pass_instrument_checks(self):
        self.assertEqual([], [r["id"] for r in prepare_study.self_check(self.documents) if not r["ok"]])

    def test_reproducible_generation_and_overwrite_rejection(self):
        entry = self.pack["cases"][1]
        key = next(d["key"] for d in self.documents if d["id"] == entry["id"])
        generated = generator.generate_case(20261018, key["generator"]["index"],
                                            attempt=key["covariates"]["generation_attempt"])
        self.assertEqual((ROOT / entry["rfp"]).read_text(encoding="utf-8"), generated["rfp"])
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "generated"
            generator.write_batch(12, 2, out, Path(temporary) / "keys")
            with self.assertRaises(FileExistsError):
                generator.write_batch(12, 2, out, Path(temporary) / "keys")


if __name__ == "__main__":
    unittest.main()
