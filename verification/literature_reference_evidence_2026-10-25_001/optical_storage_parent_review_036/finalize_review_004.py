"""Final independent generation/preservation audit, without scientific execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
OWNER = BASE / "optical_storage_036"
PIN = BASE / "literature_model_run_030/pin_001"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def methods(path):
    text = path.read_text()
    cls, = [node for node in ast.parse(text).body if isinstance(node, ast.ClassDef) and node.name == "WorkflowServices"]
    return {node.name: ast.get_source_segment(text, node) for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def tasks(path):
    return {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(path.read_text()).body
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"EXPERIMENTAL_TASK", "SAVED_NUMERICAL_RETURN_TASK"}}


def verify_pin(pin):
    manifest = json.loads((pin / "SOURCE_MANIFEST.json").read_bytes())
    for row in manifest["files"]:
        path = pin / row["pin_relative_path"]
        assert path.stat().st_size == row["size"] and sha(path) == row["sha256"]
    actual = {str(path.relative_to(pin)) for path in pin.rglob("*")
              if path.is_file() and path != pin / "SOURCE_MANIFEST.json"}
    assert actual == {row["pin_relative_path"] for row in manifest["files"]}
    return {"file_count": len(manifest["files"]), "manifest_sha256": sha(pin / "SOURCE_MANIFEST.json")}


def main():
    receipt = json.loads((OWNER / "FINAL_RECEIPT_004.json").read_bytes())
    expected = json.loads((OWNER / "CODE_CHECKPOINT_004_SHA256.json").read_bytes())
    assert receipt["sha256"] == expected and receipt["exit_code"] == 0
    assert receipt["terminal_result"] == "120 passed in 239.20s"
    log = (OWNER / receipt["stdout_stderr"]).read_text()
    assert log.rstrip().splitlines()[-1].startswith("120 passed in 239.20s")
    for name, digest in {**expected, **receipt["frozen_dependencies_sha256"]}.items():
        assert sha(ROOT / name) == digest, name
    rebuild = OUT / "checkpoint_004"
    rebuild.mkdir(exist_ok=False)
    for path in (OWNER / "baseline").rglob("*"):
        if path.is_file():
            target = rebuild / path.relative_to(OWNER / "baseline")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    patched = subprocess.run(["patch", "--batch", "--no-backup-if-mismatch", "-p1", "-i",
        str(OWNER / "OWNED_DIFF_CHECKPOINT_004.patch")], cwd=rebuild, capture_output=True, text=True)
    assert patched.returncode == 0, patched.stdout + patched.stderr
    for name, digest in expected.items():
        assert sha(rebuild / name) == digest, name
    before = methods(OWNER / "baseline/gene_annotation_episode/episode_services.py")
    after = methods(ROOT / "gene_annotation_episode/episode_services.py")
    assert all(after[name] == value for name, value in before.items())
    assert set(after) - set(before) == {"literature_optical_repository"}
    assert tasks(OWNER / "baseline/gene_annotation_episode/literature_experimental_prompt.py") == tasks(
        ROOT / "gene_annotation_episode/literature_experimental_prompt.py")
    assert (ROOT / "gene_annotation_episode/literature_reference_parent_prompt.py").read_bytes() == (
        PIN / "gene_annotation_episode/literature_reference_parent_prompt.py").read_bytes()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    probe = subprocess.run([sys.executable, "-P", "-B", "-c",
        "import sys,json;sys.path.insert(0,sys.argv[1]);"
        "from gene_annotation_episode.literature_episodes import _population_catalog;"
        "print(json.dumps(_population_catalog(),sort_keys=True,allow_nan=False))", str(PIN)],
        env=environment, capture_output=True, text=True, check=True)
    original_catalog = json.loads(probe.stdout)
    from gene_annotation_episode.literature_episodes import _population_catalog
    current_catalog = _population_catalog()
    assert len(original_catalog) == 16 and len(current_catalog) == 17
    assert current_catalog[:16] == original_catalog
    assert current_catalog[16]["name"] == "literature.optical.populate"
    pins = {label: verify_pin(BASE / f"literature_model_run_{label}/pin_001") for label in ("024", "030")}
    for name, digest in expected.items():
        assert sha(ROOT / name) == digest
    result = {"status": "passed", "utc": datetime.now(timezone.utc).isoformat(),
        "generation": "004", "meaning": "Independent full reviewed generation, terminal evidence and preservation verification; no root redundant test repeat or scientific/model execution",
        "owner_terminal_result": receipt["terminal_result"], "owner_exit_code": receipt["exit_code"],
        "terminal_log_sha256": sha(OWNER / receipt["stdout_stderr"]),
        "owner_receipt_sha256": sha(OWNER / "FINAL_RECEIPT_004.json"),
        "owned_files_reconstructed_and_hash_verified": expected,
        "frozen_dependencies_verified": receipt["frozen_dependencies_sha256"],
        "prior_service_method_count_unchanged": len(before),
        "prior16_catalog_entries_equal_to_immutable030": True,
        "original_catalog_sha256": hashlib.sha256(probe.stdout.encode()).hexdigest(),
        "scientific_task_constants_unchanged": True,
        "source_evidence_parent_module_unchanged": True,
        "old_actual_run_pins_verified": pins,
        "reviewed_scope": "Complete002 module/tests/shared changes plus complete454-line003 and177-line004 deltas,004 interface addendum,final receipt and implementation limits",
        "limits": receipt["limits"], "script_sha256": sha(Path(__file__))}
    with (OUT / "FINAL_PARENT_REVIEW_004.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "owned_hashes_verified": len(expected),
        "prior_service_methods_unchanged": len(before), "prior_catalog_entries_unchanged": 16,
        "old_pins": pins, "owner_terminal_result": receipt["terminal_result"]}))


if __name__ == "__main__":
    main()
