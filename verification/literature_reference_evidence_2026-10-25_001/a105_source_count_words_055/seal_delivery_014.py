"""Authenticate final owned delta and public synthetic runtime outcomes."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = OUT / "frozen_checks_012"
FILES = ["gene_annotation_episode/literature_kinetic_inputs.py", "gene_annotation_episode/literature_kinetic_validation.py",
    "gene_annotation_episode/literature_kinetic_storage.py", "gene_annotation_episode/literature_experimental_prompt.py",
    "tests/test_literature_kinetic_inputs.py", "tests/test_literature_kinetic_integration.py",
    "tests/test_literature_kinetic_count_inputs.py", "tests/test_literature_kinetic_count_integration.py"]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def main():
    terminal = json.loads((RUN / "TERMINAL_RECEIPT.json").read_bytes())
    worker = json.loads((RUN / "WORKER_RECEIPT.json").read_bytes())
    assert terminal["exit_code"] == worker["pytest_exit_code"] == 0
    pin = RUN / "pin"
    manifest_raw = (pin / "PIN_MANIFEST.json").read_bytes()
    assert digest(manifest_raw) == terminal["pin_manifest_sha256"] == worker["pin_manifest_sha256"]
    manifest = json.loads(manifest_raw)
    for name, row in manifest["files"].items():
        raw = (pin / name).read_bytes()
        assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], name
    assert worker["C7_binding_before_after_exact"] and worker["all_manifested_files_exact_before_after"]
    test_summary = re.search(r"(?m)^(\d+) passed in ([0-9.]+)s", (RUN / "TERMINAL.log").read_text())
    assert test_summary
    patch, rows = [], {}
    reconstructed = OUT / "reconstructed_014"
    reconstructed.mkdir()
    for name in FILES:
        raw = (ROOT / name).read_bytes()
        assert digest(raw) == manifest["files"][name]["sha256"], name
        baseline = OUT / "renderer_proposal_009/baseline.py" if name.endswith("literature_experimental_prompt.py") else OUT / "baseline_001" / name
        original = baseline.read_bytes() if baseline.exists() else b""
        if baseline.exists():
            dest = reconstructed / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as stream:
                stream.write(original)
        destination = OUT / "snapshot_014" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(raw)
        patch.append("".join(difflib.unified_diff(original.decode().splitlines(True), raw.decode().splitlines(True),
            fromfile="a/" + name if baseline.exists() else "/dev/null", tofile="b/" + name)))
        rows[name] = {"bytes": len(raw), "sha256": digest(raw), "baseline": str(baseline) if baseline.exists() else None,
            "baseline_sha256": digest(original) if baseline.exists() else None}
    patch_path = OUT / "FINAL_PATCH_014.diff"
    with patch_path.open("x") as stream:
        stream.write("".join(patch))
    applied = subprocess.run(["patch", "-p1", "--batch", "-i", str(patch_path)], cwd=reconstructed, capture_output=True, text=True)
    assert applied.returncode == 0, applied.stdout + applied.stderr
    for name, row in rows.items():
        assert digest((reconstructed / name).read_bytes()) == row["sha256"], name
    def helper(path):
        return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "_witness_label"), include_attributes=False)
    storage = "gene_annotation_episode/literature_kinetic_storage.py"
    assert helper(OUT / "baseline_001" / storage) == helper(OUT / "snapshot_014" / storage)
    renderer = ROOT / "gene_annotation_episode/literature_experimental_prompt.py"
    assert renderer.read_bytes() == (OUT / "renderer_proposal_009/proposed.py").read_bytes()
    scientific_tasks = []
    def tasks(path):
        return {target.id: ast.literal_eval(node.value) for node in ast.parse(path.read_text()).body if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name) and "TASK" in target.id}
    assert tasks(renderer) == tasks(OUT / "renderer_proposal_009/baseline.py")
    scientific_tasks = sorted(tasks(renderer))
    runtime = []
    # Only own controlled-test public counters and already admitted typed cells.
    # No model-call table, private provider history or source text is queried.
    for database in sorted((RUN / "pytest").rglob("state.sqlite3")):
        with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"runtime_actions", "runtime_observations", "literature_kinetic_received"} <= tables:
                continue
            if "test_selected_episode_returns_" not in str(database) and "test_original_c4_count_" not in str(database):
                continue
            received = [json.loads(row[0]) for row in db.execute("SELECT cells FROM literature_kinetic_received")]
            values = [{"component": row["component"], "count": row["numerator"]["uncertainty_values"]["count"],
                "count_reported_value": row["numerator"]["uncertainty_values"]["count_reported_value"],
                "count_status": row["numerator"]["uncertainty"]["count_reading_status"],
                "count_relation": row["numerator"]["uncertainty"]["count_relation"]} for rows_ in received for row in rows_]
            runtime.append({"database": str(database.relative_to(RUN)),
                "actions": db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0],
                "observations": db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0],
                "populations": db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0],
                "actual_action_credits": [row[0] for row in db.execute("SELECT credit FROM runtime_actions ORDER BY rowid")],
                "admitted_typed_values": values})
    ordinary = [row for row in runtime if row["observations"] == 3]
    c4 = [row for row in runtime if row["observations"] == 0]
    assert len(ordinary) == 4 and len(c4) == 1
    assert all(row["actions"] == 3 and row["populations"] == 1 and all(v == 0 for v in row["actual_action_credits"]) for row in ordinary)
    save(OUT / "RUNTIME_PUBLIC_AUDIT_014.json", {"scope": "own synthetic tests only, independent read-only public counters/typed cells", "cases": runtime})
    helper_name = "gene_annotation_episode/literature_binding_interaction_render.py"
    result = {"passed": True, "owned_files": rows, "patch_sha256": digest(patch_path.read_bytes()),
        "eight_files_reconstructed_exactly": True, "054_display_helper_AST_exact": True,
        "renderer_exact_009_delta": True, "scientific_TASK_constants_exact": scientific_tasks,
        "pin_files_verified": len(manifest["files"]), "pin_manifest_sha256": digest(manifest_raw),
        "terminal": test_summary.group(0), "C7_binding_stable_in_executed_pin": True,
        "executed052_binding_helper_sha256": manifest["files"][helper_name]["sha256"],
        "current052_binding_helper_sha256": digest((ROOT / helper_name).read_bytes()),
        "all_current_head_verification_claim": False,
        "scope": "055 code-only count reader/native producer/typed/provider/C4 engineering work; no paper/model/A105/W05 completion"}
    save(OUT / "FINAL_DELIVERY_RECEIPT_014.json", result)
    print(json.dumps({"passed": True, "reconstructed_files": len(rows), "pin_files_verified": len(manifest["files"]),
        "terminal": test_summary.group(0), "ordinary_episode_cases": len(ordinary), "original_c4_case": len(c4)}))


if __name__ == "__main__":
    main()
