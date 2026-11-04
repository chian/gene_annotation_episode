"""Explicitly gated public reference/edit integration, not a repair oracle.

The sequences are engineering inputs.  The first selector permits one genuine
global Biopython preparation action.  The second uses a pinned successful
checkpoint and permits no aligner, worker, acquisition or original-input read.
Scripted decisions pass through the real provider wire renderer without a model
RPC.  A late failure preserves the original action and never retries it.
"""

import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import reference_edit_outcome_tools as host
from gene_annotation_episode import reference_edit_outcomes as core
from gene_annotation_episode.runtime import INSTRUCTIONS, Workflow, _decode_action_response
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
REFERENCE = "GACTACGTTGCA"
EDITED = "GACTTCGTTGCA"
RUN_ID = "reference-edit-genuine-public-workflow"
PREFIX_NAME = "REFERENCE_EDIT_PREFIX.json"
PREFIX_VERSION = "reference_edit_public_workflow_prefix_v1"
QUESTION = (
    "For the supplied engineering reference GACTACGTTGCA and edited GACTTCGTTGCA, "
    "which nucleotide differences are actually observed in their selected global alignment? "
    "Return the retained reference/edit outcome group and its qualifications; keep "
    "observations separate from repair mechanism inference.")
PURPOSE = "Return the complete recorded reference/edit outcome group through the controlled form."
POLICY = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
SAVED_BINS = dict(deletion_upper_bounds_nt=[1, 4], insertion_upper_bounds_nt=[2, 5])
TABLES = ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls",
          "runtime_forms", "runtime_report_attempts", "runtime_record_receipts")


def _json(path):
    return json.loads(Path(path).read_text())


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _pin(path):
    path = Path(path).resolve(strict=True)
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))


def _inventory(directory):
    return {str(path.relative_to(directory)): {key: value for key, value in _pin(path).items() if key != "path"}
        for path in sorted(Path(directory).rglob("*")) if path.is_file() and not path.is_symlink()}


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}


def _counts(store, run_id):
    result = {name: store.db.execute("SELECT count(*) FROM " + name + " WHERE run_id=?", (run_id,)).fetchone()[0]
        for name in TABLES if name != "runtime_record_receipts"}
    result["tool_operations"] = store.db.execute("SELECT count(*) FROM tool_operations operation JOIN runtime_actions action "
        "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index WHERE action.run_id=?",
        (run_id,)).fetchone()[0]
    return result


def _audit(store, workflow, record):
    """Capture actual committed evidence before any post-execution assertion."""
    record.update(counts=_counts(store, workflow.run_id), journal={name: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (workflow.run_id,))] for name in TABLES},
        tool_operations=[dict(row) for row in store.db.execute("SELECT operation.* FROM tool_operations operation JOIN runtime_actions action "
            "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index "
            "WHERE action.run_id=? ORDER BY action.rowid", (workflow.run_id,))],
        provider_contexts=deepcopy(workflow.provider.contexts), provider_dispatches=deepcopy(workflow.provider.dispatches))
    return record


def _credit(*args, **kwargs):
    return 0


def _controller(child_actions):
    def factory(path, initial):
        stop = 1 if path[-1][0] == "annotation" else child_actions
        def estimate(history, parameters, contexts):
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= stop else 1),
                parameters, dict(engineering_fixture="explicit_public_communication_horizon"))
        return YieldController(str(path), initial, 0, estimate_with_context=estimate)
    return factory


def _schema():
    return obj({"outcomes": host.reference_edit_outcome_fact_sources()["reference_edit_outcomes"]["report_schema"]})


def _commission(library, scope, *, tools, evidence):
    return dict(selection=dict(kind="episode_child", role="scientific_process", goal=QUESTION,
        scope=deepcopy(scope), purpose=PURPOSE, schema_json=json.dumps(_schema()), initial_report_json="{}",
        assignment=dict(selection=dict(version="scientific_process_selection_v3",
            evidence_axis=library.reference("A101"), thought_pattern=library.reference("P01"),
            child_tool_info=[dict(name=name, resources="local") for name in tools]),
            evidence_refs=list(evidence), constraints=dict(no_external_acquisition=True),
            context=dict(engineering_inputs=True, repair_mechanism_not_inferred=True))), report_update={})


def _tool(name, arguments):
    return dict(selection=dict(kind="tool", tool=name, arguments=deepcopy(arguments)), report_update={})


def _alignment_operation(store, run_id):
    rows = list(store.db.execute("SELECT operation.* FROM tool_operations operation JOIN runtime_actions action "
        "ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index "
        "WHERE action.run_id=? AND operation.name='sequence.align'", (run_id,)))
    assert len(rows) == 1
    operation = dict(rows[0])
    outcome = json.loads(operation["result"])
    assert outcome["status"] == "completed", outcome
    return operation, outcome


