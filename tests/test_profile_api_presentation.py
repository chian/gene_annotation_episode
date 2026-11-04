"""Retained profile API inputs at the current wire; never acquire or recalculate.

The captured-context controls construct the new detached TASK from authentic
243/245 inputs. They do not claim that those old calls dispatched this wire.
One separate fresh commission verifies the actual current builder and stops at
the pending Results decision, before any result tool can be selected.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_prompt import select_profile_api_execution_values
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_interval_pending_results import _commission, _new_rows
from test_interval_results_presentation import (
    _assert_original_rows, _canonical, _inventory, _session, _sha, _source_for_original_context, _tables,
)
from test_native_hmmer_preparation_nested_workflow import provider_value


_GATE = "HMMER_NATIVE_ORACLE_PROFILE_API_PRESENTATION_CASES_JSON"
_PINS = {
    "rfam243": "d9752e35e48ecb10c06f6080b46186c73297be1c3ed7ec361eacd7c473a3204b",
    "rfam245": "72f9fdac7260485d9cc2db8828944637a8b301891f010289a78a430f1fdb0d54",
}
_CALLS = {
    "rfam243": ("scripted-decisions.json", "321c4fccfd17ba113b8014a92838df0b4d0795fc8bc89e063df3c11fe90f1241", 2198176),
    "rfam245": ("model-calls.json", "826ed4f74f358c220cf1e3304734a1653b970073f728dcdab3821a2910da1e75", 1992016),
}
_HANDOFF = "source_4f1eae700defcccb644b0529"


def _forbidden(*args, **kwargs):
    raise AssertionError("profile API presentation attempted acquisition/native/calculation/model/publication work")


def _guards(patch):
    # Guard call boundaries, not transitive scientific-package imports.
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "status", "collect", "cancel", "release"):
        patch.setattr("gene_annotation_episode.native_lifecycle." + name, _forbidden)
    for name in (
        "gene_annotation_episode.acquisition.PublicClients._http",
        "gene_annotation_episode.rfam_batch_transport.RfamBatchHTTP._request",
        "gene_annotation_episode.api_execution.HMMERAPIExecution._http",
        "gene_annotation_episode.api_service_execution.APIServiceExecution.execute",
        "gene_annotation_episode.api_execution.HMMERAPIExecution.execute",
        "gene_annotation_episode.rfam_batch_publication.publish_rfam_batch_result",
        "gene_annotation_episode.rfam_batch_table.populate_rfam_batch_tblout_sheet",
        "gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet",
        "gene_annotation_episode.infernal_search_inputs.populate_infernal_search_sheet",
        "gene_annotation_episode.infernal_search_grader.calculate_infernal_search_scores",
        "gene_annotation_episode.hmmer_search_grader.calculate_hmmer_search_scores",
        "gene_annotation_episode.hmmer_graders.grade_hmmer_api_result",
        "socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
        "urllib.request.OpenerDirector.open", "subprocess.run", "subprocess.Popen",
    ):
        patch.setattr(name, _forbidden)
    patch.setattr(_SessionConnection, "complete", _forbidden)
    patch.setattr(ToolRegistry, "execute_async", _forbidden)
    patch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("put", "artifact", "commit_reasoning"):
        patch.setattr(Store, name, _forbidden)


def _json(path, sha, size):
    raw = path.read_bytes()
    assert len(raw) == size and _sha(raw) == sha
    return json.loads(raw)


@pytest.fixture(scope="module")
def api_cases(tmp_path_factory):
    raw = os.environ.get(_GATE)
    if not raw:
        pytest.skip("requires explicitly pinned authentic243/245 retained profile API inputs")
    supplied = json.loads(raw)
    assert set(supplied) == set(_PINS)
    directory = tmp_path_factory.mktemp("profile-api-inputs")
    cases = {}
    with pytest.MonkeyPatch.context() as patch:
        _guards(patch)
        # Every physical member is copied and compared before any SQLite open.
        for name, expected in _PINS.items():
            item = supplied[name]
            assert set(item) == {"directory", "inventory_sha256"} and item["inventory_sha256"] == expected
            original = Path(item["directory"]).resolve(strict=True)
            inventory = _inventory(original)
            assert _sha(_canonical(inventory).encode()) == expected
            copied = directory / name
            shutil.copytree(original, copied, symlinks=True)
            assert _inventory(copied) == inventory
            database = copied / "state/state.sqlite3"
            wal = database.with_name(database.name + "-wal")
            assert not wal.exists() or wal.stat().st_size == 0, "nonempty WAL needs consolidated authority"
            filename, sha, size = _CALLS[name]
            calls = _json(copied / filename, sha, size)
            inputs = json.loads((copied / "caller-selected-inputs.json").read_text())
            publication = json.loads((copied / "publication.json").read_text())
            returned = json.loads((copied / "results-return.json").read_text())
            history = json.loads((copied / "history.json").read_text())
            acquired, = [json.loads(row["result"]) for row in history["runtime_actions"]
                if row["episode_id"] == publication["episode_id"] and row["result"] is not None
                and "projection" in json.loads(row["result"]).get("result", {})]
            assert acquired["result"] == publication["publication_result"]
            assert publication["assignment"]["selector"] == inputs["selector"]
            scientific = next(call for call in calls if "scientific_process" in call["current"])
            results = [call for call in calls if call["current"].get("execution_assignment", {}).get("version")
                == "execution_results_assignment_v1"]
            assert results and all(call["current"]["execution_assignment"] == publication["assignment"] for call in results)
            assert returned["measurements"] == json.loads((copied / "scientific-return.json").read_text())["measurements"]
            cases[name] = dict(original=original, directory=copied, inventory=inventory,
                calls=calls, inputs=inputs, publication=publication, returned=returned,
                scientific=scientific, results=results, acquired=acquired)
        try:
            database = cases["rfam243"]["directory"] / "state/state.sqlite3"
            db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
            db.row_factory = sqlite3.Row
            cases["rfam243"].update(db=db, tables=_tables(db))
            yield cases
            assert _tables(db) == cases["rfam243"]["tables"] and db.total_changes == 0
        finally:
            if "db" in cases["rfam243"]:
                cases["rfam243"]["db"].close()
            for case in cases.values():
                assert _inventory(case["directory"]) == case["inventory"]
                assert _inventory(case["original"]) == case["inventory"]


def _selected_context(case, call):
    """Pure current presentation input; historical captures remain unchanged."""
    value = deepcopy(call["current"])
    assignment = case["publication"]["target"]["assignment"]
    science = case["scientific"]["current"]
    value["selected_execution_task"] = dict(version="selected_execution_task_v1",
        scientific_question=science["goal"]["objective"],
        selected_tool_info=deepcopy(science["scientific_process"]["child_tool_info"]),
        requests=[dict(resource_id=assignment["resource_id"], resource_kind="api",
            endpoint=assignment["endpoint"], constraints=deepcopy(assignment["constraints"]),
            job=deepcopy(assignment), resource=dict(resource_id=assignment["resource_id"],
                resource_kind="api", service="rfam_batch"))],
        constraints=deepcopy(value.get("execution_assignment", {}).get("constraints", {})),
        selector=deepcopy(value.get("execution_assignment", {}).get("selector")),
        result_description=deepcopy(value.get("execution_target_description")))
    return value


def _hmmer_assignment():
    return dict(version="api_execution_assignment_v1", resource_id="ebi", service="ebi_hmmer",
        subject_ref="input_0123456789abcdef01234567", algorithm="phmmer", database="pdb",
        parameters={"E": 1e-5, "domE": 0.01, "sequence_ref": "caller_selected_literal",
            "query_path": "opaque scientific parameter, not a host path field",
            "calibration_sha256": "a" * 64,
            "association": {"source_ref": "source_0123456789abcdef01234567"}},
        page_size=2, endpoint="usable_handoff", constraints={})


def test_legacy_hmmer_parameters_and_functional_subject_survive_before_masking():
    assignment = _hmmer_assignment()
    before = deepcopy(assignment)
    safe = select_profile_api_execution_values(assignment)
    assert safe == {key: assignment[key] for key in
        ("service", "subject_ref", "algorithm", "database", "parameters", "page_size")}
    safe["parameters"]["E"] = 9
    assert assignment == before


@pytest.mark.parametrize("role", ("launch", "launch_api", "results"))
def test_selected_task_hook_accepts_actual_hmmer_api_kind_without_mutating_assignment(role):
    assignment = _hmmer_assignment()
    selected = dict(requests={"ebi": assignment}) if role == "launch" else (
        dict(version="execution_results_assignment_v1", handoff_ref="source_original_handoff", selector=dict(page=1))
        if role == "results" else assignment)
    context = SimpleNamespace(role=role, assignment=selected)
    parent = dict(scientific_question="Measure selected native HMMER domain correspondence", selected_tool_info=[])
    owner = SimpleNamespace(resources={"ebi": {"kind": "hmmer_api"}},
        services=SimpleNamespace(scientific_parent_task=lambda current: deepcopy(parent)),
        local_file_sources=SimpleNamespace(applies=lambda current: False),
        _resource_information=lambda resource: dict(resource_id=resource, resource_kind="api"))
    value = dict(execution_target=dict(resource_id="ebi", assignment=deepcopy(assignment))) if role == "results" else {}
    before = deepcopy(selected)
    result = ExecutionEpisodes._with_selected_execution_task(owner, context, value)
    task = result["selected_execution_task"]
    assert task["requests"][0]["job"] == assignment and task["requests"][0]["resource_kind"] == "api"
    assert task["scientific_question"] == parent["scientific_question"]
    assert task["selector"] == (dict(page=1) if role == "results" else None)
    assert selected == before


@pytest.mark.parametrize("invalid", ("resource_map_id", "malformed_assignment"))
def test_selected_task_hook_keeps_rejected_api_assignments_unchanged(invalid):
    assignment = _hmmer_assignment()
    if invalid == "malformed_assignment":
        assignment["page_size"] = False
    selected = dict(requests={"different_resource" if invalid == "resource_map_id" else "ebi": assignment})
    context = SimpleNamespace(role="launch", assignment=selected)
    owner = SimpleNamespace(resources={"ebi": {"kind": "hmmer_api"}},
        services=SimpleNamespace(scientific_parent_task=lambda current:
            dict(scientific_question="Original question", selected_tool_info=[])))
    value = dict(unchanged="original supplied context")
    before = deepcopy(value)
    assert ExecutionEpisodes._with_selected_execution_task(owner, context, value) == before
    assert "selected_execution_task" not in value


def test_real_session_hmmer_task_keeps_parameters_selection_and_continuation(tmp_path):
    assignment = _hmmer_assignment()
    current = dict(goal=dict(objective="Acquire original selected HMMER results"), scope=dict(subject_refs=[assignment["subject_ref"]]),
        requested_form=dict(type="object", properties={}, required=[], additionalProperties=False),
        selected_execution_task=dict(version="selected_execution_task_v1",
            scientific_question="Measure selected HMMER domain correspondence", selected_tool_info=[],
            requests=[dict(resource_id="ebi", resource_kind="api", endpoint="usable_handoff", constraints={},
                job=assignment, resource=dict(resource_id="ebi", resource_kind="api"))],
            constraints={}, selector=dict(page=1, page_size=2), result_description=None),
        last_local_outcome=dict(status="partial", result=dict(returncode=None)), child_reports=[])
    instructions = "Use only the original selected HMMER job and requested page."
    session = _session(tmp_path / "hmmer-session")
    state = instructional_model_context(current)
    text, actual = session._presentation("engineering-hmmer-result", "REASONING", instructions, state_frame(state))
    assert text.startswith("TASK") and "STEERING" in text and actual == instructions
    assert all(token in text for token in (assignment["subject_ref"], "phmmer", "pdb", "domE",
        "caller_selected_literal", "opaque scientific parameter, not a host path field", "page_size", "partial",
        "a" * 64, "source_0123456789abcdef01234567"))
    repeated, actual = session._presentation("engineering-hmmer-result", "REASONING", instructions, state_frame(state, state))
    assert repeated == text and actual == instructions


@pytest.mark.parametrize("name", ("rfam243", "rfam245"))
def test_authentic_rfam_request_occurrences_and_selector_stay_literal(api_cases, name):
    case = api_cases[name]
    assignment = case["publication"]["target"]["assignment"]
    safe = select_profile_api_execution_values(assignment)
    assert safe == dict(service="rfam_batch", request=case["inputs"]["request"])
    refs = safe["request"]["subject_refs"]
    assert len(refs) == 3 and refs[0] == refs[1] != refs[2]
    assert select_profile_api_execution_values(case["inputs"]["selector"]) == case["inputs"]["selector"]


@pytest.mark.parametrize("version,representation", (("rfam_batch_result_selector_v1", "json"),
    ("rfam_batch_result_selector_v2", "tblout"), ("rfam_batch_result_selector_v3", "out")))
def test_three_existing_rfam_selectors_preserve_metadata_operand_and_metric_order(version, representation):
    value = dict(version=version, representation=representation,
        model_metadata_ref=None if version.endswith("v3") else "source_abcdef0123456789abcdef01",
        projection=dict(family="hit", rows=dict(offset=1, limit=2),
            metrics=["native_score_bits", "query_span_fraction"]))
    assert select_profile_api_execution_values(value) == value


@pytest.mark.parametrize("kind", ("extra", "bad_ref", "duplicate_metric", "bool_offset", "wrong_representation", "unknown"))
def test_malformed_recognized_and_unknown_api_shapes_do_not_break_wire_selection(kind):
    value = dict(version="rfam_batch_result_selector_v3", representation="out", model_metadata_ref=None,
        projection=dict(family="hit", rows=dict(offset=0, limit=1), metrics=["native_score_bits"]))
    if kind == "extra": value["host_path"] = "/private/control"
    elif kind == "bad_ref": value["model_metadata_ref"] = "source_not_permitted_by_v3"
    elif kind == "duplicate_metric": value["projection"]["metrics"] *= 2
    elif kind == "bool_offset": value["projection"]["rows"]["offset"] = True
    elif kind == "wrong_representation": value["representation"] = "tblout"
    else: value["version"] = "unrelated_api_result_v1"
    before = deepcopy(value)
    assert select_profile_api_execution_values(value) is None and value == before


@pytest.mark.parametrize("name", ("rfam243", "rfam245"))
def test_current_session_captured_rfam_results_task_frames_and_selected_values(api_cases, name, tmp_path):
    case = api_cases[name]
    call = case["results"][0]
    current = _selected_context(case, call)
    before = deepcopy(current)
    session = _session(tmp_path / "captured-results")
    state = instructional_model_context(current)
    text, instructions = session._presentation(call["episode_id"], call["role"], call["instructions"], state_frame(state))
    assert text.startswith("TASK") and "STEERING" in text and instructions == call["instructions"]
    assert current["selected_execution_task"]["scientific_question"] in text
    for info in current["selected_execution_task"]["selected_tool_info"]:
        assert info["description"] in text and info["instructions"] in text
    for ref in case["inputs"]["request"]["subject_refs"]:
        assert ref in text
    assert case["inputs"]["selector"]["version"] in text
    assert case["inputs"]["selector"]["representation"] in text
    assert all(metric in text for metric in case["inputs"]["selector"]["projection"]["metrics"])
    repeated, actual = session._presentation(call["episode_id"], call["role"], call["instructions"], state_frame(state, state))
    assert repeated == text and actual == instructions and current == before
    # Apply the real persisted fetch outcome to the current Results state.
    # This is current retained-data rendering, not an old post-fetch capture.
    update = deepcopy(state)
    update["last_local_outcome"] = deepcopy(case["acquired"])
    received, actual = session._presentation(call["episode_id"], call["role"], call["instructions"], state_frame(update, state))
    assert actual == instructions and "104.6" in received and "model_length_unavailable" in received
    if name == "rfam245":
        assert "118" in received and "75" in received and "5S_rRNA" in received
        assert case["returned"]["populations"][0] == dict(available_row_count=3, family="hit",
            more_rows=True, population_complete=True, selected_row_count=2,
            source_ref="source_1d09b389cd2041a9aae25a4d")
    else:
        assert len({row["query_occurrence_key"] for row in case["returned"]["measurements"]}) == 3
        assert [row["strand"] for row in case["returned"]["measurements"]] == ["+", "+", "-"]


def test_rfam_launch_uses_authenticated_selected_question_and_keeps_own_progress_private(api_cases, tmp_path):
    case = api_cases["rfam243"]
    call = next(row for row in case["calls"] if row["current"].get("api_service") == "rfam_batch")
    current = _selected_context(case, call)
    current["goal"]["task_context"]["root_objective"] = "BROADER_ROOT_OBJECTIVE_ENGINEERED"
    current["last_local_outcome"] = dict(status="partial", result=dict(state="unknown", returncode=None,
        host_path="PRIVATE_CAPTURE_PATH", credential="PRIVATE_CREDENTIAL", body="PRIVATE_BODY"))
    text, actual = _session(tmp_path / "api-launch")._presentation(call["episode_id"], call["role"], call["instructions"],
        state_frame(instructional_model_context(current)))
    assert text.startswith("TASK") and "STEERING" in text and actual == call["instructions"]
    assert current["selected_execution_task"]["scientific_question"] in text
    assert "BROADER_ROOT_OBJECTIVE_ENGINEERED" not in text
    assert all(info["instructions"] in text for info in current["selected_execution_task"]["selected_tool_info"])
    assert all(token not in text for token in ("PRIVATE_CAPTURE_PATH", "PRIVATE_CREDENTIAL", "PRIVATE_BODY"))
    assert "partial" in text and "unknown" in text


def _controller(path, initial):
    def estimate(raw, parameters, contexts):
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= 1 else 1), parameters,
            {"fixture": "caller_selected_api_presentation_estimator_only"})
    scientific = path[-1][0] in {"annotation", "scientific_process"}
    return YieldController(str(path), initial, 0, YieldParameters(100, 50),
        estimate_with_context=estimate if scientific else None)


def _neutral(*args, **kwargs):
    return 0


class PendingAPICaptured(RuntimeError):
    pass


class UnexpectedAPIFeedback(RuntimeError):
    pass


def test_new_current_rfam_results_builder_stops_before_any_result_selection(api_cases, tmp_path, monkeypatch):
    case = api_cases["rfam243"]
    db = case["db"]
    run_id = case["publication"]["run_id"]
    science = _commission(db, run_id, case["scientific"]["episode_id"], "scientific_process")
    results = _commission(db, run_id, case["publication"]["episode_id"], "results")
    assert results["selected"]["assignment"]["handoff_ref"] == _HANDOFF
    old_binding = science["request"]["message"]["scientific_process"]["mechanics_binding"]
    root = tmp_path / "current-pending"
    state = root / "state"
    state.mkdir(parents=True)
    destination = sqlite3.connect(state / "state.sqlite3")
    try:
        db.backup(destination)
        assert _tables(destination) == case["tables"]
    finally:
        destination.close()
    shutil.copytree(case["directory"] / "state/artifacts", state / "artifacts")
    run = root / "run"
    run.mkdir()
    for name in ("api-service-execution", "scientific-process-library", "scientific-tool-library", "tool-knowledge", "launch-instructions"):
        source = case["directory"] / "run" / name
        if source.exists():
            target = root / "original-scientific-tool-library" if name == "scientific-tool-library" else run / name
            shutil.copytree(source, target, symlinks=True)
    original_library = ScientificToolLibrary(root / "original-scientific-tool-library")
    process_library = ScientificProcessLibrary(run / "scientific-process-library")
    assert original_library.as_record() == old_binding["configuration"]["tool_library"]
    assert process_library.as_record() == old_binding["configuration"]["library"]
    original_info = original_library.resolve_tool_info(science["request"]["message"]["scientific_process"]["selection"]["child_tool_info"])
    assert original_info == case["scientific"]["current"]["scientific_process"]["child_tool_info"]
    factory = ExecutionServiceFactory({"rfam": dict(kind="api", service="rfam_batch", timeout=90.0)}, {}, 3, 2, .5)
    session = _session(tmp_path / "pending-session")
    calls, pending = [], {}
    current_info = current_science = None

    class Choices:
        async def complete(self, episode_id, role, instructions, current, schema):
            calls.append(dict(episode_id=episode_id, role=role, instructions=instructions, context=deepcopy(current)))
            if current.get("feedback"):
                raise UnexpectedAPIFeedback("unexpected API action-contract feedback: " + _canonical(plain(current["feedback"])))
            frame = state_frame(instructional_model_context(current))
            wire, actual = session._presentation(episode_id, role, instructions, frame)
            calls[-1]["wire"] = wire
            if current.get("execution_assignment", {}).get("version") == "execution_results_assignment_v1":
                assert len(calls) == 3 and current["execution_assignment"] == results["selected"]["assignment"]
                assert current["execution_target"] == case["publication"]["target"]
                task = current["selected_execution_task"]
                assert task["scientific_question"] == science["selected"]["goal"]
                assert task["selected_tool_info"] == current_info
                assert task["requests"][0]["job"] == case["publication"]["target"]["assignment"]
                assert task["selector"] == results["selected"]["assignment"]["selector"]
                assert current["requested_form"] == json.loads(results["selected"]["schema_json"])
                assert current["last_local_outcome"] is None and current["child_reports"] == []
                assert wire.startswith("TASK") and "STEERING" in wire and actual == instructions
                assert all(info["instructions"] in wire for info in current_info)
                pending.update(episode_id=episode_id, context=deepcopy(current), wire=wire)
                raise PendingAPICaptured("before any API result selection")
            selected = results["selected"] if "scientific_process" in current else current_science
            answer = provider_value({"selection": deepcopy(selected), "report_update": {}}, plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    store = Store(state)
    proof = dict(version="profile_api_current_pending_results_verification_v1", passed=False,
        historical_instruction_wire_claimed=False, native_calls=0, http_calls=0, calculator_calls=0,
        real_model_calls=0, old_replay_claimed=False)
    initialized = None
    try:
        registry = ToolRegistry(store)
        application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
        current_library = ScientificToolLibrary.freeze(run / "scientific-tool-library", catalog=registry.catalog(),
            tool_info=True, resource_catalogs=application.resource_tool_catalogs)
        selectors = [{key: info[key] for key in ("name", "resources")} for info in original_info]
        current_info = current_library.resolve_tool_info(selectors)
        descriptor = ScientificProcessEpisodes(None, library=process_library, tool_library=current_library,
            child_roles=old_binding["configuration"]["child_roles"]).as_record()
        current_science = deepcopy(science["selected"])
        current_science["assignment"]["selection"]["child_tool_info"] = selectors
        flow = Workflow(store, registry, Choices(), run, run_id, controller_factory=_controller, project_credit=_neutral,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=[_HANDOFF], episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
        constructor = _assert_original_rows(store.db, case["tables"])
        initialized = _tables(store.db)
        before_files = _inventory(root)
        episode = flow.build("annotation", "current-profile-api-pending243",
            science["request"]["goal"]["task_context"]["root_objective"], science["selected"]["scope"])
        with pytest.raises(PendingAPICaptured, match="before any API result selection"):
            asyncio.run(episode.run_async(flow.context))
        assert len(calls) == 3 and pending
        added = _new_rows(initialized, _tables(store.db))
        assert len(added["runtime_episodes"]) == 3 and len(added["runtime_actions"]) == 2
        assert len(added["runtime_model_calls"]) == 3
        for name in ("records", "artifacts", "tool_operations", "runtime_forms", "runtime_report_attempts", "runtime_observations"):
            assert added[name] == []
        records = EpisodeReturnRecords(store, run_id, failure_prefix="profile_api_pending_")
        context = records.context(pending["episode_id"])
        owner = flow.specialist(_source_for_original_context(flow, context))
        assert owner._target(context) == case["publication"]["target"]
        assert _HANDOFF in set(flow.receipts.known(context.episode_id))
        current_files = _inventory(root)
        for name, pin in before_files.items():
            if name not in {"state/state.sqlite3", "state/state.sqlite3-wal", "state/state.sqlite3-shm"}:
                assert current_files[name] == pin
        proof.update(passed=True, constructor=constructor, full_current_results_builder_verified=True,
            original_question=science["selected"]["goal"], original_binding=old_binding, current_binding=descriptor,
            original_tool_info=original_info, current_tool_info=current_info,
            actual_new_row_counts={name: len(rows) for name, rows in added.items()})
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calls"] = calls
        if initialized is not None:
            proof["actual_new_rows"] = _new_rows(initialized, _tables(store.db))
        store.close()
        (tmp_path / "PROFILE_API_CURRENT_PENDING_RESULTS.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
