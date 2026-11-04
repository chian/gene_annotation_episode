"""Retained ATAC views and a genuine new pending Results commission.

The new commission selects the authentic old handoff as a caller input. It
stops before any Results tool action. Original publications are not replayed,
relocated authority is not relaxed, and no new ATAC scores are calculated.
"""
import asyncio
from collections import Counter
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.atac_differential_presentation import (
    atac_scientific_job_view, render_atac_projections,
    select_atac_execution_values, select_atac_presentation,
)
from gene_annotation_episode.atac_differential_result_contracts import CATEGORIES, validate_atac_result_record
from gene_annotation_episode.atac_differential_result_receipts import (
    AtacDifferentialResultIntent, AtacDifferentialResultReceipt,
)
from gene_annotation_episode.atac_differential_result_views import project_atac_result
from gene_annotation_episode.atac_differential_return_views import PROJECTION_SOURCE
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest, validate_target
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import DecisionSource, EpisodeGoal, EpisodeRequest, Record, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import selector_selection
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.scientific_process_prompt import (
    _execution_presentation_values, render_episode_steering,
)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha,
    _source_for_original_context, _tables, _walk,
)


INVENTORY_SHA256 = "fe76198032ca70d5293532e671e51e97c420c7f8418d8a6fd0033817de88dc85"
HANDOFF = "source_d39fc94af9abb0de1be046a2"
FIXTURE_MODULE = "verification.tool_graders_atac_episode_path_2026-10-27_478.fixture_helpers"
FIXTURE_SHA256 = "7e15f61493ab98bf4f76bda9db6d8f10565d0dcb770a64f6501b296779b4f8b5"
KINDS = ("summary", "native_peak_rows", "native_differential_rows", "interval_components", "derived_regions")


def _forbidden(*args, **kwargs):
    raise AssertionError("unselected ATAC scoring/native/worker/acquisition/publication/model work")


