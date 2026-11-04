"""Current Rfam launch callbacks over authenticated retained inputs, without work.

The scripted choices commission new framework episodes in the original run.
They stop at the actual launch_api callback before any tool selection. Original
243 requests, libraries, histories, Files and completed results remain inputs;
this is neither historical wire replay nor another remote Rfam search.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import os
import shutil
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_prompt import is_api_launch_context
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_profile_api_presentation import (
    _CALLS, _GATE, _PINS, _controller, _guards, _json, _neutral,
)
from test_interval_pending_results import _commission, _new_rows
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha,
    _source_for_original_context, _tables,
)
from test_native_hmmer_preparation_nested_workflow import provider_value


@pytest.fixture
def retained_rfam243_launch(tmp_path):
    supplied = os.environ.get(_GATE)
    if not supplied:
        pytest.skip("requires the explicitly pinned243 profile API input")
    selection = json.loads(supplied)
    assert type(selection) is dict and "rfam243" in selection
    selected = selection["rfam243"]
    assert set(selected) == {"directory", "inventory_sha256"}
    assert selected["inventory_sha256"] == _PINS["rfam243"]
    original = Path(selected["directory"]).resolve(strict=True)
    inventory = _inventory(original)
    assert _sha(_canonical(inventory).encode()) == _PINS["rfam243"]
    copied = tmp_path / "retained-rfam243"
    with pytest.MonkeyPatch.context() as patch:
        _guards(patch)
        # Complete physical input is copied before the first SQLite connection.
        shutil.copytree(original, copied, symlinks=True)
        assert _inventory(copied) == inventory
        database = copied / "state/state.sqlite3"
        wal = database.with_name(database.name + "-wal")
        assert not wal.exists() or wal.stat().st_size == 0, "nonempty WAL needs consolidated authority"
        filename, sha, size = _CALLS["rfam243"]
        calls = _json(copied / filename, sha, size)
        db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
        db.row_factory = sqlite3.Row
        before = _tables(db)
        try:
            yield dict(original=original, directory=copied, inventory=inventory,
                calls=calls, db=db, tables=before)
            assert _tables(db) == before and db.total_changes == 0
        finally:
            db.close()
            assert _inventory(copied) == inventory
            assert _inventory(original) == inventory


class PendingRfamLaunchCaptured(RuntimeError):
    pass


def test_current_rfam_launch_and_launch_api_commissions_stop_before_first_tool(
        retained_rfam243_launch, tmp_path):
    case = retained_rfam243_launch
    db, old_calls = case["db"], case["calls"]
    science_call = next(call for call in old_calls if "scientific_process" in call["current"])
    launch_call, = [call for call in old_calls if call["current"].get("execution_assignment", {}).get("version")
        == "execution_launch_assignment_v1"]
    api_call, = [call for call in old_calls if call["current"].get("api_service") == "rfam_batch"]
    publication = json.loads((case["directory"] / "publication.json").read_text())
    run_id = publication["run_id"]
    science = _commission(db, run_id, science_call["episode_id"], "scientific_process")
    launch = _commission(db, run_id, launch_call["episode_id"], "launch")
    api = _commission(db, run_id, api_call["episode_id"], "launch_api")
    assert launch["parent_episode_id"] == science["episode_id"]
    assert api["parent_episode_id"] == launch["episode_id"]
    api_assignment = api["selected"]["assignment"]
    assert api_assignment == launch["selected"]["assignment"]["requests"]["rfam"]
    assert api_assignment == publication["target"]["assignment"]
    assert api_assignment["request"]["subject_refs"][0] == api_assignment["request"]["subject_refs"][1]
    old_binding = science["request"]["message"]["scientific_process"]["mechanics_binding"]

    directory = tmp_path / "current-rfam-launch"
    state = directory / "state"
    state.mkdir(parents=True)
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        db.backup(destination)
        assert _tables(destination) == case["tables"]
    finally:
        destination.close()
    shutil.copytree(case["directory"] / "state/artifacts", state / "artifacts")
    run = directory / "run"
    run.mkdir()
    for name in ("api-service-execution", "scientific-process-library", "scientific-tool-library",
            "tool-knowledge", "launch-instructions"):
        source = case["directory"] / "run" / name
        if source.exists():
            target = directory / "original-scientific-tool-library" if name == "scientific-tool-library" else run / name
            shutil.copytree(source, target, symlinks=True)
    original_library = ScientificToolLibrary(directory / "original-scientific-tool-library")
    process_library = ScientificProcessLibrary(run / "scientific-process-library")
    assert original_library.as_record() == old_binding["configuration"]["tool_library"]
    assert process_library.as_record() == old_binding["configuration"]["library"]
    original_info = original_library.resolve_tool_info(
        science["request"]["message"]["scientific_process"]["selection"]["child_tool_info"])
    assert original_info == science_call["current"]["scientific_process"]["child_tool_info"]
    factory = ExecutionServiceFactory({"rfam": dict(kind="api", service="rfam_batch", timeout=90.0)}, {}, 3, 2, .5)
    session = _session(tmp_path / "launch-session")
    calls, captured = [], {}
    current_info = current_science = None

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            assert len(calls) < 4, "unexpected additional scripted callback"
            assert not current.get("feedback"), current.get("feedback")
            model_state = instructional_model_context(current)
            wire, actual = session._presentation(episode_id, role, instructions, state_frame(model_state))
            repeated, repeated_instructions = session._presentation(
                episode_id, role, instructions, state_frame(model_state, model_state))
            assert repeated == wire and repeated_instructions == actual
            calls.append(dict(episode_id=episode_id, role=role, instructions=instructions,
                context=deepcopy(current), wire=wire, presented_instructions=actual))
            index = len(calls)
            if index == 1:
                assert "scientific_process" not in current and "execution_assignment" not in current
                chosen = current_science
            elif index == 2:
                assert current["scientific_process"]["child_tool_info"] == current_info
                assert current["goal"]["objective"] == science["selected"]["goal"]
                assert current["requested_form"] == json.loads(science["selected"]["schema_json"])
                chosen = launch["selected"]
            else:
                selected = launch if index == 3 else api
                expected_role = "launch" if index == 3 else "launch_api"
                assert current["execution_assignment"] == selected["selected"]["assignment"]
                assert current["goal"]["objective"] == selected["selected"]["goal"]
                assert current["scope"] == selected["selected"]["scope"]
                assert current["requested_form"] == json.loads(selected["selected"]["schema_json"])
                assert current["requested_report_purpose"] == selected["selected"]["purpose"]
                assert current["last_local_outcome"] is None and current["child_reports"] == []
                assert current["execution_progress"]["execution_completed"] is False
                task = current["selected_execution_task"]
                assert task["scientific_question"] == science["selected"]["goal"]
                assert task["selected_tool_info"] == current_info == original_info
                assert task["selector"] is None
                assert task["constraints"] == selected["selected"]["assignment"]["constraints"]
                request, = task["requests"]
                assert request["resource_id"] == "rfam" and request["resource_kind"] == "api"
                assert request["job"] == api_assignment
                assert request["endpoint"] == api_assignment["endpoint"]
                assert request["constraints"] == api_assignment["constraints"]
                assert wire.startswith("TASK") and "STEERING" in wire
                assert task["scientific_question"] in wire
                assert all(info["description"] in wire and info["instructions"] in wire for info in current_info)
                assert all(reference in wire for reference in api_assignment["request"]["subject_refs"])
                assert "rfam_batch_request_v2" in wire and "sequence_batch" in wire
                assert is_api_launch_context(current) is (expected_role == "launch_api")
                captured[expected_role] = deepcopy(calls[-1])
                if index == 4:
                    assert current["api_service"] == "rfam_batch"
                    assert current["api_request"] == api_assignment["request"]
                    assert current["api_execution_completed"] is False
                    assert "Selected API work" in wire
                    raise PendingRfamLaunchCaptured("before the first API tool selection")
                chosen = api["selected"]
            answer = provider_value({"selection": deepcopy(chosen), "report_update": {}}, plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    store = Store(state)
    proof = dict(version="rfam_current_launch_commission_verification_v1", passed=False,
        historical_wire_replay_claimed=False, native_calls=0, http_calls=0,
        calculator_calls=0, real_model_calls=0)
    initialized = None
    try:
        registry = ToolRegistry(store)
        application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
        current_library = ScientificToolLibrary.freeze(run / "scientific-tool-library", catalog=registry.catalog(),
            tool_info=True, resource_catalogs=application.resource_tool_catalogs)
        selectors = [{key: info[key] for key in ("name", "resources")} for info in original_info]
        current_info = current_library.resolve_tool_info(selectors)
        assert current_info == original_info
        descriptor = ScientificProcessEpisodes(None, library=process_library, tool_library=current_library,
            child_roles=old_binding["configuration"]["child_roles"]).as_record()
        current_science = deepcopy(science["selected"])
        current_science["assignment"]["selection"]["child_tool_info"] = selectors
        flow = Workflow(store, registry, Choices(), run, run_id, controller_factory=_controller, project_credit=_neutral,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=[], episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        constructor = _assert_original_rows(store.db, case["tables"])
        initialized = _tables(store.db)
        before_files = _inventory(directory)
        episode = flow.build("annotation", "current-profile-api-launch243",
            science["request"]["goal"]["task_context"]["root_objective"], science["selected"]["scope"])
        with pytest.raises(PendingRfamLaunchCaptured, match="before the first API tool selection"):
            asyncio.run(episode.run_async(flow.context))
        assert len(calls) == 4 and set(captured) == {"launch", "launch_api"}
        added = _new_rows(initialized, _tables(store.db))
        assert len(added["runtime_episodes"]) == 4 and len(added["runtime_actions"]) == 3
        assert len(added["runtime_model_calls"]) == 4
        for name in ("records", "artifacts", "tool_operations", "runtime_forms", "runtime_report_attempts",
                "runtime_observations", "api_execution_actions"):
            if name in added:
                assert added[name] == []
        episodes = [dict(zip(initialized["runtime_episodes"]["columns"], row)) for row in added["runtime_episodes"]]
        assert all(row["state"] == "active" and row["completion"] is row["archive"] is None for row in episodes)
        actions = [dict(zip(initialized["runtime_actions"]["columns"], row)) for row in added["runtime_actions"]]
        assert all(json.loads(row["action"])["kind"] == "episode_child" and row["result"] is None for row in actions)
        model_calls = [dict(zip(initialized["runtime_model_calls"]["columns"], row)) for row in added["runtime_model_calls"]]
        unanswered, = [row for row in model_calls if row["response"] is None]
        assert unanswered["episode_id"] == captured["launch_api"]["episode_id"]
        records = EpisodeReturnRecords(store, run_id, failure_prefix="rfam_launch_commission_")
        for role in ("launch", "launch_api"):
            context = records.context(captured[role]["episode_id"])
            assert context.role == role
            source = _source_for_original_context(flow, context)
            assert plain(context.assignment) == (launch if role == "launch" else api)["selected"]["assignment"]
            assert flow.specialist(source) is not None
        current_files = _inventory(directory)
        for name, pin in before_files.items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert current_files[name] == pin
        proof.update(passed=True, constructor=constructor,
            full_current_launch_builder_verified=True, full_current_launch_api_builder_verified=True,
            original_question=science["selected"]["goal"], original_tool_info=original_info,
            current_tool_info=current_info, original_binding=old_binding, current_binding=descriptor,
            original_launch_assignment=launch["selected"]["assignment"], original_api_assignment=api_assignment,
            actual_new_row_counts={name: len(rows) for name, rows in added.items()},
            original_rows_and_copied_files_unchanged=True)
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"] = calls
        try:
            if initialized is not None:
                proof["actual_new_rows"] = _new_rows(initialized, _tables(store.db))
        finally:
            store.close()
            (tmp_path / "RFAM_CURRENT_LAUNCH_COMMISSION.json").write_text(
                json.dumps(proof, indent=2, allow_nan=False) + "\n")
