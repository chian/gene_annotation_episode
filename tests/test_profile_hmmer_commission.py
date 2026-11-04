"""One new SCI-to-HMMER Results commission over a real retained handoff.

206 had an annotation/launch/API/Results Workflow and no SCI. This test freezes
current published process/tool libraries and creates a genuinely new commission;
it neither reconstructs historical SCI guidance nor repeats result acquisition.
The existing prepared-FASTA identity authentication remains enabled.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_reports import SOURCE as PROCESS_SOURCE
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_interval_pending_results import _commission, _new_rows
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha, _source_for_original_context, _tables,
)
from test_native_hmmer_preparation_nested_workflow import provider_value
from test_profile_api_presentation import _controller, _forbidden, _guards, _neutral


_GATE = "HMMER_NATIVE_ORACLE_HMMER_API_COMMISSION_CASE_JSON"
_INVENTORY = "d40b05fcb70b8e881bd3ed2139e1354db889719a5179a6ef517bf43e559692c6"
_DB = ("ef22dcd2001a2a34634681ce7a8383984e7916435ec2ee243ed8b8433cfd5ef5", 10203136)
_ROOT_ARCHIVE = ("a8dba193100c8b3f94f1552bfaadd9e85272f5b60c5921bdae98368fc3f817e4.json",
    "7c807eee8784ea7212348237f9766f72a94b7cf3b211c4ffc17f1ffdb99c188b", 24061)
_HANDOFF = "source_125659d31373e2d44c2e5558"
_HANDOFF_ARTIFACT = ("7387d9d381d1f900afca9059c1c8c8bc5d2090d4891cfcc62d58343f1cc4a593", 2695)
_QUESTION = "Obtain the selected original HMMER domain measurements"
_PUBLICATION = Path(__file__).resolve().parents[1] / "research/slotted_process_library/publications/2026-10-24-001"
_SLOTS = {
    "A101": ("41b90f160ff14f6ac9ae5eff4c5c7f3f83c0d28af8088677e240f18f72958c9e", 12697),
    "P01": ("218ae82b4ba0d56e6cdd1e050f432b8ebfb544efc2586abf4634062f6e56731b", 4769),
}


def _json(path, sha, size):
    raw = path.read_bytes()
    assert _sha(raw) == sha and len(raw) == size
    return json.loads(raw)


def _archive(directory, reference):
    """Follow only the authenticated archive's literal direct child edge."""
    assert set(reference) == {"$archive"}
    selected = reference["$archive"]
    assert set(selected) == {"file", "sha256", "index_sha256"}
    name = selected["file"]
    assert type(name) is str and Path(name).name == name and name.endswith(".json")
    path = directory / name
    raw = path.read_bytes()
    index = path.with_name(path.stem + ".index.json").read_bytes()
    assert _sha(raw) == selected["sha256"] and _sha(index) == selected["index_sha256"]
    return json.loads(raw)


class PendingHMMERAPICaptured(RuntimeError):
    pass


class UnexpectedHMMERAPIFeedback(RuntimeError):
    pass


