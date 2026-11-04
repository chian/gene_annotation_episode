"""Pinned ITC messages and literal views; no fit or saved calculation is run.

The native268 SQLite/WAL/SHM family is copied and hashed, never opened. Both
native-action and rich-return witnesses come from the consolidated397 copy.
Only268 retains actual dispatch instruction/wire captures. Rich receiver text
is explicitly current rendering, not a historical273/397 model-wire claim.
"""
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.itc_binding_presentation import (
    render_itc_binding_result, select_itc_binding_result,
)
from gene_annotation_episode.molecular_measurement_tools import (
    ITC_PARAMETER_SOURCE, project_itc_parameter_return, project_itc_tool_result,
)
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import (
    _selected_molecular_view, _values, render_episode_steering,
)
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha,
    _source_for_original_context, _tables,
)
from test_runtime import FixtureController


ORIGINAL = "source_4f6a6927cc1b155c54974cb7"
SAVED = "source_7275c03cef6e89f75c3d2605"
INVENTORIES = {
    "native": "9178b088730ac6d7edac308db30405faec10a8e44693fece7d937ebc4f526ab5",
    "rich": "874260a63f6afa43a93e2ea0d70861f0942e23b24003789adb1d3b94712a9802",
}
STORED = {
    ORIGINAL: ("aa029c30f55e2f408c3bcf85297e2e0d96232e900f31454ea17479bcbc68ccd4", 141702),
    SAVED: ("429c93b1c24293ee78eb0f18d49a157b23d21cb6ae35a01b7131ed2fe0347be7", 147268),
}


def _forbidden(*args, **kwargs):
    raise AssertionError("ITC presentation attempted fitting/calculation/work/publication/model/HTTP")


