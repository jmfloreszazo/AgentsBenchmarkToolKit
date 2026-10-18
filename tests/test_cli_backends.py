from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmark_v2"))
sys.path.insert(0, str(ROOT / "benchmark_v2" / "generator"))
import bench
import collect_results
import rfp_generator
import run_cases_with_bench as runner


class BackendTests(unittest.TestCase):
    def test_profiles_are_equivalent_and_render_for_all_backends(self):
        for stage in (*bench.STAGES, "team-designer"):
            copilot = bench.fixed_agent(stage, "offline-model").split("\n---\n", 1)[1].strip()
            claude = bench.fixed_agent(stage, "offline-model", "claude", "test-agent")
            codex = tomllib.loads(bench.fixed_agent(stage, "offline-model", "codex", "test-agent"))
            self.assertEqual(copilot, claude.split("\n---\n", 1)[1].strip())
            self.assertEqual(copilot, codex["developer_instructions"].strip())
            self.assertEqual("test-agent", codex["name"])
            self.assertEqual("offline-model", codex["model"])
            self.assertIn("name: test-agent", claude)
            self.assertIn("tools: []", claude)
        for cli in ("copilot", "claude", "codex"):
            rendered = bench.render_agent("test-agent", "Offline description",
                                          "Analyze the supplied RFP carefully and cite only existing anchors.",
                                          "offline-model", cli)
            if cli == "codex":
                self.assertEqual("test-agent", tomllib.loads(rendered)["name"])
            else:
                self.assertIn("tools: []", rendered)

    def test_codex_jsonl_failure_tools_and_provenance(self):
        events = [
            {"type": "item.started", "item": {"id": "c1", "type": "command_execution"}},
            {"type": "item.completed", "item": {"id": "c1", "type": "command_execution"}},
            {"type": "item.completed", "item": {"id": "a1", "type": "agent_message", "text": "{}"}},
            {"type": "turn.completed", "usage": {"input_tokens": 10}}]
        result = bench.parse_codex_response("\n".join(map(json.dumps, events)))
        self.assertEqual(1, result["tool_calls_observed"])
        self.assertEqual([], result["model_ids_reported"])
        self.assertEqual(10, result["usage"]["input_tokens"])
        for value in ("not json", "[]", '{"type":"turn.failed","error":{"message":"quota"}}',
                      '{"type":"error","message":"failed"}', '{"type":"turn.completed"}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bench.parse_codex_response(value)

    def test_invocation_rejects_tools_wrong_models_and_invalid_output(self):
        cases = [
            ("codex", '{"type":"item.completed","item":{"id":"c","type":"file_change"}}\n'
             '{"type":"item.completed","item":{"type":"agent_message","text":"{}"}}\n'
             '{"type":"turn.completed"}', 97),
            ("codex", '{"type":"item.completed","model":"other","item":{"type":"agent_message","text":"{}"}}\n'
             '{"type":"turn.completed"}', 96),
            ("claude", '{"type":"result","is_error":true,"subtype":"error","result":""}', 98),
            ("copilot", "invalid output", 98)]
        with tempfile.TemporaryDirectory() as temporary:
            wd = Path(temporary)
            directory = wd / ".codex" / "agents"
            directory.mkdir(parents=True)
            (directory / "test.toml").write_text(bench.fixed_agent("audit", "test-model", "codex"), encoding="utf-8")
            for cli, stdout, expected in cases:
                with self.subTest(cli=cli, expected=expected), patch.object(
                    bench, "cli_command", return_value=["offline"]), patch.object(
                        bench, "run_process", return_value=dict(exit=0, stdout=stdout, stderr="", timeout=False, seconds=0)):
                    result = bench.invoke("test", "RFP", "test-model", wd, wd / "logs", "call", 10, cli)
                    self.assertEqual(expected, result["exit"])
                    self.assertTrue(result["stderr"])
            with patch.object(bench, "cli_command", return_value=["missing"]), patch.object(
                    bench, "run_process", side_effect=FileNotFoundError("missing executable")):
                result = bench.invoke("test", "RFP", "test-model", wd, wd / "logs", "missing", 10, "codex")
                self.assertEqual(99, result["exit"])
                self.assertIn("launch failed", result["stderr"])

    def test_command_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            wd = Path(temporary)
            directory = wd / ".claude" / "agents"
            directory.mkdir(parents=True)
            (directory / "test.md").write_text(
                bench.fixed_agent("audit", "test-model", "claude", "test"), encoding="utf-8")
            claude = bench.cli_command("claude", "test", "RFP", "test-model", wd)
            self.assertIn("--bare", claude)
            self.assertEqual("", claude[claude.index("--tools") + 1])
            codex = bench.cli_command("codex", "test", "RFP", "test-model", wd)
            self.assertIn("--ignore-user-config", codex)
            self.assertEqual("read-only", codex[codex.index("--sandbox") + 1])
            self.assertIn("features.shell_tool=false", codex)
            self.assertIn('web_search="disabled"', codex)
            self.assertEqual("-", codex[-1])
            self.assertIn("--deny-tool=read", bench.cli_command("copilot", "test", "RFP", "test-model", wd))
            with self.assertRaises(ValueError):
                bench.agent_location("unknown")

    def test_unknown_case_is_rejected_before_any_model_call(self):
        with patch.object(sys, "argv", [
                "runner", "--cli", "codex", "--models", "offline-model", "--only", "missing",
                "--case-pack", str(ROOT / "case_pack.json")]), \
                patch.object(runner, "make_patched_bench"), \
                patch.object(runner.importlib, "import_module"), \
                patch.object(runner, "design_frozen_heldout") as designer:
            with self.assertRaises(SystemExit) as failure:
                runner.main()
            self.assertEqual(2, failure.exception.code)
            designer.assert_not_called()

    def test_subprocess_input_and_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            wd = Path(temporary)
            result = bench.run_process(
                [sys.executable, "-c", "import sys; print(len(sys.stdin.read()))"], wd, 10, "RFP" * 50000)
            self.assertEqual(0, result["exit"])
            self.assertEqual("150000", result["stdout"].strip())
            result = bench.run_process([sys.executable, "-c", "import time; time.sleep(30)"], wd, 0.2)
            self.assertTrue(result["timeout"])
            self.assertIsNone(result["exit"])

    def test_all_policies_with_local_cli_subprocesses(self):
        generated = ROOT / "bench_multicase.py"
        previous_source = generated.read_bytes() if generated.exists() else None
        original_module = sys.modules.pop("bench_multicase", None)
        try:
            runner.make_patched_bench()
            bm = importlib.import_module("bench_multicase")
            real_run = bm.run_process
            native_command = bm.cli_command
            for cli in ("copilot", "claude", "codex"):
                with self.subTest(cli=cli), tempfile.TemporaryDirectory() as temporary:
                    base = Path(temporary)
                    rfp_generator.write_batch(11, 2, base / "generated", base / "sealed")
                    calls = []

                    def command(backend, agent, prompt_text, model, wd):
                        native_command(backend, agent, prompt_text, model, wd)
                        self.assertFalse(any("answer_key" in p.name for p in wd.rglob("*")))
                        calls.append(agent)
                        return [sys.executable, str(ROOT / "tests" / "fake_backend.py"), backend, model, agent]

                    def process(cmd, wd, timeout, input_text=None):
                        if cmd[1:] == ["--version"]:
                            return dict(exit=0, stdout="offline-fixture 1.0", stderr="", timeout=False, seconds=0)
                        return real_run(cmd, wd, timeout, input_text)

                    argv = ["runner", "--cli", cli, "--models", "offline-model",
                            "--case-pack", str(base / "generated" / "case_pack.json"),
                            "--sealed", str(base / "sealed"), "--out", str(base / "out"),
                            "--runs", "1", "--timeout", "10"]
                    with patch.object(sys, "argv", argv), patch.object(bm, "cli_command", side_effect=command), \
                            patch.object(bm, "run_process", side_effect=process), \
                            patch.object(bm.shutil, "which", return_value=sys.executable):
                        self.assertEqual(0, runner.main())
                    self.assertEqual(21, len(calls))
                    self.assertEqual(1, sum(a.startswith("heldout-") for a in calls))
                    records = list((base / "out").glob("*/*/*/[0-9][0-9]_*/record.json"))
                    self.assertEqual(6, len(records))
                    for path in records:
                        record = json.loads(path.read_text(encoding="utf-8"))
                        self.assertEqual("ok", record["status"])
                        self.assertEqual(cli, record["cli"])
                        if record["arm"] == "frozen":
                            self.assertEqual(3, len(record["calls"]))
                        if cli == "codex":
                            self.assertFalse(record["model_identity_evidenced"])
                    rows = collect_results.collect(base / "out", base / "rows.csv")
                    self.assertEqual(6, len(rows))
                    self.assertTrue(all(row["cli"] == cli for row in rows))
                    frozen_dir = base / "out" / "_frozen_heldout" / cli / "offline-model"
                    with self.assertRaises(ValueError):
                        runner.design_frozen_heldout(bm, "different-model", "RFP", 10, frozen_dir, cli)
        finally:
            sys.modules.pop("bench_multicase", None)
            if original_module is not None:
                sys.modules["bench_multicase"] = original_module
            if previous_source is None:
                generated.unlink(missing_ok=True)
            else:
                generated.write_bytes(previous_source)


if __name__ == "__main__":
    unittest.main()
