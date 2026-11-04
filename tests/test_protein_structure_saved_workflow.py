"""Gated retained protein values through one current scientific Workflow.

The original two-residue comparison is genuine retained engineering evidence.
Scripted choices and explicit controller horizons exercise public tools and the
real provider renderer; they are not model reasoning or biological inference.
Only one selected saved-sheet worker may run.  Native parsing, fitting and the
original comparison are forbidden, and every failure preserves its prefix.
"""

import asyncio
import builtins
from copy import deepcopy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3

import pytest
from jsonschema import Draft202012Validator
from method_loop import ClosedChildUnit
from method_loop.archive import ArchivedRecord, iter_json

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import apply_state_frame, state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_protein_structure_contracts import POLICY
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.protein_structure_action_records import (
    SAVED_SOURCE, VIEW_SOURCE, frozen_protein_structure_action_facts,
    protein_structure_action_fact_sources,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import INSTRUCTIONS, DecisionSource, Workflow, _decode_action_response
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_macs2_peak_workflow import _provider_value
from test_protein_structure_ordinary_workflow import _configuration, _projection


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
ORIGINAL_DATABASE_SHA256 = "ef1d21820f9302b8a74ae38af7ef6f10beeee2707c0c54e54eb44b69cbc8a3f1"
ORIGINAL_SOURCE = "source_f530802cb4abed939775443b"
TOOL = "compare_protein_structures"
QUESTION = ("For the retained two-structure comparison, what fraction of evaluated corresponding Cα sites "
    "exceeds 0.5 Å rather than 2 Å, using the same supplied transform and site population?")
PURPOSE = "Return the actual retained protein value views with their site populations and qualifications."
SUMMARY = ["mapped_pair_count", "fit_used_count", "evaluation_used_count", "above_threshold_count",
    "above_threshold_fraction", "evaluation_sse", "evaluation_rmsd"]
PREFIX_NAME = "PROTEIN_STRUCTURE_SAVED_WORKFLOW.json"


def _pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _inventory(directory):
    return {str(path.relative_to(directory)): _pin(path) for path in sorted(Path(directory).rglob("*")) if path.is_file()}


def _journal(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [dict(row) for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')]
        for name in names}


def _json(store, reference):
    return json.loads(store.get_artifact(reference))


def _archive_value(record):
    """Use the existing serializer, including nested archived Episode records."""
    return json.loads("".join(iter_json(record.as_record())))


def _sqlite_bundle_pins(directory):
    return [dict(name=name, sha256=entry["sha256"], size_bytes=entry["size_bytes"])
        for name in ("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm")
        if (path := Path(directory) / name).is_file() for entry in [_pin(path)]]


def _modes(directory):
    root = Path(directory)
    return {str(path.relative_to(root)): path.lstat().st_mode
        for path in [root, *sorted(root.rglob("*"))]}


def _schema():
    return obj({"views": protein_structure_action_fact_sources()[VIEW_SOURCE]["report_schema"]})


def _summary(identity, fields=SUMMARY):
    return _projection(identity, "comparison_summary", dict(kind="comparison"), list(fields))


def _sites():
    return _projection("saved-distances", "site_measurements", dict(kind="all_evaluation_requests"),
        ["distance", "distance_squared"])


def _cells(view):
    row, = view["outcome"]["rows"]
    return {cell["field"]: cell for cell in row["values"]}


def _assert_post_calculation_wire(context, wire, result):
    """Check actual selected quantity leaves in STEERING, not schema prose."""
    assert context["last_local_outcome"]["result"] == result
    steering = wire.split("\n\nSTEERING\n", 1)[1]
    summary = result["views"][0]["outcome"]["rows"][0]["values"]
    for index, cell in enumerate(summary):
        prefix = "result.views[0].outcome.rows[0].values[" + str(index) + "]"
        assert "| " + prefix + ".field | " + cell["field"] + " |" in steering
        for key in ("value", "state", "unit"):
            value = cell["value"][key]
            literal = "null" if value is None else str(value)
            assert "| " + prefix + ".value." + key + " | " + literal + " |" in steering
        if cell["field"] == "above_threshold_fraction":
            assert cell["population"]["numerator"] == 1 and cell["population"]["denominator"] == 2
            for key in ("numerator", "denominator"):
                assert "| " + prefix + ".population." + key + " | " + str(cell["population"][key]) + " |" in steering
    for index, row in enumerate(result["views"][1]["outcome"]["rows"]):
        cell = row["values"][0]["value"]
        assert cell["value"] == index and cell["unit"] == "angstrom"
        prefix = "result.views[1].outcome.rows[" + str(index) + "].values[0].value"
        assert "| " + prefix + ".value | " + str(cell["value"]) + " |" in steering
        assert "| " + prefix + ".unit | angstrom |" in steering


def _outcomes(store, run_id):
    rows = list(store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? ORDER BY rowid", (run_id,)))
    return [(dict(row), json.loads(row["result"])) for row in rows
        if row["result"] is not None and json.loads(row["action"]).get("tool") == TOOL]


def _controller(path, initial):
    horizon = 4 if path[-1][0] == "scientific_process" else 1
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1), parameters,
            dict(engineering_fixture="explicit retained-protein communication horizon; not scientific confidence"))
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


def _forbidden(*args, **kwargs):
    raise AssertionError("retained protein proof attempted original native, acquisition, fitting or new work")


def _guard_raw_files(monkeypatch, directories, references, attempts):
    """Deny selected original input bodies through ordinary Python file APIs."""
    paths = {str(Path(directory) / "artifacts" / ref[9:11] / ref[9:])
        for directory in directories for ref in references}
    original_open, original_io_open, original_os_open = builtins.open, io.open, os.open
    def check(value, *, dir_fd=None):
        if isinstance(value, int):
            return
        path = Path(os.fsdecode(value))
        if not path.is_absolute():
            base = Path(os.readlink("/proc/self/fd/" + str(dir_fd))) if dir_fd is not None else Path.cwd()
            path = base / path
        if os.path.normpath(str(path)) in paths:
            attempts.append(str(path))
            raise AssertionError("saved protein operation opened an original structure/map File")
    def opened(file, *args, **kwargs):
        check(file)
        return original_open(file, *args, **kwargs)
    def io_opened(file, *args, **kwargs):
        check(file)
        return original_io_open(file, *args, **kwargs)
    def os_opened(file, flags, *args, **kwargs):
        check(file, dir_fd=kwargs.get("dir_fd"))
        return original_os_open(file, flags, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", opened)
    monkeypatch.setattr(io, "open", io_opened)
    monkeypatch.setattr(os, "open", os_opened)


def _closed_delivery(flow, scope, parent, science):
    root = flow.build("annotation", "root", QUESTION, scope)
    record = asyncio.run(root.run_async(flow.context))
    final = plain(asyncio.run(root.build_result(record)).as_record())
    commission = flow.journal.row("runtime_actions", parent.episode_id, 0)
    selected = flow.selected(root.source, json.loads(commission["action"]), 0)
    if isinstance(selected, ClosedChildUnit):
        assert selected.record.episode_id == science.episode_id
        assert plain(selected.record.path) == plain(science.path)
        return _archive_value(record), final, plain(selected.result.as_record())
    child = selected.child
    assert child.source.episode_id == science.episode_id
    current = flow.context
    boundary = type(current).from_commission(tree=current.tree, run_id=flow.run_id,
        parent_path=root.source.path, parent_goal_id=root.goal.goal_id, child_goal_id=child.goal.goal_id,
        grain=child.grain.name, key=child.key)
    try:
        flow.context = boundary
        closed = asyncio.run(child.run_async(boundary))
        returned = plain(asyncio.run(child.build_result(closed)).as_record())
    finally:
        flow.context = current
    return _archive_value(record), final, returned


class PublishedSavedProteinProvider:
    """Scripted public decisions rendered from their actual full state frames."""

    def __init__(self, store, library, scope, run_id, checkpoint):
        self.store, self.library, self.scope, self.run_id = store, library, deepcopy(scope), run_id
        self.checkpoint = checkpoint
        self.calls, self.previous, self.released = [], {}, []
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, output_schema):
        previous = self.previous.get(episode_id)
        frame = state_frame(context, previous)
        assert apply_state_frame(previous, frame) == context
        self.previous[episode_id] = deepcopy(context)
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions, frame)
        call = dict(episode_id=episode_id, role=role, context=deepcopy(context), frame=deepcopy(frame),
            instructions=instructions, wire_instructions=wire_instructions, wire=wire,
            wire_sha256=hashlib.sha256(wire.encode()).hexdigest(), wire_bytes=len(wire.encode()), response=None)
        self.calls.append(call)
        self.checkpoint("decision_recorded")
        assert role == "REASONING" and len(self.calls) <= 5
        assert context["goal"]["objective"] == QUESTION
        assert context["goal"]["task_context"]["root_objective"] == QUESTION
        assert context["scope"] == self.scope
        if context["feedback"] is not None:
            previous_outcomes = _outcomes(self.store, self.run_id)
            assert previous_outcomes and context["feedback"] == previous_outcomes[-1][1].get("feedback")
        assert wire.startswith("TASK\n") and "\nSTEERING\n" in wire and QUESTION in wire
        assert "/home/chia/" not in wire and "ordinary-tool-binding.json" not in wire
        if "scientific_process" not in context:
            assert len(self.calls) == 1 and instructions.startswith(INSTRUCTIONS)
            response = dict(selection=dict(kind="episode_child", role="scientific_process", goal=QUESTION,
                scope=deepcopy(self.scope), purpose=PURPOSE, schema_json=json.dumps(_schema()), initial_report_json="{}",
                assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A102"), thought_pattern=self.library.reference("P13"),
                    child_tool_info=[dict(name=TOOL, resources="local")]), evidence_refs=[ORIGINAL_SOURCE],
                    constraints=dict(no_external_acquisition=True), context=dict(retained_comparison_only=True))),
                report_update={})
        else:
            process = context["scientific_process"]
            assert process["selection"]["evidence_axis"] == self.library.reference("A102")
            assert process["selection"]["thought_pattern"] == self.library.reference("P13")
            assert process["evidence_axis"] == instruction_view(self.library.resolve(self.library.reference("A102")))
            assert process["thought_pattern"]["name"] == self.library.resolve(self.library.reference("P13"))["name"]
            assert {row["name"] for row in process["child_tool_info"]} == {TOOL}
            assert TOOL in {row["name"] for row in context["tools"]}
            assert "Configured software choices" in wire and "Saved-data modes" in wire
            assert context["requested_form"] == _schema() and context["requested_report_purpose"] == PURPOSE
            prior = _outcomes(self.store, self.run_id)
            if not prior:
                arguments = dict(mode="read_stored", result_ref=ORIGINAL_SOURCE)
            else:
                descriptor, = prior[0][1]["result"]["saved_sheets"]
                assert descriptor["custody"]["source_ref"] == ORIGINAL_SOURCE
                if len(prior) == 1:
                    capsule = _json(self.store, self.store.get(ORIGINAL_SOURCE)["request_ref"])
                    parameters = deepcopy(capsule["arguments"]["request"]["parameters"])
                    assert parameters["distance_threshold_A"] == 2.0
                    parameters["distance_threshold_A"] = 0.5
                    arguments = dict(mode="recalculate", resource_id="ordinary-selected", binding_ordinal_0based=2,
                        saved_sheet=descriptor, parameters=parameters, projections=[_summary("saved-summary"), _sites()])
                elif len(prior) == 2:
                    # This actual post-calculation decision inspects its own
                    # recorded values; no extra model call is added for display.
                    result = prior[1][1]["result"]
                    assert result["saved_sheets"] == [] and result["source_ref"] != ORIGINAL_SOURCE
                    assert result["source_ref"] in wire
                    _assert_post_calculation_wire(context, wire, result)
                    arguments = dict(mode="select_projection", saved_sheet=descriptor, result_ref=result["source_ref"],
                        projections=[_summary("threshold-only", ["above_threshold_count", "above_threshold_fraction"])])
                else:
                    assert len(prior) == 3
                    result = prior[2][1]["result"]
                    arguments = dict(mode="select_projection", saved_sheet=descriptor, result_ref=result["source_ref"],
                        projections=[view["selection"] for view in result["views"]])
            response = dict(selection=dict(kind="tool", tool=TOOL, arguments=arguments), report_update={})
        response = _provider_value(response, output_schema)
        Draft202012Validator(output_schema).validate(response)
        call["response"] = deepcopy(response)
        self.checkpoint("decision_selected")
        return response

    async def release(self, episode_id):
        self.released.append(episode_id)