def _guard_work(patch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect", "cancel", "release"):
        patch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    for target in (
        "gene_annotation_episode.itc_binding_fit.fit_itc_binding_measurements",
        "gene_annotation_episode.itc_binding_measurements.predict_itc_binding_heats",
        "gene_annotation_episode.itc_binding_measurements.calculate_itc_binding_components",
        "gene_annotation_episode.itc_binding_measurements._prepare_fit_inputs",
        "gene_annotation_episode.itc_binding_measurements._fit_diagnostics",
        "gene_annotation_episode.molecular_measurement_tools.run_itc_tool_request",
        "gene_annotation_episode.molecular_measurement_tools.run_owned_molecular_worker",
        "gene_annotation_episode.molecular_measurement_tools.retain_molecular_publication",
        "gene_annotation_episode.molecular_measurement_tools.publish_itc_work",
        "gene_annotation_episode.acquisition.PublicClients._http",
        "socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
    ):
        patch.setattr(target, _forbidden)
    patch.setattr(_SessionConnection, "complete", _forbidden)
    patch.setattr(ToolRegistry, "execute", _forbidden)
    patch.setattr(ToolRegistry, "execute_async", _forbidden)
    patch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("put", "artifact", "commit_reasoning"):
        patch.setattr(Store, name, _forbidden)


def _json_file(path, sha, size):
    raw = path.read_bytes()
    assert (_sha(raw), len(raw)) == (sha, size)
    return json.loads(raw)


def _artifact(case, reference):
    row = case["db"].execute("SELECT sha256,size FROM artifacts WHERE id=?", (reference,)).fetchone()
    assert row is not None and reference == "artifact_" + row["sha256"]
    path = case["rich"] / "retained268/store/artifacts" / row["sha256"][:2] / row["sha256"]
    raw = path.read_bytes()
    assert (_sha(raw), len(raw)) == (row["sha256"], row["size"])
    return raw


@pytest.fixture(scope="module")
def retained_itc(tmp_path_factory):
    supplied = os.environ.get("HMMER_NATIVE_ORACLE_ITC_PRESENTATION_CASES_JSON")
    if not supplied:
        pytest.skip("requires explicitly selected native268 and consolidated rich397 cases")
    selected = json.loads(supplied)
    assert set(selected) == set(INVENTORIES)
    with pytest.MonkeyPatch.context() as patch:
        _guard_work(patch)
        originals, inventories, copies = {}, {}, {}
        owned = tmp_path_factory.mktemp("itc-presentation-input")
        for name, expected in INVENTORIES.items():
            assert set(selected[name]) == {"directory", "inventory_sha256"}
            assert selected[name]["inventory_sha256"] == expected
            original = Path(selected[name]["directory"]).resolve(strict=True)
            inventory = _inventory(original)
            assert _sha(_canonical(inventory).encode()) == expected
            destination = owned / name
            shutil.copytree(original, destination, symlinks=True)
            assert _inventory(destination) == inventory
            originals[name], inventories[name], copies[name] = original, inventory, destination
        # Both entire physical families are copied before any SQLite open.
        database = copies["rich"] / "retained268/store/state.sqlite3"
        assert (_sha(database.read_bytes()), database.stat().st_size) == (
            "fbb7a44e685b2d804b7d964da85a4a577bb7f786b429be3f265d0c7e70955cb1", 5095424)
        assert not database.with_name("state.sqlite3-wal").exists()
        assert not database.with_name("state.sqlite3-shm").exists()
        db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
        db.row_factory = sqlite3.Row
        before = _tables(db)
        case = dict(native=copies["native"], rich=copies["rich"], db=db, before=before)
        try:
            delivery = _json_file(copies["native"] / "ACTUAL_ITC_DELIVERY.json",
                "5ed3d43c9dea33ceeb7fc8db37b65cf4d696497f15cfa902b5573e45c1b500e1", 76679)
            turns = _json_file(copies["native"] / "ACTUAL_ITC_TURNS.json",
                "98d548ebd1f60fcbf7697b76bb6fcc69ab4b13cccde94916db69840953b8d12f", 1249540)
            assert len(delivery["actions"]) == len(delivery["outcomes"]) == 3 and len(turns) == 4
            raw = _artifact(case, delivery["input_artifact"])
            assert (_sha(raw), len(raw)) == ("8127b46a65f7cfea49238e758fc1647c1487f2c2e8c60c298a87240c1d423108", 25052)
            stored, sources = {}, {}
            for ref, (sha, size) in STORED.items():
                row = db.execute("SELECT data FROM records WHERE id=? AND record_type='source'", (ref,)).fetchone()
                source = json.loads(row[0])
                assert source["provider"] == "analyze_itc_binding_thermodynamics"
                assert source["artifact_ref"] == "artifact_" + sha
                body = _artifact(case, source["artifact_ref"])
                assert len(body) == size
                stored[ref], sources[ref] = json.loads(body), source
            counts, contexts = Counter(), []
            for turn in turns:
                assert set(turn) == {"episode_id", "text", "instructions", "output_schema"}
                index = counts[turn["episode_id"]]
                counts[turn["episode_id"]] += 1
                row = db.execute("SELECT request,response FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=?",
                    ("ordinary-itc-fixture", turn["episode_id"], index)).fetchone()
                assert row is not None and row["response"] is not None
                request = json.loads(row["request"])
                contexts.append(dict(turn=turn, context=request["context"], journal_schema=request["schema"], call_index=index))
            scientific = [x for x in contexts if "scientific_process" in x["context"]]
            assert len(scientific) == 3
            episode = scientific[0]["turn"]["episode_id"]
            actions = db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index",
                ("ordinary-itc-fixture", episode)).fetchall()
            assert [json.loads(x["action"]) for x in actions] == delivery["actions"]
            assert [json.loads(x["result"]) for x in actions] == delivery["outcomes"]
            packets = [x["result"] for x in delivery["outcomes"]]
            assert [x["version"] for x in packets] == ["ordinary_itc_partial_values_v1", "ordinary_itc_values_v1", "ordinary_itc_values_v1"]
            rich_forms = db.execute("SELECT episode_id,facts,form FROM runtime_forms WHERE run_id=?",
                ("retained-itc-parameter-forms",)).fetchall()
            assert len(rich_forms) == 3
            groups = [json.loads(row["form"])["parameters"] for row in rich_forms]
            assert all(group == groups[0] for group in groups)
            assert [x["source_ref"] for x in groups[0]] == [ORIGINAL, SAVED]
            for row, group in zip(rich_forms, groups):
                assert json.loads(row["facts"])[ITC_PARAMETER_SOURCE] == group
            reports = db.execute("SELECT child_episode_id,form,failure FROM runtime_report_attempts WHERE run_id=? ORDER BY decision_index",
                ("retained-itc-parameter-forms",)).fetchall()
            assert len(reports) == 2 and all(x["failure"] is None and json.loads(x["form"])["parameters"] == groups[0] for x in reports)
            for report in reports:
                original = db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
                    ("retained-itc-parameter-forms", report["child_episode_id"])).fetchone()
                assert json.loads(original["facts"])[ITC_PARAMETER_SOURCE] == json.loads(report["form"])["parameters"]
            parents = db.execute("SELECT episode_id,path,request FROM runtime_episodes WHERE run_id=?",
                ("retained-itc-parameter-forms",)).fetchall()
            parent, = [x for x in parents if len(json.loads(x["path"])) == 1]
            call = db.execute("SELECT request FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index=1",
                ("retained-itc-parameter-forms", parent["episode_id"])).fetchone()
            receiver = json.loads(call[0])["context"]
            assert receiver["child_reports"][0]["parameters"] == groups[0]
            case.update(delivery=delivery, contexts=contexts, scientific=scientific,
                stored=stored, sources=sources, packets=packets, rich_groups=groups[0],
                rich_forms=rich_forms, receiver=receiver, parent_episode_id=parent["episode_id"])
            yield case
            assert _tables(db) == before and db.total_changes == 0
        finally:
            db.close()
            for name in INVENTORIES:
                assert _inventory(copies[name]) == inventories[name]
                assert _inventory(originals[name]) == inventories[name]