class PublishedReferenceEditProvider:
    """Real TASK/STEERING presentation and protocol validation; no transport."""

    def __init__(self, store, library, scope, reference, edited, *, mode="analyze", result_ref=None):
        self.store, self.library, self.scope = store, library, deepcopy(scope)
        self.reference, self.edited, self.mode, self.result_ref = reference, edited, mode, result_ref
        self.contexts, self.dispatches, self.released = [], [], []
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, output_schema):
        index = len(self.contexts)
        self.contexts.append(deepcopy(context))
        rendered, wire_instructions = self.connection._presentation(episode_id, role, instructions, context)
        dispatch = dict(episode_id=episode_id, role=role, instructions=instructions, wire_instructions=wire_instructions,
            rendered=rendered, output_schema_sha256=digest(output_schema), response=None)
        self.dispatches.append(dispatch)
        assert role == "REASONING" and index < (3 if self.mode == "analyze" else 2)
        assert rendered.startswith("TASK\n") and "STEERING" in rendered and QUESTION in rendered
        assert context["goal"]["objective"] == QUESTION
        assert context["goal"]["task_context"]["root_objective"] == QUESTION
        assert context["scope"] == self.scope and context["feedback"] is None
        assert context["available_report_facts"]["reference_edit_outcomes"]["type"] == "array"
        names = ["sequence.align", host.TOOL] if self.mode == "analyze" else [host.TOOL]
        if index == 0:
            assert instructions.startswith(INSTRUCTIONS) and "scientific_process" not in context
            assert context["tools"] == [] and context["requested_form"] is None
            response = _commission(self.library, self.scope, tools=names,
                evidence=[] if self.mode == "analyze" else [self.result_ref])
        else:
            process = context["scientific_process"]
            selection = process["selection"]
            assert selection["evidence_axis"] == self.library.reference("A101")
            assert selection["thought_pattern"] == self.library.reference("P01")
            assert process["evidence_axis"] == instruction_view(self.library.resolve(selection["evidence_axis"]))
            assert process["thought_pattern"]["name"] == self.library.resolve(selection["thought_pattern"])["name"]
            assert context["requested_form"] == _schema() and context["requested_report_purpose"] == PURPOSE
            assert {row["name"] for row in process["child_tool_info"]} == set(names)
            assert set(names) <= {row["name"] for row in context["tools"]}
            for name in names:
                assert "Selected tool: " + name + " (local)" in rendered
            if self.mode == "analyze" and index == 1:
                response = _tool("sequence.align", dict(query_ref=self.edited, reference_ref=self.reference,
                    molecule="dna", mode="global"))
            elif self.mode == "analyze":
                _, aligned = _alignment_operation(self.store, RUN_ID)
                response = _tool(host.TOOL, dict(mode="analyze", population=[dict(reference_ref=self.reference,
                    edited_ref=self.edited, alignment_ref=aligned["result"]["observation_ref"], group_label="engineering_pair")],
                    gap_bins=None, guide_comparisons=[], template_comparisons=[]))
                assert aligned["result"]["observation_ref"] in rendered
            else:
                arguments = dict(mode=self.mode, result_ref=self.result_ref)
                if self.mode == "calculate_saved":
                    arguments["gap_bins"] = deepcopy(SAVED_BINS)
                response = _tool(host.TOOL, arguments)
        selected = response["selection"]
        discriminators = ("kind", "role", "tool")
        branches = [branch for branch in output_schema["properties"]["selection"]["anyOf"]
            if all(selected[key] in branch["properties"].get(key, {}).get("enum", [])
                for key in discriminators if key in selected)]
        assert len(branches) == 1
        fields = branches[0]["properties"]
        for key in ("assignment", "arguments"):
            if key in selected and fields[key].get("type") == "string":
                selected[key] = json.dumps(selected[key], allow_nan=False)
        if selected["kind"] == "episode_child":
            for key in fields["scope"]["required"]:
                if key not in selected["scope"]:
                    assert {"type": "null"} in fields["scope"]["properties"][key]["anyOf"]
                    selected["scope"][key] = None
        Draft202012Validator(output_schema).validate(response)
        dispatch["response"] = deepcopy(response)
        return response

    async def release(self, episode_id):
        self.released.append(episode_id)


def _workflow(store, tools, provider, directory, factory, scientific, initial, *, run_id, actions):
    application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
    return Workflow(store, tools, provider, directory, run_id, _controller(actions), _credit,
        project_child_credit=_credit, episode_binding_descriptors=[scientific, *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=initial)


def _prepare(store, directory, scope, reference, edited, *, run_id, mode="analyze", result_ref=None):
    workspace = directory / "workspace"
    workspace.mkdir(parents=True)
    factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))}, {}, 2, .25, .5)
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    factory.configure_tool_registry(tools)
    scientific = prepare_scientific_binding(run_directory=directory / "run", source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=["scientific_process"])
    library = ScientificProcessLibrary(directory / "run" / "scientific-process-library")
    provider = PublishedReferenceEditProvider(store, library, scope, reference, edited, mode=mode, result_ref=result_ref)
    initial = [] if mode == "analyze" else [result_ref]
    workflow = _workflow(store, tools, provider, directory / "run", factory, scientific, initial,
        run_id=run_id, actions=2 if mode == "analyze" else 1)
    record = dict(run_id=run_id, mode=mode, factory=factory.as_record(), scientific_binding=scientific,
        initial_known_record_refs=initial, workflow_directory=str(directory / "run"), scope=deepcopy(scope),
        reference_ref=reference, edited_ref=edited, calculator_events=[], input_file_read_attempts=[], passed=False)
    return tools, workflow, record