def test_new_scientific_parent_commissions_retained_hmmer_results_without_acquisition(tmp_path, monkeypatch):
    raw = os.environ.get(_GATE)
    if not raw:
        pytest.skip("requires the explicitly pinned authentic206 phmmer Workflow family")
    supplied = json.loads(raw)
    assert set(supplied) == {"directory", "inventory_sha256"} and supplied["inventory_sha256"] == _INVENTORY
    original = Path(supplied["directory"]).resolve(strict=True)
    inventory = _inventory(original)
    assert _sha(_canonical(inventory).encode()) == _INVENTORY
    _guards(monkeypatch)
    monkeypatch.setattr(ToolRegistry, "publish_hmmer_result", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.hmmer_search_inputs.parse_hmmer_api_result", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.hmmer_search_inputs.build_hmmer_search_sheet", _forbidden)
    # Copy every physical member before the first SQLite connection. Original
    # databases are hashed/copied only; neither URI nor Store opens an original.
    retained = tmp_path / "retained206"
    shutil.copytree(original, retained, symlinks=True)
    assert _inventory(retained) == inventory
    database = retained / "state/state.sqlite3"
    assert (_sha(database.read_bytes()), database.stat().st_size) == _DB
    for suffix in ("-wal", "-shm"):
        assert not database.with_name(database.name + suffix).exists()
    archived = _json(retained / "run/archive" / _ROOT_ARCHIVE[0], *_ROOT_ARCHIVE[1:])
    assert archived["scope_level"] == "annotation" and archived["request"]["goal"]["objective"] == _QUESTION
    archive_directory = retained / "run/archive"
    launch = _archive(archive_directory, archived["units"][0]["child"])
    api = _archive(archive_directory, launch["units"][0]["child"])
    result = _archive(archive_directory, archived["units"][1]["child"])
    returned = _archive(archive_directory, archived["units"][0]["child_result"])
    assert returned["form"]["references"] == [_HANDOFF]
    assert api["scope_level"] == "launch_api" and result["scope_level"] == "results"
    assert all(_archive(archive_directory, unit["child"])["scope_level"] != "scientific_process"
        for unit in archived["units"])
    assignment = api["request"]["message"]["episode_assignment"]
    scope = api["request"]["message"]["scope"]
    assert assignment == dict(version="api_execution_assignment_v1", resource_id="ebi", service="ebi_hmmer",
        subject_ref="input_d14dec7a2167972e3147cee9", algorithm="phmmer", database="pdb", parameters={},
        page_size=2, endpoint="usable_handoff", constraints={})
    assert scope == dict(subject_refs=[assignment["subject_ref"]])
    handoff_sha, handoff_size = _HANDOFF_ARTIFACT
    body = _json(retained / "state/artifacts" / handoff_sha[:2] / handoff_sha, handoff_sha, handoff_size)
    assert body["assignment"] == assignment and body["episode_id"] == api["episode_id"]
    assert body["scope"] == scope and body["run_id"] == archived["run_id"] == "hmmer-grading-typed-api"
    run_id = body["run_id"]
    owned_db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    owned_db.row_factory = sqlite3.Row
    store = None
    initialized = None
    calls, pending = [], {}
    proof = dict(version="hmmer_api_current_pending_commission_v1", passed=False,
        historical_scientific_parent_claimed=False, old_replay_claimed=False,
        real_model_calls=0, http_calls=0, result_parser_calls=0, calculator_calls=0,
        publication_calls=0, native_calls=0, prepared_fasta_identity_authentication_enabled=True)
    try:
        old_tables = _tables(owned_db)
        result_commission = _commission(owned_db, run_id, result["episode_id"], "results")
        assert result_commission["request"] == result["request"]
        assert result_commission["selected"]["assignment"] == dict(version="execution_results_assignment_v1",
            handoff_ref=_HANDOFF, selector=dict(page=1))
        current_root = tmp_path / "new-current-commission"
        state = current_root / "state"
        state.mkdir(parents=True)
        destination = sqlite3.connect(state / "state.sqlite3")
        try:
            owned_db.backup(destination)
            assert _tables(destination) == old_tables
        finally:
            destination.close()
        shutil.copytree(retained / "state/artifacts", state / "artifacts")
        run = current_root / "run"
        run.mkdir()
        # These original immutable manuals stay literal. The new process/tool
        # libraries did not exist in206 and are frozen from current authorities.
        for name in ("tool-knowledge", "launch-instructions"):
            shutil.copytree(retained / "run" / name, run / name, symlinks=True)
        publication_before = _inventory(_PUBLICATION)
        for name, (sha, size) in _SLOTS.items():
            entry = _json(_PUBLICATION / "entries" / (name + ".json"), sha, size)
            assert entry["id"] == name
        process_library = ScientificProcessLibrary.freeze(run / "scientific-process-library", source=_PUBLICATION)
        factory = ExecutionServiceFactory({"ebi": {"kind": "hmmer_api"}}, {}, 3, 2, .5)
        store = Store(state)
        registry = ToolRegistry(store)
        application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
        tool_library = ScientificToolLibrary.freeze(run / "scientific-tool-library", catalog=registry.catalog(),
            tool_info=True, resource_catalogs=application.resource_tool_catalogs)
        tool_selection = [{"name": "api.hmmer.result", "resources": "api"}]
        tool_info = tool_library.resolve_tool_info(tool_selection)
        assert len(tool_info) == 1 and set(tool_info[0]) == {"name", "description", "resources", "instructions"}
        scientific = ScientificProcessEpisodes(None, library=process_library, tool_library=tool_library,
            child_roles=("scientific_process", "results"))
        descriptor = scientific.as_record()
        source_schema = scientific.fact_sources("scientific_process")[PROCESS_SOURCE]["report_schema"]
        process_form = dict(type="object", properties={"processes": source_schema},
            required=["processes"], additionalProperties=False)
        scientific_choice = dict(kind="episode_child", role="scientific_process", goal=_QUESTION, scope=deepcopy(scope),
            purpose="Retain the selected original process and its qualified continuation state",
            assignment=dict(selection=dict(version="scientific_process_selection_v3",
                evidence_axis=process_library.reference("A101"), thought_pattern=process_library.reference("P01"),
                child_tool_info=tool_selection), evidence_refs=[_HANDOFF], constraints={}, context={}),
            schema_json=json.dumps(process_form), initial_report_json="{}")
        session = _session(tmp_path / "pending-hmmer-session")

        class Choices:
            async def complete(self, episode_id, role, instructions, current, schema):
                calls.append(dict(episode_id=episode_id, role=role, instructions=instructions, context=deepcopy(current)))
                if current.get("feedback"):
                    raise UnexpectedHMMERAPIFeedback("unexpected HMMER commissioning feedback: " + _canonical(plain(current["feedback"])))
                state = instructional_model_context(current)
                wire, actual = session._presentation(episode_id, role, instructions, state_frame(state))
                calls[-1]["wire"] = wire
                if current.get("execution_assignment", {}).get("version") == "execution_results_assignment_v1":
                    assert len(calls) == 3 and current["execution_assignment"] == result_commission["selected"]["assignment"]
                    assert current["requested_form"] == result["request"]["report_contract"]["measurements"]["schema"]
                    assert current["execution_target"]["assignment"] == assignment
                    assert current["execution_target"]["handle"] == _HANDOFF
                    task = current["selected_execution_task"]
                    assert task["scientific_question"] == _QUESTION and task["selected_tool_info"] == tool_info
                    assert task["requests"][0]["job"] == assignment and task["requests"][0]["resource_kind"] == "api"
                    assert task["selector"] == {"page": 1}
                    assert current["last_local_outcome"] is None and current["child_reports"] == []
                    assert wire.startswith("TASK") and "STEERING" in wire and actual == instructions
                    assert all(info["description"] in wire and info["instructions"] in wire for info in tool_info)
                    assert all(token in wire for token in (_QUESTION, assignment["subject_ref"], "phmmer", "pdb", "page_size"))
                    assert all(token not in wire for token in (str(original), str(retained), "hmmer_search_sheet_v1", "hmmer_search_scores_v1"))
                    repeated, actual = session._presentation(episode_id, role, instructions, state_frame(state, state))
                    assert repeated == wire and actual == instructions
                    pending.update(episode_id=episode_id, context=deepcopy(current), wire=wire)
                    raise PendingHMMERAPICaptured("before first HMMER result selection")
                choice = result_commission["selected"] if "scientific_process" in current else scientific_choice
                if "scientific_process" in current:
                    assert current["scientific_process"]["child_tool_info"] == tool_info
                answer = provider_value({"selection": deepcopy(choice), "report_update": {}}, plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        flow = Workflow(store, registry, Choices(), run, run_id, controller_factory=_controller, project_credit=_neutral,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=[_HANDOFF], episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        source = store.get(_HANDOFF)
        assert source["artifact_ref"] == "artifact_" + handoff_sha
        assert store.get_artifact(source["artifact_ref"]) == (retained / "state/artifacts" / handoff_sha[:2] / handoff_sha).read_bytes()
        constructor = _assert_original_rows(store.db, old_tables)
        initialized = _tables(store.db)
        before_files = _inventory(current_root)
        episode = flow.build("annotation", "current-hmmer-api-pending206", _QUESTION, scope)
        with pytest.raises(PendingHMMERAPICaptured, match="before first HMMER result selection"):
            asyncio.run(episode.run_async(flow.context))
        assert len(calls) == 3 and pending
        added = _new_rows(initialized, _tables(store.db))
        assert len(added["runtime_episodes"]) == 3 and len(added["runtime_actions"]) == 2
        assert len(added["runtime_model_calls"]) == 3 and len(added["api_execution_episodes"]) == 1
        for name in ("records", "artifacts", "tool_operations", "runtime_forms", "runtime_report_attempts", "runtime_observations",
                "api_execution_actions", "api_execution_preparations", "api_execution_observations"):
            assert added[name] == []
        records = EpisodeReturnRecords(store, run_id, failure_prefix="hmmer_api_pending_")
        context = records.context(pending["episode_id"])
        owner = flow.specialist(_source_for_original_context(flow, context))
        assert owner._target(context)["assignment"] == assignment
        assert _HANDOFF in set(flow.receipts.known(context.episode_id))
        current_files = _inventory(current_root)
        for name, pin in before_files.items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert current_files[name] == pin
        assert _inventory(_PUBLICATION) == publication_before
        proof.update(passed=True, constructor=constructor, full_current_results_builder_verified=True,
            question=_QUESTION, original_assignment=assignment, original_handoff=_HANDOFF,
            original_result_request=result["request"], current_scientific_binding=descriptor,
            current_scientific_selection=scientific_choice, current_tool_info=tool_info,
            actual_new_row_counts={name: len(rows) for name, rows in added.items()})
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"] = calls
        if store is not None:
            if initialized is not None:
                proof["actual_new_rows"] = _new_rows(initialized, _tables(store.db))
            store.close()
        assert _tables(owned_db) == old_tables and owned_db.total_changes == 0
        owned_db.close()
        assert _inventory(retained) == inventory and _inventory(original) == inventory
        (tmp_path / "HMMER_API_CURRENT_PENDING_COMMISSION.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")


def test_new_scientific_parent_reaches_hmmer_launch_api_before_first_tool(tmp_path, monkeypatch):
    raw = os.environ.get(_GATE)
    if not raw:
        pytest.skip("requires the explicitly pinned authentic206 phmmer Workflow family")
    supplied = json.loads(raw)
    assert set(supplied) == {"directory", "inventory_sha256"} and supplied["inventory_sha256"] == _INVENTORY
    original = Path(supplied["directory"]).resolve(strict=True)
    inventory = _inventory(original)
    assert _sha(_canonical(inventory).encode()) == _INVENTORY
    _guards(monkeypatch)
    monkeypatch.setattr(ToolRegistry, "publish_hmmer_result", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.hmmer_search_inputs.parse_hmmer_api_result", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.hmmer_search_inputs.build_hmmer_search_sheet", _forbidden)
    retained = tmp_path / "retained206-launch"
    shutil.copytree(original, retained, symlinks=True)
    assert _inventory(retained) == inventory
    database = retained / "state/state.sqlite3"
    assert (_sha(database.read_bytes()), database.stat().st_size) == _DB
    for suffix in ("-wal", "-shm"):
        assert not database.with_name(database.name + suffix).exists()
    archived = _json(retained / "run/archive" / _ROOT_ARCHIVE[0], *_ROOT_ARCHIVE[1:])
    archive_directory = retained / "run/archive"
    launch = _archive(archive_directory, archived["units"][0]["child"])
    api = _archive(archive_directory, launch["units"][0]["child"])
    run_id = archived["run_id"]
    assert run_id == "hmmer-grading-typed-api" and archived["request"]["goal"]["objective"] == _QUESTION
    assignment = api["request"]["message"]["episode_assignment"]
    scope = api["request"]["message"]["scope"]
    assert assignment["algorithm"] == "phmmer" and assignment["database"] == "pdb"
    assert scope == {"subject_refs": [assignment["subject_ref"]]}
    owned_db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
    owned_db.row_factory = sqlite3.Row
    store = None
    initialized = None
    calls, pending = [], {}
    proof = dict(version="hmmer_api_current_pending_launch_verification_v1", passed=False,
        historical_scientific_parent_claimed=False, old_replay_claimed=False,
        real_model_calls=0, http_calls=0, native_calls=0, result_parser_calls=0,
        calculator_calls=0, publication_calls=0, new_handoff_claimed=False)
    try:
        old_tables = _tables(owned_db)
        launch_commission = _commission(owned_db, run_id, launch["episode_id"], "launch")
        api_commission = _commission(owned_db, run_id, api["episode_id"], "launch_api")
        assert launch_commission["request"] == launch["request"]
        assert api_commission["request"] == api["request"]
        assert launch_commission["selected"]["assignment"]["requests"] == {"ebi": assignment}
        assert api_commission["selected"]["assignment"] == assignment
        current_root = tmp_path / "new-current-launch"
        state = current_root / "state"
        state.mkdir(parents=True)
        destination = sqlite3.connect(state / "state.sqlite3")
        try:
            owned_db.backup(destination)
            assert _tables(destination) == old_tables
        finally:
            destination.close()
        shutil.copytree(retained / "state/artifacts", state / "artifacts")
        run = current_root / "run"
        run.mkdir()
        for name in ("tool-knowledge", "launch-instructions"):
            shutil.copytree(retained / "run" / name, run / name, symlinks=True)
        publication_before = _inventory(_PUBLICATION)
        for name, (sha, size) in _SLOTS.items():
            assert _json(_PUBLICATION / "entries" / (name + ".json"), sha, size)["id"] == name
        process_library = ScientificProcessLibrary.freeze(run / "scientific-process-library", source=_PUBLICATION)
        factory = ExecutionServiceFactory({"ebi": {"kind": "hmmer_api"}}, {}, 3, 2, .5)
        store = Store(state)
        registry = ToolRegistry(store)
        application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
        tool_library = ScientificToolLibrary.freeze(run / "scientific-tool-library", catalog=registry.catalog(),
            tool_info=True, resource_catalogs=application.resource_tool_catalogs)
        tool_selection = [{"name": name, "resources": "api"} for name in
            ("api.hmmer.prepare", "api.hmmer.submit", "api.hmmer.check_handoff")]
        tool_info = tool_library.resolve_tool_info(tool_selection)
        assert len(tool_info) == 3 and all(set(row) == {"name", "description", "resources", "instructions"}
            for row in tool_info)
        scientific = ScientificProcessEpisodes(None, library=process_library, tool_library=tool_library,
            child_roles=("scientific_process", "launch"))
        descriptor = scientific.as_record()
        process_form = dict(type="object", properties={"processes":
            scientific.fact_sources("scientific_process")[PROCESS_SOURCE]["report_schema"]},
            required=["processes"], additionalProperties=False)
        scientific_choice = dict(kind="episode_child", role="scientific_process", goal=_QUESTION, scope=deepcopy(scope),
            purpose="Retain the selected original process and its qualified continuation state",
            assignment=dict(selection=dict(version="scientific_process_selection_v3",
                evidence_axis=process_library.reference("A101"), thought_pattern=process_library.reference("P01"),
                child_tool_info=tool_selection), evidence_refs=[assignment["subject_ref"]], constraints={}, context={}),
            schema_json=json.dumps(process_form), initial_report_json="{}")
        session = _session(tmp_path / "pending-hmmer-launch-session")

        class Choices:
            async def complete(self, episode_id, role, instructions, current, schema):
                calls.append(dict(episode_id=episode_id, role=role, instructions=instructions, context=deepcopy(current)))
                if current.get("feedback"):
                    raise UnexpectedHMMERAPIFeedback("unexpected HMMER launch feedback: " + _canonical(plain(current["feedback"])))
                state = instructional_model_context(current)
                wire, actual = session._presentation(episode_id, role, instructions, state_frame(state))
                calls[-1]["wire"] = wire
                execution = current.get("execution_assignment", {})
                if execution.get("version") in {"execution_launch_assignment_v1", "api_execution_assignment_v1"}:
                    expected = launch_commission if execution["version"] == "execution_launch_assignment_v1" else api_commission
                    assert execution == expected["selected"]["assignment"]
                    assert current["requested_form"] == expected["request"]["report_contract"]["measurements"]["schema"]
                    task = current["selected_execution_task"]
                    assert task["scientific_question"] == _QUESTION and task["selected_tool_info"] == tool_info
                    assert task["requests"][0]["job"] == assignment and task["requests"][0]["resource_kind"] == "api"
                    assert task["selector"] is None
                    assert current["last_local_outcome"] is None and current["child_reports"] == []
                    assert wire.startswith("TASK") and "STEERING" in wire and actual == instructions
                    assert all(info["description"] in wire and info["instructions"] in wire for info in tool_info)
                    assert all(token in wire for token in (_QUESTION, assignment["subject_ref"], "phmmer", "pdb", "page_size"))
                    assert all(token not in wire for token in (str(original), str(retained), "hmmer_search_sheet_v1", "hmmer_search_scores_v1"))
                    repeated, actual = session._presentation(episode_id, role, instructions, state_frame(state, state))
                    assert repeated == wire and actual == instructions
                    if execution["version"] == "api_execution_assignment_v1":
                        assert len(calls) == 4
                        assert current["api_execution_prepared_request"] is None
                        assert current["api_execution_job"] is None and current["api_execution_completion"] is None
                        pending.update(episode_id=episode_id, context=deepcopy(current), wire=wire)
                        raise PendingHMMERAPICaptured("before first HMMER API launch tool")
                    choice = api_commission["selected"]
                elif "scientific_process" in current:
                    assert current["scientific_process"]["child_tool_info"] == tool_info
                    choice = launch_commission["selected"]
                else:
                    choice = scientific_choice
                answer = provider_value({"selection": deepcopy(choice), "report_update": {}}, plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        flow = Workflow(store, registry, Choices(), run, run_id, controller_factory=_controller, project_credit=_neutral,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=[], episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        constructor = _assert_original_rows(store.db, old_tables)
        initialized = _tables(store.db)
        before_files = _inventory(current_root)
        episode = flow.build("annotation", "current-hmmer-api-launch206", _QUESTION, scope)
        with pytest.raises(PendingHMMERAPICaptured, match="before first HMMER API launch tool"):
            asyncio.run(episode.run_async(flow.context))
        assert len(calls) == 4 and pending
        added = _new_rows(initialized, _tables(store.db))
        assert len(added["runtime_episodes"]) == 4 and len(added["runtime_actions"]) == 3
        assert len(added["runtime_model_calls"]) == 4 and len(added["api_execution_episodes"]) == 1
        for name in ("records", "artifacts", "tool_operations", "runtime_forms", "runtime_report_attempts", "runtime_observations",
                "api_execution_actions", "api_execution_preparations", "api_execution_observations"):
            assert added[name] == []
        context = EpisodeReturnRecords(store, run_id, failure_prefix="hmmer_api_launch_").context(pending["episode_id"])
        assert context.role == "launch_api" and plain(context.assignment) == assignment
        assert _HANDOFF not in set(flow.receipts.known(context.episode_id))
        current_files = _inventory(current_root)
        for name, pin in before_files.items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert current_files[name] == pin
        assert _inventory(_PUBLICATION) == publication_before
        proof.update(passed=True, constructor=constructor, full_current_launch_and_api_builders_verified=True,
            question=_QUESTION, original_launch_request=launch["request"], original_api_request=api["request"],
            current_scientific_binding=descriptor, current_scientific_selection=scientific_choice,
            current_tool_info=tool_info, actual_new_row_counts={name: len(rows) for name, rows in added.items()})
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"] = calls
        if store is not None:
            if initialized is not None:
                proof["actual_new_rows"] = _new_rows(initialized, _tables(store.db))
            store.close()
        assert _tables(owned_db) == old_tables and owned_db.total_changes == 0
        owned_db.close()
        assert _inventory(retained) == inventory and _inventory(original) == inventory
        (tmp_path / "HMMER_API_CURRENT_PENDING_LAUNCH.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
