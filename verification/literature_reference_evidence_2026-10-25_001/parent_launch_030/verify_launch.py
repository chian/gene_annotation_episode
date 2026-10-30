"""Prospective custody/import check; no model calls or workflow state creation."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys


BASE = Path(__file__).resolve().parents[1]
PIN = BASE / "literature_model_run_030/pin_001"
OLD = BASE / "literature_model_run_024/pin_001"
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runner = PIN / "runner/run_literature_source_job_019.py"
    assert sha(runner) == "45dd9a8fd93ce1777358cd7a23f3a25ead609aa23a56d0699a65c0c640c02a70"
    assert sha(PIN / "SOURCE_MANIFEST.json") == "2616012239523f24d41ce1c9d04d08ab7bd6c75ee7f1e10943172e39b090c2df"
    spec = importlib.util.spec_from_file_location("pinned_source_runner", runner)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    adapter.configure_pin(PIN)
    manifest = adapter.verify_pin(PIN)
    old_manifest = adapter.verify_pin(OLD)
    metadata, job = adapter.load_inputs(PIN)
    old_metadata, old_job = adapter.load_inputs(OLD)
    assert metadata == old_metadata and job == old_job
    assert not (BASE / "literature_model_run_030/live_001").exists()
    assert len(manifest["files"]) == 658 and len(old_manifest["files"]) == 637
    offline_path = BASE / "literature_model_run_030/offline_001/RECEIPT.json"
    offline = json.loads(offline_path.read_bytes())
    assert offline["status"] == "passed" and not offline["attempted_model_calls"]
    assert offline["pin_manifest_sha256"] == sha(PIN / "SOURCE_MANIFEST.json")
    from gene_annotation_episode.providers import load_config
    from gene_annotation_episode.state import Store
    from method_loop.episode import Episode
    from method_loop.durable import DurableExecutionStore
    models = adapter.selected_models(load_config())
    assert models == offline["models"]
    roots = [str(Path(inspect.getfile(DurableExecutionStore)).resolve().parent.parent),
             *(str(Path(entry or os.getcwd()).resolve()) for entry in sys.path)]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(roots))
    probe = subprocess.run([sys.executable, "-P", "-B", "-c",
        "import inspect,json; from gene_annotation_episode.state import Store; "
        "from gene_annotation_episode.independent_execution import open_commission; "
        "from method_loop.episode import Episode; import method_loop.durable_worker as worker; "
        "print(json.dumps([inspect.getfile(x) for x in (Store,Episode,worker,inspect.unwrap(open_commission))]))"],
        env=environment, check=True, capture_output=True, text=True)
    worker_paths = json.loads(probe.stdout)
    assert len(worker_paths) == 4 and all(Path(path).resolve().is_relative_to(PIN) for path in worker_paths)
    imported = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and name.split(".")[0] in {"gene_annotation_episode", "method_loop"}:
            path = Path(filename).resolve()
            assert path.is_relative_to(PIN), (name, str(path))
            imported.append({"module": name, "path": str(path), "sha256": sha(path)})
    adapter.verify_pin(PIN)
    adapter.verify_pin(OLD)
    result = {"status": "passed", "utc": datetime.now(timezone.utc).isoformat(),
        "meaning": "Prospective pin, unchanged job/input/model and safe-path worker import verification only",
        "pin_files_verified": len(manifest["files"]), "old_pin_files_verified": len(old_manifest["files"]),
        "pin_manifest_sha256": sha(PIN / "SOURCE_MANIFEST.json"),
        "old_pin_manifest_sha256": sha(OLD / "SOURCE_MANIFEST.json"),
        "runner_sha256": sha(runner), "unchanged_input_metadata_and_job": True,
        "models": models, "worker_probe_imports": worker_paths, "runtime_imports": imported,
        "offline_receipt_sha256": sha(offline_path), "new_workflow_started": False,
        "scientific_source_bytes_interpreted": False,
        "script_sha256": sha(Path(__file__))}
    with (OUT / "PRELAUNCH_RECEIPT.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "pin_files_verified": len(manifest["files"]),
        "old_pin_files_verified": len(old_manifest["files"]), "worker_probe_imports": worker_paths,
        "runtime_imports_verified": len(imported), "models": models}))


if __name__ == "__main__":
    main()
