"""Literal retained NMF views and one genuinely new pending Results path.

Scripted engineering choices create only framework bookkeeping. They stop at
the first current Results callback before tools. Old fitting, calculation,
typed returns and failures remain historical evidence, never rerun here.
"""
import asyncio
from copy import deepcopy
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest, validate_target
from gene_annotation_episode.expression_nmf_presentation import (
    expression_nmf_scientific_job_view, render_expression_nmf_projections,
    select_expression_nmf_execution_values, select_expression_nmf_presentation,
)
from gene_annotation_episode.expression_nmf_result_contracts import validate_file, validate_projection
from gene_annotation_episode.expression_nmf_result_views import project_nmf_result
from gene_annotation_episode.expression_nmf_return_views import PROJECTION_SOURCE, SAVED_SOURCE
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import _execution_presentation_values, render_episode_steering
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_interval_pending_results import _commission, _new_rows
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha, _source_for_original_context, _tables, _walk,
)


INVENTORY_SHA256 = "5da9d2d4843059c7d94634930f3e9eac15dca4bb45f86476454ff92038426b50"
HANDOFF = "source_47c4dbb9b0de614ab3ea96e4"
FIXTURE_MODULE = "verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers"
FIXTURE_SHA256 = "c02cbd4e36d223efcd9efb2ee17634c20cb3f63c65f029ee275b77c14be4d17e"
LABEL = "Selected NMF projection "


def _forbidden(*args, **kwargs):
    raise AssertionError("presentation attempted NMF fitting/calculation/native/worker/HTTP/real-model work")


def _guard_work(monkeypatch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status",
            "collect", "cancel", "release"):
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    for name in ("reconstruct_nmf", "residual_measurements", "component_measurements", "calculate_nmf_sheet"):
        monkeypatch.setattr("gene_annotation_episode.expression_nmf_calculations." + name, _forbidden)
    for target in (
        "gene_annotation_episode.native_expression_nmf_driver.run_expression_nmf",
        "gene_annotation_episode.native_expression_nmf_driver.execute_expression_nmf_plan",
        "gene_annotation_episode.expression_nmf_result_worker.execute_expression_nmf_worker",
        "gene_annotation_episode.native_expression_nmf_results.NativeExpressionNMFResults.execute",
        "gene_annotation_episode.acquisition.PublicClients._http",
        "socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
    ):
        monkeypatch.setattr(target, _forbidden)
    class NoFittingImports:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "sklearn" or fullname.startswith("sklearn."):
                raise AssertionError("presentation attempted to import the unselected fitting library")
            return None
    assert "sklearn" not in sys.modules
    monkeypatch.setattr(sys, "meta_path", [NoFittingImports(), *sys.meta_path])
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    for name in ("put", "artifact", "commit_reasoning"):
        monkeypatch.setattr(Store, name, _forbidden)


def _fixture(monkeypatch):
    root = (Path(__file__).parent / "retained_workflow_fixtures").resolve(strict=True)
    path = root / (FIXTURE_MODULE.replace(".", "/") + ".py")
    raw = path.read_bytes()
    assert len(raw) == 20129 and _sha(raw) == FIXTURE_SHA256
    previous = sys.modules.get(FIXTURE_MODULE)
    if previous is not None:
        assert Path(previous.__file__).resolve() == path
    monkeypatch.syspath_prepend(str(root))
    fixture = import_module(FIXTURE_MODULE)
    assert Path(fixture.__file__).resolve() == path
    return fixture


def _file(case, identity, *, required=True):
    identity = validate_file(identity)
    row = case["db"].execute("SELECT sha256,size FROM artifacts WHERE id=?", (identity["artifact_ref"],)).fetchone()
    assert row is not None and (row["sha256"], row["size"]) == (identity["sha256"], identity["size_bytes"])
    sha = identity["sha256"]
    path = case["historical"] / "state/artifacts" / sha[:2] / sha
    if not path.exists():
        assert not required
        return None
    raw = path.read_bytes()
    assert len(raw) == identity["size_bytes"] and _sha(raw) == sha
    return raw


