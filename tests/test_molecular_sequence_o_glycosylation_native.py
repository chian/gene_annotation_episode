"""Explicit genuine ordinary O heuristic, fixed saved views and closed replay.

The deterministic choices are test controls. The unchanged native callable and
glycosylation sheet/calculator own the measurements; no occupancy is measured.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode import glycosylation_measurements as glyco
from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_result_contracts as contracts
from gene_annotation_episode import molecular_sequence_tools as host
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.evidence_axis_instructions import instruction_view
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, ReturnedActionUnit
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_homer_motif_saved_workflow import _archive, _archive_value, _encode
from tests.test_molecular_sequence_n_glycosylation_native import (
    _assemble, _cell, _checkpoint, _document, _files, _history, _NoNewDecisions,
    _selected_closure, _sqlite_pins,
)
from tests.test_molecular_sequence_tools_native import _pin, _write, _tables


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = "research/slotted_process_library/publications/2026-10-24-001"
ORIGINAL_MODULE = "reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/glycoengineering.py"
MODULE_SHA256 = "ed3726d318f239e98183a359f18bcd341f4159ef2e400322c6141f77dcd2aff2"
CALLABLE_SHA256 = "dac5fa5bd182e0f7d4154ad72289c9adae173864e07e6392ae32d1e1102b2ca6"
TOOL = "predict_o_glycosylation_hotspots"
FACT = "o_glycosylation_hotspot_outcomes"
PARAMETERS = dict(window=2, min_st_fraction=.4, disallow_proline_next=True)
QUESTION = ("For the supplied STP protein fragment, under requested window 2, minimum S/T "
    "fraction 0.4 and immediate-next-proline exclusion, which literal candidate centers and "
    "qualified native/printed populations does the original O-glycosylation heuristic support? "
    "Preserve requested versus effective window, center and clipped-window/source intervals, "
    "actual S/T numerator and denominator, full-precision fraction versus native rounded display, "
    "and whether the original retained and saved-sheet recalculated results agree under the "
    "same input and parameters without a second scan. Keep both Source-owned groups. "
    "Candidate hotspots do not establish measured glycosylation, occupancy, calibrated probability, "
    "confidence or protein function; those properties remain unmeasured for this fragment.")


def _forbidden(*args, **kwargs):
    raise AssertionError("No new scanner, calculation, model, input or acquisition work is permitted here")


def _rows():
    return [dict(row_id={"kind": "summary"}, fields=["original_symbol_count", "processed_symbol_count",
        "native_reported_sequence_length", "native_reported_total_count", "retained_printed_row_count",
        "usable_checked_row_count", "native_reported_remaining_count", "unretained_reported_row_count",
        "native_total_operand_upper_bound", "native_report_complete", "scan_exhaustiveness_verified"]),
        dict(row_id={"kind": "glycosylation_site", "row_ordinal": 0}, fields=["row_ordinal", "residue",
            "position_1based", "processed_interval", "source_intervals", "native_window_interval",
            "expected_clipped_window_interval", "window_source_intervals", "window_symbols", "window_symbol_counts",
            "st_count", "window_denominator_symbols", "native_st_fraction", "native_st_fraction_token",
            "calculated_st_fraction", "source_rounded_st_fraction", "following_proline", "following_proline_allowed",
            "unrounded_threshold_satisfied", "window_matches_source_clipping", "printed_fraction_matches_calculation"])]


def _form():
    return obj(dict(hotspots=contracts.ordinary_molecular_sequence_fact_sources(TOOL)[FACT]["report_schema"]))


def _configuration(case, deployment, software):
    assert deployment["version"] == contracts.ordinary_molecular_sequence_profile(TOOL)["deployment_version"]
    workspace = case / "native-workspace"
    workspace.mkdir()
    resources = {"selected-o": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY),
        native_molecular_sequence=[dict(version=host.BINDING_VERSION, operation=TOOL,
            deployment=deployment, software=software)])}
    environments = [dict(operation=TOOL, resource_id="selected-o", binding_ordinal_0based=0,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


def _assert_display(steering, public, store):
    for name in ("parameters.supplied_window", "parameters.effective_window", "native_st_fraction",
            "calculated_st_fraction", "st_count", "window_denominator_symbols", "Denominator operands"):
        assert name in steering
    assert "0.667" in steering and "0.6666666666666666" in steering
    assert "Candidate hotspots do not establish measured glycosylation" in steering
    source = store.get(public["source_ref"])
    for reference in {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}:
        assert reference not in steering


class _Choices:
    def __init__(self, store, library, proof, output, active):
        self.store, self.library, self.proof, self.output, self.active = store, library, proof, output, active
        self.turns, self.states = {}, {}
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, schema):
        context = plain(context)
        row = self.store.db.execute("SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.proof["run_id"], episode_id)).fetchone()
        grain = json.loads(row["path"])[-1][0]
        turn = self.turns.get(episode_id, 0) + 1
        self.turns[episode_id] = turn
        assert role == "REASONING" and not context.get("feedback"), context.get("feedback")
        assert context["goal"]["objective"] == context["goal"]["task_context"]["root_objective"] == QUESTION
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions,
            state_frame(context, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(context)
        call = dict(episode_id=episode_id, grain=grain, turn=turn, context=deepcopy(context), schema=deepcopy(schema),
            instructions=plain(instructions), wire=wire, wire_instructions=plain(wire_instructions),
            wire_sha256=hashlib.sha256(wire.encode()).hexdigest(), wire_size_bytes=len(wire.encode()))
        self.proof["calls"].append(call)
        if grain == "annotation":
            assert turn == 1
            selection = dict(kind="episode_child", role="scientific_process", goal=QUESTION,
                scope=deepcopy(self.proof["scope"]), purpose=QUESTION, schema_json=json.dumps(_form()),
                initial_report_json="{}", assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A101"), thought_pattern=self.library.reference("P02"),
                    child_tool_info=[dict(name=TOOL, resources="local")]), evidence_refs=[], constraints={},
                    context=dict(o_hotspot_request=deepcopy(self.proof["arguments"]))))
        else:
            assert grain == "scientific_process" and 1 <= turn <= 4
            self.active["turn"] = turn
            assert context["requested_form"] == _form()
            assert context["scientific_process"]["assignment"]["context"]["o_hotspot_request"] == self.proof["arguments"]
            assert context["scientific_process"]["evidence_axis"] == instruction_view(self.library.resolve(self.library.reference("A101")))
            entry, = [item for item in context["tools"] if item["name"] == TOOL]
            assert entry["resources"] == "local"
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire
            task, steering = wire.split("\n\nSTEERING\n", 1)
            assert QUESTION in task and self.proof["selected_tool_contract"]["instructions"] in task
            assert self.proof["selected_tool_contract"]["description"] in task
            assert "/home/" not in wire
            previous = [json.loads(item["result"]) for item in self.store.db.execute(
                "SELECT result FROM tool_operations WHERE substr(operation_key,1,?)=? ORDER BY rowid",
                (len(self.proof["run_id"]) + 1, self.proof["run_id"] + ":"))]
            if turn == 1:
                arguments = deepcopy(self.proof["arguments"])
            elif turn == 2:
                assert len(previous) == 1
                arguments = dict(mode="read_stored", result_ref=previous[0]["result"]["source_ref"], rows=_rows())
            elif turn == 3:
                assert len(previous) == 2 and previous[1]["result"] == previous[0]["result"]
                assert previous[1]["changed_record_refs"] == []
                self.proof["literal_original_read_verified"] = True
                workspace = Path(self.proof["factory"]["resources"]["selected-o"]["workspace"])
                assert workspace.parent == Path(self.proof["case_directory"])
                original_files = _files(workspace)
                retained = workspace.parent / "retained-native-workspace"
                assert not retained.exists()
                workspace.rename(retained)
                workspace.mkdir()
                assert list(workspace.iterdir()) == [] and _files(retained) == original_files
                self.proof["retained_native_workspace"] = dict(path=str(retained), original_files=original_files)
                retained_native_file(self.store, self.proof["input_file"]).unlink()
                self.proof["owned_original_operand_body_removed"] = True
                arguments = dict(mode="calculate_saved", result_ref=previous[0]["result"]["source_ref"], rows=_rows())
            else:
                assert len(previous) == 3 and previous[2]["result"]["source_ref"] != previous[0]["result"]["source_ref"]
                arguments = dict(mode="read_stored", result_ref=previous[2]["result"]["source_ref"], rows=_rows())
            if turn > 1:
                public = contracts.validate_ordinary_molecular_sequence_return(context["last_local_outcome"]["result"], operation=TOOL)
                assert public == previous[-1]["result"]
                _assert_display(steering, public, self.store)
                call["literal_display_verified"] = True
            selection = dict(kind="tool", tool=TOOL, arguments=arguments)
        answer = _encode(dict(selection=selection, report_update={}), schema)
        call["response"] = deepcopy(answer)
        self.proof["phase"] = "decision_selected"
        _checkpoint(self.store, self.proof, self.output)
        return answer

    async def release(self, episode_id):
        pass


def _scientific_cell(cell):
    result = deepcopy(cell)
    result.pop("source_ref")
    result.pop("source_state")
    for value in result["denominators"]:
        value.pop("source_ref")
        value.pop("source_state")
        for source in value["unit_sources"]:
            source.pop("source_ref")
            source.pop("source_state")
    for value in result["scientific_qualifiers"]["states"].values():
        value.pop("source_ref")
        value.pop("source_state")
    return result


def _scientific_context(context):
    """Compare fixed retained meanings while keeping provenance joins separate."""
    def stored(cell):
        return {key: deepcopy(value) for key, value in cell.items() if key not in ("source_ref", "source_state")}
    return dict(schema=context["schema"],
        **{group: {name: stored(cell) for name, cell in context[group].items()}
            for group in ("parameters", "input", "mapping", "native")},
        **{name: stored(context[name]) for name in ("component_status", "completeness", "component_issues")},
        row_issues=None if context["row_issues"] is None else [dict(row_ordinal=row["row_ordinal"],
            issues=stored(row["issues"])) for row in context["row_issues"]])


def _assert_public_custody(public, *, saved):
    """Keep declared native output and undeclared host-calculation custody exact."""
    component_state = "retained_undeclared" if saved else "retained"
    assert public["file_states"] == dict(capture="not_requested" if saved else "retained",
        sheet="retained", components=component_state)
    assert public["values"]["source_states"] == dict(sheet="retained", components=component_state)
    def check(cell, role):
        assert cell["source_ref"] == public["values"]["source_" + role + "_ref"]
        assert cell["source_state"] == (component_state if role == "components" else "retained")
    for row in public["values"]["rows"]:
        check(row, "components")
        for operand in row["denominators"]:
            check(operand, "components")
            assert operand["unit_sources"] == []
        for qualifier in row["scientific_qualifiers"]["states"].values():
            check(qualifier, "components")
    context = public["values"]["context"]
    for name in ("component_status", "component_issues"):
        check(context[name], "components")
    check(context["completeness"], "sheet")
    for group in ("parameters", "input", "mapping", "native"):
        for cell in context[group].values():
            check(cell, "components" if group == "parameters" else "sheet")
    assert type(context["row_issues"]) is list
    for row in context["row_issues"]:
        check(row["issues"], "components")


def _verify(store, workflow, registry, proof):
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" and row["archive"] and row["completion"] for row in episodes)
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    operations = history["tool_operations"]
    assert len(operations) == 4 and all(row["name"] == TOOL for row in operations)
    arguments = [json.loads(row["arguments"]) for row in operations]
    outcomes = [json.loads(row["result"]) for row in operations]
    values = [contracts.validate_ordinary_molecular_sequence_return(row["result"], operation=TOOL) for row in outcomes]
    assert arguments == [proof["arguments"], dict(mode="read_stored", result_ref=values[0]["source_ref"], rows=_rows()),
        dict(mode="calculate_saved", result_ref=values[0]["source_ref"], rows=_rows()),
        dict(mode="read_stored", result_ref=values[2]["source_ref"], rows=_rows())]
    assert all(row["status"] == "completed" for row in outcomes)
    assert values[0] == values[1] and values[2] == values[3] and values[0]["source_ref"] != values[2]["source_ref"]
    assert values[0]["values"]["source_sheet_ref"] == values[2]["values"]["source_sheet_ref"]
    for index, value in enumerate(values):
        _assert_public_custody(value, saved=index >= 2)
    assert [_scientific_cell(row) for row in values[0]["values"]["rows"]] == [_scientific_cell(row) for row in values[2]["values"]["rows"]]
    assert _scientific_context(values[0]["values"]["context"]) == _scientific_context(values[2]["values"]["context"])
    for index, (outcome, public) in enumerate(zip(outcomes, values)):
        assert outcome["record_refs"] == [public["source_ref"]]
        assert outcome["changed_record_refs"] == ([] if index in (1, 3) else [public["source_ref"]])
        assert public["failures"] == []
        expected = dict(original_symbol_count=3, processed_symbol_count=3, native_reported_sequence_length=3,
            native_reported_total_count=1, retained_printed_row_count=1, usable_checked_row_count=1,
            native_reported_remaining_count=None, unretained_reported_row_count=0,
            native_total_operand_upper_bound=2, native_report_complete=True, scan_exhaustiveness_verified=False)
        for field, value in expected.items():
            assert _cell(public, field)["value"] == value and type(_cell(public, field)["value"]) is type(value)
        for field, value in dict(row_ordinal=0, residue="S", position_1based=1, processed_interval=[0, 1],
                native_window_interval=[0, 3], expected_clipped_window_interval=[0, 3], window_symbols="STP",
                window_symbol_counts={"S": 1, "T": 1, "P": 1}, st_count=2, window_denominator_symbols=3,
                native_st_fraction=.667, native_st_fraction_token="0.667", calculated_st_fraction=2 / 3,
                source_rounded_st_fraction=.667, following_proline=False, following_proline_allowed=True,
                unrounded_threshold_satisfied=True, window_matches_source_clipping=True,
                printed_fraction_matches_calculation=True).items():
            assert _cell(public, field, 0)["value"] == value
        context = public["values"]["context"]
        for name, value in dict(supplied_window=2, requested_window=2, effective_window=7,
                source_default_window=7, supplied_min_st_fraction=.4, effective_min_st_fraction=.4,
                supplied_disallow_proline_next=True, effective_disallow_proline_next=True).items():
            assert context["parameters"][name]["value"] == value
        assert context["native"]["selected_metadata"]["value"]["sequence"] == dict(sequence_length=3, window=7,
            threshold_token="0.4", threshold=.4)
        for field in ("native_st_fraction", "calculated_st_fraction", "source_rounded_st_fraction"):
            numerator, denominator = _cell(public, field)["denominators"]
            assert (numerator["kind"], numerator["value"], numerator["unit"]) == ("numerator", 2, "symbols")
            assert (denominator["kind"], denominator["value"], denominator["unit"]) == ("denominator", 3, "symbols")
            assert type(numerator["value"]) is type(denominator["value"]) is int
        assert _cell(public, "st_count")["denominators"] == _cell(public, "window_denominator_symbols")["denominators"] == []
    records = EpisodeReturnRecords(store, proof["run_id"], failure_prefix="o_native_proof_")
    parent, science = [records.context(row["episode_id"]) for row in episodes]
    for context in (parent, science):
        records.authenticate(context)
    expected = dict(hotspots=[values[0], values[2]])
    frozen, = history["runtime_forms"]
    report, = history["runtime_report_attempts"]
    assert frozen["episode_id"] == science.episode_id and json.loads(frozen["form"]) == expected
    assert json.loads(frozen["facts"])[FACT] == expected["hotspots"]
    assert report["failure"] is None and json.loads(report["form"]) == expected
    assert report["parent_episode_id"] == parent.episode_id and report["child_episode_id"] == science.episode_id
    assert workflow.services.molecular_own_facts(science, fact_source=FACT) == expected["hotspots"]
    assert workflow.services.molecular_frozen_facts(science, fact_source=FACT) == expected["hotspots"]
    assert workflow.services.molecular_received_facts(parent, fact_source=FACT) == expected["hotspots"]
    archives = [_archive(row, workflow.directory) for row in episodes]
    assert [row["units_consumed"] for row in archives] == [1, 4]
    assert all(row["ended_by"] == "yield_stop" for row in archives)
    assert archives[0]["units"][0]["child_result"] == dict(form=expected)
    owner = registry.molecular_sequence_results_for(proof["run_id"])
    publications = [owner.read_ordinary_molecular_sequence_publication(science, public["source_ref"], operation=TOOL,
        read_received=workflow.services.read_received_molecular_input) for public in expected["hotspots"]]
    control, saved = [publication["control"] for publication in publications]
    original = control["original"]
    execution = _document(store, original["execution_file"])
    request = _document(store, original["driver_request_file"])
    bundle, declaration = [_document(store, original[key]) for key in ("bundle_file", "declaration_file")]
    assert execution["terminal"] is execution["quiescent"] is True and execution["returncode"] == 0
    assert execution["failure"] is None and execution["metadata"]["policy"] == ordinary.POLICY
    assert execution["plan"]["identity"]["operation_key"] == operations[0]["operation_key"]
    assert bundle["invocation"]["invocation_count"] == bundle["invocation"]["launch_attempt_count"] == 1
    assert bundle["invocation"]["process_exit_observed"] is True
    assert declaration["native_call_state"] == "returned" and declaration["native_failure"] is declaration["driver_failure"] is None
    operand = _document(store, control["request"]["input_binding_file"])["frozen_operand"]
    assert operand["sequence"] == proof["stored_sequence"] == "STP" and operand["input_file"] == proof["input_file"]
    assert request["selection"]["version"] == "molecular_sequence_request_v2"
    assert request["selection"]["arguments"] == dict(sequence="STP", **PARAMETERS)
    assert request["scientific_context"] == dict(input_ref=proof["subject_ref"], input_mapping=operand["parent_mapping"])
    files = control["source_files"]
    capture, sheet, components = [_document(store, files[role]["file"]) for role in ("capture", "sheet", "components")]
    assert capture["native_call_state"] == "returned" and capture["failure"] is None
    assert capture["execution_receipt"]["module_load"]["source_file"]["sha256"] == MODULE_SHA256
    assert capture["execution_receipt"]["observed_callable"]["sha256"] == CALLABLE_SHA256
    assert capture["execution_receipt"]["libraries"] == []
    assert capture["native_record"]["result"] == sheet["inputs"]["native_log"]
    assert hashlib.sha256(sheet["inputs"]["native_log"].encode()).hexdigest() == "d7e33970da8e2a0c544a144cc8d4196e04d0353052b81e9f6bf2a54658c919cc"
    assert sheet["inputs"]["sequence"] == "STP" and sheet["inputs"]["parameters"] == PARAMETERS
    assert components["status"] == sheet["status"] == "complete" and len(components["rows"]) == 1
    assert components["rows"][0]["native_values"]["residue"] == "S"
    assert _cell(values[0], "source_intervals")["value"] == components["rows"][0]["cells"]["source_intervals"]
    assert _cell(values[0], "window_source_intervals")["value"] == components["rows"][0]["cells"]["window_source_intervals"]
    assert saved["source_files"]["sheet"]["file"] == files["sheet"]["file"]
    assert saved["calculation"]["native_call_state"] == "not_requested" and saved["calculation"]["state"] == "returned"
    assert saved["calculation"]["call_count"] == 1
    for context in (parent, science):
        known = set(workflow.receipts.known(context.episode_id))
        assert {proof["subject_ref"], proof["input_file"]["artifact_ref"], values[0]["source_ref"], values[2]["source_ref"]} <= known
        assert workflow.resolver(plain(context.scope), context=context)(proof["input_file"]["artifact_ref"], "artifact") is True
        for publication in publications:
            source = publication["source"]
            private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
            assert private.isdisjoint(known) and proof["input_file"]["artifact_ref"] not in private
            for reference in private:
                denied, path = workflow.services.read_received_molecular_input(context, reference, "artifact", file_format="json")
                assert denied["failure"] is not None and path is None
        assert set(workflow.receipts.known(context.episode_id)) == known
    assert len(proof["calls"]) == len(history["runtime_model_calls"]) == 5
    for row, call in zip(history["runtime_model_calls"], proof["calls"]):
        assert row["episode_id"] == call["episode_id"] and json.loads(row["request"])["context"] == call["context"]
        assert json.loads(row["response"]) == call["response"]
        assert hashlib.sha256(call["wire"].encode()).hexdigest() == call["wire_sha256"]
        assert len(call["wire"].encode()) == call["wire_size_bytes"]
    assert all(call["literal_display_verified"] for call in proof["calls"][2:])
    return dict(returned=expected, archives=archives, original_native_handle=execution["handle"],
        episode_ids=[parent.episode_id, science.episode_id], source_files=files,
        original_invocation_count=1, saved_calculation_count=1, scientific_cells_equal=True)


def _closed_replay(store, directory, proof, monkeypatch):
    before, history = _tables(store), _history(store, proof["run_id"])
    before_files, before_artifacts = _files(directory), _files(store.path / "artifacts")
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    parent_archive, child_archive = [_archive(row, directory) for row in episodes]
    child_request = json.loads(episodes[1]["request"])
    form = json.loads(history["runtime_forms"][0]["form"])
    cached, returned = [], []
    with monkeypatch.context() as guarded:
        for module, names in ((ordinary, ("prepare_ordinary_molecular_sequence_attempt", "run_ordinary_molecular_sequence_attempt")),
                (native, ("execute_molecular_sequence_request",)),
                (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel"))):
            for name in names:
                guarded.setattr(module, name, _forbidden)
        guarded.setattr(glyco, "calculate_glycosylation_components", _forbidden)
        guarded.setattr(ToolRegistry, "_prepare_molecular_sequence_operand", _forbidden)
        guarded.setattr("socket.create_connection", _forbidden)
        workflow, registry = _assemble(store, directory, proof, _NoNewDecisions())
        guarded.setattr(registry.clients, "_http", _forbidden)
        original_call = DecisionSource.call
        async def call(source, context, schema):
            assert source.path[-1][0] == "annotation"
            row = source.workflow.journal.row("runtime_model_calls", source.episode_id, source.calls)
            assert row is not None and row["response"] is not None
            answer = await original_call(source, context, schema)
            cached.append(dict(episode_id=source.episode_id, index=answer[1]))
            return answer
        guarded.setattr(DecisionSource, "call", call)
        original_closed = workflow._closed_child_commission
        def closed(*args, **kwargs):
            unit = original_closed(*args, **kwargs)
            assert isinstance(unit, ReturnedActionUnit)
            assert plain(unit.request.as_record()) == child_request
            assert _archive_value(unit.record) == child_archive and plain(unit.result.as_record()) == dict(form=form)
            returned.append(unit.record.episode_id)
            return unit
        guarded.setattr(workflow, "_closed_child_commission", closed)
        root = workflow.build("annotation", "root", QUESTION, proof["scope"])
        completed = asyncio.run(root.run_async(workflow.context))
        final = _archive_value(asyncio.run(root.build_result(completed)))
        assert final == dict(credit=0, pending_handles=[]) and _archive_value(completed) == parent_archive
        assert returned == [episodes[1]["episode_id"]]
        assert cached == [dict(episode_id=episodes[0]["episode_id"], index=0)]
    assert _tables(store) == before and _history(store, proof["run_id"]) == history
    assert _files(directory) == before_files and _files(store.path / "artifacts") == before_artifacts
    return dict(cached_parent_calls=cached, new_model_calls=0, new_actions=0, new_native=0, new_calculations=0,
        all_tables_unchanged=True, files_and_modes_unchanged=True, final=final)


def test_genuine_o_glycosylation_native_saved_and_typed_parent(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_O_GLYCOSYLATION") != "1":
        pytest.skip("requires explicit bounded ordinary O native selection")
    tag = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_O_GLYCOSYLATION_ATTEMPT_ID")
    assert tag and Path(tag).name == tag and tag not in (".", "..")
    case = tmp_path / ("o-glycosylation-" + tag)
    case.mkdir()
    output = case / "O_GLYCOSYLATION_WORKFLOW.json"
    proof = dict(version="ordinary_o_glycosylation_workflow_v1", run_id="ordinary-o-" + tag,
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        question=QUESTION, calls=[], native_attempts=[], saved_calculator_calls=[], phase="prepared", passed=False,
        literal_original_read_verified=False, owned_original_operand_body_removed=False,
        native_custody_verified=False, typed_delivery_verified=False, closed_replay_verified=False,
        qualification="Scripted finite choices; original O native heuristic and shared calculator, no occupancy/probability/function measurement.")
    _write(output, proof)
    active = dict(turn=0)
    try:
        deployment, software, proof["closure"] = _selected_closure(case)
        resources, environments = _configuration(case, deployment, software)
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            molecular_sequence_environments=environments, molecular_sequence_saved_modes=True)
        proof["factory"] = factory.as_record()
        with Store(case / "store") as store:
            subject, = store.create_problem(raw_sequence="STP", molecule="protein")["subject_refs"]
            record = store.get(subject)
            metadata = store.get(record["sequence_ref"])
            raw = store.get_artifact(metadata["id"])
            assert raw == b"STP"
            proof.update(subject_ref=subject, scope=store.validate_scope(), stored_sequence=raw.decode("ascii"),
                input_file=dict(artifact_ref=metadata["id"], sha256=metadata["sha256"], size_bytes=metadata["size"], format="ascii_sequence"),
                initial_known_record_refs=[subject, metadata["id"]], arguments=dict(subject_ref=subject, **PARAMETERS, rows=_rows()))
            configured = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
            factory.configure_tool_registry(configured)
            proof["selected_tool_contract"] = configured.catalog()[TOOL]
            assert proof["selected_tool_contract"]["invocation_route"] == dict(kind="direct")
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=case / "run", source_directory=ROOT / PUBLICATION,
                tool_catalog=configured.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(case / "run/scientific-process-library")
            provider = _Choices(store, library, proof, output, active)
            workflow, registry = _assemble(store, case / "run", proof, provider)
            prepare, observe, calculate = ordinary.prepare_ordinary_molecular_sequence_attempt, host._observe_original, glyco.calculate_glycosylation_components
            def prepare_once(**kwargs):
                assert active["turn"] == 1 and not proof["native_attempts"]
                prepared = prepare(**kwargs)
                proof["native_attempts"].append(dict(prepared=deepcopy(prepared), returned=None))
                _checkpoint(store, proof, output)
                return prepared
            async def observe_once(prepared):
                assert active["turn"] == 1 and len(proof["native_attempts"]) == 1
                result = await observe(prepared)
                proof["native_attempts"][0]["returned"] = deepcopy(result)
                _checkpoint(store, proof, output)
                return result
            def saved_once(sheet):
                assert active["turn"] == 3 and not proof["saved_calculator_calls"]
                proof["saved_calculator_calls"].append(dict(sheet_sha256=digest(sheet), phase="entered"))
                _checkpoint(store, proof, output)
                result = calculate(sheet)
                proof["saved_calculator_calls"][0].update(phase="returned", components_sha256=digest(result))
                _checkpoint(store, proof, output)
                return result
            with monkeypatch.context() as measured:
                measured.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", prepare_once)
                measured.setattr(host, "_observe_original", observe_once)
                measured.setattr(glyco, "calculate_glycosylation_components", saved_once)
                measured.setattr(registry.clients, "_http", _forbidden)
                root = workflow.build("annotation", "root", QUESTION, proof["scope"])
                try:
                    _checkpoint(store, proof, output)
                    completed = asyncio.run(root.run_async(workflow.context))
                    proof.update(phase="workflow_returned", archive=_archive_value(completed))
                    _checkpoint(store, proof, output)
                    proof["delivery"] = _verify(store, workflow, registry, proof)
                    proof.update(native_custody_verified=True, typed_delivery_verified=True)
                    assert len(proof["native_attempts"]) == len(proof["saved_calculator_calls"]) == 1
                    assert proof["saved_calculator_calls"][0]["phase"] == "returned"
                    proof["final_result"] = _archive_value(asyncio.run(root.build_result(completed)))
                    assert proof["final_result"] == dict(credit=0, pending_handles=[])
                    _checkpoint(store, proof, output)
                finally:
                    _checkpoint(store, proof, output)
            proof["replay"] = _closed_replay(store, case / "run", proof, monkeypatch)
            proof.update(phase="verified", passed=True, closed_replay_verified=True)
            _checkpoint(store, proof, output)
    except BaseException as error:
        proof["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (case / "store/state.sqlite3").is_file():
            proof["sqlite_pins"] = _sqlite_pins(case / "store")
            proof["sqlite_pins_sha256"] = digest(proof["sqlite_pins"])
        _write(output, proof)


def test_retained_completed_o_glycosylation_finishes_without_scan_or_calculation(tmp_path, monkeypatch):
    selected = os.environ.get("HMMER_NATIVE_ORACLE_O_GLYCOSYLATION_RETAINED_PROOF")
    if not selected:
        pytest.skip("requires explicit retained genuine O proof")
    output = Path(selected).resolve(strict=True)
    assert _pin(output)["sha256"] == os.environ["HMMER_NATIVE_ORACLE_O_GLYCOSYLATION_PROOF_SHA256"]
    proof = json.loads(output.read_text())
    assert proof["version"] == "ordinary_o_glycosylation_workflow_v1" and proof["question"] == QUESTION
    original = output.parent
    assert original == Path(proof["case_directory"]) and Path(proof["store_directory"]) == original / "store"
    pins = _sqlite_pins(original / "store")
    assert pins == proof["sqlite_pins"] and digest(pins) == proof["sqlite_pins_sha256"]
    assert digest(pins) == os.environ["HMMER_NATIVE_ORACLE_O_GLYCOSYLATION_SQLITE_PINS_SHA256"]
    assert len(proof["calls"]) == 5 and len(proof["native_attempts"]) == len(proof["saved_calculator_calls"]) == 1
    original_files = _files(original)
    owned = tmp_path / "owned-retained-o"
    shutil.copytree(original, owned, ignore=shutil.ignore_patterns("state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"))
    staging = tmp_path / "owned-sqlite-recovery"
    staging.mkdir()
    for pin in pins:
        shutil.copy2(original / "store" / pin["name"], staging / pin["name"])
        assert _pin(staging / pin["name"])["sha256"] == pin["sha256"]
    with sqlite3.connect(staging / "state.sqlite3") as source:
        with sqlite3.connect(owned / "store/state.sqlite3") as target:
            source.backup(target)
    result = dict(version="ordinary_o_glycosylation_retained_finish_v1", original_proof=_pin(output),
        original_sqlite_pins=pins, passed=False, new_native=0, new_calculations=0, new_model_calls=0)
    finish = tmp_path / "O_GLYCOSYLATION_RETAINED_FINISH.json"
    _write(finish, result)
    try:
        with Store(owned / "store") as store:
            before = _tables(store)
            with monkeypatch.context() as guarded:
                guarded.setattr(glyco, "calculate_glycosylation_components", _forbidden)
                guarded.setattr(ordinary, "prepare_ordinary_molecular_sequence_attempt", _forbidden)
                guarded.setattr(ordinary, "run_ordinary_molecular_sequence_attempt", _forbidden)
                guarded.setattr(native, "execute_molecular_sequence_request", _forbidden)
                guarded.setattr("socket.create_connection", _forbidden)
                workflow, registry = _assemble(store, owned / "run", proof, _NoNewDecisions())
                guarded.setattr(registry.clients, "_http", _forbidden)
                assert _tables(store) == before
                result["delivery"] = _verify(store, workflow, registry, proof)
                assert _tables(store) == before
                result["replay"] = _closed_replay(store, owned / "run", proof, guarded)
                result["passed"] = True
    except BaseException as error:
        result["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        result["original_files_and_modes_unchanged"] = _files(original) == original_files
        result["owned_sqlite_pins"] = _sqlite_pins(owned / "store")
        _write(finish, result)
    assert result["original_files_and_modes_unchanged"]