def _workflow(store, directory, run_id, resources, environments, scientific, provider, *, factory=None):
    if factory is None:
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, protein_structure_environments=environments)
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=run_id, directory=directory, tool_registry=tools)
    flow = Workflow(store, tools, provider, directory, run_id, _controller, lambda *_a, **_k: 0,
        project_child_credit=lambda *_a, **_k: 0, episode_record_receipts=True,
        initial_known_record_refs=[ORIGINAL_SOURCE],
        episode_binding_descriptors=[scientific, *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return flow, tools, factory


def _contexts(store, run_id):
    records = EpisodeReturnRecords(store, run_id, failure_prefix="protein_saved_workflow_")
    rows = list(store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
    assert len(rows) == 2
    return rows, tuple(records.context(row["episode_id"]) for row in rows)


def _authenticate_completed_prefix(store, proof, run):
    """Join a pinned past prefix to real committed closure, never create it."""
    run_id = proof["run_id"]
    assert proof["original_source"] == ORIGINAL_SOURCE
    assert proof["selected_publication"] == dict(evidence_axis="A102", thought_pattern="P13")
    assert proof["configuration"]["initial_known_record_refs"] == [ORIGINAL_SOURCE]
    assert len(proof["calls"]) == 5 and len(proof["tool_calls"]) == 4 and len(proof["workers"]) == 1
    assert proof["failures"] == proof["raw_file_attempts"] == []
    assert proof["external_model_rpc_calls"] == proof["new_original_native_calls"] == 0
    rows, (parent, science) = _contexts(store, run_id)
    calls = list(store.db.execute("SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid", (run_id,)))
    assert len(calls) == 5
    for captured, row in zip(proof["calls"], calls, strict=True):
        request = json.loads(row["request"])
        assert captured["episode_id"] == row["episode_id"]
        assert canonical(request["context"]) == canonical(captured["context"])
        assert canonical(json.loads(row["response"])) == canonical(captured["response"])
        assert hashlib.sha256(captured["wire"].encode()).hexdigest() == captured["wire_sha256"]
        assert len(captured["wire"].encode()) == captured["wire_bytes"]
        assert captured["wire"].startswith("TASK\n") and "\nSTEERING\n" in captured["wire"]
        assert QUESTION in captured["wire"] and "/home/chia/" not in captured["wire"]
        action = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (run_id, row["episode_id"], row["call_index"])).fetchone()
        assert action is not None and action["result"] is not None
        decoded = _decode_action_response(captured["response"], request["schema"])
        assert canonical(decoded["selection"]) == canonical(json.loads(action["action"]))
    outcomes = _outcomes(store, run_id)
    assert len(outcomes) == 4
    for captured, (action, outcome) in zip(proof["tool_calls"], outcomes, strict=True):
        assert captured["name"] == TOOL
        assert captured["operation_key"] == f'{run_id}:{science.episode_id}:{action["decision_index"]}'
        assert canonical(captured["arguments"]) == canonical(json.loads(action["action"])["arguments"])
        operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (captured["operation_key"],)).fetchone()
        assert operation is not None and operation["name"] == TOOL
        assert canonical(json.loads(operation["arguments"])) == canonical(captured["arguments"])
        assert canonical(json.loads(operation["result"])) == canonical(captured["outcome"])
        assert canonical(captured["outcome"]) == canonical({key: value for key, value in outcome.items()
            if key != "pending_work_after_action"})
    form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (run_id, science.episode_id)).fetchone()[0])
    attempt, = list(store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=?", (run_id,)))
    assert attempt["parent_episode_id"] == parent.episode_id and attempt["child_episode_id"] == science.episode_id
    assert attempt["decision_index"] == 0 and attempt["failure"] is None
    assert canonical(json.loads(attempt["form"])) == canonical(form)
    archives = {}
    for row in rows:
        n = 1 if row["episode_id"] == parent.episode_id else 4
        assert row["state"] == "yielded" and json.loads(row["completion"])["actions"] == n
        descriptor = json.loads(row["archive"])
        assert Path(descriptor["file"]).name == descriptor["file"]
        archive = ArchivedRecord(Path(run) / "archive" / descriptor["file"],
            descriptor["sha256"], descriptor["index_sha256"]).load()
        assert archive["episode_id"] == row["episode_id"] and archive["run_id"] == run_id
        assert canonical(archive["request"]) == canonical(json.loads(row["request"]))
        assert archive["ended_by"] == "yield_stop" and archive["units_consumed"] == n
        assert archive["controller_state"]["estimate"]["expected_next_gain"]["value"] == 0
        for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
            assert store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                (run_id, row["episode_id"])).fetchone()[0] == n
        archives[row["episode_id"]] = archive
    parent_archive = archives[parent.episode_id]
    assert canonical(parent_archive["units"][0]["child_result"]) == canonical(dict(form=form))
    return dict(rows=rows, parent=parent, science=science, outcomes=outcomes,
        archive=parent_archive, form=form)