def _native_view(case, ordinals=(31, 0)):
    partial = case["packets"][0]["retained_sources"]
    original, = [x for x in partial if x["source_ref"] == ORIGINAL]
    return project_itc_tool_result(case["stored"][ORIGINAL],
        selection=dict(mode="fit", injection_ordinals=list(ordinals), fields=["predicted_heat", "residual"]),
        source_ref=ORIGINAL, artifact_ref=original["native_file"]["artifact_ref"], grading_ref=original["grading_ref"])


@pytest.mark.parametrize("kind", ["partial", "full", "rich"])
def test_three_actual_public_versions_are_detached_literal_views(retained_itc, kind):
    value = {"partial": retained_itc["packets"][0], "full": retained_itc["packets"][1],
        "rich": retained_itc["rich_groups"][0]}[kind]
    before = deepcopy(value)
    selected = select_itc_binding_result(value)
    assert selected == value and selected is not value
    assert "ITC retained values" in render_itc_binding_result(selected, 1)
    assert value == before


def test_original_native_parameter_cells_and_units_require_no_new_fit(retained_itc):
    value = _native_view(retained_itc)
    assert [value["parameters"][name]["value"] for name in ("kd", "n", "delta_h")] == [
        2.999999999999987e-6, 1.4000000000000001, -27999.999999999985]
    assert [value["parameters"][name]["unit"] for name in ("kd", "n", "delta_h")] == [
        "mol_per_litre", "sites_per_macromolecule", "joule_per_mole"]
    assert value["parameter_source"] == "fit_observation" and value["fit_call_count"] == 1
    text = render_itc_binding_result(value, 1)
    assert "2.999999999999987e-06" in text and "-27999.999999999985" in text
    assert "effective sites per declared macromolecule" in text


def test_saved_read_keeps_original_fit_diagnostics_and_selected_ordinal_order(retained_itc):
    native = _native_view(retained_itc)
    saved, read = retained_itc["packets"][1:]
    assert [saved["parameters"][x]["value"] for x in ("kd", "n", "delta_h")] == [6e-6, 1.4, -28000]
    assert saved["parameter_source"] == "selected_parameters" and read["parameter_source"] == "selected_parameters"
    for value in (saved, read):
        assert value["fit_call_count"] == 1 and value["this_operation_fit"] is False
        for field in ("sse", "selected_objective", "residual_population_count", "residual_degrees_of_freedom",
                "fit_diagnostics_scope", "covariance_estimate", "covariance_scope"):
            assert value[field] == native[field]
    assert [row["injection_ordinal"] for row in saved["rows"]] == list(range(32))
    assert [row["injection_ordinal"] for row in read["rows"]] == [31, 0]
    assert all(set(row) == {"injection_ordinal", "predicted_heat", "residual"} for row in read["rows"])
    text = render_itc_binding_result(read, 1)
    assert text.index("\n| 31 | ") < text.index("\n| 0 | ")
    assert "Saved calculation and literal read do not imply another fit." in text


def test_rich_native_saved_parent_onward_and_frozen_groups_keep_json_exact(retained_itc):
    expected = [project_itc_parameter_return(retained_itc["stored"][ref], source_ref=ref) for ref in (ORIGINAL, SAVED)]
    before = _canonical(expected)
    assert expected == retained_itc["rich_groups"]
    assert expected[0]["kd"]["value"] == 2.999999999999987e-6 and expected[1]["kd"]["value"] == 6e-6
    for value in expected:
        assert select_itc_binding_result(value) == value
        text = render_itc_binding_result(value, 1)
        assert "supplied_assertion" in text and "not_assessed" in text
        assert value["source_ref"] in text
    assert _canonical(expected) == before