def _archive(case, descriptor):
    assert Path(descriptor["file"]).name == descriptor["file"]
    path = case["historical"] / "run/archive" / descriptor["file"]
    assert _sha(path.read_bytes()) == descriptor["sha256"]
    assert _sha(path.with_suffix(".index.json").read_bytes()) == descriptor["index_sha256"]
    def expand(value):
        if isinstance(value, dict):
            if set(value) == {"$archive"}:
                return _archive(case, value["$archive"])
            return {name: expand(child) for name, child in value.items()}
        return [expand(child) for child in value] if isinstance(value, list) else value
    return expand(json.loads(path.read_bytes()))


@pytest.fixture(scope="module")
def retained_nmf(tmp_path_factory):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_NMF_PRESENTATION_CASE_JSON")
    if not supplied:
        pytest.skip("requires the caller-selected authentic NMF490 case and exact inventory")
    selected = json.loads(supplied)
    assert set(selected) == {"directory", "inventory_sha256"} and selected["inventory_sha256"] == INVENTORY_SHA256
    original = Path(selected["directory"]).resolve(strict=True)
    inventory = _inventory(original)
    assert _sha(_canonical(inventory).encode()) == INVENTORY_SHA256
    assert not (original / "state/state.sqlite3-wal").exists() and not (original / "state/state.sqlite3-shm").exists()
    historical = tmp_path_factory.mktemp("nmf-presentation-input") / "historical"
    shutil.copytree(original, historical, symlinks=True)
    assert _inventory(historical) == inventory
    db = sqlite3.connect((historical / "state/state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    case = dict(original=original, historical=historical, inventory=inventory, db=db,
        configuration=json.loads((historical / "fixture-configuration.json").read_bytes()),
        captures={p.name: json.loads(p.read_bytes()) for p in sorted(historical.glob("decision-*.json"))})
    receipts = {}
    try:
        for name, pin in sorted(inventory.items()):
            parts = Path(name).parts
            if (len(parts) != 6 or parts[:2] != ("run", "execution-results")
                    or parts[3] != "native-expression-nmf-actions" or parts[5] != "receipt.json"):
                continue
            assert pin["kind"] == "file" and pin["mode"] == 0o444
            raw = (historical / name).read_bytes()
            assert len(raw) == pin["size_bytes"] and _sha(raw) == pin["sha256"]
            receipt = json.loads(raw)
            assert receipt["version"] == "native_expression_nmf_acquired_result_v1"
            intent = receipt["intent"]
            assert parts[2] == digest([intent["run_id"], intent["episode_id"]]) and parts[4] == digest(intent["operation_key"])
            prefix = intent["run_id"] + ":" + intent["episode_id"] + ":"
            index = int(intent["operation_key"].removeprefix(prefix))
            assert intent["operation_key"] == prefix + str(index)
            action = db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
                (intent["run_id"], intent["episode_id"], index)).fetchone()
            assert json.loads(action["action"]) == {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
            outcome = json.loads(action["result"])
            assert outcome["status"] == "completed" and outcome["result"] == receipt
            episode = db.execute("SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (intent["run_id"], intent["episode_id"])).fetchone()
            request = json.loads(episode["request"])
            assert digest(request) == intent["original_request_sha256"]
            assert request["message"]["episode_assignment"] == intent["assignment"]
            projection, = receipt["facts"][PROJECTION_SOURCE]
            assert validate_projection(projection) == receipt["projection"] == projection
            files = receipt["qualified_files"]
            sheet = json.loads(_file(case, files["sheet"]))
            calculations = json.loads(_file(case, files["calculations"]))
            projection_bytes = _file(case, files["projection"], required=False)
            if projection_bytes is not None:
                assert json.loads(projection_bytes) == projection
            frozen = db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (intent["run_id"], intent["episode_id"])).fetchone()
            form = json.loads(frozen["form"])
            assert json.loads(frozen["facts"])[PROJECTION_SOURCE] == form["nmf"] == [projection]
            assert form["saved"] == receipt["facts"][SAVED_SOURCE] == [files["sheet"]]
            commission_index = int(json.loads(episode["path"])[-1][1].removeprefix("child_"))
            report = db.execute("SELECT parent_episode_id,form,failure FROM runtime_report_attempts WHERE run_id=? AND child_episode_id=? AND decision_index=?",
                (intent["run_id"], intent["episode_id"], commission_index)).fetchone()
            assert report["failure"] is None and json.loads(report["form"]) == form
            parent = db.execute("SELECT archive FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (intent["run_id"], report["parent_episode_id"])).fetchone()
            archive = _archive(case, json.loads(parent["archive"]))
            units = [unit for unit in archive["units"] if (unit.get("child") or {}).get("episode_id") == intent["episode_id"]]
            assert len(units) == 1 and units[0]["child_result"] == {"form": form}
            mode = intent["assignment"]["selector"]["mode"]
            assert mode not in receipts
            receipts[mode] = dict(receipt=receipt, outcome=outcome, form=form, projection=projection,
                sheet=sheet, calculations=calculations, projection_file_available=projection_bytes is not None)
        assert set(receipts) == {"native_result", "saved_sheet_recalculation"}
        assert not receipts["native_result"]["projection_file_available"]
        assert receipts["saved_sheet_recalculation"]["projection_file_available"]
        assert receipts["native_result"]["sheet"] == receipts["saved_sheet_recalculation"]["sheet"]
        assert receipts["native_result"]["calculations"] == receipts["saved_sheet_recalculation"]["calculations"]
        case.update(receipts=receipts, before=_tables(db))
        yield case
        assert _tables(db) == case["before"] and db.total_changes == 0
    finally:
        db.close()
        assert _inventory(historical) == inventory and _inventory(original) == inventory


def test_native_diagnostics_keep_independent_reports_units_and_denominators(retained_nmf, monkeypatch):
    _guard_work(monkeypatch)
    projection = retained_nmf["receipts"]["native_result"]["projection"]
    assert (projection["total_available_rows"], projection["selected_row_count"], projection["filtered_row_count"],
        projection["row_offset"], projection["returned_row_count"], projection["has_more"]) == (10, 8, 8, 0, 8, False)
    rows = {row["field"]: row for row in projection["rows"]}
    assert rows["native_reconstruction_error"] == dict(field="native_reconstruction_error", value=0.0001383408514600178, units="counts", denominator=None)
    assert rows["frobenius_residual"] == dict(field="frobenius_residual", value=0.00013834085146004034, units="counts", denominator=None)
    assert rows["rmse"] == dict(field="rmse", value=4.611361715334678e-05, units="counts", denominator=9)
    assert rows["relative_frobenius_residual"] == dict(field="relative_frobenius_residual", value=2.3725260292806895e-05,
        units="dimensionless", denominator=5.830951894845301)
    assert rows["sse"]["value"] == 1.9138191182688943e-08 and rows["sse"]["units"] == "counts^2"
    assert [rows[name]["value"] for name in ("native_n_iter", "fit_call_count", "cell_count")] == [17, 1, 9]
    text = render_expression_nmf_projections([projection])
    for row in projection["rows"]:
        assert row["field"] in text and str(row["value"]) in text
    assert "5.830951894845301" in text and "counts^2" in text


def test_saved_residual_page_preserves_original_position_order_and_file_operand(retained_nmf, monkeypatch):
    _guard_work(monkeypatch)
    data = retained_nmf["receipts"]["saved_sheet_recalculation"]
    value, selector = data["projection"], data["receipt"]["intent"]["assignment"]["selector"]
    assert value["selector"] == dict(view="residual_cells", gene_positions=[1, 0], sample_positions=[2, 1],
        row_window={"offset": 1, "limit": 3})
    assert (value["total_available_rows"], value["selected_row_count"], value["filtered_row_count"], value["row_offset"], value["returned_row_count"], value["has_more"]) == (9, 4, 4, 1, 3, False)
    assert [(r["gene_position"], r["sample_position"], r["gene_label"], r["sample_label"]) for r in value["rows"]] == [(1, 1, "g", "B"), (0, 2, "g", "B"), (0, 1, "g", "B")]
    assert [r["raw_value"] for r in value["rows"]] == [1.0, 0.0, 2.0]
    assert [r["signed_residual"] for r in value["rows"]] == [-8.855204043167753e-05, 0.0, -4.1450697748413035e-05]
    assert selector["saved_sheet_file"] == data["form"]["saved"][0]
    assert set(selector["saved_sheet_file"]) == {"artifact_ref", "sha256", "size_bytes", "format"}
    assert select_expression_nmf_execution_values(selector) == selector
    assert _execution_presentation_values(selector) == selector
    text = render_expression_nmf_projections([value])
    assert "-8.855204043167753e-05" in text and "-4.1450697748413035e-05" in text


@pytest.mark.parametrize("view", ["gene_loadings", "sample_contributions"])
def test_current_projection_only_axis_views_use_authentic_sheet_and_calculations(retained_nmf, view, monkeypatch):
    _guard_work(monkeypatch)
    data = retained_nmf["receipts"]["native_result"]
    selector = dict(view=view, component_positions=[1, 0], row_window={"offset": 0, "limit": 4})
    selector["gene_positions" if view == "gene_loadings" else "sample_positions"] = [1, 0]
    before = deepcopy((data["sheet"], data["calculations"]))
    projection = project_nmf_result(data["sheet"], data["calculations"], selector=selector)
    assert validate_projection(projection) == projection and (data["sheet"], data["calculations"]) == before
    axis = "gene" if view == "gene_loadings" else "sample"
    assert [(r[axis + "_position"], r["component_position"]) for r in projection["rows"]] == [(1, 1), (1, 0), (0, 1), (0, 0)]
    assert projection["total_available_rows"] == 6 and projection["returned_row_count"] == 4
    text = render_expression_nmf_projections([projection])
    assert axis + ":1" in text and "component:1" in text


def test_authentic_receipt_public_views_deduplicate_reenter_and_ignore_private_siblings(retained_nmf, monkeypatch):
    _guard_work(monkeypatch)
    projections = [retained_nmf["receipts"][mode]["projection"] for mode in ("native_result", "saved_sheet_recalculation")]
    for data in retained_nmf["receipts"].values():
        state = dict(last_local_outcome=deepcopy(data["outcome"]), child_reports=[deepcopy(data["form"])])
        original = deepcopy(state)
        selected = select_expression_nmf_presentation(state, lookup_results=[data["projection"]])
        assert selected["projections"] == [data["projection"]] and state == original
        views = [value for value in _walk(selected["context"]) if isinstance(value, dict)
            and value.get("version") == "expression_nmf_result_receipt_view_v1"]
        assert len(views) == 1
        assert select_expression_nmf_execution_values(views[0]) == views[0]
        assert _execution_presentation_values(views[0]) == views[0]
        assert data["form"]["saved"][0] in list(_walk(views[0]))
        marker = "unrequested-private-NMF-carrier"
        changed = deepcopy(data["outcome"])
        for field in ("projection", "host_failures", "worker_plan", "native"):
            changed["result"][field] = {"invalid_private_value": marker}
        changed["result"]["intent"]["target"] = {"invalid_private_value": marker}
        assert select_expression_nmf_presentation({"last_local_outcome": changed})["projections"] == [data["projection"]]
        assert marker not in render_episode_steering({"last_local_outcome": changed})
    state = dict(child_reports=[{"nmf": projections}, {"nmf": [projections[0]]}],
        current_report_update={"nmf": [projections[1]]})
    assert select_expression_nmf_presentation(state, lookup_results=projections)["projections"] == projections


@pytest.mark.parametrize("kind", ["invalid_extent", "unknown_schema", "unknown_version", "opaque_slots"])
def test_engineered_invalid_or_opaque_packets_remain_literal(retained_nmf, kind, monkeypatch):
    _guard_work(monkeypatch)
    value = deepcopy(retained_nmf["receipts"]["native_result"]["projection"])
    if kind == "invalid_extent":
        value["returned_row_count"] = 99
    elif kind == "unknown_schema":
        value["schema"] = "unknown_nmf_projection_v1"
    elif kind == "unknown_version":
        value = {"version": "unknown_packet_v1", "nested": value}
    else:
        value = {name: deepcopy(value) for name in ("inputs", "schema_json", "input_schema", "instructions", "arguments")}
    state = {"child_reports": [value]}
    assert select_expression_nmf_presentation(state)["context"] == state
    assert select_expression_nmf_presentation(state)["projections"] == []


def test_current_empty_diagnostic_selection_keeps_complete_fit_distinct(retained_nmf, monkeypatch):
    _guard_work(monkeypatch)
    data = retained_nmf["receipts"]["native_result"]
    projection = project_nmf_result(data["sheet"], data["calculations"], selector={
        "view": "fit_diagnostics", "fields": [], "row_window": {"offset": 0, "limit": 8}})
    assert projection["status"] == "calculated" and projection["native_outcome"] == "complete"
    assert (projection["total_available_rows"], projection["selected_row_count"], projection["returned_row_count"]) == (10, 0, 0)
    assert projection["rows"] == [] and projection["has_more"] is False
    assert select_expression_nmf_presentation({"child_reports": [{"nmf": [projection]}]})["projections"] == [projection]
    text = render_expression_nmf_projections([projection])
    assert "complete" in text and "10" in text and "[]" in text


def test_engineered_missing_values_keep_raw_unit_unknown_and_actual_zero_literal(retained_nmf, monkeypatch):
    """Engineered display controls; these are not additional native reports."""
    _guard_work(monkeypatch)
    residual = deepcopy(retained_nmf["receipts"]["saved_sheet_recalculation"]["projection"])
    residual["rows"][0]["raw_value"] = None
    residual["rows"][0]["units"] = "engineered_fit_units"
    assert validate_projection(residual) == residual
    text = render_expression_nmf_projections([residual])
    assert "The raw input unit is not supplied by this projection." in text
    assert "Raw input value (unit not supplied)" in text
    assert "Fit unit (fitted/reconstructed/residual only)" in text
    first = next(line for line in text.splitlines() if line.startswith("| 1 | gene:1 |"))
    cells = [cell.strip() for cell in first.strip("|").split("|")]
    assert cells[6] == "null" and cells[-1] == '"engineered_fit_units"'
    zero = next(line for line in text.splitlines() if line.startswith('| 0 | gene:0 | "g" | 2 | sample:2 |'))
    assert [cell.strip() for cell in zero.strip("|").split("|")][6] == "0.0"
    diagnostics = deepcopy(retained_nmf["receipts"]["native_result"]["projection"])
    next(row for row in diagnostics["rows"] if row["field"] == "native_n_iter")["value"] = None
    missing = render_expression_nmf_projections([diagnostics])
    iteration = next(line for line in missing.splitlines() if line.startswith("| native_n_iter |"))
    assert "| null |" in iteration and "| 0 |" not in iteration


def _application(case, directory, fixture, provider):
    state = directory / "state"
    state.mkdir()
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
    original = configuration["scientific_binding"]
    library = ScientificProcessLibrary(run / "scientific-process-library")
    tools = ScientificToolLibrary(run / "scientific-tool-library")
    assert library.as_record() == original["configuration"]["library"]
    assert tools.as_record() == original["configuration"]["tool_library"]
    configuration["scientific_binding"] = ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=original["configuration"]["child_roles"]).as_record()
    assert configuration["scientific_binding"]["configuration"] == original["configuration"]
    configuration["initial_refs"] = [HANDOFF]
    store = Store(state)
    try:
        flow, registry = fixture.assemble(store, directory, provider, configuration)
        constructor = _assert_original_rows(store.db, case["before"])
        return dict(store=store, flow=flow, registry=registry, configuration=configuration,
            constructor=constructor, initialized=_tables(store.db), files=_inventory(directory))
    except BaseException:
        store.close()
        raise


class PendingResultsCaptured(RuntimeError):
    pass


def test_genuine_current_pending_nmf_results_and_engineering_receiver_frames(retained_nmf, tmp_path, monkeypatch):
    _guard_work(monkeypatch)
    fixture = _fixture(monkeypatch)
    captures = retained_nmf["captures"]
    native_capture = captures["decision-5.json"]
    target = validate_target(native_capture["context"]["execution_target"])
    assert target["run_id"] == fixture.RUN_ID == "expression-nmf-workflow490"
    science = _commission(retained_nmf["db"], fixture.RUN_ID, captures["decision-1.json"]["episode_id"], "scientific_process")
    native = _commission(retained_nmf["db"], fixture.RUN_ID, native_capture["episode_id"], "results")
    full_info = science["request"]["message"]["episode_assignment"]["selection"]["child_tool_info"]
    assert full_info == captures["decision-1.json"]["context"]["scientific_process"]["child_tool_info"]
    assert science["selected"]["assignment"] == captures["decision-1.json"]["context"]["scientific_process"]["assignment"]
    assert native["selected"]["assignment"] == native_capture["context"]["execution_assignment"]
    selector = native["selected"]["assignment"]["selector"]
    assert native["selected"]["assignment"]["handoff_ref"] == HANDOFF and selector["mode"] == "native_result"
    assert selector["saved_sheet_file"] is None and selector["projection"]["view"] == "fit_diagnostics"
    job = target["assignment"]["requested_job"]["native_expression_nmf"]
    original_get = Store.get_artifact

    def control_bytes_only(store, reference):
        assert reference != job["input"]["artifact_ref"], "pending builder reopened original expression matrix"
        return original_get(store, reference)

    monkeypatch.setattr(Store, "get_artifact", control_bytes_only)
    session = _session(tmp_path / "nmf-current-presentation")
    calls, pending = [], {}

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            call = dict(episode_id=episode_id, role=role, instructions=instructions,
                context=deepcopy(current), schema=deepcopy(schema))
            calls.append(call)
            wire, model_instructions = session._presentation(episode_id, role, instructions, current)
            call.update(wire=wire, model_instructions=model_instructions)
            if current.get("execution_assignment", {}).get("version") == "execution_results_assignment_v1":
                assert len(calls) == 3 and current["execution_assignment"] == native["selected"]["assignment"]
                assert current["execution_target"] == target
                assert current["requested_form"] == json.loads(native["selected"]["schema_json"])
                assert current["requested_report_purpose"] == native["selected"]["purpose"]
                assert current["goal"]["objective"] == native["selected"]["goal"]
                task = current["selected_execution_task"]
                assert task["scientific_question"] == science["request"]["goal"]["objective"] == retained_nmf["configuration"]["goal"]
                assert task["selected_tool_info"] == full_info and task["selector"] == selector
                assert len(task["requests"]) == 1 and task["requests"][0]["job"] == expression_nmf_scientific_job_view(job)
                assert wire.startswith("TASK") and "STEERING" in wire and task["scientific_question"] in wire
                assert instructions in wire and model_instructions == instructions
                for info in full_info:
                    assert info["name"] in wire and info["description"] in wire and info["instructions"] in wire
                assert current["last_local_outcome"] is None and current["child_reports"] == []
                assert current["execution_progress"]["execution_completed"] is False
                for source_name in fixture.SOURCES.values():
                    assert current["execution_progress"][source_name] == []
                pending.update(episode_id=episode_id, context=deepcopy(current), wire=wire)
                raise PendingResultsCaptured("full current NMF Results reached before tool selection")
            if "scientific_process" in current:
                assert len(calls) == 2 and current["scientific_process"]["assignment"] == science["selected"]["assignment"]
                assert current["scientific_process"]["child_tool_info"] == full_info
                assert retained_nmf["configuration"]["goal"] in wire
                for info in full_info:
                    assert info["instructions"] in wire
                selected = native["selected"]
            else:
                assert len(calls) == 1 and current["scope"] == science["selected"]["scope"]
                selected = science["selected"]
            answer = fixture.provider_value({"selection": deepcopy(selected), "report_update": {}}, plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    proof = dict(version="nmf_current_pending_results_presentation_v1", passed=False,
        original_inventory_sha256=INVENTORY_SHA256, historical_postcollect_context_claimed=False,
        historical_instruction_bytes_claimed=False, closed_replay_claimed=False,
        full_current_results_builder_verified=False, native_calls=0, fit_calls=0,
        calculation_calls=0, worker_calls=0, http_calls=0, real_model_calls=0, scientific_publications=0)
    app = None
    directory = tmp_path / "current-pending"
    directory.mkdir()
    try:
        app = _application(retained_nmf, directory, fixture, Choices())
        store, flow = app["store"], app["flow"]
        root = flow.build("annotation", "current-pending-nmf-presentation", retained_nmf["configuration"]["goal"],
            deepcopy(retained_nmf["configuration"]["scope"]))
        with pytest.raises(PendingResultsCaptured, match="before tool selection"):
            asyncio.run(root.run_async(flow.context))
        assert len(calls) == 3 and pending
        after = _tables(store.db)
        added = _new_rows(app["initialized"], after)
        episodes = [dict(zip(after["runtime_episodes"]["columns"], row)) for row in added["runtime_episodes"]]
        assert len(episodes) == 3 and all(row["state"] == "active" and row["completion"] is row["archive"] is None for row in episodes)
        ids = {row["episode_id"] for row in episodes}
        assert {json.loads(row["path"])[-1][0] for row in episodes} == {"annotation", "scientific_process", "results"}
        actions = [dict(zip(after["runtime_actions"]["columns"], row)) for row in added["runtime_actions"]]
        assert len(actions) == 2 and all(row["result"] is None for row in actions)
        models = [dict(zip(after["runtime_model_calls"]["columns"], row)) for row in added["runtime_model_calls"]]
        assert len(models) == 3 and sum(row["response"] is None for row in models) == 1
        assert next(row for row in models if row["response"] is None)["episode_id"] == pending["episode_id"]
        for name in ("runtime_observations", "runtime_forms", "runtime_report_attempts", "records", "artifacts", "tool_operations"):
            assert added[name] == []
        for name, rows in added.items():
            for row in rows:
                record = dict(zip(after[name]["columns"], row))
                for field in ("episode_id", "parent_episode_id", "child_episode_id"):
                    if record.get(field) is not None:
                        assert record[field] in ids
        records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="nmf_current_pending_")
        context = records.context(pending["episode_id"])
        owner = flow.specialist(_source_for_original_context(flow, context))
        assert owner.native_expression_nmf_results.receipts.completed_receipts(context) == []
        assert owner._target(context) == target and HANDOFF in set(flow.receipts.known(context.episode_id))
        # Current engineering channels use authentic stored values. They are
        # not new acquired outcomes, grants or historical postcollect captures.
        native_data = retained_nmf["receipts"]["native_result"]
        engineering_own = deepcopy(pending["context"])
        engineering_own["last_local_outcome"] = deepcopy(native_data["outcome"])
        first_state = instructional_model_context(engineering_own)
        first, _ = session._presentation("current-engineering-NMF-own", "REASONING", calls[2]["instructions"], state_frame(first_state))
        second, _ = session._presentation("current-engineering-NMF-own", "REASONING", calls[2]["instructions"], state_frame(first_state, first_state))
        assert first == second and render_expression_nmf_projections([native_data["projection"]]) in first
        receiver = deepcopy(calls[0]["context"])
        receiver["child_reports"] = [{"nmf": [data["projection"] for data in retained_nmf["receipts"].values()]}]
        text, _ = session._presentation("current-engineering-NMF-receiver", "REASONING", calls[0]["instructions"],
            state_frame(instructional_model_context(receiver)))
        assert text.startswith("TASK") and "STEERING" in text and retained_nmf["configuration"]["goal"] in text
        assert "0.0001383408514600178" in text and "-8.855204043167753e-05" in text
        assert _tables(store.db) == after
        files = _inventory(directory)
        for name, pin in app["files"].items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert files[name] == pin
        proof.update(passed=True, full_current_results_builder_verified=True,
            original_rows_unchanged=True, original_scientific_request=science, original_native_request=native,
            constructor=app["constructor"], original_scientific_binding=retained_nmf["configuration"]["scientific_binding"],
            new_scientific_binding=app["configuration"]["scientific_binding"], initial_handoff_input=HANDOFF,
            new_episode_ids=sorted(ids), new_framework_row_counts={name: len(rows) for name, rows in added.items()},
            new_framework_paths={name: pin for name, pin in files.items() if name not in app["files"]},
            scripted_completed_calls=2, unanswered_results_calls=1,
            current_context_sha256=_sha(_canonical(pending["context"]).encode()),
            current_wire_sha256=_sha(pending["wire"].encode()),
            engineering_own_continuation_wire_sha256=_sha(first.encode()), engineering_receiver_wire_sha256=_sha(text.encode()))
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"] = calls
        proof["actual_scripted_provider_calls"] = len(calls)
        if app is not None:
            proof["actual_new_rows"] = _new_rows(app["initialized"], _tables(app["store"].db))
            app["store"].close()
        (tmp_path / "NMF_CURRENT_PENDING_RESULTS.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")

