"""Fresh pending Results commissions over explicitly supplied old handoffs.

These are scripted engineering calls through the current Workflow. No old
commission is replayed, no relocated completed-worker authority is relaxed,
and the unanswered Results call stops before any tool selection.
"""
import asyncio
from collections import Counter
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import shutil
import sqlite3
import sys

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import validate_target
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import selector_selection
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha,
    _source_for_original_context, _tables, retained,
)


HANDOFFS = {
    "overlap_complete": "source_e9d83bac5878449642579894",
    "overlap_invalid_c": "source_1cb31997e49587a183cc32c9",
    "overlap_missing_stdout": "source_891e42e8813f06f9750afaad",
    "chromatin_weighted": "source_63876777ace6cc4b2f71f17e",
    "chromatin_insulation": "source_8bf6391cba7bbf39c0eb5b0e",
}
FIXTURE_FILES = {
    "verification/tool_graders_protein_structure_inputs_2026-10-27_386/fixture_helpers.py":
        (9593, "48ff94a3d0e94097c8df3c1c74fa786972477ba8d19f4abd81e2d1d5d7808c9c"),
    "verification/tool_graders_protein_structure_execution_2026-10-27_390/fixture_helpers.py":
        (8696, "da8a433ffe24165d787903b02ad6cd2f3b0e740a121cc3baae3303371d89e33d"),
    "verification/tool_graders_protein_structure_workflow_2026-10-27_410/fixture_helpers.py":
        (25729, "6405670c166657c0ae2bceb628fc2d4f430eef824a3e7c9526a55c3266207863"),
    "verification/tool_graders_genomic_overlap_native_driver_2026-10-27_427/fixture_helpers.py":
        (9948, "5bab7a5ba1a905c8909e372bd535b03e6d491dd54eba2813ba15dd7447538462"),
    "verification/tool_graders_genomic_overlap_workflow_2026-10-27_437/fixture_helpers.py":
        (21560, "57a40c56cef87d41dc19155cbf7dd5c0539e97ab1b58f32cc99e4829748ad61e"),
    "verification/tool_graders_chromatin_workflow_2026-10-27_451/fixture_helpers.py":
        (23541, "810684760292590357d147cb1d9b8568a7e8cb977648208eb30124400c8e317b"),
    "verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/WORKED_RECORDS.json":
        (678790, "d1002a156dac237954f0663c2f98a422b8e1258a69f8ad00aa9610f6ad9be82a"),
}
G1_FIELDS = ["unfiltered.native_pair_count", "unfiltered.pairwise_overlap_bp_sum",
    "unfiltered.intersection_union_bp", "unfiltered.combined_union_bp", "unfiltered.jaccard_bp",
    "selected.selected_pair_count", "selected.selected_pairwise_bp_sum"]


def _forbidden(*args, **kwargs):
    raise AssertionError("pending presentation attempted scientific/native/worker/HTTP/real-model work")


def _guard_work(monkeypatch):
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status",
            "collect", "cancel", "release"):
        monkeypatch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    for target in (
        "gene_annotation_episode.genomic_overlap_calculations.calculate_genomic_overlap_components",
        "gene_annotation_episode.chromatin_interaction_calculations.calculate_chromatin_components",
        "gene_annotation_episode.chromatin_interaction_calculations.calculate_contact_enrichment",
        "gene_annotation_episode.chromatin_interaction_calculations.calculate_insulation_components",
        "gene_annotation_episode.genomic_overlap_result_worker.run_genomic_overlap_result_worker",
        "gene_annotation_episode.chromatin_interaction_result_worker.run_chromatin_result_worker",
        "gene_annotation_episode.native_genomic_overlap_driver.run_genomic_overlap_driver",
        "gene_annotation_episode.native_chromatin_interaction_driver.run_chromatin_interaction_driver",
        "gene_annotation_episode.native_genomic_overlap_results.NativeGenomicOverlapResults.execute",
        "gene_annotation_episode.native_chromatin_interaction_results.NativeChromatinInteractionResults.execute",
        "gene_annotation_episode.acquisition.PublicClients._http",
        "socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
    ):
        monkeypatch.setattr(target, _forbidden)
    monkeypatch.setattr(_SessionConnection, "complete", _forbidden)
    monkeypatch.setattr(ToolRegistry, "execute_async", _forbidden)
    for name in ("put", "artifact", "commit_reasoning"):
        monkeypatch.setattr(Store, name, _forbidden)


