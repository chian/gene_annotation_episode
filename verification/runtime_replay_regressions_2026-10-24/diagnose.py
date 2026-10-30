"""Run the two unchanged regressions with trace evidence and a memory-only baseline.

The baseline deletes only the completed-observation reuse block added to
Workflow.controller_value. Shared source and test files are never edited.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import inspect
import json
from pathlib import Path
import sqlite3
import sys
import textwrap
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
import gene_annotation_episode.runtime as runtime


NODES = [
    "tests/test_runtime.py::test_resume_recovers_published_operation_before_runtime_response",
    "tests/test_runtime.py::test_caller_native_resource_changes_preserve_original_history_on_resume",
]
FILES = [
    "gene_annotation_episode/runtime.py",
    "gene_annotation_episode/composition_information.py",
    "gene_annotation_episode/episode_journal.py",
    "gene_annotation_episode/application_execution_binding.py",
    "gene_annotation_episode/decision_context.py",
    "gene_annotation_episode/boundary_validation.py",
    "method_loop/episode.py", "method_loop/runtime.py", "method_loop/archive.py",
    "tests/test_runtime.py", "pyproject.toml",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return {name: digest(ROOT / name) for name in FILES}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def snapshot_db(path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    tables = {}
    for name in ("synthetic_records", "synthetic_operations", "runtime_runs",
                 "runtime_episodes", "runtime_model_calls", "runtime_actions",
                 "runtime_observations", "runtime_estimation_contexts",
                 "runtime_decision_exchanges"):
        if name in names:
            tables[name] = [dict(row) for row in db.execute(f"SELECT * FROM {name}")]
    db.close()
    return tables


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["current", "before_controller_input_reuse"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = hashes()
    original = textwrap.dedent(inspect.getsource(runtime.Workflow.controller_value))
    expected_start = "    observed = self.store.db.execute("
    start = original.index(expected_start)
    stop = original.index('    value = {"credit": credit}\n', start)
    baseline = original[:start] + original[stop:]
    # The baseline has exactly the pre-change remainder; it preserves native
    # estimation, practical completion and ordinary unobserved-action accounting.
    assert baseline.startswith('def controller_value(self, source, index, credit):\n    value = {"credit": credit}\n')
    assert "recorded controller input does not match its action" not in baseline
    (output / "current_controller_value.py").write_text(original)
    (output / "before_controller_input_reuse.py").write_text(baseline)
    (output / "memory_only_baseline.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(keepends=True), baseline.splitlines(keepends=True),
        fromfile="current Workflow.controller_value",
        tofile="before completed-observation reuse")))
    if args.mode == "before_controller_input_reuse":
        namespace = {}
        exec(compile(baseline, str(output / "before_controller_input_reuse.py"), "exec"),
             runtime.__dict__, namespace)
        runtime.Workflow.controller_value = namespace["controller_value"]

    code_names = {
        runtime.DecisionSource.call.__code__: "DecisionSource.call",
        runtime.DecisionSource.apply_response.__code__: "DecisionSource.apply_response",
        runtime.DecisionSource.execute.__code__: "DecisionSource.execute",
        runtime.Workflow.execute.__code__: "Workflow.execute",
        runtime.Workflow.controller_value.__code__: "Workflow.controller_value",
        runtime.ExecutionContextController._observe.__code__: "ExecutionContextController._observe",
        runtime.Journal.save.__code__: "Journal.save",
    }
    events = []
    counts = Counter()
    current_test = None

    def profile(frame, event, value):
        if event not in ("call", "return"):
            return
        code = frame.f_code
        name = code_names.get(code)
        if (name is None and code.co_filename == str(ROOT / "tests/test_runtime.py")
                and code.co_name in {"execute", "complete", "crash_once"}):
            name = "Fixture." + code.co_name
        if name is None:
            return
        key = f"{current_test}:{name}:{event}"
        counts[key] += 1
        local = frame.f_locals
        row = {"test": current_test, "function": name, "event": event}
        if name == "Journal.save" or name == "Fixture.crash_once":
            row.update(table=local.get("table"), has_result=bool(local.get("values", {}).get("result")))
        elif name == "DecisionSource.apply_response":
            source = local["self"]
            row.update(index=local["index"], path=source.path,
                selection=local["response"].get("selection"),
                schema_action_kinds=[branch["properties"]["kind"]["const"]
                    for branch in local["schema"]["properties"]["selection"]["anyOf"]],
                feedback=deepcopy(source.feedback), returned_type=type(value).__name__ if event == "return" else None)
        elif name == "DecisionSource.call":
            row.update(calls=local["self"].calls, path=local["self"].path)
        elif name == "Fixture.complete":
            row.update(episode_id=local.get("episode_id"), feedback=local.get("context", {}).get("feedback"))
        events.append(deepcopy(row))

    class Recorder:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_call(self, item):
            nonlocal current_test
            current_test = item.nodeid
            sys.setprofile(profile)
            try:
                yield
            finally:
                sys.setprofile(None)

    pytest_args = [*NODES, "-vv", "--tb=long", "-p", "no:cacheprovider",
        f"--basetemp={output / 'pytest-temp'}", f"--junitxml={output / 'pytest.xml'}"]
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    exit_code = int(pytest.main(pytest_args, plugins=[Recorder()]))
    after = hashes()
    write_json(output / "trace.json", {"events": events, "counts": dict(counts)})
    databases = {}
    for path in sorted((output / "pytest-temp").glob("*/state.db")):
        if path.parent.is_symlink():
            continue
        data = snapshot_db(path)
        name = path.parent.name
        write_json(output / (name + ".database.json"), data)
        databases[name] = {table: len(rows) for table, rows in data.items()}
    write_json(output / "RUN.json", {
        "command": [sys.executable, str(Path(__file__).resolve()), args.mode, str(args.output)],
        "cwd": str(ROOT), "pytest_arguments": pytest_args, "mode": args.mode,
        "python": sys.version, "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - tick, "exit_code": exit_code,
        "source_sha256_before": before, "source_sha256_after": after,
        "source_versions_unchanged": before == after,
        "controller_method_sha256": hashlib.sha256((original if args.mode == "current" else baseline).encode()).hexdigest(),
        "database_row_counts": databases,
        "verification_boundary": "unchanged scripted tests; no model, network, native scientific execution, or production/test source edits",
    })
    assert before == after, "shared inspected source changed while diagnostic was running"
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
