"""MinHash input custody while a selected results child is still unsaved.

These are focused authority-boundary fixtures, not full Workflow executions.
They reuse synthetic supplied scalar bytes processed by actual material.parse
and original typed-admission fixtures from B521. The MinHash response is also
an explicitly synthetic native fixture.
The separate D522 selected Workflow cases cover the complete runtime path.
"""
from copy import deepcopy
from dataclasses import replace
import json
import socket
import subprocess

import pytest

from method_loop.identities import EpisodeRef

from gene_annotation_episode import api_bvbrc_minhash as service_module
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_bindings import BindingContext
from test_api_bvbrc_minhash import (
    RESULT_OPERATION, executor, explicit_pair_inputs, harness, request,
    saved_input, selected_inputs,
)
from test_bvbrc_minhash_metadata_custody import (
    SOURCE_SCHEMA, admit, handoff, own_context, parse_selected, results_context,
    setup_inputs,
)
from test_execution_episodes_family import select


@pytest.fixture(autouse=True)
def no_network_or_native_processes(monkeypatch):
    def prohibited(*args, **kwargs):
        raise AssertionError("Custody validation must not use a network or native process")

    monkeypatch.setattr(socket, "create_connection", prohibited)
    monkeypatch.setattr(socket.socket, "connect", prohibited)
    monkeypatch.setattr(subprocess, "Popen", prohibited)


def prospective_child(h, parent, native, selector, *, index=1, role="results"):
    """Construct the precommit BindingContext without saving either side."""
    assignment = {"version": "execution_results_assignment_v1",
        "handoff_ref": native, "selector": deepcopy(selector)}
    path = (*parent.path, (role, "child_" + str(index)))
    episode_id = EpisodeRef(parent.run_id, path).episode_id
    contract = {"decision": "Retain the requested typed result.",
        "measurements": {"schema": deepcopy(SOURCE_SCHEMA)}}
    child_request = {"message": {"scope": deepcopy(h.scope),
        "episode_assignment": deepcopy(assignment)}, "report_contract": contract}
    child = BindingContext(parent.run_id, episode_id, role, path, h.scope,
        assignment, child_request)
    selection = {"kind": "episode_child", "role": role,
        "goal": "Retain the selected MinHash result.", "scope": deepcopy(h.scope),
        "assignment": deepcopy(assignment), "purpose": contract["decision"],
        "schema_json": canonical(SOURCE_SCHEMA), "initial_report_json": "{}"}
    assert h.journal.row("runtime_episodes", child.episode_id) is None
    assert h.journal.row("runtime_actions", parent.episode_id, index) is None
    return child, selection


def record_response(h, parent, index, response):
    """Save the original parent response, including intentionally malformed cases."""
    with h.store.transaction():
        h.journal.save("runtime_model_calls", {"episode_id": parent.episode_id,
            "call_index": index, "purpose": "decision", "request": "{}",
            "response": response})


def response_for(selection, *, atomic_assignment=False):
    selected = deepcopy(selection)
    if atomic_assignment:
        selected["assignment"] = canonical(selected["assignment"])
    return canonical({"selection": selected, "report_update": {}})


def save_child(h, child):
    with h.store.transaction():
        h.journal.save("runtime_episodes", {"episode_id": child.episode_id,
            "path": canonical(child.path), "request": canonical(plain(child.request)),
            "initial_credit": 0, "state": "running"})


def commit_selection(h, parent, index, selection):
    with h.store.transaction():
        h.journal.save("runtime_actions", {"episode_id": parent.episode_id,
            "decision_index": index, "action": canonical(selection),
            "result": None, "credit": None})


def retained_state(h):
    """Compare existing journal contents and retained artifacts, not only counts."""
    return {
        "database": tuple(h.store.db.iterdump()),
        "files": {str(path.relative_to(h.tmp_path)): path.read_bytes()
            for root in (h.tmp_path / "run", h.tmp_path / "store" / "artifacts")
            for path in root.rglob("*") if path.is_file()},
        "client_calls": deepcopy(h.client.calls),
        "source_count": h.store.count("source"),
        "observation_count": h.store.count("observation"),
    }


