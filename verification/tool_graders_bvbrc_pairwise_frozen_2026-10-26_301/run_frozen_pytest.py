"""Verify isolated imports, then execute the exact existing five-test module."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

EVIDENCE = Path(__file__).resolve().parent
SNAPSHOT = EVIDENCE / "snapshot"
CHECK = SNAPSHOT / "verification/frozen_check_001"
TEST = SNAPSHOT / "tests/test_bvbrc_homology_pairwise_workflow.py"


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def source_check(phase):
    manifest = json.loads((EVIDENCE / "SOURCE_SNAPSHOT_MANIFEST.json").read_text())
    assert manifest["source_and_copy_stable"] is True
    differences = []
    for row in manifest["files"]:
        path = Path(row["copied_path"])
        observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if observed != row["sha256"]:
            differences.append({"copied_path": str(path), "expected": row["sha256"], "observed": observed})
    result = {"phase": phase, "at": datetime.now(timezone.utc).isoformat(),
        "files_checked": len(manifest["files"]), "differences": differences, "unchanged": not differences}
    write(CHECK / ("source_" + phase + ".json"), result)
    if differences:
        raise RuntimeError("immutable_snapshot_changed:" + phase)
    return result


def verify_imports(phase):
    modules = {}
    failures = []
    for name, module in sorted(sys.modules.items()):
        if not (name == "gene_annotation_episode" or name.startswith("gene_annotation_episode.")
                or name == "method_loop" or name.startswith("method_loop.")
                or (SNAPSHOT / "tests" / (name + ".py")).is_file()):
            continue
        filename = getattr(module, "__file__", None)
        if filename is None:
            failures.append({"module": name, "reason": "missing_module_file"})
            continue
        path = Path(filename).resolve()
        modules[name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        if not path.is_relative_to(SNAPSHOT):
            failures.append({"module": name, "path": str(path), "reason": "outside_snapshot"})
    result = {"phase": phase, "at": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable, "python_version": sys.version,
        "cwd": str(Path.cwd()), "sys_path": sys.path, "modules": modules,
        "module_count": len(modules), "failures": failures,
        "all_project_and_fixture_imports_copied": not failures}
    write(CHECK / ("imports_" + phase + ".json"), result)
    if failures:
        raise RuntimeError("mutable_source_import_detected")
    return result


class VerificationPlugin:
    def pytest_collection_finish(self, session):
        paths = {Path(str(item.path)).resolve() for item in session.items}
        if paths != {TEST} or len(session.items) != 5:
            raise RuntimeError("unexpected_pairwise_test_selection")
        verify_imports("collection")
        write(CHECK / "collected_tests.json", {"tests": [item.nodeid for item in session.items]})
        print("FROZEN_IMPORTS_VERIFIED", flush=True)


def main():
    if Path.cwd().resolve() != SNAPSHOT:
        raise RuntimeError("snapshot_cwd_required")
    source_check("before")
    import gene_annotation_episode
    import method_loop
    import pytest
    verify_imports("preflight")
    print("SNAPSHOT_PRECHECK_OK", flush=True)
    code = pytest.main(["-vv", "-p", "no:cacheprovider", str(TEST),
        "--basetemp", str(CHECK / "temporary/pytest"), "--junitxml", str(CHECK / "junit.xml")],
        plugins=[VerificationPlugin()])
    verify_imports("after")
    source_check("after")
    write(CHECK / "runner_result.json", {"pytest_exitcode": int(code),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_after_unchanged": True, "test_file_unmodified": True})
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
