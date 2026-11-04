"""Fresh current-v2 operands through the existing shared scientific Workflow.

Tiny structures and scripted scientific choices are engineering inputs. Native
extraction, alignment, comparison, authority and typed delivery use production
paths. Presentation is the actual renderer over dispatched scripted inputs;
no live model, biological relationship or additional saved calculation is claimed.
"""
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.native_protein_structure_worker import _alignment_grading
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_operands import (
    authenticate_selected_alignment, authenticate_structure_sequence_reference,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource
from gene_annotation_episode.tools import ToolRegistry


F = import_module("verification.tool_graders_protein_structure_workflow_2026-10-27_410.fixture_helpers")
HELPER_SHA = "6405670c166657c0ae2bceb628fc2d4f430eef824a3e7c9526a55c3266207863"
QUESTION = ("For the two received AGST structure sequences, what are the native alignment score and "
    "mapped pair count, and, after fitting their first three CA pairs, what fit and held-out "
    "fourth-pair evaluation counts, SSE and RMSD follow?")


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr)
        for name in names}


def _cells(projection):
    row, = projection["delivery"]["rows"]
    return {cell["field"]: cell for cell in row["values"]}


def test_current_v2_alignment_operand_and_typed_comparison_workflow(tmp_path, monkeypatch):
    assert hashlib.sha256(Path(F.__file__).read_bytes()).hexdigest() == HELPER_SHA
    original_descriptor, original_job = F.alignment_descriptor, F.selected_job
    original_commission = F.commission
    original_authenticate = WorkflowServices.authenticate_structure_alignment_operands
    original_prepare = ToolRegistry._prepare_alignment_async
    original_sequence_worker, original_call = ToolRegistry._sequence_worker_async, DecisionSource.call
    events, selected_jobs, presentations, alignment_dispatches = [], [], [], []
    session = object.__new__(_SessionConnection)
    session.scientific_prompt_states = {}

    def commission(role, assignment, scope, form, *, objective):
        if role == "scientific_process" and assignment.get("context", {}).get("fixture_phase") == "align_compare":
            objective = QUESTION
        return original_commission(role, assignment, scope, form, objective=objective)

    def current_descriptor(store, context, arguments):
        # The old fixture labels its actual grading file v1. Observe the current
        # retained envelope; do not create a Source, receipt, grade or native row.
        descriptor, outcome = original_descriptor(store, context, arguments)
        source = store.get(descriptor["source_ref"])
        raw = store.get_artifact(descriptor["grading_file"]["artifact_ref"])
        grading = json.loads(raw)
        assert set(grading) == {"schema", "provider", "native_artifact_ref", "grading", "correspondence"}
        assert grading["schema"] == "tool_grading_artifact_v2"
        assert grading["provider"] == source["provider"] == "biopython.alignment"
        assert grading["native_artifact_ref"] == source["artifact_ref"] == descriptor["native_file"]["artifact_ref"]
        assert descriptor["grading_file"]["artifact_ref"] in source["auxiliary_artifact_refs"]
        descriptor["grading_file"]["format"] = grading["schema"]
        events.append({"event": "observed_original_v2_descriptor", "episode_id": context.episode_id,
            "grading_file": deepcopy(descriptor["grading_file"]), "grading_keys": sorted(grading)})
        return descriptor, outcome

    def current_job(store, request, software):
        job = original_job(store, request, software)
        # The bounded worker's selected dependency tree is separate from the
        # source root. Preserve that actual caller-selected path for these NEW
        # jobs; do not edit or reinterpret an historical job reservation.
        paths = list(dict.fromkeys([str(F.ROOT), *filter(None, os.environ.get("PYTHONPATH", "").split(os.pathsep))]))
        job["environment"]["PYTHONPATH"] = os.pathsep.join(paths)
        selected_jobs.append(deepcopy(job))
        return job

    def authenticate(services, context, arguments):
        descriptors = original_authenticate(services, context, arguments)
        assert descriptors["query"] is not None and descriptors["reference"] is not None
        events.append({"event": "actual_received_operands_authenticated", "episode_id": context.episode_id,
            "arguments": deepcopy(arguments), "descriptors": deepcopy(descriptors)})
        return descriptors

    async def prepare(registry, arguments, scope, directory):
        assert events[-1]["event"] == "actual_received_operands_authenticated"
        assert events[-1]["arguments"] == arguments
        events.append({"event": "actual_native_alignment_preparation", "arguments": deepcopy(arguments)})
        return await original_prepare(registry, arguments, scope, directory)

    async def sequence_worker(registry, operation, arguments, **kwargs):
        assert operation == "align_pair", "this fixture selects only one direct native sequence operation"
        alignment_dispatches.append({"operation": operation, "arguments": deepcopy(arguments)})
        return await original_sequence_worker(registry, operation, arguments, **kwargs)

    async def call(source, context, schema):
        answer = await original_call(source, context, schema)
        actual_context, index = answer[2], answer[1]
        saved = json.loads(source.workflow.journal.row("runtime_model_calls", source.episode_id, index)["request"])
        assert saved["context"] == actual_context
        before = canonical(actual_context)
        instructions = source.instructions(actual_context)
        shown, shown_instructions = session._presentation(source.episode_id, "REASONING", instructions, actual_context)
        assert canonical(actual_context) == before
        objective = actual_context["goal"]["objective"]
        kind = "task_steering" if shown.startswith("TASK\n") and "\n\nSTEERING" in shown else "json_fallback"
        if source.path[-1][0] == "scientific_process":
            assert shown.startswith("TASK\n") and "\n\nSTEERING" in shown
            assert objective in shown
        presentations.append({"episode_id": source.episode_id, "role": source.path[-1][0], "call_index": index,
            "assigned_question": objective, "context_sha256": digest(actual_context),
            "presentation_kind": kind, "six_quantity_question_visible": QUESTION in shown,
            "text": shown, "instructions": shown_instructions,
            "received_child_reports": deepcopy(actual_context.get("child_reports", []))})
        return answer

    def forbidden(*args, **kwargs):
        raise AssertionError("current-v2 tiny Workflow attempted external acquisition")

    monkeypatch.setattr(F, "alignment_descriptor", current_descriptor)
    monkeypatch.setattr(F, "selected_job", current_job)
    monkeypatch.setattr(F, "commission", commission)
    monkeypatch.setattr(WorkflowServices, "authenticate_structure_alignment_operands", authenticate)
    monkeypatch.setattr(ToolRegistry, "_prepare_alignment_async", prepare)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", sequence_worker)
    monkeypatch.setattr(DecisionSource, "call", call)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    case = F.workflow_case(tmp_path / "current-v2", saved=False)
    try:
        store, returns = case.store, case.owner.native_protein_structure_returns
        assert case.saved is False and case.provider.original_return is None
        assert len(case.provider.plans) == len(selected_jobs) == 3
        assert [job["request"]["operation"] for job in selected_jobs] == ["extract_sequence", "extract_sequence", "compare"]
        assert len(alignment_dispatches) == 1
        assert [len(case.by_role[role]) for role in ("annotation", "scientific_process", "launch", "launch_local", "results")] == [1, 3, 3, 3, 3]
        early, coordinator, aligner = case.science_contexts
        fixed, moving = case.provider.descriptors
        assert [row["event"] for row in events] == ["actual_received_operands_authenticated",
            "actual_native_alignment_preparation", "observed_original_v2_descriptor"]
        assert events[0]["descriptors"] == {"query": fixed, "reference": moving}
        assert fixed == case.returned[0]["sequences"][0] and moving == case.returned[1]["sequences"][0]
        for descriptor in (fixed, moving):
            assert descriptor["allowed_uses"] == ["sequence_align", "structure_correspondence"]
            assert descriptor["sequence_length"] == 4
            assert store.get_artifact(descriptor["sequence_file"]["artifact_ref"]) == b"AGST"
            assert authenticate_structure_sequence_reference(store, aligner, descriptor["reference_ref"], returns=returns) == descriptor
            assert returns.authenticate_received_sequence(aligner, descriptor,
                required_use="structure_correspondence")["custody"] == descriptor["custody"]
        alignment = case.provider.alignment
        native = json.loads(store.get_artifact(alignment["native_file"]["artifact_ref"]))
        grading = json.loads(store.get_artifact(alignment["grading_file"]["artifact_ref"]))
        assert alignment["grading_file"]["format"] == grading["schema"] == "tool_grading_artifact_v2"
        assert native["native_format"] == "biopython_pairwise_native_v2" and native["native_score"] == 19
        assert grading["grading"]["scores"]["paired_positions"] == 4
        assert len(grading["correspondence"]["instances"]) == 1
        snapshot = authenticate_selected_alignment(store, aligner, alignment, fixed=fixed, moving=moving,
            orientation="fixed_is_query", returns=returns)
        assert snapshot["native_result"] == native and snapshot["pairwise_sheet"] == grading["grading"]["sheet"]
        action = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
            (F.RUN_ID, aligner.episode_id)).fetchone()
        operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
            (alignment["original_operation_key"],)).fetchone()
        assert operation["name"] == "sequence.align" and json.loads(operation["scope"]) == plain(aligner.scope)
        assert json.loads(action["action"]) == {"kind": "tool", "tool": "sequence.align",
            "arguments": json.loads(operation["arguments"])}
        runtime_outcome = json.loads(action["result"])
        assert runtime_outcome == case.provider.alignment_outcome
        runtime_outcome.pop("pending_work_after_action", None)
        assert runtime_outcome == json.loads(operation["result"])
        assert runtime_outcome["operation_ref"] == operation["id"]
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='sequence.align'").fetchone()[0] == 1
        comparison = selected_jobs[-1]
        assert comparison["request"]["correspondence"]["alignment"] == alignment
        comparison_grading, = [row for row in comparison["inputs"] if row["role"] == "alignment_grading"]
        assert comparison_grading["file_identity"] == alignment["grading_file"]
        descriptor, = case.returned[2]["saved"]
        sheet = json.loads(store.get_artifact(descriptor["sheet_file"]["artifact_ref"]))
        components = json.loads(store.get_artifact(descriptor["original_components_file"]["artifact_ref"]))
        assert sheet["native_baseline"] == components
        assert sheet["correspondence"]["alignment_native"]["descriptor"] == alignment
        assert components["fit"]["used_correspondence_ids"] == ["column_0", "column_1", "column_2"]
        assert components["evaluation"]["used_correspondence_ids"] == ["column_3"]
        projection, = case.returned[2]["summary"]
        cells = _cells(projection)
        assert list(cells) == F.SUMMARY_FIELDS
        expected = {"alignment_score": 19, "mapped_pair_count": 4, "fit_used_count": 3,
            "evaluation_used_count": 1, "evaluation_sse": 4, "evaluation_rmsd": 2}
        for field, value in expected.items():
            group = ("alignment" if field == "alignment_score" else "evaluation" if field in {"evaluation_sse", "evaluation_rmsd"} else "counts")
            assert cells[field]["value"] == components[group][field]
            assert cells[field]["value"]["value"] == pytest.approx(value, abs=1e-10)
        assert cells["evaluation_rmsd"]["value"]["unit"] == "angstrom"
        assert cells["evaluation_sse"]["value"]["unit"] == "angstrom_squared"
        assert cells["evaluation_rmsd"]["population"]["denominator"] == 1
        assert case.forwarded == [{"credit": 0}, {"summary": [projection]}, {"summary": [projection]}]
        assert case.flow.journal.row("runtime_forms", case.root_context.episode_id) is None
        root_received = returns.received_context(case.root_context)
        assert next(group["facts"] for group in root_received if group["fact_source"] == F.SOURCES["summary"]) == [projection]
        assert next(group["facts"] for group in returns.received_context(coordinator)
            if group["fact_source"] == F.SOURCES["summary"]) == [projection]
        for index, outcome in enumerate(case.outcomes):
            receipt, context = outcome["result"], case.result_contexts[index]
            body, publication = receipt["body"], receipt["publication"]
            assert body["intent"]["operation_key"] == f"{F.RUN_ID}:{context.episode_id}:0"
            assert body["intent"]["original_request_sha256"] == digest(plain(context.request))
            assert body["native_success"] and body["capture_complete"] and publication["delivery_complete"]
            assert body["worker"]["plan"]["mode"] == "original_native_result"
            assert body["bundle"]["requested_job"] == case.provider.plans[index]["requested_job"]
            assert case.owner.native_protein_structure_results.own_fact_groups(context, verify_artifacts=True) == publication["facts"]
            assert case.owner.native_protein_structure_results.read_result_authority(publication["custody"], scope=case.scope)["custody"] == publication["custody"]
        counts = {}
        for record in case.records:
            context = case.contexts[record["episode_id"]]
            n = store.db.execute("SELECT count(*) FROM runtime_actions WHERE run_id=? AND episode_id=?",
                (F.RUN_ID, context.episode_id)).fetchone()[0]
            assert n == record["units_consumed"] == case.provider.turns[context.episode_id]
            assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE run_id=? AND episode_id=?",
                (F.RUN_ID, context.episode_id)).fetchone()[0] == n
            counts[context.episode_id] = {"role": context.role, "actions": n, "observations": n}
            if context.role in {"launch", "launch_local", "results"}:
                assert n == 1 and record["controller_state"]["estimate"]["diagnostics"]["fitting_scope"] == "verified_assignment_endpoint"
                proof = case.owner.completion_for_action(context, f"{F.RUN_ID}:{context.episode_id}:0")
                assert proof is not None and case.owner.verify_completion(context, proof)
        # These are actual dispatched receiver inputs, not a new post-return
        # model call. Final numerical closure occurs after each final action.
        received_presentations = [row for row in presentations if row["received_child_reports"]]
        assert received_presentations
        assert any(row["episode_id"] == aligner.episode_id and "AGST" in row["text"] for row in presentations)
        assert all(row["six_quantity_question_visible"] for row in presentations if row["episode_id"] == aligner.episode_id)
        assert any("structure_sequence_descriptor_v1" in row["text"] for row in received_presentations)
        before = _tables(store)
        denied = []
        for fault in ("v1_label", "source", "receipt", "reference"):
            forged = deepcopy(alignment)
            if fault == "v1_label": forged["grading_file"]["format"] = "tool_grading_artifact_v1"
            elif fault == "source": forged["source_ref"] = fixed["custody"]["source_ref"]
            elif fault == "receipt": forged["original_operation_key"] = f"{F.RUN_ID}:{aligner.episode_id}:999"
            else: forged["query_reference_ref"] = moving["reference_ref"]
            with pytest.raises(ProteinStructureOperandError) as error:
                authenticate_selected_alignment(store, aligner, forged, fixed=fixed, moving=moving,
                    orientation="fixed_is_query", returns=returns)
            denied.append({"fault": fault, "issue": error.value.issue})
        broken = deepcopy(grading)
        broken["correspondence"]["instances"] = []
        with pytest.raises(ValueError, match="^invalid_traceback$"):
            _alignment_grading(broken, native_artifact_ref=alignment["native_file"]["artifact_ref"],
                grading_format="tool_grading_artifact_v2")
        for sequence in (fixed, moving):
            with pytest.raises(ProteinStructureOperandError) as error:
                authenticate_structure_sequence_reference(store, early, sequence["reference_ref"], returns=returns)
            assert error.value.issue["code"] == "sequence_not_received"
            assert case.flow.resolver(early.scope, grain=early.role, context=early)(sequence["reference_ref"], "reference") is False
        assert _tables(store) == before
        assert hashlib.sha256(Path(F.__file__).read_bytes()).hexdigest() == HELPER_SHA
        (tmp_path / "PROTEIN_STRUCTURE_CURRENT_V2_WORKFLOW.json").write_text(json.dumps({
            "qualification": "fresh tiny engineering structures and scripted decisions; actual native work and receipt-bound typed returns",
            "helper_sha256": HELPER_SHA, "saved_recalculation": False,
            "selected_native_jobs": selected_jobs, "native_plans": case.provider.plans,
            "alignment_dispatches": alignment_dispatches, "alignment_events": events,
            "alignment_descriptor": alignment, "alignment_operation_ref": operation["id"],
            "current_v2_companion": grading["correspondence"], "requested_values": expected,
            "literal_typed_projection": projection, "forwarded": case.forwarded,
            "root_received": root_received, "action_observation_counts": counts,
            "model_presentations": presentations, "negative_operand_checks": denied,
            "scientific_question": QUESTION,
            "local_message_scope": "Actual per-role kind/question visibility recorded; no local TASK/STEERING pass is claimed",
            "presentation_limit": "No added model turn after final numeric delivery; receiver text uses actual earlier dispatched contexts",
            "limits": "No biological accuracy, live acquisition, alternative structure population or saved recalculation claim"
        }, indent=2) + "\n")
    finally:
        case.store.close()