def _verify_quantities(store, flow, original, descriptor, outcomes):
    read, recalculated, projected, noop = [outcome for _, outcome in outcomes]
    assert read["result"] == original and read["status"] == "partial"
    assert read["record_refs"] == [ORIGINAL_SOURCE] and read["changed_record_refs"] == []
    for outcome in (recalculated, projected):
        assert outcome["status"] == "completed"
        assert outcome["record_refs"] == outcome["changed_record_refs"] == [outcome["result"]["source_ref"]]
        assert outcome["result"]["saved_sheets"] == outcome["result"]["sequences"] == []
        assert store.get(outcome["result"]["source_ref"])["version"] == "protein_structure_saved_action_v1"
    assert len({ORIGINAL_SOURCE, recalculated["result"]["source_ref"], projected["result"]["source_ref"]}) == 3
    assert noop["result"] == projected["result"] and noop["changed_record_refs"] == []
    assert noop["record_refs"] == [projected["result"]["source_ref"]]
    rows, (parent, science) = _contexts(store, flow.run_id)
    owner = flow.services.protein_structure_input_authority()
    authority = owner.read_result_authority(science,
        dict(version="protein_structure_action_custody_v1", source_ref=recalculated["result"]["source_ref"]))
    components = authority["scientific"]["components"]
    assert components["parameters"]["distance_threshold_A"] == .5
    assert authority["sheet_file"] == descriptor["sheet_file"]
    assert authority["original_components_file"] == descriptor["original_components_file"]
    original_components = _json(store, descriptor["original_components_file"]["artifact_ref"])
    assert original_components["parameters"]["distance_threshold_A"] == 2.0
    assert original_components["evaluation"]["above_threshold_count"]["value"] == 0
    views = recalculated["result"]["views"]
    summary = _cells(views[0])
    expected = dict(mapped_pair_count=2, evaluation_used_count=2, above_threshold_count=1,
        above_threshold_fraction=.5, evaluation_sse=1, evaluation_rmsd=math.sqrt(.5))
    for field, value in expected.items():
        group = "counts" if field in ("mapped_pair_count", "evaluation_used_count") else "evaluation"
        assert summary[field]["value"] == components[group][field]
        assert summary[field]["value"]["state"] == "present" and summary[field]["value"]["reason"] is None
        assert summary[field]["value"]["value"] == pytest.approx(value, abs=1e-10)
    assert summary["fit_used_count"]["value"]["state"] == "not_applicable"
    assert summary["fit_used_count"]["value"]["value"] is None
    assert summary["above_threshold_fraction"]["population"]["numerator"] == 1
    assert summary["above_threshold_fraction"]["population"]["denominator"] == 2
    assert summary["evaluation_sse"]["value"]["unit"] == "angstrom_squared"
    assert summary["evaluation_rmsd"]["value"]["unit"] == "angstrom"
    sites = views[1]["outcome"]["rows"]
    assert [row["values"][0]["value"]["value"] for row in sites] == [0, 1]
    assert all(row["values"][0]["value"]["unit"] == "angstrom" for row in sites)
    projected_cells = _cells(projected["result"]["views"][0])
    assert projected_cells == {field: summary[field] for field in ("above_threshold_count", "above_threshold_fraction")}
    own = flow.services.protein_structure_action_own_facts(science, fact_source=VIEW_SOURCE)
    assert own == frozen_protein_structure_action_facts(store, flow.run_id, science, fact_source=VIEW_SOURCE)
    form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (flow.run_id, science.episode_id)).fetchone()[0])
    assert form == dict(views=own)
    assert flow.services.protein_structure_action_received_facts(parent, fact_source=VIEW_SOURCE) == own
    assert flow.services.protein_structure_action_own_facts(science, fact_source=SAVED_SOURCE) == [descriptor]
    assert flow.services.protein_structure_action_received_facts(parent, fact_source=SAVED_SOURCE) == []
    for row in rows:
        assert row["state"] == "yielded"
        assert json.loads(row["completion"])["actions"] == (1 if row["episode_id"] == parent.episode_id else 4)
        archived = json.loads(row["archive"])
        closed = ArchivedRecord(flow.directory / "archive" / archived["file"],
            archived["sha256"], archived["index_sha256"]).load()
        assert closed["ended_by"] == "yield_stop"
        assert closed["controller_state"]["estimate"]["expected_next_gain"]["value"] == 0
        n = 1 if row["episode_id"] == parent.episode_id else 4
        for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
            assert store.db.execute("SELECT count(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                (flow.run_id, row["episode_id"])).fetchone()[0] == n
    for row in store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=?", (flow.run_id,)):
        assert row["failure"] is None and json.loads(row["form"]) == form
    for action, outcome in outcomes:
        operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
            (flow.run_id + ":" + action["episode_id"] + ":" + str(action["decision_index"]),)).fetchone()
        assert operation is not None and operation["name"] == TOOL
        assert json.loads(operation["arguments"]) == json.loads(action["action"])["arguments"]
        assert json.loads(operation["result"]) == {key: value for key, value in outcome.items() if key != "pending_work_after_action"}
    return dict(form=form, expected=expected, descriptor=descriptor, recalculated=recalculated["result"],
        projected=projected["result"], original_components=original_components)


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_PROTEIN_SAVED_RETAINED_STORE"),
    reason="requires the explicitly declared immutable original342 Store support")