def _fixture(case, monkeypatch):
    """Normal namespace imports of the exact original reusable functions."""
    root = (Path(__file__).parent / "retained_workflow_fixtures").resolve(strict=True)
    modules = {}
    for name, (size, sha) in FIXTURE_FILES.items():
        path = root / name
        raw = path.read_bytes()
        assert len(raw) == size and _sha(raw) == sha
        if path.suffix == ".py":
            logical = name.removesuffix(".py").replace("/", ".")
            modules[logical] = path
            previous = sys.modules.get(logical)
            if previous is not None:
                assert Path(previous.__file__).resolve() == path
    monkeypatch.syspath_prepend(str(root))
    family = ("tool_graders_genomic_overlap_workflow_2026-10-27_437" if case["name"].startswith("overlap_")
        else "tool_graders_chromatin_workflow_2026-10-27_451")
    logical = "verification." + family + ".fixture_helpers"
    module = import_module(logical)
    for name, path in modules.items():
        if name in sys.modules:
            assert Path(sys.modules[name].__file__).resolve() == path
            assert _sha(path.read_bytes()) == FIXTURE_FILES[str(path.relative_to(root))][1]
    assert Path(module.__file__).resolve() == modules[logical]
    return module


def _commission(db, run_id, episode_id, role):
    """Join literal original request/contract to its actual selected action."""
    row = db.execute("SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
        (run_id, episode_id)).fetchone()
    assert row is not None
    path, request = json.loads(row["path"]), json.loads(row["request"])
    assert path[-1][0] == role and path[-1][1].startswith("child_")
    index = int(path[-1][1].removeprefix("child_"))
    assert path[-1][1] == "child_" + str(index)
    parents = [parent for parent in db.execute("SELECT episode_id,path FROM runtime_episodes WHERE run_id=?", (run_id,))
        if json.loads(parent["path"]) == path[:-1]]
    assert len(parents) == 1
    action = db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
        (run_id, parents[0]["episode_id"], index)).fetchone()
    assert action is not None
    selected = json.loads(action["action"])
    assert selected["kind"] == "episode_child" and selected["role"] == role
    assert selected["scope"] == request["message"]["scope"]
    assert selected["goal"] == request["goal"]["objective"]
    assert selected["purpose"] == request["report_contract"]["decision"]
    assert json.loads(selected["schema_json"]) == request["report_contract"]["measurements"]["schema"]
    assert json.loads(selected["initial_report_json"]) == request["message"]["initial_report"] == {}
    assignment = deepcopy(request["message"]["episode_assignment"])
    if role == "scientific_process":
        assert assignment["selection"] == request["message"]["scientific_process"]["selection"]
        assignment["selection"] = selector_selection(assignment["selection"])
    assert assignment == selected["assignment"]
    return dict(episode_id=episode_id, request=request, selected=selected,
        parent_episode_id=parents[0]["episode_id"], decision_index=index)


def _native_meanings(case, assignment, target):
    selector = assignment["selector"]
    assert selector["mode"] == "native_result" and assignment["handoff_ref"] == HANDOFFS[case["name"]]
    job = target["assignment"]["requested_job"][case["domain"]["kind"]]
    request = job["request"]
    if case["name"].startswith("overlap_"):
        assert request["mode"] == "unstranded_outer_span"
        assert [row["set_key"] for row in request["region_sets"]] == ["A", "B", "C"]
        assert [row["comparison_key"] for row in request["comparisons"]] == ["AB", "AC", "BC"]
        assert selector["comparison_keys"] == ["AB", "AC", "BC"] and selector["saved_sheet_file"] is None
        assert selector["parameters"] == {"version": "genomic_overlap_calculation_parameters_v1",
            "minimum_overlap_bp": 1, "minimum_a_fraction": {"numerator": 0, "denominator": 1},
            "minimum_b_fraction": {"numerator": 0, "denominator": 1}}
        assert selector["projection"]["measurement_fields"] == G1_FIELDS
        return {row["source"]["file"]["artifact_ref"] for row in request["region_sets"]}
    assert selector["saved_sheet_bundle"] is None
    if case["name"] == "chromatin_weighted":
        assert [row["population_key"] for row in request["populations"]] == ["p0", "p1"]
        assert selector["population_keys"] == ["p1"]
        assert selector["parameters"]["normalization"] == {
            "kind": "precomputed_weighted", "convention": "multiplicative", "weight_column": "weight"}
        assert selector["parameters"]["contact"] == {"expectation": "same_population_distance_mean",
            "fold_threshold": 2, "minimum_separation_bins": 1,
            "missing_policy": "exclude_declared_masked_bins_require_complete_population",
            "threshold_comparison": "strict_gt"}
        assert "threshold0.5" in case["configuration"]["goal"]
    else:
        assert request["elements"] is None and selector["population_keys"] == ["p0"]
        assert selector["parameters"]["normalization"] == {"kind": "raw", "convention": None, "weight_column": None}
        assert selector["parameters"]["contact"] is None
        assert selector["parameters"]["insulation"] == {"window_bins": 1, "zscore_ddof": 0,
            "z_threshold": -1, "threshold_comparison": "strict_lt", "window_end_rule": "all_full_windows",
            "boundary_rule": "strict_two_neighbor_minimum", "missing_policy": "complete_window"}
    return {row["file"]["artifact_ref"] for row in job["input_bindings"]}


