"""One new authentic info invocation after the approved 678 parser correction.

The 673 setup supplies scripted episode choices, with actual production native
execution, capture, workers, publication and typed admission. Its historical
info verifier is deliberately not used. No production behavior is overridden.
Saved replay uses 673's explicit exact-existing-byte immutable-writer adapter.
"""
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_result
from gene_annotation_episode.blast_utility_result_views import (
    IDENTIFIER_NAMESPACES, PROJECTION_V2_FIELDS, projection_identifiers,
)
from gene_annotation_episode.episode_monitoring import read_progress
from gene_annotation_episode.native_blast_utility_result_publication import (
    validate_prepared_utility_result, validate_utility_publication,
)
from gene_annotation_episode.native_blast_utility_result_worker import qualified_utility_context
from gene_annotation_episode.native_blast_vdb_utility_context import validate_vdb_context_authentication
from gene_annotation_episode.numerical import NumericBand
from test_blast_vdb_workflow_673 import (
    INFO_FIELDS, POLICY, fields_for, history, run_case, save, saved_checks,
)


NATIVE_SHA = "cb65d0f9b71a60a74dcbabb602dcd86cdc29e6b5d65c2d0ec3d7c7235c174e0a"
OPERAND = ("/home/chia/repos/gene_annotation_episode/verification/"
           "tool_graders_blast_vdb_fixture_acquisition_2026-10-28_658/"
           "retained/fixture/ERR3487613")
WRAPPED_LEXEME = (
    " \n/home/chia/repos/gene_annotation_episode/verification/tool_graders_blast_vdb_"
    "\nfixture_acquisition_2026-10-28_658/retained/fixture/ERR3487613")
NUMBERS = {
    "vdb_sequence_count": (20, "sequences", "20", 7),
    "vdb_total_unclipped_bases": (5000, "nt", "5,000", 7),
    "vdb_longest_sequence_bases": (250, "nt", "250", 8),
    "vdb_average_sequence_bases": (250, "nt", "250", 9),
}