def _forbidden(*args, **kwargs):
    raise AssertionError("retained reference/edit proof attempted new scientific work")


def _forbid_native(patch):
    patch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
        patch.setattr(native_lifecycle, name, _forbidden)
    patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    patch.setattr("socket.create_connection", _forbidden)


def _guard_files(patch, references=None):
    """Guard actual File readers, independently of legitimate baseline receipts."""
    attempts = []
    selected = None if references is None else set(references)
    actual_get = Store.get_artifact
    actual_verified = retained_native_file.__globals__["_verified_artifact_path"]
    def check(reference):
        if selected is None or reference in selected:
            attempts.append(reference)
            raise AssertionError("reference/edit proof reopened a forbidden scientific File")
    def get(current, reference, *args, **kwargs):
        check(reference)
        return actual_get(current, reference, *args, **kwargs)
    def verified(current, reference, *args, **kwargs):
        check(reference)
        return actual_verified(current, reference, *args, **kwargs)
    patch.setattr(Store, "get_artifact", get)
    patch.setattr("gene_annotation_episode.materials._verified_artifact_path", verified)
    patch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", verified)
    return attempts


def _run_guarded(root, workflow, record, input_files, monkeypatch):
    """Guard CAS9/input independence without changing initial input delivery."""
    actual_execute = host.execute_reference_edit_outcome
    with monkeypatch.context() as patch:
        def execute(registry, arguments, *, scope, operation_key, authority):
            with patch.context() as guarded:
                _forbid_native(guarded)
                attempts = _guard_files(guarded, input_files)
                try:
                    return actual_execute(registry, arguments, scope=scope, operation_key=operation_key, authority=authority)
                finally:
                    record["input_file_read_attempts"].extend(attempts)
        patch.setattr(host, "execute_reference_edit_outcome", execute)
        for name in ("molecular_own_facts", "molecular_received_facts", "molecular_frozen_facts"):
            actual = getattr(type(workflow.services), name)
            def facts(current, *args, _actual=actual, **kwargs):
                with patch.context() as guarded:
                    _forbid_native(guarded)
                    attempts = _guard_files(guarded, input_files)
                    try:
                        return _actual(current, *args, **kwargs)
                    finally:
                        record["input_file_read_attempts"].extend(attempts)
            patch.setattr(type(workflow.services), name, facts)
        return asyncio.run(root.run_async(workflow.context))


def _recorded_calls(store, workflow, record):
    calls = [dict(row) for row in store.db.execute("SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid", (workflow.run_id,))]
    assert len(calls) == len(record["provider_dispatches"]) == (3 if record["mode"] == "analyze" else 2)
    for call, dispatch in zip(calls, record["provider_dispatches"]):
        request = json.loads(call["request"])
        assert call["episode_id"] == dispatch["episode_id"] and call["purpose"] == "decision"
        assert json.loads(call["response"]) == dispatch["response"]
        Draft202012Validator(request["schema"]).validate(_decode_action_response(json.loads(call["response"]), request["schema"]))
        assert request["context"]["goal"]["objective"] == QUESTION
        assert request["context"]["scope"] == record["scope"]
        assert dispatch["rendered"].startswith("TASK\n") and QUESTION in dispatch["rendered"]
    return calls


