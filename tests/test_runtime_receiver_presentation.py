"""Current presentation reconstructed from retained569 ordinary callbacks.

The compact inputs preserve selected original subdocuments. They are not new
Source receipts or historical replays. Continuation, URI and opaque-data edits
below are explicitly engineered display controls, with no acquisition or model.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.decision_context import VERSION, state_frame
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.providers import _SessionConnection, _ordinary_runtime_receiver_context
from gene_annotation_episode.rna_structure_comparison_receiver_prompt import _source_operands
from gene_annotation_episode.scientific_process_prompt import text_instructions
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


FIXTURE = Path(__file__).parent / "fixtures/runtime_receiver569"
PINS = {
    "contexts.json": ("8f2d26bce1257c0c30f9e27bc50e99c4b6b7e945ec4f87765ca55315275107e6", 77876),
    "provenance.json": ("c3065ceb3b759c03177f90a53ec8d457dc2b9a4a7b0c6e45484fbe43d163113d", 4515),
}


def _forbidden(*args, **kwargs):
    raise AssertionError("receiver presentation attempted work, private records or transport")


@pytest.fixture(autouse=True)
def no_work(monkeypatch):
    for owner, names in ((Store, ("get", "get_artifact", "read_snapshot", "put", "artifact")),
            (PublicClients, ("_http",)), (ToolRegistry, ("execute_async",)),
            (_SessionConnection, ("_rpc",)),
            (native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect"))):
        for name in names:
            monkeypatch.setattr(owner, name, _forbidden)


@pytest.fixture
def retained():
    documents = {}
    for name, (sha256, size_bytes) in PINS.items():
        raw = (FIXTURE / name).read_bytes()
        assert len(raw) == size_bytes and hashlib.sha256(raw).hexdigest() == sha256
        documents[name] = json.loads(raw)
    data, provenance = documents["contexts.json"], documents["provenance.json"]
    assert provenance["original_proof"]["sha256"] == "e5ae8e4398466df0d8933f14e4275b83a1b85bdc4ebcf56f20a3bf866260edd0"
    assert provenance["fixture"] == dict(path="contexts.json", sha256=PINS["contexts.json"][0], size_bytes=PINS["contexts.json"][1])
    assert len(data["contexts"]) == 2
    return data


def _connection():
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    return connection


def _public_and_private(state):
    source, = [row for row in state["working_state"]["sources"] if row["provider"] == "hpa"]
    return source, [source["request_ref"], *source["auxiliary_artifact_refs"]]


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("framed", [False, True])
def test_retained569_ordinary_callbacks_get_current_task_and_callable_operands(retained, index, framed):
    state = retained["contexts"][index]
    frame = state_frame(state) if framed else deepcopy(state)
    before = deepcopy((state, frame))
    connection = _connection()
    wire, instructions = connection._presentation("retained569", "REASONING", retained["instructions"], frame)
    assert wire.startswith("TASK\n\n") and "\n\nSTEERING\n" in wire
    assert state["goal"]["objective"] in wire and text_instructions(retained["instructions"]) in wire
    assert "Absent: no parent return form was supplied." in wire
    assert instructions == text_instructions(retained["instructions"])
    assert "Callable supplied Sources" in wire and "HTTP(S) resource URI" in wire
    assert all(source["id"] in wire for source in state["working_state"]["sources"])
    for operation in ("public.hpa.gene", "source.read", "state.query", "public.ncbi.entrez"):
        assert operation in wire
    entrez, = [tool for tool in state["tools"] if tool["name"] == "public.ncbi.entrez"]
    assert entrez["instructions"] in wire and "Operation guidance for public.ncbi.entrez" in wire
    if "resources" in entrez:
        assert "(resources: " + entrez["resources"] + ")" in wire
    if index == 1:
        source, private = _public_and_private(state)
        result = state["last_local_outcome"]["result"]
        assert result == dict(acquired=True, source_ref=source["id"], data_ref=source["artifact_ref"], failure_code=None)
        assert all(value in wire for value in (result["source_ref"], result["data_ref"], source["uri"]))
        assert all(reference not in wire for reference in private)
    assert '"visible_record_refs"' not in wire
    assert "action_yields" not in state and "estimate" not in state["controller"]
    assert connection.scientific_prompt_states[("retained569", "REASONING")] == state
    assert (state, frame) == before


def test_bootstrap_update_lookup_and_restart_preserve_the_full_current_question(retained):
    first, second = retained["contexts"]
    frames = [state_frame(first), state_frame(second, first)]
    # The payload is an actual recorded outcome, supplied here as a display
    # control. No original569 history lookup or model exchange is claimed.
    lookup = {"version": VERSION, "kind": "decision_lookup_result", "result": deepcopy(second["last_local_outcome"])}
    restart = state_frame(second)
    restart.update(restored_public_exchanges=[dict(exchange_index=0, lookup_result=deepcopy(lookup["result"]))],
        restored_pending_decision_index=1)
    before = deepcopy((first, second, frames, lookup, restart))
    connection = _connection()
    wires = [connection._presentation("episode", "REASONING", retained["instructions"], frame)[0] for frame in frames]
    wires.append(connection._presentation("episode", "REASONING", retained["instructions"], lookup)[0])
    fresh = _connection()
    wires.append(fresh._presentation("episode", "REASONING", retained["instructions"], restart)[0])
    question = second["goal"]["objective"]
    assert all(wire.startswith("TASK\n\n") and question in wire for wire in wires)
    tasks = [wire.split("\n\nSTEERING\n", 1)[0] for wire in wires]
    assert tasks[1] == tasks[2] == tasks[3]
    assert "Requested information; continue the same decision" in wires[2]
    assert "Requested information; continue the same decision" in wires[3]
    source, private = _public_and_private(second)
    assert all(source["id"] in wire and source["artifact_ref"] in wire for wire in wires[1:])
    assert all(reference not in wire for reference in private for wire in wires)
    assert connection.scientific_prompt_states[("episode", "REASONING")] == fresh.scientific_prompt_states[("episode", "REASONING")] == second
    assert (first, second, frames, lookup, restart) == before


def test_engineered_continuation_bands_replace_prior_values_without_repricing_actions(retained):
    # These literal protocol values are not numerical measurements from569.
    first = deepcopy(retained["contexts"][1])
    first["action_yields"] = {"rows": [dict(category="tool/example", completed_actions=9, total_yield=-3.0,
        attempted_uncompleted=2, expected_yield=dict(status="available", band=dict(status_code=0, value=3.25,
            lower=2.0, upper=4.5, uncertainty_code=2, alpha=0.1)))]}
    first["controller"].update(estimate=dict(turns=9, expected_next_gain=dict(status_code=0, value=2.5,
        lower=-1.25, upper=4.75, uncertainty_code=1, alpha=0.2)), decision=dict(stop=False, continuation_cost=0.75))
    second = deepcopy(first)
    second["action_yields"]["rows"][0]["expected_yield"] = dict(status="unavailable", unavailable_reason="unidentifiable", band=None)
    second["controller"]["estimate"]["expected_next_gain"] = dict(status_code=0, value=1.125, lower=0.25, upper=1.875)
    before = deepcopy((first, second))
    connection = _connection()
    old = connection._presentation("bands", "REASONING", retained["instructions"], state_frame(first))[0]
    current = connection._presentation("bands", "REASONING", retained["instructions"], state_frame(second, first))[0]
    assert "| tool/example | 9 | -3.0 | 3.25 |" in old
    assert "approximate Laplace model band" in old and "Chebyshev bound" in old
    assert "| tool/example | 9 | -3.0 | unavailable | unidentifiable | 2 |" in current
    assert "| 9 | 1.125 | lower=0.25; upper=1.875 | 0.75 |" in current
    assert "3.25" not in current and "2.5" not in current
    assert old.split("\n\nSTEERING\n", 1)[0] == current.split("\n\nSTEERING\n", 1)[0]
    assert (first, second) == before


@pytest.mark.parametrize("uri,shown", [
    ("https://example.org/resource?q=literal%20value#part", True),
    ("HTTP://example.org:8080/CaseSensitive", True),
    ("file:///private/native/workspace/result.json", False),
    ("native:///private/native/workspace/result.json", False),
    ("/private/native/workspace/result.json", False), ("relative/result.json", False),
    ("//example.org/resource", False), ("ftp://example.org/resource", False),
    ("https://user:password@example.org/resource", False),
    ("https://example.org:invalid/resource", False), ("https://[broken/resource", False),
    (" https://example.org/resource", False), ("https://example.org/line\nbreak", False), (None, False),
])
def test_source_uri_summary_uses_only_literal_valid_http_resources(retained, monkeypatch, uri, shown):
    # URI replacements are engineered metadata-only controls, not new Sources.
    source, _private = _public_and_private(retained["contexts"][1])
    source = deepcopy(source)
    source["uri"] = uri
    working = dict(sources=[source])
    before = deepcopy(working)
    with monkeypatch.context() as guarded:
        for name in ("open", "read_text", "read_bytes"):
            guarded.setattr(Path, name, _forbidden)
        rows = _source_operands(working)
    assert rows == [(source["id"], source["provider"], source["accession"], source["version"], uri if shown else None)]
    assert working == before


def test_inventory_only_source_and_job_options_remain_callable_without_private_fields(retained):
    # Engineering display variants of a retained context, not receipt changes.
    state = deepcopy(retained["contexts"][1])
    state["last_local_outcome"] = None
    state["job_episode_options"] = {"job_launch": {"responsibility": "CALLER_SELECTED_JOB_RESPONSIBILITY",
        "report_facts": {"job_ref": {"type": "reference", "meaning": "CALLER_SELECTED_JOB_RETURN"}}}}
    source, private = _public_and_private(state)
    wire = _connection()._presentation("inventory", "REASONING", retained["instructions"], state_frame(state))[0]
    assert source["id"] in wire and source["uri"] in wire
    assert source["artifact_ref"] not in wire and all(reference not in wire for reference in private)
    assert "Child construction and requested facts" in wire and state["child_options"] in wire
    assert "Configured job child roles and requested facts" in wire
    assert "CALLER_SELECTED_JOB_RESPONSIBILITY" in wire and "CALLER_SELECTED_JOB_RETURN" in wire


def test_opaque_native_data_is_unchanged_outside_the_declared_source_inventory(retained):
    state = deepcopy(retained["contexts"][1])
    literal = dict(uri="file:///literal/scientific/operand", request_ref="literal-native-value",
        auxiliary_artifact_refs=["literal-native-association"], nested=dict(data_ref="literal-native-data"))
    # A supplied generic opaque result, not a modified HPA acquisition DTO.
    state["last_local_outcome"] = dict(status="completed", record_refs=[], result=dict(opaque_native=deepcopy(literal)))
    before = deepcopy(state)
    wire = _connection()._presentation("opaque", "REASONING", retained["instructions"], state_frame(state))[0]
    assert all(value in wire for value in (literal["uri"], literal["request_ref"],
        literal["auxiliary_artifact_refs"][0], literal["nested"]["data_ref"]))
    assert state == before


def test_host_feedback_diagnostic_slots_hide_only_their_own_private_addresses(retained):
    state = deepcopy(retained["contexts"][1])
    diagnostic, separate = "artifact_" + "a" * 64, "artifact_" + "b" * 64
    # Display-only host feedback and opaque result. No Artifact is created or
    # received; matching native-data tokens must not be recursively removed.
    state["last_local_outcome"] = dict(status="failed", record_refs=[],
        result=dict(diagnostic_ref=diagnostic), feedback=dict(code="HOST_FAILURE_CODE",
            detail="HOST_FAILURE_DETAIL", diagnostic_ref=diagnostic))
    state["feedback"] = dict(code="SEPARATE_FAILURE_CODE", detail="SEPARATE_FAILURE_DETAIL", diagnostic_ref=separate)
    before = deepcopy(state)
    wire = _connection()._presentation("feedback", "REASONING", retained["instructions"], state_frame(state))[0]
    assert wire.count(diagnostic) == 1 and separate not in wire
    assert "result.diagnostic_ref" in wire and "feedback.diagnostic_ref" not in wire
    assert all(value in wire for value in ("HOST_FAILURE_CODE", "HOST_FAILURE_DETAIL",
        "SEPARATE_FAILURE_CODE", "SEPARATE_FAILURE_DETAIL"))
    assert state == before


@pytest.mark.parametrize("kind", ["frame_only", "operational_assignment"])
def test_sparse_protocol_and_operational_assignment_contexts_keep_their_original_json(retained, kind):
    state = ({"goal": {"id": "retained"}, "counter": 1} if kind == "frame_only" else deepcopy(retained["contexts"][0]))
    if kind == "operational_assignment":
        state["working_state"] = dict(role="job_launch", assignment=dict(job_ref="literal-selected-job"))
    frame = state_frame(state)
    before = deepcopy(frame)
    assert _ordinary_runtime_receiver_context(state) is False
    connection = _connection()
    wire, instructions = connection._presentation("protocol", "REASONING", "unchanged instructions", frame)
    assert json.loads(wire) == frame and instructions == "unchanged instructions"
    assert connection.scientific_prompt_states == {} and frame == before