def verify_corrected_info_case(case):
    assert case.mode == "info"
    body, returned = case.outcome["result"], case.returned
    capture, prepared = body["capture"], body["prepared"]
    assert body["complete"] and returned["completed"]
    assert body["version"] == "native_blast_utility_acquired_result_v2"
    assert body["reused_from"] is None and not body["operational_failures"]
    bundle = capture["original_bundle"]
    assert bundle["started"] and bundle["returncode"] == 0
    assert bundle["writer_closed"] and bundle["inventory_complete"] and not bundle["failures"]
    assert capture["bundle_validated"] and not capture["failures"]
    assert bundle["requested_job"]["native_blast_utility"] == case.job
    assert bundle["operation"] == case.job["operation"]
    assert bundle["realized_argv"] == [case.job["software"]["executable"], "-db", OPERAND,
        "-info", "-line_length", "80"]
    offline = bundle["offline_execution"]
    assert offline["child_exit_code"] == offline["launcher_returncode"] == 0
    assert not offline["failures"]
    assert len([r for r in offline["status_records"] if "child-pid" in r]) == 1
    assert len([r for r in offline["status_records"] if "exit-code" in r]) == 1
    assert "--unshare-net" in offline["launcher_argv"] and "--remount-ro" in offline["launcher_argv"]
    assert offline["launcher_argv"][offline["launcher_argv"].index("--") + 1:] == bundle["realized_argv"]
    assert all((r["expected_sha256"], r["expected_size_bytes"]) ==
        (r["before_sha256"], r["before_size_bytes"]) == (r["final_sha256"], r["final_size_bytes"])
        for r in offline["runtime_files"])
    selection = json.loads((case.directory / "INPUT_SELECTION.json").read_text())
    assert not selection["prior_store_or_source_ids_imported"]
    assert selection["supplied"]["ERR3487613"]["path"] == OPERAND
    for ref in selection["registered_initial_refs"]:
        row = case.store.get(ref)
        if row["record_type"] == "source":
            assert row["origin"] == row["provider"] == "caller"
    parameters = case.job["operation"]["parameters"]
    assert parameters["database_selection"] == {"source": "db", "list_occurrence_id": None,
        "inputs": [{"ordinal": 0, "kind": "path", "value": OPERAND,
            "binding_native_path": OPERAND, "list_entry_ordinal": None}]}
    assert parameters["selection"] is None and parameters["include_filtered_reads"] is False
    assert parameters["output_format"] == "blast_vdb_info_text_v1"
    assert body["target"]["resource_kind"] == "local" and body["target"]["resource_id"] == "here"
    validate_prepared_utility_result(case.store, prepared)
    result = json.loads(case.store.get_artifact(prepared["result_artifact_ref"]))
    validate_blast_utility_result(result)
    context = qualified_utility_context(capture)
    assert result["operation"] == case.job["operation"]
    assert result["vdb_context"]["member_bindings"] == result["vdb_context"]["sample_links"] == []
    source_input, = result["vdb_context"]["source_inputs"]
    assert source_input["dataset_key"] is None and source_input["dataset_type"] == "unknown"
    assert source_input["selected_input"] == {"kind": "path", "value": OPERAND}
    assert source_input["binding_native_path"] == OPERAND and source_input["run_identifiers"] == []
    assert source_input["snapshot"] == {"release": None, "snapshot_id": None, "manifest_sha256": None}
    stable = json.loads(case.store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
    receipt = json.loads(case.store.get_artifact(stable["worker_receipt_artifact_ref"]))
    proof = receipt["manifest"]["context_authentication"]
    validate_vdb_context_authentication(proof, capture=capture, context=context)
    assert proof["passed"] and receipt["manifest"]["completed"] and receipt["returncode"] == 0
    assert receipt["plan"]["context"] == context
    assert all(row["source_ref"] == capture["source_ref"] and row["source_namespace"] == "source"
        for row in proof["provenance"])
    publication_dir = case.owner.native_blast_utility_results._saved_directory(
        case.result_context.episode_id, body["operation_key"])
    publication = json.loads((publication_dir / "publication.json").read_text())
    validate_utility_publication(case.store, source_ref=body["source_ref"], prepared=prepared,
        selector=case.selector, publication=publication)
    assert all(publication[field] == body[field] for field in PROJECTION_V2_FIELDS)
    for field in fields_for("info"):
        assert returned[field] == ([body[field]] if field == "status" else body[field])
        assert case.forwarded[field] == returned[field]
    case.owner.validate_report(case.result_context, returned, case.results_form)
    case.owner.validate_received_report(case.science_context, returned, case.results_form)
    case.owner.validate_received_report(case.root_context, case.forwarded, case.science_form)
    assert set(returned) == {*fields_for("info"), "completed"}
    assert set(case.forwarded) == set(fields_for("info"))
    stdout, = [r for r in context["occurrences"] if r["direction"] == "output" and r["role"] == "stdout"]
    native_bytes = case.store.get_artifact(stdout["artifact_ref"])
    assert stdout["size_bytes"] == len(native_bytes) == 423 and stdout["sha256"] == NATIVE_SHA
    stderr, = [r for r in context["occurrences"] if r["direction"] == "output" and r["role"] == "stderr"]
    assert stderr["size_bytes"] == 0 and case.store.get_artifact(stderr["artifact_ref"]) == b""
    originals = result["native_fields"]
    assert len(originals) == len(INFO_FIELDS) == 9
    assert {r["field_name"] for r in originals} == set(INFO_FIELDS)
    assert [{k: v for k, v in row.items() if k not in {"source_ref", "database_key"}}
        for row in returned["database_fields"]] == originals
    fields = {r["field_name"]: r for r in originals}
    for row in originals:
        assert row["value_basis"] == "native_reported" and row["occurrence_id"] == stdout["occurrence_id"]
    for name, line, unit in (("vdb_selected_inputs", 1, "native_input_tokens"), ("vdb_resolved_paths", 4, "paths")):
        row = fields[name]
        assert row["value"] is None and row["missing_reason"] == "ambiguous_population"
        assert row["native_lexeme"] == WRAPPED_LEXEME and row["unit"] == unit
        assert row["line_number"] == line and row["json_pointer"] is None
    for name, (value, unit, lexeme, line) in NUMBERS.items():
        row = fields[name]
        assert type(row["value"]) is int and row["value"] == value and row["unit"] == unit
        assert row["native_lexeme"] == lexeme and row["line_number"] == line
        assert row["missing_reason"] is None and row["json_pointer"] is None
    for name, unit in (("vdb_csra_inputs", "paths"), ("vdb_reference_sequence_count", "sequences"),
            ("vdb_reference_total_bases", "nt")):
        row = fields[name]
        assert row["value"] is None and row["missing_reason"] == "native_field_absent" and row["unit"] == unit
        assert row["native_lexeme"] is None and row["line_number"] is None and row["json_pointer"] == ""
    failures = [{"stage": "validation", "code": "semantic_validation_unavailable",
        "occurrence_id": stdout["occurrence_id"], "record_key": None,
        "line_number": line, "native_returncode": None} for line in (1, 4)]
    assert result["failures"] == failures
    assert returned["failures"] == [{"source_ref": body["source_ref"], **f} for f in failures]
    checks = {r["name"]: r for r in result["checks"]}
    assert checks["syntax"]["status"] == "pass" and checks["database_metadata"]["status"] == "unknown"
    assert result["completeness"] == body["status"]["result_completeness"] == "partial"
    assert body["status"]["state"] == "complete" and not body["missing"]
    assert result["path_records"] == result["path_sections"] == []
    assert all(body[name] == [] for name in ("sequences", "paths", "path_sections", "vdb_context", "checks"))
    assert case.monitor_return["target"] == case.provider.handoff
    assert case.monitor_return["latest_state"] == "returned" and case.monitor_return["result_available"]
    for reference in case.monitor_return["progress"]:
        assert read_progress(case.store, case.run_id, reference, case.scope)["target_handle"] == case.provider.handoff
    grants = {r["artifact_ref"] for r in [*body["artifacts"], *body["saved_data"]]}
    assert body["record_refs"] == list(dict.fromkeys([body["source_ref"],
        *[r["artifact_ref"] for r in body["artifacts"]], *[r["artifact_ref"] for r in body["saved_data"]]]))
    assert len(body["artifacts"]) == len(body["saved_data"]) == 1
    assert body["artifacts"][0]["role"] == "stdout" and body["saved_data"][0]["kind"] == "result"
    for receiver in (case.science_context, case.root_context):
        known = set(case.flow.receipts.known(receiver.episode_id))
        resolver = case.flow.resolver(case.scope, context=receiver)
        assert {body["source_ref"], *grants} <= known
        assert all(resolver(ref, "artifact") for ref in grants)
        assert not resolver(capture["bundle_artifact_ref"], "artifact")
        for namespace in IDENTIFIER_NAMESPACES:
            assert all(resolver(ref, namespace) for ref in projection_identifiers(body, namespace))
    accounting = []
    for row in case.records:
        role = case.contexts[row["episode_id"]].role
        for table in ("runtime_actions", "runtime_observations"):
            assert case.store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                (case.run_id, row["episode_id"])).fetchone()[0] == row["units_consumed"]
        accounting.append({"role": role, "episode_id": row["episode_id"], "own_actions": row["units_consumed"],
            "raw_history": history(row), "estimate": row["controller_state"]["estimate"]})
        if role in {"launch_local", "launch", "results"}:
            assert row["units_consumed"] == 1
            assert row["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
            assert history(row) == [{"launch_local": 7, "launch": 3, "results": 2}[role]]
    completion = case.owner.completion_for_action(case.result_context, body["operation_key"])
    assert completion and case.owner.verify_completion(case.result_context, completion)
    metadata = native.NativeJobHandle(Path(case.provider.plan["identity"]["execution_id"])).read()["metadata"]
    assert metadata["policy"] == POLICY
    assert metadata["verified_cgroup"]["memory_max"] == 20 * 1024**3
    assert metadata["verified_cgroup"]["memory_swap_max"] == 0
    assert 'runtime_max' not in metadata["verified_cgroup"]
    assert len(list(case.directory.glob("workspace/.episode-operations/*/*/native.json"))) == 1
    closure = json.loads((case.directory / "NATIVE_CLOSURE.json").read_text())
    assert closure["returncode"] == 0
    assert case.store.count("annotation") == case.store.count("observation") == 0
    summary = {"mode": "info", "native_commands": 1, "native_returncode": 0,
        "native_stdout": {k: stdout[k] for k in ("sha256", "size_bytes", "artifact_ref")},
        "native_fields": originals, "inspection_completeness": result["completeness"],
        "delivery_state": body["status"]["state"], "context_authenticated": True,
        "typed_immediate_parent_and_root_admission": True, "publication_equal": True,
        "inferred_biological_identities": False, "average_recomputed_or_substituted": False,
        "one_observation_per_selected_action": True, "accounting": accounting,
        "operational_acquisition_credit": 2, "practical_future_expected_credit": 0,
        "monitor_received_original_target": True, "requested_artifact_grants": sorted(grants),
        "raw_bundle_granted": False, "corrected_saved_result_artifact_ref": prepared["result_artifact_ref"],
        "native_handle": case.provider.plan["identity"]["execution_id"]}
    save(case.directory / "VERIFIED_VALUES_682.json", summary)
    return summary


def test_corrected_info_full_workflow(tmp_path_factory, monkeypatch):
    if not os.environ.get("HMMER529_ATTEMPT"):
        pytest.skip("authentic corrected VDB info verification requires bounded529")
    assert os.environ.get("HMMER_NATIVE_ORACLE_VDB_MODE") == "info"
    directory = tmp_path_factory.mktemp("vdb-info-corrected682")
    save(Path(os.environ["HMMER529_ATTEMPT"]) / "VDB_CASE_PATH.json", {"directory": str(directory), "mode": "info"})
    case = run_case(directory, "info")
    try:
        verify_corrected_info_case(case)
        saved_checks(case, monkeypatch)
    finally:
        case.store.close()