def _application(case, directory, provider, fixture, source, before):
    state = directory / "state"
    state.mkdir()
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        source.backup(destination)
        assert _tables(destination) == before
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
    original_binding = configuration["scientific_binding"]
    library = ScientificProcessLibrary(run / "scientific-process-library")
    tools = ScientificToolLibrary(run / "scientific-tool-library")
    assert library.as_record() == original_binding["configuration"]["library"]
    assert tools.as_record() == original_binding["configuration"]["tool_library"]
    configuration["scientific_binding"] = ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=original_binding["configuration"]["child_roles"]).as_record()
    assert configuration["scientific_binding"]["configuration"] == original_binding["configuration"]
    configuration["initial_refs"] = [HANDOFFS[case["name"]]]
    store = Store(state)
    try:
        flow, registry = fixture.assemble(store, directory, provider, configuration)
        constructor = _assert_original_rows(store.db, before)
        return dict(store=store, flow=flow, registry=registry, configuration=configuration,
            constructor=constructor, initialized=_tables(store.db), files=_inventory(directory))
    except BaseException:
        store.close()
        raise


def _new_rows(before, after):
    assert set(before) == set(after)
    result = {}
    for name, old in before.items():
        assert old["columns"] == after[name]["columns"] and old["sql"] == after[name]["sql"]
        first, second = Counter(map(_canonical, old["rows"])), Counter(map(_canonical, after[name]["rows"]))
        assert not first - second
        result[name] = [json.loads(row) for row, count in (second - first).items() for _ in range(count)]
    return result


class PendingResultsCaptured(RuntimeError):
    pass