def _assert_values(public, *, reference, edited, alignment, native_source, bins):
    assert core.validate_reference_edit_outcome_return(public) == public
    assert public["status"] == "complete" and public["issue_codes"] == []
    assert public["alignment_unit"] == "nt" and public["coordinate_system"] == "zero_based_half_open_local_operands"
    assert public["gap_bins"] == bins and public["guide_comparisons"] == public["template_comparisons"] == []
    pair, = public["pairs"]
    assert {key: pair[key] for key in ("pair_ordinal", "reference_ref", "edited_ref", "alignment_ref", "source_ref", "group_label")} == dict(
        pair_ordinal=0, reference_ref=reference, edited_ref=edited, alignment_ref=alignment, source_ref=native_source, group_label="engineering_pair")
    assert pair["state"] == "complete" and pair["coverage_scope"] == "full_global" and pair["full_global_pair"] is True
    assert pair["observed_change_types"] == ["substitution"] and pair["whole_pair_type"] == "substitution_only"
    assert pair["counts"] == dict(alignment_columns=12, paired_positions=12, identical_positions=11,
        substituted_positions=1, query_gap_columns=0, reference_gap_columns=0,
        query_aligned_positions=12, reference_aligned_positions=12)
    assert pair["native"]["molecule"] == "dna" and pair["native"]["mode"] == "global"
    assert pair["native"]["format"] == "biopython_pairwise_native_v2"
    assert pair["native"]["score_unit"] == "native_alignment_score"
    event, = pair["events"]
    assert {key: event[key] for key in ("event_ordinal", "kind", "alignment_column_interval", "reference_interval", "query_interval",
        "reference_sequence", "query_sequence", "reference_boundary")} == dict(event_ordinal=0, kind="substitution",
        alignment_column_interval=[4, 5], reference_interval=[4, 5], query_interval=[4, 5], reference_sequence="A", query_sequence="T", reference_boundary=None)
    for role, subject in (("query", edited), ("reference", reference)):
        mapping = event[role + "_mapping"]
        assert mapping["status"] == "available" and mapping["reason"] is None
        assert mapping["intervals"] == [dict(subject_ref=subject, start=4, end=5, unit="nt", strand="+")]
    overall = public["populations"]["overall"]
    assert overall["unit"] == "pair_occurrences"
    assert {key: overall[key] for key in ("declared_pair_count", "selected_alignment_count", "classified_pair_count",
        "not_selected_pair_count", "unclassified_pair_count")} == dict(declared_pair_count=1, selected_alignment_count=1,
        classified_pair_count=1, not_selected_pair_count=0, unclassified_pair_count=0)
    for category in overall["categories"]:
        count = 1 if category["kind"] == "substitution_only" else 0
        assert category["count"] == count
        for key in ("fraction_of_classified", "observed_fraction_of_declared"):
            assert category[key] == dict(value=float(count), numerator=count, denominator=1, unit="fraction")


def _contexts(store, workflow):
    records = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="reference_edit_workflow_proof_")
    rows = list(store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (workflow.run_id,)))
    assert len(rows) == 2
    return tuple(records.context(row["episode_id"]) for row in rows)


def _closed_return(workflow, parent, science, scope):
    root = workflow.build("annotation", "root", QUESTION, scope)
    completed = asyncio.run(root.run_async(workflow.context))
    final = plain(asyncio.run(root.build_result(completed)).as_record())
    commission = workflow.journal.row("runtime_actions", parent.episode_id, 0)
    child = workflow.selected(root.source, json.loads(commission["action"]), 0).child
    assert child.source.episode_id == science.episode_id
    current = workflow.context
    boundary = type(current).from_commission(tree=current.tree, run_id=workflow.run_id,
        parent_path=root.source.path, parent_goal_id=root.goal.goal_id, child_goal_id=child.goal.goal_id,
        grain=child.grain.name, key=child.key)
    try:
        workflow.context = boundary
        closed = asyncio.run(child.run_async(boundary))
        returned = plain(asyncio.run(child.build_result(closed)).as_record())
    finally:
        workflow.context = current
    return final, returned


def _frozen(store, tools, workflow, record, monkeypatch):
    parent, science = _contexts(store, workflow)
    before, artifacts, run = _tables(store), _inventory(store.path / "artifacts"), _inventory(workflow.directory)
    with monkeypatch.context() as patch:
        _forbid_native(patch)
        patch.setattr(core, "calculate_reference_edit_outcome_components", _forbidden)
        patch.setattr(core, "populate_reference_edit_outcome_sheet", _forbidden)
        patch.setattr(ToolRegistry, "execute_async", _forbidden)
        patch.setattr(workflow.provider, "complete", _forbidden)
        blocked = _guard_files(patch)
        final, child = _closed_return(workflow, parent, science, record["scope"])
    assert final == dict(credit=0, pending_handles=[]) and child == dict(form=record["returned"])
    assert blocked == [] and _tables(store) == before and _inventory(store.path / "artifacts") == artifacts
    assert _inventory(workflow.directory) == run
    # Reconstruct actual factory/services, library, runtime and closed child.
    provider = PublishedReferenceEditProvider(store, workflow.scientific_process_binding.library, record["scope"],
        record["reference_ref"], record["edited_ref"], mode=record["mode"])
    factory = ExecutionServiceFactory.from_record(record["factory"])
    with monkeypatch.context() as patch:
        _forbid_native(patch)
        patch.setattr(core, "calculate_reference_edit_outcome_components", _forbidden)
        patch.setattr(core, "populate_reference_edit_outcome_sheet", _forbidden)
        patch.setattr(ToolRegistry, "execute_async", _forbidden)
        patch.setattr(provider, "complete", _forbidden)
        blocked = _guard_files(patch)
        reopened_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        factory.configure_tool_registry(reopened_tools)
        reopened = _workflow(store, reopened_tools, provider, workflow.directory, factory,
            deepcopy(record["scientific_binding"]), record["initial_known_record_refs"],
            run_id=record["run_id"], actions=2 if record["mode"] == "analyze" else 1)
        reopened_parent, reopened_science = _contexts(store, reopened)
        other_final, other_child = _closed_return(reopened, reopened_parent, reopened_science, record["scope"])
    assert other_final == final and other_child == child and blocked == []
    assert provider.contexts == provider.dispatches == []
    assert _tables(store) == before and _inventory(store.path / "artifacts") == artifacts
    assert _inventory(workflow.directory) == run
    return dict(final_result=final, closed_child=child, reopened_child=other_child,
        new_model_dispatches=0, scientific_file_attempts=blocked)