def test_retained_protein_threshold_and_value_projection_in_current_published_workflow(tmp_path, monkeypatch):
    original_path = Path(os.environ["HMMER_NATIVE_ORACLE_PROTEIN_SAVED_RETAINED_STORE"]).resolve(strict=True)
    assert _pin(original_path / "state.sqlite3")["sha256"] == ORIGINAL_DATABASE_SHA256
    assert not Path(str(original_path / "state.sqlite3") + "-wal").exists()
    original_database = sqlite3.connect((original_path / "state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        original_database.execute("PRAGMA query_only=ON")
        row = original_database.execute("SELECT data FROM records WHERE id=?", (ORIGINAL_SOURCE,)).fetchone()
        assert row is not None
        selected_source = json.loads(row[0])
        assert selected_source["id"] == ORIGINAL_SOURCE
        assert selected_source["provider"] == "episode.execution_result"
        assert selected_source["version"] == "native_protein_structure_bundle_v1"
        capsule_sha = selected_source["request_ref"].removeprefix("artifact_")
        capsule_path = original_path / "artifacts" / capsule_sha[:2] / capsule_sha
        assert _pin(capsule_path)["sha256"] == capsule_sha
        selected_capsule = json.loads(capsule_path.read_text())
        assert selected_capsule["tool_name"] == TOOL
        assert selected_capsule["arguments"]["request"]["parameters"]["distance_threshold_A"] == 2.0
        native_input = selected_capsule["worker"]["plan"]["native_result"]
        native_sha = native_input["file_identity"]["sha256"]
        # Authenticate the ACTUAL historical artifact root. A staged copy of
        # the same database is not substituted for the original Store.
        assert Path(native_input["path"]) == original_path / "artifacts" / native_sha[:2] / native_sha
        assert original_database.total_changes == 0
    finally:
        original_database.close()
    original_inventory = _inventory(original_path)
    directory = tmp_path / "protein-saved-public"
    directory.mkdir()
    owned = directory / "store"
    shutil.copytree(original_path, owned)
    prefix = directory / PREFIX_NAME
    run_id = "protein-saved-public-" + os.environ.get("HMMER529_ATTEMPT", "selected-retained-attempt")
    proof = dict(version="protein_structure_saved_public_workflow_v1", question=QUESTION, run_id=run_id,
        original_store=str(original_path), original_database=_pin(original_path / "state.sqlite3"),
        original_source=ORIGINAL_SOURCE, publication=str(PUBLICATION), selected_publication=dict(evidence_axis="A102", thought_pattern="P13"),
        original_inventory=original_inventory, phase="owned_clone", passed=False, external_model_rpc_calls=0,
        new_original_native_calls=0, workers=[], tool_calls=[], calls=[], failures=[], raw_file_attempts=[])
    store, provider, flow = None, None, None

    def checkpoint(phase, *, include_journal=True):
        proof["phase"] = phase
        if provider is not None:
            proof["calls"] = deepcopy(provider.calls)
        if store is not None and include_journal:
            proof["journal"] = _journal(store)
        temporary = prefix.with_suffix(".writing")
        temporary.write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
        temporary.replace(prefix)

    checkpoint("owned_clone")
    try:
        store = Store(owned)
        record_counts_before = {row["record_type"]: row["n"] for row in store.db.execute(
            "SELECT record_type,count(*) n FROM records GROUP BY record_type")}
        scope = json.loads(store.db.execute("SELECT scope FROM tool_operations WHERE name=?", (TOOL,)).fetchone()[0])
        original_row, = [row for row in store.db.execute("SELECT * FROM tool_operations WHERE name=?", (TOOL,))
            if json.loads(row["result"])["result"]["source_ref"] == ORIGINAL_SOURCE]
        original_outcome = json.loads(original_row["result"])
        original = deepcopy(original_outcome["result"])
        descriptor, = original["saved_sheets"]
        capsule = _json(store, store.get(ORIGINAL_SOURCE)["request_ref"])
        raw_refs = {row["file_identity"]["artifact_ref"] for row in capsule["plan"]["requested_job"]["native_protein_structure"]["inputs"]}
        proof["raw_input_refs"] = sorted(raw_refs)
        proof["owned_store_directory"] = str(owned)
        _guard_raw_files(monkeypatch, [original_path, owned], raw_refs, proof["raw_file_attempts"])
        get_artifact = Store.get_artifact
        def retained_bytes(actual_store, reference, *args, **kwargs):
            assert reference not in raw_refs, "saved action opened an original raw structure or correspondence File"
            return get_artifact(actual_store, reference, *args, **kwargs)
        monkeypatch.setattr(Store, "get_artifact", retained_bytes)
        monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
        monkeypatch.setattr("socket.create_connection", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_tools._run_reserved", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_tools.resolve_protein_structure_operands", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_formats.parse_pdb_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_formats.parse_mmcif_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_calculations.fit_ca_transform", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components", _forbidden)
        resources, environments = _configuration(directory)
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        tools.configure_protein_structure_resources(resources, environments)
        scientific = prepare_scientific_binding(run_directory=directory / "run", source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=["scientific_process"])
        library = ScientificProcessLibrary(directory / "run/scientific-process-library")
        provider = PublishedSavedProteinProvider(store, library, scope, run_id, checkpoint)
        flow, tools, factory = _workflow(store, directory / "run", run_id, resources, environments, scientific, provider)
        proof["configuration"] = dict(factory=factory.as_record(), scientific_binding=scientific,
            scope=scope, initial_known_record_refs=[ORIGINAL_SOURCE], directory=str(directory / "run"))
        actual_prepare, actual_execute = native_lifecycle.prepare_job, ToolRegistry.execute_async
        def prepare(command, **kwargs):
            assert "gene_annotation_episode.protein_structure_result_worker" in command
            assert len(proof["workers"]) == 0, "more than one saved worker was requested"
            plan = json.loads(Path(command[-1]).read_text())
            assert plan["mode"] == "saved_sheet_recalculation"
            assert plan["parameters"]["distance_threshold_A"] == .5
            assert plan["sheet"]["file_identity"] == descriptor["sheet_file"]
            assert plan["original_components"]["file_identity"] == descriptor["original_components_file"]
            proof["workers"].append(dict(command=list(command), plan=plan, handle_path=str(kwargs["handle_path"])))
            # Preparation runs in its existing thread. The immediately prior
            # main-thread checkpoint already retained the selected action;
            # never use its SQLite connection from this worker thread.
            checkpoint("selected_saved_worker", include_journal=False)
            handle = actual_prepare(command, **kwargs)
            proof["workers"][0]["handle"] = _pin(handle.path)
            checkpoint("saved_worker_prepared", include_journal=False)
            return handle
        async def execute(registry, name, arguments, **kwargs):
            assert name == TOOL
            proof["tool_calls"].append(dict(name=name, arguments=deepcopy(arguments), operation_key=kwargs["operation_key"]))
            checkpoint("selected_tool_action")
            value = await actual_execute(registry, name, arguments, **kwargs)
            proof["tool_calls"][-1]["outcome"] = deepcopy(value)
            checkpoint("tool_publication_returned")
            return value
        monkeypatch.setattr(native_lifecycle, "prepare_job", prepare)
        monkeypatch.setattr(ToolRegistry, "execute_async", execute)
        root = flow.build("annotation", "root", QUESTION, scope)
        record = asyncio.run(root.run_async(flow.context))
        proof["archive"] = _archive_value(record)
        proof["final_result"] = plain(asyncio.run(root.build_result(record)).as_record())
        checkpoint("workflow_closed")
        outcomes = _outcomes(store, run_id)
        assert len(outcomes) == 4 and len(provider.calls) == 5 and len(proof["workers"]) == 1
        verified = _verify_quantities(store, flow, original, descriptor, outcomes)
        proof["verified"] = verified
        record_counts_after = {row["record_type"]: row["n"] for row in store.db.execute(
            "SELECT record_type,count(*) n FROM records GROUP BY record_type")}
        assert record_counts_after == {**record_counts_before, "source": record_counts_before["source"] + 2}
        proof["record_counts_before"] = record_counts_before
        proof["record_counts_after"] = record_counts_after
        rows, (parent, science) = _contexts(store, run_id)
        assert proof["archive"]["controller_state"]["estimate"]["expected_next_gain"]["value"] == 0
        known = {context.episode_id: set(flow.receipts.known(context.episode_id)) for context in (parent, science)}
        private = set(raw_refs)
        for ref in [ORIGINAL_SOURCE, verified["recalculated"]["source_ref"], verified["projected"]["source_ref"]]:
            source = store.get(ref)
            private.update(x for x in [source.get("artifact_ref"), source.get("request_ref"), *source.get("auxiliary_artifact_refs", [])] if x)
        assert all(not private & refs for refs in known.values())
        for context in (parent, science):
            receipts = [dict(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts WHERE run_id=? AND episode_id=?", (run_id, context.episode_id))]
            assert all(not row["record_ref"].startswith("artifact_") for row in receipts if row["receipt_kind"] != "initial")
        proof["receipts"] = [dict(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts WHERE run_id=?", (run_id,))]
        handle_path = Path(proof["workers"][0]["handle_path"])
        handle = json.loads(handle_path.read_text())
        proof["workers"][0]["final_handle"] = _pin(handle_path)
        proof["workers"][0]["native_result"] = json.loads(Path(handle["paths"]["result"]).read_text())
        proof["workers"][0]["native_status"] = json.loads(Path(handle["paths"]["status"]).read_text())
        assert proof["workers"][0]["native_result"]["native_returncode"] == 0
        assert proof["raw_file_attempts"] == []
        for call, saved in zip(provider.calls, store.db.execute("SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid", (run_id,)), strict=True):
            request = json.loads(saved["request"])
            assert request["context"] == call["context"] and json.loads(saved["response"]) == call["response"]
            Draft202012Validator(request["schema"]).validate(_decode_action_response(call["response"], request["schema"]))
        before = _journal(store)
        artifacts_before = _inventory(store.path / "artifacts")
        with monkeypatch.context() as frozen:
            frozen.setattr(ToolRegistry, "execute_async", _forbidden)
            frozen.setattr(native_lifecycle, "prepare_job", _forbidden)
            frozen.setattr(provider, "complete", _forbidden)
            replayed, replay_result, child_result = _closed_delivery(flow, scope, parent, science)
            assert replayed == proof["archive"] and replay_result == proof["final_result"]
            assert child_result == dict(form=verified["form"])
            reopened_provider = PublishedSavedProteinProvider(store, library, scope, run_id, lambda _phase: None)
            frozen.setattr(reopened_provider, "complete", _forbidden)
            reopened, _, _ = _workflow(store, directory / "run", run_id, resources, environments, scientific, reopened_provider)
            reopened_record, reopened_result, reopened_child = _closed_delivery(reopened, scope, parent, science)
            assert reopened_record == proof["archive"] and reopened_result == proof["final_result"]
            assert reopened_child == child_result
            assert reopened_provider.calls == []
        assert _journal(store) == before and _inventory(store.path / "artifacts") == artifacts_before
        assert _inventory(original_path) == original_inventory
        proof["frozen_replay"] = dict(journal_unchanged=True, artifact_bytes_unchanged=True, new_actions=0,
            new_native=0, new_workers=0, new_model_dispatches=0, original_store_unchanged=True)
        proof["passed"] = True
        checkpoint("verified_closed_workflow")
    except BaseException as error:
        proof["failures"].append(dict(type=type(error).__name__, message=str(error)))
        raise
    finally:
        if store is not None:
            try:
                checkpoint(proof["phase"])
            finally:
                store.close()
            proof["owned_database"] = _pin(owned / "state.sqlite3")
            proof["owned_files"] = _inventory(owned)
            store = None
        proof["original_inventory_unchanged"] = _inventory(original_path) == original_inventory
        checkpoint(proof["phase"])


@pytest.mark.skipif(not os.environ.get("HMMER_NATIVE_ORACLE_PROTEIN_SAVED_WORKFLOW_PROOF"),
    reason="requires an explicitly pinned already-completed saved protein Workflow prefix")
def test_retained_completed_protein_saved_workflow_finishes_checks_without_work(tmp_path, monkeypatch):
    """Reuse a completed worker/Workflow after any late verification failure.

    As in the existing original-342 closed replay, the SQL/archive destinations
    are owned copies while the authenticated historical artifact root stays
    read-only. This is not arbitrary saved-worker path relocation.
    """
    prefix = Path(os.environ["HMMER_NATIVE_ORACLE_PROTEIN_SAVED_WORKFLOW_PROOF"]).resolve(strict=True)
    assert _pin(prefix)["sha256"] == os.environ["HMMER_NATIVE_ORACLE_PROTEIN_SAVED_WORKFLOW_PROOF_SHA256"]
    proof = json.loads(prefix.read_text())
    assert proof["version"] == "protein_structure_saved_public_workflow_v1" and proof["question"] == QUESTION
    original_store = Path(proof["owned_store_directory"]).resolve(strict=True)
    original_run = Path(proof["configuration"]["directory"]).resolve(strict=True)
    original_files, original_run_files = _inventory(original_store), _inventory(original_run)
    original_modes, original_run_modes = _modes(original_store), _modes(original_run)
    sqlite_pins = _sqlite_bundle_pins(original_store)
    precheckpoint = "owned_database" not in proof
    if precheckpoint:
        # The exact failed418 prefix was saved before archive serialization;
        # its committed closure exists in the separately pinned WAL bundle.
        assert proof["phase"] == "tool_publication_returned" and proof["passed"] is False
        assert not {"owned_files", "archive", "verified", "frozen_replay"}.intersection(proof)
        assert digest(sqlite_pins) == os.environ["HMMER_NATIVE_ORACLE_PROTEIN_SAVED_WORKFLOW_SQLITE_PINS_SHA256"]
        assert [entry["name"] for entry in sqlite_pins] == ["state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"]
    else:
        assert _pin(original_store / "state.sqlite3") == proof["owned_database"]
        assert original_files == proof["owned_files"]
    # Never open original WAL storage: even a read-only connection may use its
    # shared-memory read marks. Standard SQLite sees only these owned copies.
    staging = tmp_path / "owned-wal-recovery"
    staging.mkdir()
    for entry in sqlite_pins:
        shutil.copyfile(original_store / entry["name"], staging / entry["name"])
    assert _sqlite_bundle_pins(staging) == sqlite_pins
    database = tmp_path / "owned-closed-protein.sqlite3"
    connection = sqlite3.connect(staging / "state.sqlite3")
    connection.execute("PRAGMA query_only=ON")
    target = sqlite3.connect(database)
    try:
        connection.backup(target)
    finally:
        target.close()
        connection.close()
    run = tmp_path / "owned-closed-run"
    shutil.copytree(original_run, run)
    store = Store.__new__(Store)
    store.path = original_store
    store.db = sqlite3.connect(database, isolation_level=None, timeout=30)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    recovery = dict(version="protein_structure_saved_closed_verification_v1", original_prefix=_pin(prefix),
        phase="owned_recovery", passed=False, new_native=0, new_workers=0, new_decisions=0,
        original_sqlite_bundle=sqlite_pins, original_sqlite_bundle_sha256=digest(sqlite_pins),
        original_checkpoint_qualification=("failed418 prefix before archive serialization; final committed WAL state authenticated separately"
            if precheckpoint else "original final checkpoint retained"), restored_fields={})
    try:
        for method in ("artifact", "put", "commit_reasoning"):
            monkeypatch.setattr(Store, method, _forbidden)
        for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status"):
            monkeypatch.setattr(native_lifecycle, name, _forbidden)
        for name in ("execute", "execute_async"):
            monkeypatch.setattr(ToolRegistry, name, _forbidden)
        monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
        monkeypatch.setattr("socket.create_connection", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_calculations.fit_ca_transform", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_formats.parse_pdb_structure", _forbidden)
        monkeypatch.setattr("gene_annotation_episode.protein_structure_formats.parse_mmcif_structure", _forbidden)
        original_call = DecisionSource.call
        replayed_calls = []
        async def cached_call(source, context, schema):
            saved = source.workflow.journal.row("runtime_model_calls", source.episode_id, source.calls)
            assert saved is not None and saved["response"] is not None, "recovery requested a new decision"
            result = await original_call(source, context, schema)
            replayed_calls.append(dict(episode_id=source.episode_id, index=result[1]))
            return result
        monkeypatch.setattr(DecisionSource, "call", cached_call)
        attempts = []
        recovery["raw_file_attempts"] = attempts
        _guard_raw_files(monkeypatch, [Path(proof["original_store"]), original_store], proof["raw_input_refs"], attempts)
        before = _journal(store)
        run_id, configuration = proof["run_id"], proof["configuration"]
        authenticated = _authenticate_completed_prefix(store, proof, original_run)
        parent, science, outcomes = (authenticated[name] for name in ("parent", "science", "outcomes"))
        recovery["phase"] = "actual_closed_prefix_authenticated"
        original = outcomes[0][1]["result"]
        descriptor, = original["saved_sheets"]
        factory = ExecutionServiceFactory.from_record(configuration["factory"])
        library = ScientificProcessLibrary(run / "scientific-process-library")
        provider = PublishedSavedProteinProvider(store, library, configuration["scope"], run_id, lambda _phase: None)
        monkeypatch.setattr(provider, "complete", _forbidden)
        flow, tools, _ = _workflow(store, run, run_id, plain(factory.resources),
            plain(factory.protein_structure_environments), configuration["scientific_binding"], provider, factory=factory)
        verified = _verify_quantities(store, flow, original, descriptor, outcomes)
        archive, result, child = _closed_delivery(flow, configuration["scope"], parent, science)
        assert archive["ended_by"] == "yield_stop" and result == dict(credit=0, pending_handles=[])
        assert child == dict(form=verified["form"])
        assert canonical(archive) == canonical(authenticated["archive"])
        assert canonical(verified["form"]) == canonical(authenticated["form"])
        if not precheckpoint:
            assert canonical(archive) == canonical(proof["archive"])
            assert canonical(result) == canonical(proof["final_result"])
        assert provider.calls == attempts == [] and _journal(store) == before
        assert _inventory(original_store) == original_files and _inventory(original_run) == original_run_files
        assert _modes(original_store) == original_modes and _modes(original_run) == original_run_modes
        assert _pin(prefix) == recovery["original_prefix"]
        private = set(proof["raw_input_refs"])
        for reference in (ORIGINAL_SOURCE, verified["recalculated"]["source_ref"], verified["projected"]["source_ref"]):
            source = store.get(reference)
            private.update(x for x in [source.get("artifact_ref"), source.get("request_ref"),
                *source.get("auxiliary_artifact_refs", [])] if x)
        for context in (parent, science):
            assert private.isdisjoint(flow.receipts.known(context.episode_id))
        receipts = [dict(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts WHERE run_id=?", (run_id,))]
        assert all(not row["record_ref"].startswith("artifact_") for row in receipts if row["receipt_kind"] != "initial")
        worker = deepcopy(proof["workers"][0])
        handle_path = Path(worker["handle_path"])
        handle = json.loads(handle_path.read_text())
        worker.update(final_handle=_pin(handle_path), native_result=json.loads(Path(handle["paths"]["result"]).read_text()),
            native_status=json.loads(Path(handle["paths"]["status"]).read_text()))
        assert worker["native_result"]["native_returncode"] == 0
        recovery["restored_fields"] = dict(archive=authenticated["archive"], final_result=result,
            verified=verified, receipts=receipts, workers=[worker], original_owned_files=original_files)
        recovery.update(phase="verified", passed=True, verified=verified, form=child,
            journal_unchanged=True, original_store_and_run_unchanged=True, raw_file_attempts=attempts,
            original_modes_unchanged=True, original_prefix_unchanged=True, replayed_saved_calls=replayed_calls,
            actual_parent_and_closed_child_archive_return_equal=True)
    except BaseException as error:
        recovery["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        recovery["journal"] = _journal(store)
        store.close()
        recovery["owned_database"] = _pin(database)
        (tmp_path / "PROTEIN_STRUCTURE_SAVED_RECOVERY.json").write_text(json.dumps(recovery, indent=2, allow_nan=False) + "\n")