def test_current_native_pending_results_uses_authentic_handoff_and_full_task(retained, tmp_path, monkeypatch):
    _guard_work(monkeypatch)
    fixture = _fixture(retained, monkeypatch)
    historical = tmp_path / "historical"
    shutil.copytree(retained["directory"], historical, symlinks=True)
    assert _inventory(historical) == retained["original_inventory"]
    source = sqlite3.connect((historical / "state/state.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    source.row_factory = sqlite3.Row
    case = dict(retained, historical=historical)
    before = _tables(source)
    captures = case["captures"]
    captured_results = captures["decision-5.json"]
    original_target = validate_target(captured_results["context"]["execution_target"])
    run_id = original_target["run_id"]
    assert run_id == fixture.RUN_ID
    science = _commission(source, run_id, captures["decision-1.json"]["episode_id"], "scientific_process")
    native = _commission(source, run_id, captured_results["episode_id"], "results")
    assert science["request"]["goal"]["objective"] == case["configuration"]["goal"]
    full_info = science["request"]["message"]["episode_assignment"]["selection"]["child_tool_info"]
    assert full_info == captures["decision-1.json"]["context"]["scientific_process"]["child_tool_info"]
    assert science["selected"]["assignment"] == captures["decision-1.json"]["context"]["scientific_process"]["assignment"]
    assert native["selected"]["assignment"] == captured_results["context"]["execution_assignment"]
    original_files = _native_meanings(case, native["selected"]["assignment"], original_target)
    original_get = Store.get_artifact

    def control_bytes_only(store, reference):
        assert reference not in original_files, "pending builder reopened an original scientific input File"
        return original_get(store, reference)

    monkeypatch.setattr(Store, "get_artifact", control_bytes_only)
    session = _session(tmp_path / "pending-results-presentation")
    calls, pending = [], {}

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            call = dict(episode_id=episode_id, role=role, instructions=instructions,
                context=deepcopy(current), schema=deepcopy(schema))
            calls.append(call)
            wire, model_instructions = session._presentation(episode_id, role, instructions, current)
            call.update(wire=wire, model_instructions=model_instructions)
            if current.get("execution_assignment", {}).get("version") == "execution_results_assignment_v1":
                assert len(calls) == 3
                assert current["execution_assignment"] == native["selected"]["assignment"]
                assert current["execution_target"] == original_target
                assert current["requested_form"] == json.loads(native["selected"]["schema_json"])
                assert current["requested_report_purpose"] == native["selected"]["purpose"]
                assert current["goal"]["objective"] == native["selected"]["goal"]
                task = current["selected_execution_task"]
                assert task["scientific_question"] == science["request"]["goal"]["objective"]
                assert task["selected_tool_info"] == full_info
                job = original_target["assignment"]["requested_job"][case["domain"]["kind"]]
                assert len(task["requests"]) == 1 and task["requests"][0]["job"] == case["domain"]["job"](job)
                assert task["selector"] == native["selected"]["assignment"]["selector"]
                assert wire.startswith("TASK") and "STEERING" in wire and task["scientific_question"] in wire
                assert instructions in wire and model_instructions == instructions
                for info in full_info:
                    assert info["name"] in wire and info["description"] in wire and info["instructions"] in wire
                assert current["last_local_outcome"] is None and current["child_reports"] == []
                assert current["execution_progress"]["execution_completed"] is False
                for source_name in fixture.SOURCES.values():
                    assert current["execution_progress"][source_name] == []
                pending.update(episode_id=episode_id, context=deepcopy(current), wire=wire)
                raise PendingResultsCaptured("current full Results builder reached before tool selection")
            if "scientific_process" in current:
                assert len(calls) == 2
                assert current["scientific_process"]["assignment"] == science["selected"]["assignment"]
                assert current["scientific_process"]["child_tool_info"] == full_info
                assert case["configuration"]["goal"] in wire
                for info in full_info:
                    assert info["description"] in wire and info["instructions"] in wire
                selected = native["selected"]
            else:
                assert len(calls) == 1 and current["scope"] == science["selected"]["scope"]
                selected = science["selected"]
            answer = fixture.provider_value({"selection": deepcopy(selected), "report_update": {}}, plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    proof = dict(version="interval_current_pending_results_verification_v1", case=case["name"], passed=False,
        original_inventory_sha256=_sha(_canonical(case["original_inventory"]).encode()),
        original481_full_builder_failures_preserved=True, historical_postcollect_context_claimed=False,
        legacy_closed_replay_claimed=False, saved_mode_verified=False,
        full_current_results_builder_verified=False, native_calls=0, calculation_calls=0,
        worker_calls=0, http_calls=0, real_model_calls=0, scientific_publications=0)
    app = None
    directory = tmp_path / "current-pending"
    directory.mkdir()
    try:
        app = _application(case, directory, Choices(), fixture, source, before)
        store, flow = app["store"], app["flow"]
        root = flow.build("annotation", "current-pending-" + case["name"], case["configuration"]["goal"],
            deepcopy(case["configuration"]["scope"]))
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
        assert [json.loads(row["action"]) for row in sorted(actions,
            key=lambda row: json.loads(row["action"])["role"])] == [native["selected"], science["selected"]]
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
        records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="interval_current_pending_")
        context = records.context(pending["episode_id"])
        owner = flow.specialist(_source_for_original_context(flow, context))
        result_owner = (owner.native_genomic_overlap_results if case["name"].startswith("overlap_")
            else owner.native_chromatin_interaction_results)
        assert result_owner.receipts.completed_receipts(context) == []
        assert owner._target(context) == original_target
        assert HANDOFFS[case["name"]] in set(flow.receipts.known(context.episode_id))
        files = _inventory(directory)
        for name, pin in app["files"].items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert files[name] == pin
        proof.update(passed=True, full_current_results_builder_verified=True,
            original_rows_unchanged=True, constructor=app["constructor"],
            original_scientific_request=science, original_native_request=native,
            original_scientific_binding=case["configuration"]["scientific_binding"],
            new_scientific_binding=app["configuration"]["scientific_binding"],
            initial_handoff_input=HANDOFFS[case["name"]], new_episode_ids=sorted(ids),
            new_framework_row_counts={name: len(rows) for name, rows in added.items()},
            new_framework_paths={name: pin for name, pin in files.items() if name not in app["files"]},
            scripted_completed_calls=2, unanswered_results_calls=1,
            current_context_sha256=_sha(_canonical(pending["context"]).encode()),
            current_wire_sha256=_sha(pending["wire"].encode()))
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["actual_scripted_provider_calls"] = len(calls)
        proof["calls"] = calls
        if app is not None:
            proof["actual_new_rows"] = _new_rows(app["initialized"], _tables(app["store"].db))
            app["store"].close()
        proof["original_historical_rows_unchanged"] = _tables(source) == before and source.total_changes == 0
        source.close()
        proof["original_historical_files_unchanged"] = _inventory(historical) == case["original_inventory"]
        proof["original_files_unchanged"] = _inventory(case["directory"]) == case["original_inventory"]
        (tmp_path / "INTERVAL_CURRENT_PENDING_RESULTS.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
        assert proof["original_historical_rows_unchanged"] and proof["original_historical_files_unchanged"] and proof["original_files_unchanged"]