def validate_without_work(h, monkeypatch, child, native, selector, source_ref, *,
                          original=None, expected=None,
                          failure_code="minhash_metadata_source_not_received"):
    """Validation may read custody; it may neither acquire nor rewrite history."""
    original = request() if original is None else original
    retained_source = h.store.get(source_ref)
    retained_bytes = h.store.get_artifact(retained_source["artifact_ref"])
    before = retained_state(h)

    def prohibited(*args, **kwargs):
        raise AssertionError("Input validation must not execute, acquire, publish, or grade")

    try:
        with monkeypatch.context() as guard:
            for owner, name in [(h.client, "rpc"), (h.service, "invoke"),
                    (h.service, "publish"), (h.tools, "execute"), (h.family, "execute"),
                    (service_module, "parse_minhash_result"),
                    (service_module, "calculate_minhash_components")]:
                guard.setattr(owner, name, prohibited)
            if expected is not None:
                actual = h.family.minhash.validate_inputs(child, selector,
                    request=original, handoff_ref=native)
                assert actual == expected
            else:
                with pytest.raises(ContractError, match="^" + failure_code + "$") as failure:
                    h.family.minhash.validate_inputs(child, selector,
                        request=original, handoff_ref=native)
                assert failure.value.detail["source_ref"] == source_ref
                if failure_code == "minhash_metadata_source_not_received":
                    assert failure.value.detail == {"source_ref": source_ref,
                        "pair_metadata_index": 0, "row_index": 0,
                        "genome_id": "511145.12", "field": "kmer_length",
                        "record_path": "/kmer_length"}
    finally:
        assert retained_state(h) == before
        assert h.store.get(source_ref) == retained_source
        assert h.store.get_artifact(retained_source["artifact_ref"]) == retained_bytes


@pytest.mark.parametrize("mode", ["genome", "fasta"])
@pytest.mark.parametrize("child_receipt", [False, True], ids=["own-parse", "typed-return"])
@pytest.mark.parametrize("atomic_assignment", [False, True], ids=["object", "atomic-json"])
def test_unsaved_child_uses_exact_pending_choice_and_prior_receipt(
        executor, monkeypatch, mode, child_receipt, atomic_assignment):
    h = executor
    parent, native, selector, expected, material = setup_inputs(h,
        mode=mode, child_receipt=child_receipt)
    child, selection = prospective_child(h, parent, native, selector)
    record_response(h, parent, 1, response_for(selection, atomic_assignment=atomic_assignment))
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"],
        original=request(mode), expected=expected)
    assert h.journal.row("runtime_episodes", child.episode_id) is None
    assert h.journal.row("runtime_actions", parent.episode_id, 1) is None


@pytest.mark.parametrize("problem", ["missing-row", "null-response", "malformed-json",
    "json-null", "json-array", "missing-selection", "null-selection", "array-selection",
    "duplicate-selection"])
def test_absent_or_malformed_parent_choice_cannot_supply_source(executor, monkeypatch, problem):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector)
    responses = {"null-response": None, "malformed-json": "{", "json-null": "null",
        "json-array": "[]", "missing-selection": "{}", "null-selection": '{"selection":null}',
        "array-selection": '{"selection":[]}',
        "duplicate-selection": '{"selection":' + canonical(selection)
            + ',"selection":' + canonical(selection) + '}'}
    if problem != "missing-row":
        record_response(h, parent, 1, responses[problem])
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


@pytest.mark.parametrize("problem", ["assignment", "role", "scope", "purpose", "schema",
    "kind", "non-results-child"])
def test_pending_selection_cannot_change_child_assignment_or_return_contract(
        executor, monkeypatch, problem):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector,
        role="scientific_process" if problem == "non-results-child" else "results")
    if problem == "assignment":
        selection["assignment"]["selector"] = {}
    elif problem == "role":
        selection["role"] = "launch_api"
    elif problem == "scope":
        selection["scope"]["subject_refs"] = []
    elif problem == "purpose":
        selection["purpose"] = "Return a different result."
    elif problem == "schema":
        selection["schema_json"] = canonical({"type": "object", "properties": {},
            "required": [], "additionalProperties": False})
    elif problem == "kind":
        selection["kind"] = "job_child"
    record_response(h, parent, 1, response_for(selection))
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


@pytest.mark.parametrize("problem", ["malformed", "non-object", "double-encoded", "duplicate-key"])
def test_atomic_assignment_is_one_unambiguous_object(executor, monkeypatch, problem):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector)
    encoded = canonical(selection["assignment"])
    selection["assignment"] = {"malformed": "{", "non-object": "[]",
        "double-encoded": json.dumps(encoded),
        "duplicate-key": encoded[:-1] + ',"selector":{}}'}[problem]
    record_response(h, parent, 1, response_for(selection))
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


