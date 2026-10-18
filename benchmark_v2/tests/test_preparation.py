from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PreparationTests(unittest.TestCase):
    def test_english_corpus_demo_collect_and_analysis_pipeline(self):
        generated_runner = ROOT / "bench_multicase.py"
        previous_source = generated_runner.read_bytes() if generated_runner.exists() else None
        try:
            with tempfile.TemporaryDirectory() as temporary:
                out = Path(temporary)
                pack = json.loads((ROOT / "case_pack.json").read_text(encoding="utf-8"))
                first = next(c["id"] for c in pack["cases"] if c["role"] == "test")
                commands = [
                    [str(ROOT / "benchmark_v2" / "run_cases_with_bench.py"),
                     "--cli", "codex", "--models", "offline-model", "--demo", "--runs", "1",
                     "--case-pack", str(ROOT / "case_pack.json"), "--sealed", str(ROOT / "oracle"),
                     "--only", first, "--out", str(out / "runs")],
                    [str(ROOT / "benchmark_v2" / "collect_results.py"),
                     str(out / "runs"), str(out / "rows.csv")],
                    [str(ROOT / "benchmark_v2" / "analysis" / "analyze_study.py"),
                     "--results", str(out / "rows.csv"), "--case-pack", str(ROOT / "case_pack.json"),
                     "--sealed", str(ROOT / "oracle"), "--rfp-dir", str(ROOT / "rfp"),
                     "--out", str(out / "analysis.json")],
                ]
                for command in commands:
                    result = subprocess.run([sys.executable, *command], cwd=ROOT,
                                            capture_output=True, text=True, timeout=60)
                    self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                analysis = json.loads((out / "analysis.json").read_text(encoding="utf-8"))
                self.assertEqual(3, analysis["n_rows"])
                self.assertEqual({"fixed": 1, "dynamic": 1, "frozen": 1}, analysis["mean_recall_by_policy"])
                self.assertEqual(1, analysis["reliability"]["frozen"]["completed"])
                self.assertEqual("Insufficient data (<3 cases)",
                                 analysis["contrasts"]["fixed_vs_frozen"]["primary_PP_recall"]["decision"])
        finally:
            if previous_source is None:
                generated_runner.unlink(missing_ok=True)
            else:
                generated_runner.write_bytes(previous_source)

    def test_agreement_cli_uses_only_supplied_csv_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            header = "vid,item_id,kind,found_0_1\n"
            (base / "one.csv").write_text(
                header + "v1,M01,risk,1\nv1,M02,risk,1\nv1,M03,risk,0\nv1,M04,risk,0\n",
                encoding="utf-8")
            (base / "two.csv").write_text(
                header + "v1,M01,risk,1\nv1,M02,risk,0\nv1,M03,risk,0\nv1,M04,risk,0\n",
                encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "benchmark_v2" / "validation" / "agreement.py"),
                 "--reviewer1", str(base / "one.csv"), "--reviewer2", str(base / "two.csv"),
                 "--out", str(base / "out")],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            report = json.loads((base / "out" / "agreement_report.json").read_text(encoding="utf-8"))
            self.assertEqual(4, report["n_items"])
            self.assertEqual(0.5, report["kappa"])
            self.assertEqual(1, report["items_to_adjudicate"])

    def test_preparation_wires_each_cli_without_model_execution(self):
        for backend in ("copilot", "claude", "codex"):
            with self.subTest(backend=backend), tempfile.TemporaryDirectory(dir=ROOT) as temporary:
                out = Path(temporary) / "study"
                completed = subprocess.run(
                    [sys.executable, str(ROOT / "benchmark_v2" / "prepare_study.py"),
                     "--cli", backend, "--models", "offline-model", "--n", "16",
                     "--seed", "20261016", "--out", str(out)],
                    cwd=ROOT, capture_output=True, text=True, timeout=90)
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                plan = json.loads((out / "study_plan.json").read_text(encoding="utf-8"))
                self.assertEqual(backend, plan["cli"])
                self.assertEqual(321, plan["calls_per_model"])
                smoke = (out / "1_smoke_test.ps1").read_text(encoding="utf-8")
                run = (out / "2_run_offline-model.ps1").read_text(encoding="utf-8")
                self.assertIn(f"--cli {backend}", smoke)
                self.assertIn(f"--cli {backend}", run)
                self.assertIn(f"{backend} --version", smoke)
                self.assertIn("Set-Location -LiteralPath '" + str(ROOT).replace("'", "''") + "'", smoke)
                self.assertTrue((out / "seal_manifest.json").exists())
                self.assertFalse((out / "results_cases").exists())


if __name__ == "__main__":
    unittest.main()