def _verify_phase(store, tools, workflow, record, *, original, baseline_files, monkeypatch):
    native = record["mode"] == "analyze"
    assert record["counts"] == dict(runtime_episodes=2, runtime_actions=3 if native else 2,
        runtime_observations=3 if native else 2, runtime_model_calls=3 if native else 2,
        runtime_forms=1, runtime_report_attempts=1, tool_operations=2 if native else 1)
    assert record["calculator_events"] == (["call", "return"] if record["mode"] != "read_stored" else [])
    assert record["input_file_read_attempts"] == []
    parent, science = _contexts(store, workflow)
    index = 1 if native else 0
    key = f"{workflow.run_id}:{science.episode_id}:{index}"
    operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
    assert operation is not None and operation["name"] == host.TOOL
    arguments, outcome = json.loads(operation["arguments"]), json.loads(operation["result"])
    assert outcome["status"] == "completed" and outcome["feedback"] is None
    assert outcome["record_refs"] == [outcome["result"]["source_ref"]]
    assert outcome["changed_record_refs"] == ([] if record["mode"] == "read_stored" else outcome["record_refs"])
    action = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
        (workflow.run_id, science.episode_id, index)).fetchone()
    assert json.loads(action["action"]) == dict(kind="tool", tool=host.TOOL, arguments=arguments)
    assert canonical({key: value for key, value in json.loads(action["result"]).items() if key != "pending_work_after_action"}) == canonical(outcome)
    with monkeypatch.context() as patch:
        attempts = _guard_files(patch, original["forbidden_saved_files"])
        public = host.read_reference_edit_outcome_action_result(tools, science, arguments, key,
            reader=workflow.services.read_received_molecular_input)
        publication = host.read_reference_edit_outcome_publication(tools, science,
            workflow.services.read_received_molecular_input, public["source_ref"], require_envelope=True)
        assert workflow.services.molecular_own_facts(science, fact_source="reference_edit_outcomes") == [public]
        assert workflow.services.molecular_frozen_facts(science, fact_source="reference_edit_outcomes") == [public]
        assert workflow.services.molecular_received_facts(parent, fact_source="reference_edit_outcomes") == [public]
    assert attempts == [] and public == outcome["result"] == publication["public"]
    capture, = publication["stored"]["sheet"]["alignment_inputs"]
    assert set(capture) == {"source", "operands", "grading", "correspondence", "original_mappings"}
    assert capture["source"]["source_ref"] == original["native_source_ref"]
    assert capture["source"]["alignment_ref"] == original["alignment_ref"]
    assert capture["source"]["provider"] == "biopython.alignment" and capture["source"]["format"] == "biopython_pairwise_json"
    assert capture["grading"]["sheet"] is not None and capture["grading"]["scores"] is not None
    assert capture["grading"]["failure"] is None and capture["correspondence"] is not None
    _assert_values(public, reference=record["reference_ref"], edited=record["edited_ref"],
        alignment=original["alignment_ref"], native_source=original["native_source_ref"],
        bins=SAVED_BINS if record["mode"] == "calculate_saved" else None)
    source = publication["source"]
    assert source["provider"] == host.TOOL and source["version"] == host.RESULT_VERSION and "operand_refs" not in source
    if record["mode"] == "read_stored":
        assert source["id"] == record["result_ref"] and public == original["public"]
    elif record["mode"] == "calculate_saved":
        assert source["id"] != record["result_ref"] and source["parent_source_refs"] == [record["result_ref"]]
        for field in ("pairs", "populations", "guide_comparisons", "template_comparisons", "issue_codes", "status"):
            actual, retained = deepcopy(public[field]), deepcopy(original["public"][field])
            if field == "pairs":
                for pair in actual:
                    pair["gap_bins"] = None
            assert actual == retained
    else:
        assert source["parent_source_refs"] == [original["native_source_ref"]]
    packet = publication["packet"]
    assert packet == dict(version=host.PACKET_VERSION,
        value={key: deepcopy(value) for key, value in public.items() if key not in ("version", "source_ref")})
    assert REFERENCE not in json.dumps(packet) and EDITED not in json.dumps(packet)
    returned = dict(outcomes=[public])
    form, = list(store.db.execute("SELECT * FROM runtime_forms WHERE run_id=? AND episode_id=?", (workflow.run_id, science.episode_id)))
    assert json.loads(form["form"]) == returned and json.loads(form["facts"])["reference_edit_outcomes"] == [public]
    delivery, = list(store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=?", (workflow.run_id,)))
    assert delivery["failure"] is None and json.loads(delivery["form"]) == returned
    private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
    for context in (parent, science):
        known = set(workflow.receipts.known(context.episode_id))
        assert source["id"] in known and not private.intersection(known)
        files = {reference for reference in known if reference.startswith("artifact_")}
        permitted = set(baseline_files)
        if native and context is science:
            # The actual alignment action retains its own existing delivery.
            permitted.update(original["alignment_delivered_files"])
        assert files <= permitted
    parent_known = set(workflow.receipts.known(parent.episode_id))
    assert original["alignment_ref"] not in parent_known and original["native_source_ref"] not in parent_known
    calls = _recorded_calls(store, workflow, record)
    record.update(public=public, source=source, returned=returned, operation=dict(operation), model_calls=calls,
        private_source_files=sorted(private), privacy=dict(baseline_input_files=sorted(baseline_files),
            new_cas9_file_grants=[], input_file_read_attempts=[]))
    record["frozen"] = _frozen(store, tools, workflow, record, monkeypatch)
    record["passed"] = True
    return record


def _profile(record):
    previous = sys.getprofile()
    code = core.calculate_reference_edit_outcome_components.__code__
    def observe(frame, event, value):
        if previous is not None:
            previous(frame, event, value)
        if frame.f_code is code and event in ("call", "return"):
            record["calculator_events"].append(event)
    return previous, observe


def _source_files(source):
    return [reference for reference in [source.get("artifact_ref"), source.get("request_ref"),
        *source.get("auxiliary_artifact_refs", [])] if reference is not None]


def test_genuine_reference_edit_public_workflow_and_parent_return(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_REFERENCE_EDIT_WORKFLOW") != "1" or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("requires explicit bounded genuine reference/edit Workflow selection")
    path, store_directory = tmp_path / PREFIX_NAME, tmp_path / "store"
    proof = dict(version=PREFIX_VERSION, run_id=RUN_ID, question=QUESTION, store_directory=str(store_directory),
        workflow_directory=str(tmp_path / "run"), test_root=str(tmp_path), passed=False, native_execution_verified=False,
        qualification="Engineering input pair; one genuine global alignment; observed substitution is not a repair mechanism",
        runtime_python=_pin(sys.executable), publication_inputs={name: _pin(PUBLICATION / name)
            for name in ("index.json", "entries/A101.json", "entries/P01.json")}, native_calls=[], native_handles=[])
    _write(path, proof)
    try:
        with Store(store_directory) as store:
            pair_file = tmp_path / "engineering-reference-edited.fa"
            pair_file.write_text(">reference\n" + REFERENCE + "\n>edited\n" + EDITED + "\n")
            reference, edited = store.create_problem(pair_file, molecule="dna")["subject_refs"]
            scope = store.validate_scope(dict(subject_refs=[reference, edited]))
            inputs = [store.get(reference)["sequence_ref"], store.get(edited)["sequence_ref"]]
            tools, workflow, phase = _prepare(store, tmp_path, scope, reference, edited, run_id=RUN_ID)
            proof.update(phase, input_files=inputs, input_records=[store.get(reference), store.get(edited)])
            proof["initial_scientific_observation_count"] = store.count("observation")
            root = workflow.build("annotation", "root", QUESTION, scope)
            baseline_files = {ref for ref in workflow.receipts.known(root.source.episode_id) if ref.startswith("artifact_")}
            assert set(inputs) <= baseline_files
            proof.update(baseline_input_files=sorted(baseline_files), engineering_input_file=_pin(pair_file))
            actual_worker = ToolRegistry._sequence_worker_async
            actual_prepare, actual_collect = native_lifecycle.prepare_job, native_lifecycle.collect
            async def worker(current, operation, arguments, directory):
                evidence = dict(operation=operation, arguments=deepcopy(arguments), directory=str(directory), metadata=None)
                proof["native_calls"].append(evidence)
                assert len(proof["native_calls"]) == 1 and operation == "align_pair"
                result = await actual_worker(current, operation, arguments, directory=directory)
                evidence["metadata"] = deepcopy(result.metadata)
                return result
            def prepare(*args, **kwargs):
                assert proof["native_handles"] == []
                handle = actual_prepare(*args, **kwargs)
                body = handle.read()
                proof["native_handles"].append(dict(prepared=body, returned=None, metadata=None,
                    lifecycle_request_file=_pin(body["paths"]["request"]),
                    scientific_request_file=_pin(body["command"][-2]), scientific_request=_json(body["command"][-2])))
                return handle
            def collect(handle):
                result = actual_collect(handle)
                proof["native_handles"][0].update(returned=handle.read(), metadata=deepcopy(result.metadata))
                return result
            previous, observe = _profile(proof)
            try:
                with monkeypatch.context() as patch:
                    patch.setattr(ToolRegistry, "_sequence_worker_async", worker)
                    patch.setattr(native_lifecycle, "prepare_job", prepare)
                    patch.setattr(native_lifecycle, "collect", collect)
                    patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
                    patch.setattr("socket.create_connection", _forbidden)
                    sys.setprofile(observe)
                    completed = _run_guarded(root, workflow, proof, baseline_files, patch)
            finally:
                sys.setprofile(previous)
                _audit(store, workflow, proof)
                _write(path, proof)
            _, aligned = _alignment_operation(store, RUN_ID)
            observation = store.get(aligned["result"]["observation_ref"])
            native_source = store.get(aligned["result"]["source_ref"])
            assert observation["source_ref"] == native_source["id"]
            assert native_source["provider"] == "biopython.alignment"
            assert native_source["operand_refs"] == [edited, reference]
            assert store.count("observation") == proof["initial_scientific_observation_count"] + 1
            assert proof["native_calls"][0]["arguments"] == dict(query=EDITED, reference=REFERENCE, molecule="dna", mode="global")
            handle, = proof["native_handles"]
            assert handle["prepared"]["command"][:3] == [sys.executable, "-m", "gene_annotation_episode.sequence_worker"]
            assert handle["scientific_request"] == dict(operation="align_pair", arguments=proof["native_calls"][0]["arguments"])
            assert handle["returned"]["unit"] == handle["prepared"]["unit"]
            assert handle["metadata"]["native_returncode"] == 0 and handle["metadata"]["policy"] == POLICY
            proof["native_execution_verified"] = True
            original = dict(alignment_ref=observation["id"], native_source_ref=native_source["id"],
                forbidden_saved_files=[*sorted(baseline_files), *_source_files(native_source)],
                alignment_delivered_files=_source_files(native_source))
            proof.update(alignment_ref=observation["id"], native_source_ref=native_source["id"], native_source=native_source,
                original_alignment=observation, original_native_file_pins={ref: store.get(ref) for ref in _source_files(native_source)})
            _write(path, proof)
            _verify_phase(store, tools, workflow, proof, original=original, baseline_files=baseline_files, monkeypatch=monkeypatch)
            assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
            proof.update(original=original, original_scientific_observations=[store.get(ref) for ref in aligned["record_refs"]
                if store.get(ref).get("record_type") == "observation"], native_call_count=1)
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (store_directory / "state.sqlite3").is_file():
            proof["database_file"] = _pin(store_directory / "state.sqlite3")
        _write(path, proof)


def _retained_prefix():
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_REFERENCE_EDIT_RETAINED_PREFIX")
    selected_sha = os.environ.get("HMMER_NATIVE_ORACLE_REFERENCE_EDIT_RETAINED_SHA256")
    if not supplied or not selected_sha or "HMMER529_ATTEMPT" not in os.environ:
        pytest.skip("requires an explicit successful reference/edit prefix and byte digest")
    path = Path(supplied).resolve(strict=True)
    assert _pin(path)["sha256"] == selected_sha
    prefix = _json(path)
    assert prefix["version"] == PREFIX_VERSION and prefix["run_id"] == RUN_ID and prefix["question"] == QUESTION
    assert prefix["passed"] is True and prefix["native_execution_verified"] is True and prefix["native_call_count"] == 1
    assert _pin(prefix["database_file"]["path"]) == prefix["database_file"]
    assert not Path(prefix["database_file"]["path"] + "-wal").exists()
    return path, prefix


def _clone(prefix, directory):
    directory.mkdir()
    target = directory / "store"
    target.mkdir()
    source = Store.__new__(Store)
    source.path = Path(prefix["store_directory"]).resolve(strict=True)
    source.db = sqlite3.connect((source.path / "state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    source.db.row_factory = sqlite3.Row
    source._savepoint = 0
    source.db.create_function("library_scope_record", 2, source._scope_filter_record)
    try:
        original = _tables(source)
        connection = sqlite3.connect(target / "state.sqlite3")
        try:
            source.db.backup(connection)
        finally:
            connection.close()
        assert source.db.total_changes == 0
    finally:
        source.close()
    for name in ("artifacts", "cache"):
        retained = Path(prefix["store_directory"]) / name
        if retained.exists():
            shutil.copytree(retained, target / name)
    shutil.copytree(prefix["workflow_directory"], directory / "original-run")
    return target, original


def _saved_phase(store, prefix, directory, *, mode, monkeypatch):
    directory.mkdir()
    run_id = RUN_ID + "-" + mode
    tools, workflow, record = _prepare(store, directory, prefix["scope"], prefix["reference_ref"], prefix["edited_ref"],
        run_id=run_id, mode=mode, result_ref=prefix["public"]["source_ref"])
    record["result_ref"] = prefix["public"]["source_ref"]
    path = directory / "REFERENCE_EDIT_SAVED_PHASE.json"
    _write(path, record)
    try:
        root = workflow.build("annotation", "root", QUESTION, prefix["scope"])
        baseline = set(workflow.receipts.known(root.source.episode_id))
        baseline_files = {ref for ref in baseline if ref.startswith("artifact_")}
        assert baseline_files == set(prefix["baseline_input_files"])
        assert {prefix["reference_ref"], prefix["edited_ref"], record["result_ref"]} <= baseline
        previous, observe = _profile(record)
        try:
            with monkeypatch.context() as patch:
                _forbid_native(patch)
                # Parent/child context construction may legitimately inspect
                # the initially scoped Inputs.  The action and fact guards in
                # _run_guarded independently forbid those Input File reads.
                original_native_files = set(prefix["original"]["forbidden_saved_files"]) - set(prefix["baseline_input_files"])
                blocked = _guard_files(patch, original_native_files)
                if mode == "read_stored":
                    patch.setattr(core, "calculate_reference_edit_outcome_components", _forbidden)
                    patch.setattr(core, "populate_reference_edit_outcome_sheet", _forbidden)
                    # A literal read needs only the original public packet.
                    source = prefix["source"]
                    private = [source["request_ref"], *source["auxiliary_artifact_refs"]]
                    with patch.context() as literal:
                        private_attempts = _guard_files(literal, [*original_native_files, *private])
                        completed = _run_guarded(root, workflow, record, prefix["baseline_input_files"], literal)
                    assert private_attempts == []
                else:
                    sys.setprofile(observe)
                    completed = _run_guarded(root, workflow, record, prefix["baseline_input_files"], patch)
                assert blocked == []
        finally:
            sys.setprofile(previous)
            _audit(store, workflow, record)
            _write(path, record)
        assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
        original = dict(prefix["original"], public=prefix["public"])
        with monkeypatch.context() as patch:
            _forbid_native(patch)
            patch.setattr(core, "calculate_reference_edit_outcome_components", _forbidden)
            _verify_phase(store, tools, workflow, record, original=original, baseline_files=baseline_files, monkeypatch=patch)
        return record
    except BaseException as error:
        record["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        _write(path, record)


def test_retained_reference_edit_public_saved_modes_and_closed_replay(tmp_path, monkeypatch):
    prefix_path, prefix = _retained_prefix()
    owned = tmp_path / "owned-reference-edit"
    target, before = _clone(prefix, owned)
    proof_path = tmp_path / "REFERENCE_EDIT_SAVED_PROOF.json"
    proof = dict(version="reference_edit_public_saved_proof_v1", retained_prefix=_pin(prefix_path),
        original_database=prefix["database_file"], store_directory=str(target), phases=[], passed=False)
    _write(proof_path, proof)
    try:
        with Store(target) as store:
            assert _tables(store) == before
            original_records = {reference: store.get(reference) for reference in [prefix["public"]["source_ref"],
                prefix["alignment_ref"], prefix["native_source_ref"]]}
            original_files = {reference: store.get_artifact(reference) for reference in [*prefix["original"]["forbidden_saved_files"],
                *_source_files(prefix["source"])]}
            original_rows = {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (RUN_ID,))]
                for name in TABLES}
            original_observation_count = store.count("observation")
            with monkeypatch.context() as patch:
                _forbid_native(patch)
                for mode in ("read_stored", "calculate_saved"):
                    phase = _saved_phase(store, prefix, owned / mode, mode=mode, monkeypatch=patch)
                    proof["phases"].append(phase)
                    _write(proof_path, proof)
            read, calculated = proof["phases"]
            assert read["source"]["id"] == prefix["source"]["id"]
            assert calculated["source"]["id"] != prefix["source"]["id"]
            assert calculated["source"]["parent_source_refs"] == [prefix["source"]["id"]]
            assert read["calculator_events"] == [] and calculated["calculator_events"] == ["call", "return"]
            assert {reference: store.get(reference) for reference in original_records} == original_records
            assert {reference: store.get_artifact(reference) for reference in original_files} == original_files
            assert store.count("observation") == original_observation_count
            assert {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name + " WHERE run_id=? ORDER BY rowid", (RUN_ID,))]
                for name in TABLES} == original_rows
            assert _pin(prefix["database_file"]["path"]) == prefix["database_file"]
            proof.update(passed=True, original_records_unchanged=True, original_native_and_model_work_unchanged=True,
                new_native_call_state="not_requested", explicit_saved_calculator_events=calculated["calculator_events"])
    except BaseException as error:
        proof["test_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (target / "state.sqlite3").is_file():
            proof["database_file"] = _pin(target / "state.sqlite3")
        _write(proof_path, proof)