@pytest.mark.parametrize("different_owner", [False, True], ids=["unreceived", "other-parent"])
def test_matching_pending_choice_does_not_grant_unreceived_source(
        executor, monkeypatch, different_owner):
    h = executor
    material, metadata = explicit_pair_inputs(h, request())
    selector, _ = selected_inputs([metadata])
    native = handoff(h)
    receiver = own_context(h, "scientific_process", {}, "unrelated-receiver")
    child, selection = prospective_child(h, receiver, native, selector)
    # An explicit input reference is not a receipt. A different parent's real
    # selected parse and matching pending choice cannot authorize this receiver.
    child = replace(child, received_record_refs=(material["source_ref"],))
    record_response(h, receiver, 1, response_for(selection))
    if different_owner:
        parent = own_context(h, "scientific_process", {}, "different-parent")
        parse_selected(h, parent, material)
        record_response(h, parent, 1, response_for(selection))
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


@pytest.mark.parametrize("offset", [-1, 1])
def test_parent_response_must_be_at_exact_child_decision_index(executor, monkeypatch, offset):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector)
    record_response(h, parent, 1 + offset, response_for(selection))
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


@pytest.mark.parametrize("child_receipt", [False, True], ids=["own-parse", "typed-return"])
def test_source_must_be_received_strictly_before_prospective_commission(
        executor, monkeypatch, child_receipt):
    h = executor
    material, metadata = explicit_pair_inputs(h, request())
    selector, _ = selected_inputs([metadata])
    parent = own_context(h, "scientific_process", {}, "timing-parent")
    native = handoff(h)
    child, selection = prospective_child(h, parent, native, selector)
    record_response(h, parent, 1, response_for(selection))
    if child_receipt:
        producer = own_context(h, "scientific_process", {}, "unused", parent=parent,
            index=2, schema=SOURCE_SCHEMA)
        parse_selected(h, producer, material)
        admit(h, parent, producer, 2, {"source": material["source_ref"]}, SOURCE_SCHEMA)
    else:
        parse_selected(h, parent, material, index=2)
    assert h.journal.row("runtime_actions", parent.episode_id, 1) is None
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


def test_saved_child_cannot_use_pending_choice_when_commission_is_missing(executor, monkeypatch):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector)
    record_response(h, parent, 1, response_for(selection))
    save_child(h, child)
    assert h.journal.row("runtime_actions", parent.episode_id, 1) is None
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])


@pytest.mark.parametrize("child_saved", [False, True], ids=["prospective", "saved"])
def test_explicit_saved_result_uses_the_same_commission_boundary(executor, monkeypatch, child_saved):
    h = executor
    parent, native, _, _, _ = setup_inputs(h)
    producer = results_context(h, parent, native, {}, 1)
    result = select(h, producer, 0, RESULT_OPERATION)
    assert result["status"] == "completed", result
    source_ref = result["result"]["source_ref"]
    admit(h, parent, producer, 1, {"source": source_ref}, SOURCE_SCHEMA)
    selector, expected = selected_inputs([], saved=saved_input(h, result))
    child, selection = prospective_child(h, parent, native, selector, index=2)
    record_response(h, parent, 2, response_for(selection, atomic_assignment=True))
    if child_saved:
        save_child(h, child)
    validate_without_work(h, monkeypatch, child, native, selector, source_ref,
        expected=None if child_saved else expected, failure_code="minhash_saved_result_not_received")


@pytest.mark.parametrize("child_saved", [False, True], ids=["unsaved", "saved"])
@pytest.mark.parametrize("response", ["missing", "conflicting"])
def test_committed_original_selection_is_authority_independent_of_model_response(
        executor, monkeypatch, child_saved, response):
    h = executor
    parent, native, selector, expected, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector)
    commit_selection(h, parent, 1, selection)
    if child_saved:
        save_child(h, child)
    if response == "conflicting":
        changed = deepcopy(selection)
        changed["assignment"]["selector"] = {}
        record_response(h, parent, 1, response_for(changed))
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"],
        expected=expected)


@pytest.mark.parametrize("child_saved", [False, True], ids=["unsaved", "saved"])
@pytest.mark.parametrize("conflict", ["assignment", "role", "kind"])
def test_matching_model_response_cannot_override_different_committed_selection(
        executor, monkeypatch, child_saved, conflict):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    child, selection = prospective_child(h, parent, native, selector)
    record_response(h, parent, 1, response_for(selection))
    committed = deepcopy(selection)
    if conflict == "assignment":
        committed["assignment"]["selector"] = {}
    elif conflict == "role":
        committed["role"] = "launch_api"
    else:
        committed["kind"] = "tool"
    commit_selection(h, parent, 1, committed)
    if child_saved:
        save_child(h, child)
    validate_without_work(h, monkeypatch, child, native, selector, material["source_ref"])