def test_authentic268_scientific_instructions_and_current_session_frames(retained_itc, tmp_path):
    session = _session(tmp_path / "native-message-views")
    previous, rendered = None, []
    for record in retained_itc["scientific"]:
        context, turn = record["context"], record["turn"]
        question = retained_itc["delivery"]["question"]
        assert turn["text"].startswith("TASK") and "STEERING" in turn["text"] and question in turn["text"]
        state = instructional_model_context(context)
        text, instructions = session._presentation(turn["episode_id"], "REASONING", turn["instructions"], state_frame(state, previous))
        assert text.startswith("TASK") and "STEERING" in text and question in text
        assert instructions == turn["instructions"] and instructions in text
        for info in context["scientific_process"]["child_tool_info"]:
            for field in ("name", "description", "instructions"):
                assert info[field] in text and info[field] in turn["text"]
        if context["last_local_outcome"] is not None:
            assert render_itc_binding_result(context["last_local_outcome"]["result"], 1) in text
        rendered.append(text)
        previous = state
    last = retained_itc["scientific"][-1]
    continuation, _ = session._presentation(last["turn"]["episode_id"], "REASONING",
        last["turn"]["instructions"], state_frame(previous, previous))
    assert continuation == rendered[-1]


def test_current_rich_parent_session_uses_real_readside_instructions(retained_itc, tmp_path, monkeypatch):
    """Current reconstruction only;397 did not capture dispatch instructions."""
    directory = tmp_path / "current-readside"
    state = directory / "state"
    state.mkdir(parents=True)
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        retained_itc["db"].backup(destination)
        assert _tables(destination) == retained_itc["before"]
    finally:
        destination.close()
    run = directory / "run"
    shutil.copytree(retained_itc["rich"] / "rich-run", run, symlinks=True)
    original_run = _inventory(run)
    store = Store(state)
    try:
        monkeypatch.setattr(store, "get_artifact", _forbidden)
        descriptor = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(run / "scientific-process-library"),
            tool_library=ScientificToolLibrary(run / "scientific-tool-library"), child_roles=["scientific_process"]).as_record()
        initial = [ref for source in retained_itc["sources"].values() for ref in
            (source["id"], source["artifact_ref"], *source["auxiliary_artifact_refs"])]
        flow = Workflow(store, ToolRegistry(store), object(), run, "retained-itc-parameter-forms",
            lambda path, credit: FixtureController(str(path), credit,
                2 if len(path) == 1 else 3 if path[-1][1] == "child_0" else 1),
            lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True, initial_known_record_refs=initial)
        constructor = _assert_original_rows(store.db, retained_itc["before"])
        initialized = _tables(store.db)
        context = EpisodeReturnRecords(store, flow.run_id, failure_prefix="itc_presentation_").context(retained_itc["parent_episode_id"])
        assert context.role == "annotation"
        source = _source_for_original_context(flow, context)
        current = deepcopy(retained_itc["receiver"])
        instructions = source.instructions(current)
        text, actual = _session(tmp_path / "rich-parent-message")._presentation(context.episode_id,
            "REASONING", instructions, state_frame(instructional_model_context(current)))
        assert text.startswith("TASK") and "STEERING" in text and current["goal"]["objective"] in text
        assert actual == instructions and instructions in text
        for index, value in enumerate(retained_itc["rich_groups"], 1):
            assert render_itc_binding_result(value, index) in text
        assert _tables(store.db) == initialized
        current_files = _inventory(run)
        assert all(current_files.get(name) == pin for name, pin in original_run.items())
        (tmp_path / "ITC_CURRENT_RECEIVER_PRESENTATION.json").write_text(json.dumps(dict(
            version="itc_current_receiver_presentation_v1", passed=True, historical_instruction_wire_claimed=False,
            current_instruction_composition_verified=True, full_new_decision_builder_verified=False,
            constructor=constructor, context_sha256=_sha(_canonical(current).encode()),
            wire_sha256=_sha(text.encode()), no_new_models_actions_observations=True), indent=2) + "\n")
    finally:
        store.close()


