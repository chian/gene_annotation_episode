"""One real single-genome prediction through the existing scientific child.

The selected choices, continuation estimator and zero credit are communication
fixtures reused from the established child-return harness. Pyrodigal, the
bounded native worker, publication, typed forms and receipt admission are real.
No launch_local episode, scientific-confidence policy or model call is claimed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket

import pytest

from gene_annotation_episode import native_lifecycle, sequence_ops
from gene_annotation_episode import tools as tool_module
from gene_annotation_episode.prodigal_grader import calculate_prodigal_scores
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_published_axis_workflow import PUBLICATION, ScriptedDecisions, select
from test_tool_grading_child_returns import (
    RETURN_FORM, fixed_completion_estimate, zero_fixture_credit,
)
from test_tool_grading_publication import numerical, only_grading, operation_count


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "verification/tool_graders_batch_001/prodigal"
POLICY = {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3,
          "wall_seconds": None}


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def file_pins(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(directory.rglob("*")) if path.is_file()}


def histories(store):
    return {name: [dict(row) for row in store.db.execute(f"SELECT * FROM {name} ORDER BY rowid")]
            for name in ("runtime_actions", "runtime_observations", "runtime_forms",
                         "runtime_record_receipts", "tool_operations")}


def forbidden(*args, **kwargs):
    pytest.fail("Unexpected acquisition, prediction or native execution")


def test_single_native_publication_requested_return_and_saved_replay(tmp_path, monkeypatch):
    """All 103 original candidates reach the parent as one completed action."""
    evidence = Path(os.environ.get("PRODIGAL505_ATTEMPT", tmp_path)) / "evidence"
    evidence.mkdir(parents=True, exist_ok=False)
    originals = {name: (DATA / name).read_bytes() for name in (
        "single.input.fna", "single.native.json", "single.graded.json", "single.recalculated.json")}
    sequence = "".join(line for line in originals["single.input.fna"].decode().splitlines()
                       if not line.startswith(">"))
    file_hash = hashlib.sha256(originals["single.input.fna"]).hexdigest()
    sequence_hash = hashlib.sha256(sequence.encode()).hexdigest()
    assert file_hash == "07cc14da390e0616418b0973f61b8c4386c87bf097b3e88a92a42227c9b6f93b"
    assert sequence_hash == "8dd87e70a6e09ecb0c54ca659c18d2246558ca548d30744d923d89c1aee3986e"
    assert len(sequence) == 100000
    expected_native = json.loads(originals["single.native.json"])
    historical = json.loads(originals["single.graded.json"])
    expected_scores = json.loads(originals["single.recalculated.json"])
    assert historical["sheet"]["native_result"] == expected_native
    assert historical["scores"] == expected_scores
    dump(evidence / "input_identity.json", {"fasta_sha256": file_hash,
        "sequence_sha256": sequence_hash, "sequence_length_nt": len(sequence),
        "provenance": "retained installed-Pyrodigal NZ_LN831026.1 100000 nt test fragment",
        "parent_offset_nt": 13, "flanks": "synthetic N padding outside the selected native input"})

    # Observe the production seam without replacing either execution or data.
    # The blocking adapter normally releases this handle after collection.
    real_run = tool_module.run_local_job_async
    real_release = native_lifecycle.release
    native_calls, original_handles = [], []

    def retain_handle(handle):
        body = handle.read()
        if "gene_annotation_episode.sequence_worker" in body["command"]:
            original_handles.append(body)
            folder = evidence / "native_control"
            folder.mkdir(exist_ok=False)
            dump(folder / "original_handle.json", body)
            dump(folder / "original_status.json", native_lifecycle.status(handle))
            for name, original in body["paths"].items():
                if Path(original).is_file():
                    (folder / name).write_bytes(Path(original).read_bytes())
        return real_release(handle)

    async def observed_run(command, **kwargs):
        native_calls.append(list(command))
        request = json.loads(Path(command[-2]).read_text())
        assert request == {"operation": "predict_genes", "arguments": {
            "sequence": sequence, "code": 11, "mode": "single"}}
        assert kwargs["policy"].to_dict() == POLICY
        assert not store.db.in_transaction
        dump(evidence / "worker_request.json", request)
        result = await real_run(command, **kwargs)
        (evidence / "worker_unshifted.native.json").write_bytes(Path(command[-1]).read_bytes())
        dump(evidence / "worker_receipt.json", result.metadata)
        return result

    monkeypatch.setattr(native_lifecycle, "release", retain_handle)
    monkeypatch.setattr(tool_module, "run_local_job_async", observed_run)
    monkeypatch.setattr(sequence_ops, "predict_genes", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(ToolRegistry, "_acquire_async", forbidden)
    store_directory, directory = tmp_path / "state", tmp_path / "run"
    with Store(store_directory) as store:
        target, = store.create_problem(raw_sequence="N" * 13 + sequence + "N" * 11,
                                       molecule="dna")["subject_refs"]
        scope = store.validate_scope({"subject_refs": [target]})
        args = {"subject_ref": target, "mode": "single", "code": 11,
                "start": 13, "end": 100013}
        tools = ToolRegistry(store, job_limits=POLICY)
        descriptor = prepare_scientific_binding(run_directory=directory,
            source_directory=PUBLICATION, tool_catalog=tools.catalog(), child_roles=("scientific_process",))
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        commission = {"kind": "episode_child", "role": "scientific_process",
            "goal": "Predict candidate coding intervals in the supplied unnamed DNA region using single-genome Prodigal.",
            "scope": scope, "purpose": "Return all committed prediction records with native measurements and mappings; function remains unresolved.",
            "schema_json": json.dumps(RETURN_FORM), "initial_report_json": "{}",
            "assignment": {"selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": "genes.predict", "resources": "local"}]},
                "evidence_refs": [target], "constraints": {"no_external_acquisition": True},
                "context": {"molecule": "dna", "selected_interval": {"start": 13, "end": 100013},
                            "mode": "single", "genetic_code": 11}}}
        decisions = ScriptedDecisions([select(commission),
            select({"kind": "tool", "tool": "genes.predict", "arguments": args})])
        workflow = Workflow(store, tools, decisions, directory, "prodigal-single-505",
            fixed_completion_estimate, zero_fixture_credit, episode_binding_descriptors=[descriptor],
            episode_record_receipts=True, initial_known_record_refs=[], decision_protocol="decision_exchange_v1")
        root = workflow.build("annotation", "root", "Investigate the supplied unnamed DNA", scope)
        assert workflow.catalog(scope, source=root.source) == []
        assert not workflow.permits_common_action(root.source, "tool")
        assert list(workflow.receipts.known(root.source.episode_id, record_type="observation")) == []

        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record

        record = asyncio.run(run())
        publication_row = store.db.execute("SELECT * FROM tool_operations WHERE name='genes.predict'").fetchone()
        publication = json.loads(publication_row["result"])
        dump(evidence / "publication.json", publication)
        assert publication["status"] == "completed", publication
        assert len(decisions.calls) == 2  # Scripted parent and child; no grader/composer call.
        child_id, root_id = decisions.calls[1]["episode_id"], root.source.episode_id
        returned = json.loads(workflow.journal.row("runtime_forms", child_id)["form"])
        dump(evidence / "requested_form.json", RETURN_FORM)
        dump(evidence / "returned_form.json", returned)
        source = store.get(publication["result"]["source_ref"])
        source_bytes = store.get_artifact(source["artifact_ref"])
        grading = only_grading(store, source["id"])
        dump(evidence / "published.grading.json", grading)
        (evidence / "published.source.json").write_bytes(source_bytes)
        dump(evidence / "selected_native_commands.json", native_calls)
        assert len(native_calls) == len(original_handles) == 1
        assert native_calls[0][1:3] == ["-m", "gene_annotation_episode.sequence_worker"]
        original_native = json.loads((evidence / "worker_unshifted.native.json").read_text())
        assert original_native == expected_native
        body = json.loads(source_bytes)
        assert body["local_job"]["policy"] == POLICY
        assert body["local_job"]["verified_cgroup"] == {
            "memory_max": POLICY["memory_bytes"], "memory_swap_max": 0,
            "runtime_max": "infinity", "kill_mode": "control-group", "oom_policy": "kill"}
        assert body["local_job"]["native_returncode"] == 0
        assert body["input_interval"] == [13, 100013] and body["subject_ref"] == target
        assert grading["sheet"]["native_result"] == original_native
        assert grading["sheet"]["input_start"] == 13 and grading["sheet"]["input_length"] == 100000
        scores = grading["scores"]
        shifted_expected = deepcopy(expected_scores)
        for row in shifted_expected["candidates"]:
            row["parent_interval"] = [value + 13 for value in row["parent_interval"]]
        assert scores == shifted_expected
        assert scores["summary"]["reported_candidate_count"] == 103
        assert scores["summary"]["union_coding_bases"] == 85743
        assert scores["summary"]["coding_coverage"] == .85743
        assert scores["summary"]["partial_candidate_count"] == 2
        assert {row["strand"] for row in scores["candidates"]} == {"+", "-"}

        # The result preview is bounded; complete recorded/requested data is not.
        assert publication["result"]["count"] == 103
        assert len(publication["result"]["records"]) == publication["result"]["preview_limit"] == 12
        assert publication["result"]["more_records_available_through_state_query"] is True
        assert returned == {"records": publication["record_refs"]}
        assert len(returned["records"]) == 2 + 103 * 3
        root_receipts = set(workflow.receipts.known(root_id))
        assert set(returned["records"]) <= root_receipts
        observations = [store.get(ref) for ref in returned["records"]
                        if store.get(ref)["record_type"] == "observation"]
        assert len(observations) == store.count("observation") == 103
        assert len({row["id"] for row in observations}) == 103
        assert {row["id"] for row in observations} == set(workflow.receipts.known(root_id, record_type="observation"))
        checked_rows = []
        for index, (observation, native, scored) in enumerate(zip(observations, original_native["candidates"], scores["candidates"], strict=True)):
            feature_ref, product_ref = observation["subject_refs"]
            feature, product = store.get(feature_ref), store.get(product_ref)
            start, end = scored["parent_interval"]
            assert scored["candidate_index"] == index
            assert scored["relative_interval"] == [native["start"], native["end"]]
            assert [start, end] == [native["start"] + 13, native["end"] + 13]
            assert body["candidates"][index] == {**native, "start": start, "end": end}
            assert grading["sheet"]["candidates"][index]["native_candidate"] == native
            assert feature["subject_ref"] == target and feature["kind"] == "CDS"
            assert feature["segments"] == [{"start": start, "end": end}]
            assert feature["strand"] == native["strand"]
            assert product["parent_refs"] == [feature_ref]
            assert product["mapping_source_ref"] == observation["source_ref"] == source["id"]
            assert product["context_refs"] == feature["context_refs"]
            assert observation["dependencies"] == [target, *feature["context_refs"]]
            assert store.get_artifact(product["sequence_ref"]).decode() == native["protein_sequence"]
            assert product["mapping"] == {"version": "oriented_source_subject_path_v2",
                "units_per_symbol": 3, "symbol_length": scored["translated_symbol_count"],
                "path": [{"subject_ref": target, "start": start, "end": end,
                          "unit": "nt", "strand": native["strand"]}]}
            assert product["footprint"] == [{"target_ref": target, "start": start, "end": end, "unit": "nt"}]
            values = numerical(observation)
            assert values == {"genetic_code": 11, "start": start, "end": end,
                "native_confidence": native["native_confidence"], "model_score": native["native_score"],
                **{key: scored[key] for key in ("interval_length_nt", "protein_length_aa",
                                              "internal_stop_count", "terminal_stop_count")}}
            assert values["native_confidence"] == scored["native_confidence_percent"]
            assert values["model_score"] == scored["native_score"]
            checked_rows.append({"candidate_index": index, "feature_ref": feature_ref,
                "product_ref": product_ref, "observation_ref": observation["id"],
                "strand": native["strand"], "measurements": values})
        dump(evidence / "checked_candidate_records.json", checked_rows)

        child_state = decisions.calls[1]["state"]
        selected_info, = child_state["scientific_process"]["child_tool_info"]
        parent_info, = [row for row in workflow.scientific_process_binding.tool_library.parent_tool_info()
                       if row["name"] == "genes.predict" and row["resources"] == "local"]
        assert set(parent_info) == {"name", "description", "resources"}
        assert {key: selected_info[key] for key in parent_info} == parent_info
        assert set(selected_info) == {"name", "description", "resources", "instructions"}
        guidance = (ROOT / "gene_annotation_episode/knowledge/gene-prediction.md").read_text().strip()
        assert guidance in selected_info["instructions"]
        child_text = render_scientific_process_prompt(child_state, decisions.calls[1]["instructions"])
        assert selected_info["instructions"] in child_text
        assert "TASK" in child_text and "STEERING" in child_text
        (evidence / "child_prompt.txt").write_text(child_text)
        for presented in (json.dumps(workflow.working_state(root.source)), child_text):
            for full_sheet_key in ("native_result", "prodigal_sheet_v1", "prodigal_scores_v1"):
                assert full_sheet_key not in presented
        assert record.units_consumed == 1
        for episode_id in (root_id, child_id):
            assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
            assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
        assert store.count("annotation") == 0 and operation_count(store, "genes.predict") == 1
        assert store.count("feature") == store.count("product") == 103

        before_histories, before_archive = histories(store), file_pins(directory)
        dump(evidence / "histories_before_replay.json", before_histories)
        monkeypatch.setattr(tool_module, "run_local_job_async", forbidden)
        monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
        operation_key = publication_row["operation_key"]
        assert tools.execute("genes.predict", args, scope=scope, operation_key=operation_key) == publication
        root_action = store.db.execute("SELECT decision_index FROM runtime_actions WHERE episode_id=?", (root_id,)).fetchone()[0]
        workflow.receive_form(root.source, returned, RETURN_FORM, root_action, redelivery=True)
        assert histories(store) == before_histories
        assert file_pins(directory) == before_archive
        assert len(native_calls) == len(original_handles) == 1 and len(decisions.calls) == 2
        dump(evidence / "histories_after_replay.json", histories(store))
        dump(evidence / "archive_pins_before.json", before_archive)
        dump(evidence / "archive_pins_after.json", file_pins(directory))

    # Reopen saved custody with prediction, execution and acquisition forbidden.
    with Store(store_directory) as reopened, monkeypatch.context() as offline:
        offline.setattr(socket, "socket", forbidden)
        saved = only_grading(reopened, source["id"])
        original_sheet = deepcopy(saved["sheet"])
        recalculated = calculate_prodigal_scores(saved["sheet"])
        assert recalculated == saved["scores"] == shifted_expected
        assert saved["sheet"] == original_sheet
        assert calculate_prodigal_scores(historical["sheet"]) == expected_scores
        assert reopened.get_artifact(source["artifact_ref"]) == source_bytes
        assert histories(reopened) == before_histories
        assert reopened.count("observation") == 103 and reopened.count("annotation") == 0
        dump(evidence / "saved_only.recalculated.json", recalculated)
    for name, original in originals.items():
        assert (DATA / name).read_bytes() == original
    dump(evidence / "verification_summary.json", {
        "actual_native_predictions": len(native_calls), "mode": "single", "native_version": original_native["pyrodigal_version"],
        "candidate_count": 103, "returned_record_count": len(returned["records"]),
        "union_coding_bases": 85743, "coding_coverage_denominator_nt": 100000,
        "coding_coverage": .85743, "partial_candidate_count": 2,
        "child_completed_actions": 1, "parent_child_actions": 1,
        "child_controller_observations": 1, "parent_controller_observations": 1,
        "scripted_decision_calls": 2, "grader_or_composer_model_calls": 0,
        "saved_recalculation_equal": True, "replay_histories_unchanged": True,
        "closed_archive_unchanged": True, "annotation_objects": 0,
        "resource_path": "scientific_process child -> ToolRegistry -> local native sequence worker",
        "scientific_fixture": "real retained Pyrodigal test-genome fragment; synthetic parent N flanks excluded",
        "decision_fixture": "scripted choices, fixed completion estimator and zero credit; no model-based annotation"})