def _guard_science(monkeypatch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status",
            "collect", "cancel", "release"):
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.atac_differential_scores.calculate_atac_interval_scores", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.atac_differential_result_worker._calculate_sheet", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.atac_differential_result_worker.run_atac_result_worker", _forbidden)
    for name in ("iter_atac_track_segments", "iter_atac_interval_components", "iter_atac_differential_regions"):
        monkeypatch.setattr("gene_annotation_episode.atac_differential_calculations." + name, _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_atac_differential_results.NativeAtacDifferentialResults.execute", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    for name in ("put", "artifact", "commit_reasoning"):
        monkeypatch.setattr(Store, name, _forbidden)


def _file(case, identity):
    identity = validate_atac_result_record("NativeFileIdentity", identity)
    assert identity["artifact_ref"] == "artifact_" + identity["sha256"]
    row = case["db"].execute("SELECT sha256,size FROM artifacts WHERE id=?", (identity["artifact_ref"],)).fetchone()
    assert row is not None and (row[0], row[1]) == (identity["sha256"], identity["size_bytes"])
    sha = identity["sha256"]
    raw = (case["historical"] / "state/artifacts" / sha[:2] / sha).read_bytes()
    assert len(raw) == identity["size_bytes"] and _sha(raw) == sha
    return raw


def _archive(case, descriptor):
    directory = case["historical"] / "run/archive"
    assert Path(descriptor["file"]).name == descriptor["file"]
    path = directory / descriptor["file"]
    assert _sha(path.read_bytes()) == descriptor["sha256"]
    assert _sha(path.with_suffix(".index.json").read_bytes()) == descriptor["index_sha256"]
    def expand(value):
        if isinstance(value, dict):
            if set(value) == {"$archive"}:
                return _archive(case, value["$archive"])
            return {key: expand(child) for key, child in value.items()}
        if isinstance(value, list):
            return [expand(child) for child in value]
        return value
    return expand(json.loads(path.read_bytes()))


@pytest.fixture(scope="module")
def retained_atac(tmp_path_factory):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_ATAC_PRESENTATION_CASE_JSON")
    if not supplied:
        pytest.skip("requires the explicitly pinned authentic ATAC478 case")
    selected = json.loads(supplied)
    assert set(selected) == {"directory", "inventory_sha256"}
    assert selected["inventory_sha256"] == INVENTORY_SHA256
    original = Path(selected["directory"]).resolve(strict=True)
    inventory = _inventory(original)
    assert _sha(_canonical(inventory).encode()) == INVENTORY_SHA256
    assert not (original / "state/state.sqlite3-wal").exists()
    assert not (original / "state/state.sqlite3-shm").exists()
    historical = tmp_path_factory.mktemp("atac-presentation-input") / "historical"
    shutil.copytree(original, historical, symlinks=True)
    assert _inventory(historical) == inventory
    db = sqlite3.connect((historical / "state/state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    case = dict(original=original, historical=historical, inventory=inventory, db=db,
        configuration=json.loads((historical / "fixture-configuration.json").read_bytes()),
        captures={path.name: json.loads(path.read_bytes()) for path in sorted(historical.glob("decision-*.json"))})
    receipts = {}
    for name, pin in sorted(inventory.items()):
        parts = Path(name).parts
        if (len(parts) != 6 or parts[:2] != ("run", "execution-results")
                or parts[3] != "native-atac-interaction-actions" or parts[5] != "receipt.json"):
            continue
        assert pin["kind"] == "file" and pin["mode"] == 0o444
        raw = (historical / name).read_bytes()
        assert _sha(raw) == pin["sha256"] and len(raw) == pin["size_bytes"]
        receipt = json.loads(raw)
        assert set(receipt) == set(AtacDifferentialResultReceipt.__annotations__)
        assert receipt["version"] == "native_atac_differential_acquired_result_v1"
        intent = receipt["intent"]
        assert set(intent) == set(AtacDifferentialResultIntent.__annotations__)
        assert intent["version"] == "atac_differential_result_intent_v1"
        assert parts[2] == digest([intent["run_id"], intent["episode_id"]]) and parts[4] == digest(intent["operation_key"])
        prefix = intent["run_id"] + ":" + intent["episode_id"] + ":"
        index = int(intent["operation_key"].removeprefix(prefix))
        assert intent["operation_key"] == prefix + str(index)
        row = db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
            (intent["run_id"], intent["episode_id"], index)).fetchone()
        assert row is not None and row["result"] is not None
        action, outcome = json.loads(row["action"]), json.loads(row["result"])
        assert action == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
        assert intent["tool_name"] == action["tool"] and intent["arguments"] == {}
        assert outcome["status"] == "completed" and _canonical(outcome["result"]) == _canonical(receipt)
        episode = db.execute("SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (intent["run_id"], intent["episode_id"])).fetchone()
        request = json.loads(episode["request"])
        assert digest(request) == intent["original_request_sha256"]
        assert request["message"]["episode_assignment"] == intent["assignment"]
        assert request["message"]["scope"] == intent["scope"] and json.loads(episode["path"]) == intent["path"]
        mode = intent["assignment"]["selector"]["mode"]
        assert mode not in receipts
        receipt_data = dict(receipt=receipt, outcome=outcome, episode=dict(episode), control=name)
        files = receipt["qualified_files"]
        receipt_data.update(sheet=json.loads(_file(case, files["sheet"])),
            calculations=json.loads(_file(case, files["calculations"])),
            projection=json.loads(_file(case, files["projection"])))
        tables = {}
        for declaration in receipt_data["calculations"]["tables"]:
            raw_table = _file(case, declaration["file"])
            assert not raw_table or raw_table.endswith(b"\n")
            rows = [json.loads(line) for line in raw_table.splitlines()]
            assert len(rows) == declaration["row_count"]
            tables[declaration["table_key"]] = rows
        receipt_data["tables"] = tables
        assert receipt["facts"][PROJECTION_SOURCE] == [receipt_data["projection"]]
        frozen = db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (intent["run_id"], intent["episode_id"])).fetchone()
        assert frozen is not None
        assert json.loads(frozen["facts"])[PROJECTION_SOURCE] == [receipt_data["projection"]]
        form = json.loads(frozen["form"])
        assert form["atac"] == [receipt_data["projection"]]
        report = db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? AND child_episode_id=?",
            (intent["run_id"], intent["episode_id"])).fetchone()
        assert report is not None and report["failure"] is None and json.loads(report["form"]) == form
        parent = db.execute("SELECT archive FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (intent["run_id"], report["parent_episode_id"])).fetchone()
        archive = _archive(case, json.loads(parent["archive"]))
        units = [unit for unit in archive["units"] if (unit.get("child") or {}).get("episode_id") == intent["episode_id"]]
        assert len(units) == 1 and units[0]["child_result"] == {"form": form}
        receipt_data["form"] = form
        receipts[mode] = receipt_data
    assert set(receipts) == {"native_result", "saved_sheet_recalculation"}
    case["receipts"] = receipts
    case["before"] = _tables(db)
    try:
        yield case
        assert _tables(db) == case["before"] and db.total_changes == 0
        assert _inventory(historical) == inventory
    finally:
        db.close()
        assert _inventory(original) == inventory


def _view(case, kind, *, saved=False):
    data = case["receipts"]["saved_sheet_recalculation" if saved else "native_result"]
    selector = deepcopy(data["receipt"]["intent"]["assignment"]["selector"])
    selector["projection"] = dict(kind=kind, row_window=None if kind == "summary" else {"offset": 0, "limit": 10},
        run_keys=["callpeak2"] if kind == "native_peak_rows" else [],
        categories=list(CATEGORIES) if kind in {"native_differential_rows", "derived_regions"} else [])
    return project_atac_result(data["sheet"], data["calculations"], selector=selector,
        component_rows=data["tables"]["components"], region_rows=data["tables"]["regions"])


@pytest.mark.parametrize("mode", ["native_result", "saved_sheet_recalculation"])
def test_original_archived_projections_are_literal_typed_outputs(retained_atac, mode, monkeypatch):
    _guard_science(monkeypatch)
    data = retained_atac["receipts"][mode]
    projection = data["projection"]
    text = render_atac_projections([projection])
    assert projection == data["form"]["atac"][0]
    assert "Selected RESULT calculation parameters" in text
    assert "Original native callpeak/bdgdiff settings remain the separate selected job request." in text
    if mode == "native_result":
        assert projection["total_rows"] == 3
        assert [row["representation"] for row in projection["rows"]] == ["xls", "narrowpeak", "summit"]
        assert projection["rows"][0]["geometry"] == dict(start0=2909, end0=3190, summit0=3020,
            span_bp=281, row_ordinal=0, status="valid")
        assert projection["rows"][0]["row"]["pileup"] == 100
        assert projection["rows"][1]["row"]["display_score"] == 1045
        assert "108.597" in text and "104.594" in text and "2909" in text
    else:
        assert projection["parameters"]["cutoff_log10_lr"] == 1000000
        assert projection["total_rows"] == 0 and projection["rows"] == [] and projection["row_extent"] == "complete"
        assert "Stored selected rows\n\n[]" in text


@pytest.mark.parametrize("kind", KINDS)
def test_five_current_views_use_only_retained_numbers(retained_atac, kind, monkeypatch):
    _guard_science(monkeypatch)
    before = deepcopy(retained_atac["receipts"]["native_result"]["calculations"])
    projection = _view(retained_atac, kind)
    text = render_atac_projections([projection])
    assert projection["kind"] == kind and projection["parameters"] == before["parameters"]
    assert projection["selected_intervals"] == before["selected_intervals"]
    assert retained_atac["receipts"]["native_result"]["calculations"] == before
    assert "do not imply that native rows were interval-clipped" in text
    assert "native_float32" not in text or kind in {"interval_components", "derived_regions"}
    if kind == "summary":
        assert projection["row_extent"] == "complete" and projection["total_rows"] == 0
        assert projection["summary"]["coverage_completeness"] == "partial_declared_domain"
        assert projection["summary"]["uncertainty"] == {"kind": "not_estimated", "value": None}
        assert len(projection["summary"]["native_peak_counts"]) == 6
        assert all(row["count"] == 1 for row in projection["summary"]["native_peak_counts"])
        assert "partial_declared_domain" in text and "does not upgrade any inner population extent or null" in text
        assert "macs2_loaded_treatment_tags_after_duplicate_filtering" in text
    elif kind == "native_peak_rows":
        assert projection == retained_atac["receipts"]["native_result"]["projection"]
        assert "must not be summed as independent peaks" in text
    elif kind == "native_differential_rows":
        assert projection["total_rows"] == 2
        assert "macs2_2_2_9_1_native_endpos_displacement_demonstrated" in text
    elif kind == "interval_components":
        assert projection["total_rows"] == 325 and len(projection["rows"]) == 10
        assert "macs2_2_2_9_1_likelihoods_correct_track_intervals" in text
        for literal in ("ieee754_binary32", "ieee754_binary64", "unrounded", "native_float32", "signed_log10_likelihood_ratio"):
            assert literal in text
    else:
        assert projection["total_rows"] == 2
        assert "qualifying bp; bridged_gap_bp is excluded" in text


def test_atac_receipt_views_keep_saved_operands_and_opaque_inputs(retained_atac, monkeypatch):
    _guard_science(monkeypatch)
    for data in retained_atac["receipts"].values():
        state = {"last_local_outcome": deepcopy(data["outcome"]), "child_reports": [deepcopy(data["form"])]}
        before = deepcopy(state)
        selected = select_atac_presentation(state, lookup_results=[data["projection"]])
        assert selected["projections"] == [data["projection"]]
        assert state == before
        for value in _walk(selected["context"]):
            if isinstance(value, dict) and value.get("version") == "atac_result_receipt_view_v1":
                assert select_atac_execution_values(value) == value
                assert _execution_presentation_values(value) == value
        receipt = deepcopy(data["receipt"])
        marker = "private-unrequested-ATAC-carrier-sibling"
        for name in ("projection", "host_failures"):
            receipt[name] = {"invalid_private_value": marker}
        receipt["intent"]["target"] = {"invalid_private_value": marker}
        changed = deepcopy(data["outcome"])
        changed["result"] = receipt
        assert select_atac_presentation({"last_local_outcome": changed})["projections"] == [data["projection"]]
        assert marker not in render_episode_steering({"last_local_outcome": changed})
    saved = retained_atac["receipts"]["saved_sheet_recalculation"]["receipt"]["intent"]["assignment"]["selector"]
    assert _execution_presentation_values(saved) == saved
    projection = retained_atac["receipts"]["native_result"]["projection"]
    opaque = {key: deepcopy(projection) for key in ("inputs", "schema", "input_schema", "schema_json", "instructions")}
    state = {"child_reports": [opaque, {"version": "unrelated_packet_v1", "nested": projection}]}
    assert select_atac_presentation(state)["context"] == state
    assert select_atac_presentation(state)["projections"] == []


def _current_flow(case, directory, provider, *, handoff_input):
    """Use original real callables for a separate current application."""
    fixture_path = Path(__file__).parent / "atac_workflow478/fixture_helpers.py"
    assert _sha(fixture_path.read_bytes()) == FIXTURE_SHA256
    fixture = sys.modules.get(FIXTURE_MODULE)
    if fixture is None:
        specification = spec_from_file_location(FIXTURE_MODULE, fixture_path)
        assert specification is not None and specification.loader is not None
        fixture = module_from_spec(specification)
        sys.modules[FIXTURE_MODULE] = fixture
        specification.loader.exec_module(fixture)
    assert Path(fixture.__file__).resolve() == fixture_path.resolve()
    assert _sha(Path(fixture.__file__).read_bytes()) == FIXTURE_SHA256
    state = directory / "state"
    state.mkdir(parents=True)
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        case["db"].backup(destination)
        assert _tables(destination) == case["before"]
    finally:
        destination.close()
    for name in ("artifacts", "cache"):
        if (case["historical"] / "state" / name).exists():
            shutil.copytree(case["historical"] / "state" / name, state / name, symlinks=True)
    run = directory / "run"
    run.mkdir()
    for name in ("scientific-process-library", "scientific-tool-library", "tool-knowledge", "launch-instructions"):
        if (case["historical"] / "run" / name).exists():
            shutil.copytree(case["historical"] / "run" / name, run / name, symlinks=True)
    configuration = deepcopy(case["configuration"])
    old = configuration["scientific_binding"]
    library = ScientificProcessLibrary(run / "scientific-process-library")
    tools_library = ScientificToolLibrary(run / "scientific-tool-library")
    assert library.as_record() == old["configuration"]["library"]
    assert tools_library.as_record() == old["configuration"]["tool_library"]
    configuration["scientific_binding"] = ScientificProcessEpisodes(None, library=library,
        tool_library=tools_library, child_roles=old["configuration"]["child_roles"]).as_record()
    configuration["initial_refs"] = [HANDOFF] if handoff_input else deepcopy(case["configuration"]["initial_refs"])
    store = Store(state)
    try:
        flow, tools = fixture.assemble(store, directory, provider, configuration)
        initialized = _tables(store.db)
        _assert_original_rows(store.db, case["before"])
        return dict(store=store, flow=flow, tools=tools, fixture=fixture,
            configuration=configuration, initialized=initialized)
    except BaseException:
        store.close()
        raise


def _original_source(flow, context):
    if plain(context.request)["report_contract"] is not None:
        return _source_for_original_context(flow, context)
    request = plain(context.request)
    typed = EpisodeRequest(EpisodeGoal.from_record(request["goal"]), Record(request["message"]), None)
    assert plain(typed.as_record()) == request
    source = DecisionSource(flow, context.path, typed, context.scope)
    assert source.episode_id == context.episode_id
    return source


def test_captured_launch_and_current_receiving_messages_preserve_guidance(retained_atac, tmp_path, monkeypatch):
    _guard_science(monkeypatch)
    app = _current_flow(retained_atac, tmp_path / "read-side", object(), handoff_input=False)
    store, flow = app["store"], app["flow"]
    try:
        records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="atac_presentation_")
        session = _session(tmp_path / "captured-task-presentation")
        launch = retained_atac["captures"]["decision-2.json"]
        context = records.context(launch["episode_id"])
        assert context.role == "launch"
        source = _original_source(flow, context)
        supplied = flow.specialist(source)._with_selected_execution_task(context, deepcopy(launch["context"]))
        task = supplied["selected_execution_task"]
        instructions = source.instructions(supplied)
        text, _ = session._presentation(context.episode_id, "REASONING", instructions,
            state_frame(instructional_model_context(supplied)))
        assert task["scientific_question"] in text
        for tool in task["selected_tool_info"]:
            assert tool["description"] in text and tool["instructions"] in text
        assert "callpeak" in text and "bdgdiff" in text
        root_capture = retained_atac["captures"]["decision-0.json"]
        root_context = records.context(root_capture["episode_id"])
        root_source = _original_source(flow, root_context)
        receiving = deepcopy(root_capture["context"])
        receiving["child_reports"] = [deepcopy(retained_atac["receipts"]["native_result"]["form"])]
        receiver, _ = session._presentation("current-ATAC-receiver-reconstruction", "REASONING",
            root_source.instructions(receiving), state_frame(instructional_model_context(receiving)))
        assert receiver.startswith("TASK") and "STEERING" in receiver
        assert root_capture["context"]["goal"]["objective"] in receiver
        assert render_atac_projections([retained_atac["receipts"]["native_result"]["projection"]]) in receiver
        for name in ("decision-1.json", "decision-4.json", "decision-6.json"):
            capture = retained_atac["captures"][name]
            assert "instructions" not in capture
            assert capture["context"]["goal"]["objective"] == retained_atac["configuration"]["goal"]
            assert capture["context"]["scientific_process"]["child_tool_info"]
            steering = render_episode_steering(capture["context"])
            if name == "decision-6.json":
                assert render_atac_projections([retained_atac["receipts"]["native_result"]["projection"]]) in steering
        _assert_original_rows(store.db, app["initialized"])
        (tmp_path / "ATAC_LAUNCH_RECEIVER_RECONSTRUCTION.json").write_text(json.dumps(dict(
            version="atac_launch_receiver_presentation_reconstruction_v1", passed=True,
            scope="Original captured Launch task helper; current engineering receiving channel; literal SCI steering only",
            full_current_launch_builder_verified=False, old_SCI_instruction_compatibility_claimed=False,
            historical_postcollect_context_claimed=False, legacy_composition_compatibility_claimed=False), indent=2) + "\n")
    finally:
        store.close()