def test_actual_partial_packet_does_not_invent_parameter_or_zero_fit_claims(retained_itc):
    value = retained_itc["packets"][0]
    assert "source_ref" not in value and "parameters" not in value and "this_operation_fit" not in value
    assert value["retained_sources"] and any(row["source_ref"] == ORIGINAL for row in value["retained_sources"])
    text = render_itc_binding_result(value, 1)
    assert "selected projection is unavailable" in text and "Retained parameter vector" not in text
    assert "do not supply missing parameter or injection cells" in text
    assert _values(retained_itc["delivery"]["outcomes"][0])


@pytest.mark.parametrize("kind", ["classified_non_square", "empty_matrix"])
def test_engineered_covariance_shape_and_nonfinite_states_stay_literal(retained_itc, kind):
    value = _native_view(retained_itc)
    value["covariance_estimate"] = ([] if kind == "empty_matrix" else [[], [
        dict(state="nan", value=None), dict(state="positive_infinity", value=None),
        dict(state="negative_infinity", value=None), dict(state="finite", value=0.0)], [], []])
    assert select_itc_binding_result(value) == value
    text = render_itc_binding_result(value, 1)
    assert "not_assessed" in text and "not standard errors, confidence intervals" in text
    if kind == "classified_non_square":
        assert all(word in text for word in ("nan", "positive_infinity", "negative_infinity", "0.0", "undeclared axis"))
        assert "Recorded empty native row ordinals: [0, 2, 3]" in text
    else:
        assert "[]" in text


@pytest.mark.parametrize("kind", ["unknown_version", "invalid_unit"])
def test_unknown_or_malformed_packet_keeps_existing_literal_fallback(retained_itc, kind):
    value = deepcopy(retained_itc["packets"][1])
    if kind == "unknown_version":
        value["version"] = "unrecognized_itc_values_v1"
    else:
        value["parameters"]["kd"]["unit"] = "unrecognized_unit"
    assert select_itc_binding_result(value) is None
    shown, packets = _selected_molecular_view(value)
    assert shown == value and packets == []
    with pytest.raises(ValueError, match="itc_binding_presentation_invalid"):
        render_itc_binding_result(value, 1)


def test_complete_view_dedup_source_and_order_identity_do_not_alias_inputs(retained_itc):
    value = _native_view(retained_itc)
    reordered = _native_view(retained_itc, (0, 31))
    # Engineered shape-only Source control; this does not authenticate another producer.
    other_source = deepcopy(value)
    other_source["source_ref"] = SAVED
    for location in other_source["warning_locations"]:
        location["source_ref"] = SAVED
    if other_source["failure_location"] is not None:
        other_source["failure_location"]["source_ref"] = SAVED
    state = dict(child_reports=[{"itc": [value, value, reordered, other_source]}])
    before = deepcopy(state)
    _, packets = _selected_molecular_view(state)
    assert packets == [value, reordered, other_source] and state == before
    packets[0]["parameters"]["kd"]["value"] = 123
    assert state == before
    # Display validation adds no new positivity restriction to finite supplied cells.
    boundary = deepcopy(value)
    boundary["parameters"]["kd"]["value"] = 0
    boundary["parameters"]["n"]["value"] = -1
    assert select_itc_binding_result(boundary) == boundary


def test_native_file_two_fields_and_other_functional_file_four_fields_survive(retained_itc):
    packet = retained_itc["packets"][1]
    assert set(packet["native_file"]) == {"artifact_ref", "format"}
    file = deepcopy(retained_itc["stored"][ORIGINAL]["request"]["input_file"])
    assert set(file) == {"artifact_ref", "sha256", "size_bytes", "format"}
    assert file["artifact_ref"] == retained_itc["delivery"]["input_artifact"]
    value = dict(child_reports=[dict(result=packet, explicitly_supplied_file=file)])
    shown, packets = _selected_molecular_view(value)
    assert shown["child_reports"][0]["explicitly_supplied_file"] == file
    text = _values(value)
    assert file["sha256"] in text and packet["native_file"]["artifact_ref"] in text
    assert len(packets) == 1 and packets[0]["native_file"] == packet["native_file"]


def test_engineered_warning_failure_locations_expose_no_native_messages(retained_itc):
    value = _native_view(retained_itc)
    value["warning_locations"] = [dict(source_ref=ORIGINAL, location="fit_warning", occurrence=i) for i in range(2)]
    value["failure_location"] = dict(source_ref=ORIGINAL, location="fit_failure", occurrence=0)
    assert select_itc_binding_result(value) == value
    text = render_itc_binding_result(value, 1)
    assert "fit_warning" in text and "fit_failure" in text
    assert "exception_message" not in text and "python_executable" not in text and "implementation_files" not in text
