"""Offline regression checks for generation, heuristic scoring and statistics."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "benchmark_v2", ROOT / "benchmark_v2" / "generator",
               ROOT / "benchmark_v2" / "analysis", ROOT / "benchmark_v2" / "validation"):
    sys.path.insert(0, str(folder))
import bench
import rfp_generator as generator
import scorer_v2 as scorer
import stats_core as stats
import prepare_study
import agreement


class InstrumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = [generator.generate_case(777, i) for i in range(1, 21)]

    def test_determinism(self):
        self.assertEqual(generator.generate_case(5, 3), generator.generate_case(5, 3))
        self.assertNotEqual(generator.generate_case(5, 3)["rfp"], generator.generate_case(6, 3)["rfp"])

    def test_structure(self):
        for case in self.cases:
            key, ids = case["key"], set(case["source_ids"])
            self.assertEqual(15, len(key["mutants"]))
            self.assertEqual(2, len(key["controls"]))
            self.assertEqual(3, len(key["decoys"]))
            self.assertEqual(15, len({m["id"] for m in key["mutants"]}))
            self.assertTrue(20 <= len(ids) <= 99)
            self.assertTrue({m["kind"] for m in key["mutants"]} <= bench.KINDS)
            self.assertTrue(all(set(m["refs"]) <= ids for m in key["mutants"] + key["decoys"]))

    def test_oracle_and_gate(self):
        for case in self.cases:
            report = generator.oracle_report(case)
            self.assertTrue(bench.gate(report, set(case["source_ids"]))["pass"])
            for options in scorer.VARIANTS.values():
                score = scorer.score(report, case["key"], **options)
                self.assertEqual(1, score["recall"])
                self.assertTrue(score["controls_ok"])
                self.assertEqual(0, score["false_alarm_n"])

    def test_empty_and_stuffed_reports(self):
        for case in self.cases:
            self.assertEqual(0, scorer.score({}, case["key"])["recall"])
            stuffed = prepare_study.stuffed(case["key"], case["source_ids"])
            self.assertEqual(0, scorer.score(stuffed, case["key"])["recall"])
            self.assertEqual(1, scorer.score(stuffed, case["key"], **scorer.VARIANTS["v1_original"])["recall"])

    def test_decoy_false_alarm(self):
        case = self.cases[0]
        decoy = case["key"]["decoys"][0]
        report = dict(findings=[dict(kind=decoy["kind"], source_refs=decoy["refs"],
                                    summary=" ".join(decoy["keywords_any"]))])
        self.assertEqual(1, scorer.score(report, case["key"])["false_alarm_n"])

    def test_one_to_one_assignment(self):
        case = self.cases[0]
        report = generator.oracle_report(case)
        self.assertEqual(1, scorer.score(report, case["key"], one_to_one=True)["recall"])


class StatisticsTests(unittest.TestCase):
    def test_sign_flip(self):
        self.assertEqual(0.25, stats.paired_signflip_p([1, 1, 1]))

    def test_failure_bounds(self):
        self.assertAlmostEqual(0.259, stats.exact_upper_no_failure(10), places=3)

    def test_holm(self):
        self.assertEqual({"a": 0.03, "b": 0.06, "c": 0.06}, stats.holm({"a": 0.01, "b": 0.04, "c": 0.03}))

    def test_stratified_permutation(self):
        import numpy as np
        cells = [("one", np.array([.8] * 3), np.array([.5] * 3)),
                 ("two", np.array([.7] * 3), np.array([.4] * 3))]
        probability, count = stats.stratified_permutation_p(cells)
        self.assertEqual(400, count)
        self.assertAlmostEqual(0.005, probability)

    def test_reviewer_agreement(self):
        self.assertEqual(0.5, agreement.cohen_kappa([1, 1, 0, 0], [1, 0, 0, 0]))


if __name__ == "__main__":
    unittest.main()