class PendingResultsCaptured(RuntimeError):
    pass


def _new_rows(before, after):
    result = {}
    for name, old in before.items():
        assert name in after and old["columns"] == after[name]["columns"] and old["sql"] == after[name]["sql"]
        first, second = Counter(map(_canonical, old["rows"])), Counter(map(_canonical, after[name]["rows"]))
        assert not first - second
        result[name] = [json.loads(row) for row, count in (second - first).items() for _ in range(count)]
    assert set(before) == set(after)
    return result


def test_genuine_new_pending_native_results_runs_full_builder(retained_atac, tmp_path, monkeypatch):
    _guard_science(monkeypatch)
    session = _session(tmp_path / "genuine-current-presentation")
    calls, pending, setup = [], {}, {}
    captures = retained_atac["captures"]
    native_assignment = deepcopy(captures["decision-5.json"]["context"]["execution_assignment"])
    assert native_assignment["handoff_ref"] == HANDOFF and native_assignment["selector"]["mode"] == "native_result"
    original_science_id = captures["decision-1.json"]["episode_id"]
    original_run_id = captures["decision-5.json"]["context"]["execution_target"]["run_id"]
    original_science = retained_atac["db"].execute(
        "SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
        (original_run_id, original_science_id)).fetchone()
    assert original_science is not None
    original_scientific_request = json.loads(original_science["request"])
    assert original_scientific_request["goal"]["objective"] == retained_atac["configuration"]["goal"]
    assert original_scientific_request["message"]["scope"] == retained_atac["configuration"]["scope"]
    scientific_assignment = deepcopy(original_scientific_request["message"]["episode_assignment"])
    captured_process = captures["decision-1.json"]["context"]["scientific_process"]
    assert scientific_assignment["selection"]["child_tool_info"] == captured_process["child_tool_info"]
    scientific_assignment["selection"] = selector_selection(scientific_assignment["selection"])
    assert scientific_assignment == captured_process["assignment"]

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            record = dict(episode_id=episode_id, role=role, instructions=instructions, context=deepcopy(current))
            calls.append(record)
            text, model_instructions = session._presentation(episode_id, role, instructions, current)
            record.update(wire=text, model_instructions=model_instructions)
            if current.get("execution_assignment", {}).get("version") == "execution_results_assignment_v1":
                assert current["execution_assignment"] == native_assignment
                assert current["execution_target"] == captures["decision-5.json"]["context"]["execution_target"]
                task = current["selected_execution_task"]
                assert task["scientific_question"] == retained_atac["configuration"]["goal"]
                assert task["selected_tool_info"] == captures["decision-1.json"]["context"]["scientific_process"]["child_tool_info"]
                target = validate_target(current["execution_target"])
                job = target["assignment"]["requested_job"]["native_atac_differential"]
                assert len(task["requests"]) == 1 and task["requests"][0]["job"] == atac_scientific_job_view(job)
                assert text.startswith("TASK") and "STEERING" in text and task["scientific_question"] in text
                assert instructions in text and model_instructions == instructions
                for tool in task["selected_tool_info"]:
                    assert tool["name"] in text and tool["description"] in text and tool["instructions"] in text
                assert current["last_local_outcome"] is None
                assert current["execution_progress"]["execution_completed"] is False
                pending.update(episode_id=episode_id, current=deepcopy(current), wire=text)
                raise PendingResultsCaptured("actual current Results context captured before any tool selection")
            fixture = setup["fixture"]
            if "scientific_process" in current:
                assert len(calls) == 2
                answer = fixture.commission("results", deepcopy(native_assignment), deepcopy(current["scope"]),
                    fixture.result_form("atac", "saved", "failures", completed=True),
                    objective=captures["decision-5.json"]["context"]["goal"]["objective"])
            else:
                assert len(calls) == 1
                answer = fixture.commission("scientific_process", deepcopy(scientific_assignment), deepcopy(current["scope"]),
                    fixture.result_form("atac"), objective=retained_atac["configuration"]["goal"])
            value = fixture.provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(value)
            return value

        async def release(self, episode_id):
            pass

    app = _current_flow(retained_atac, tmp_path / "pending-current", Choices(), handoff_input=True)
    setup.update(app)
    store, flow = app["store"], app["flow"]
    proof = dict(version="atac_current_pending_results_verification_v1", passed=False,
        original_inventory_sha256=INVENTORY_SHA256, historical_replay_claimed=False,
        old_SCI_instruction_compatibility_claimed=False, full_current_results_builder_verified=False,
        native_calls=0, scoring_calls=0, worker_calls=0, http_calls=0,
        real_model_calls=0, scientific_publications=0)
    try:
        root = flow.build("annotation", "atac-current-pending-presentation", app["configuration"]["goal"],
            deepcopy(app["configuration"]["scope"]))
        with pytest.raises(PendingResultsCaptured, match="before any tool selection"):
            asyncio.run(root.run_async(flow.context))
        assert pending and len(calls) == 3
        after = _tables(store.db)
        added = _new_rows(app["initialized"], after)
        names = after["runtime_episodes"]["columns"]
        episodes = [dict(zip(names, row)) for row in added["runtime_episodes"]]
        assert len(episodes) == 3 and all(row["state"] == "active" and row["completion"] is row["archive"] is None for row in episodes)
        ids = {row["episode_id"] for row in episodes}
        assert {json.loads(row["path"])[-1][0] for row in episodes} == {"annotation", "scientific_process", "results"}
        actions = [dict(zip(after["runtime_actions"]["columns"], row)) for row in added["runtime_actions"]]
        assert len(actions) == 2 and all(row["episode_id"] in ids and row["result"] is None for row in actions)
        assert {json.loads(row["action"])["role"] for row in actions} == {"scientific_process", "results"}
        models = [dict(zip(after["runtime_model_calls"]["columns"], row)) for row in added["runtime_model_calls"]]
        assert len(models) == 3 and sum(row["response"] is None for row in models) == 1
        assert next(row for row in models if row["response"] is None)["episode_id"] == pending["episode_id"]
        for name in ("runtime_observations", "runtime_forms", "runtime_report_attempts", "records", "artifacts", "tool_operations"):
            assert added[name] == []
        records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="atac_current_pending_")
        context = records.context(pending["episode_id"])
        owner = flow.specialist(_source_for_original_context(flow, context))
        assert owner.atac_results.receipts.completed_receipts(context) == []
        assert owner._target(context) == pending["current"]["execution_target"]
        assert HANDOFF in set(flow.receipts.known(context.episode_id))
        for name, rows in added.items():
            columns = after[name]["columns"]
            for row in rows:
                record = dict(zip(columns, row))
                for field in ("episode_id", "parent_episode_id", "child_episode_id"):
                    if record.get(field) is not None:
                        assert record[field] in ids
        proof.update(passed=True, full_current_results_builder_verified=True,
            new_episode_ids=sorted(ids), new_framework_row_counts={name: len(rows) for name, rows in added.items()},
            new_episode_records=episodes, new_action_records=actions,
            scripted_completed_calls=2, actual_unanswered_results_calls=1,
            current_context_sha256=_sha(_canonical(pending["current"]).encode()),
            current_wire_sha256=_sha(pending["wire"].encode()), original_rows_unchanged=True,
            original_scientific_episode_id=original_science_id,
            original_scientific_request_sha256=_sha(_canonical(original_scientific_request).encode()),
            initial_handoff_input=HANDOFF, original_scientific_binding=retained_atac["configuration"]["scientific_binding"],
            new_current_scientific_binding=app["configuration"]["scientific_binding"])
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["actual_scripted_provider_calls"] = len(calls)
        proof["calls"] = calls
        proof["actual_new_rows"] = _new_rows(app["initialized"], _tables(store.db))
        (tmp_path / "ATAC_CURRENT_PENDING_RESULTS.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
        store.close()
