"""Check corrected numerical assertions against an already closed Workflow.

This is a separate retained-record verification, not a rerun of Workflow or a
replacement for its original pytest result. Native work, parsing, calculations,
model/episode construction and database mutation are forbidden here.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

import pytest
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_bvbrc_phylogeny_host_integration import supplied, configured
from test_bvbrc_phylogeny_returns import forbid_acquisition_or_scientific_work
from test_bvbrc_phylogeny_composed_workflow import (
    source_provenance, test_native_numbers_and_only_requested_facts_reach_both_parents,
)
from test_public_search import Client


def read(directory, filename):
    return json.loads((directory / filename).read_text())


def digest_database(store):
    # Hash logical SQL content, rather than SQLite's transient WAL/checkpoint.
    return hashlib.sha256("\n".join(store.db.iterdump()).encode()).hexdigest()


def main():
    directory = Path(sys.argv[1]).resolve()
    original_manifest = read(directory, "SOURCE_PROVENANCE.json")
    assert original_manifest == read(directory, "SOURCE_PROVENANCE_AFTER.json")
    current = source_provenance(original_manifest)
    changed = [path for path, sha in current["files"].items()
               if sha != original_manifest["files"][path]]
    assert changed == [str(ROOT / "tests/test_bvbrc_phylogeny_composed_workflow.py")], changed
    archive = read(directory, "archive.json")
    science = archive["units"][0]["child"]
    results = science["units"][3]["child"]
    body = read(directory, "publication.json")
    saved = read(directory, "selected-inputs.json")
    case = supplied(read(directory, "PROVENANCE.json")["mode"])
    case.request, case.selector = saved["request"], saved["selector"]

    def forbidden(*args, **kwargs):
        raise AssertionError("Retained numerical check attempted new execution")

    with pytest.MonkeyPatch.context() as patch, Store(directory / "state") as store:
        forbid_acquisition_or_scientific_work(patch)
        patch.setattr(Workflow, "build", forbidden)
        patch.setattr("socket.socket.connect", forbidden)
        patch.setattr("socket.socket.connect_ex", forbidden)
        patch.setattr("subprocess.run", forbidden)
        store.db.execute("PRAGMA query_only=ON")
        original_database = digest_database(store)
        registry = ToolRegistry(store, clients=Client())
        api = APIServiceExecution(store, run_id=body["run_id"], directory=directory / "run",
            configuration={"selected-api": configured(case.module)}, tool_registry=registry,
            handoff_unit=2, acquired_record_unit=3)
        for name in ("rpc", "task_info", "download"):
            patch.setattr(api.services["selected-api"].client, name, forbidden)
        assert api.read_result(body["reference"], body["scope"]) == body
        retained = SimpleNamespace(directory=directory, store=store, api=api, case=case,
            workflow=SimpleNamespace(run_id=body["run_id"]), archive=archive,
            science=science, results=results, body=body, final_ref=body["reference"],
            returned=read(directory, "results-return.json"),
            forwarded=read(directory, "scientific-return.json"),
            sheet=read(directory, "sheet.json"), components=read(directory, "components.json"))
        test_native_numbers_and_only_requested_facts_reach_both_parents(retained)
        final_database = digest_database(store)
        assert final_database == original_database
    result = {"status": "passed", "original_workflow_directory": str(directory),
        "verification": "corrected full numerical and two-parent return assertion function",
        "new_workflow_executions": 0, "new_native_calls": 0, "new_model_calls": 0,
        "new_parses": 0, "new_calculations": 0,
        "database_logical_sha256_before": original_database,
        "database_logical_sha256_after": final_database,
        "source_manifest": original_manifest, "current_source_manifest": current,
        "changed_source_files": changed,
        "original_pytest_result_preserved": True}
    output = directory / "corrected-numeric-retained-verification.json"
    assert not output.exists(), "Preserve existing verification receipts"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "passed", "receipt": str(output), "new_workflow_executions": 0}))


if __name__ == "__main__":
    main()
