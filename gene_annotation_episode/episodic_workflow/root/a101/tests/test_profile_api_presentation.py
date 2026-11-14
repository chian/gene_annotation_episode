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

from gene_annotation_episode.episodic_workflow.root.a101.communication import plain
from gene_annotation_episode.episodic_workflow.root.a101.decision_context import instructional_model_context, state_frame
from gene_annotation_episode.episodic_workflow.root.a101.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a101.execution_prompt import select_profile_api_execution_values
from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.episodic_workflow.root.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.episodic_workflow.root.a101.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.episodic_workflow.root.a101.providers import _SessionConnection
from gene_annotation_episode.episodic_workflow.root.a101.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.episodic_workflow.root.a101.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.episodic_workflow.root.a101.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a101.tools import ToolRegistry
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
        "gene_annotation_episode.episodic_workflow.root.a101.api_execution.HMMERAPIExecution._http",
        "gene_annotation_episode.episodic_workflow.root.a101.api_service_execution.APIServiceExecution.execute",
        "gene_annotation_episode.episodic_workflow.root.a101.api_execution.HMMERAPIExecution.execute",
        "gene_annotation_episode.episodic_workflow.root.library.rfam_batch_publication.publish_rfam_batch_result",
        "gene_annotation_episode.episodic_workflow.root.library.rfam_batch_table.populate_rfam_batch_tblout_sheet",
        "gene_annotation_episode.episodic_workflow.root.library.rfam_batch_report.populate_rfam_batch_report_sheet",
        "gene_annotation_episode.episodic_workflow.root.library.infernal_search_inputs.populate_infernal_search_sheet",
        "gene_annotation_episode.episodic_workflow.root.library.infernal_search_grader.calculate_infernal_search_scores",
        "gene_annotation_episode.episodic_workflow.root.a101.hmmer_search_grader.calculate_hmmer_search_scores",
        "gene_annotation_episode.episodic_workflow.root.a101.hmmer_graders.grade_hmmer_api_result",
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


