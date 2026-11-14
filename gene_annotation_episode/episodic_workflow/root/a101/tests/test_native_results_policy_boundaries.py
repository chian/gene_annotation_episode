"""Controlled reporting/credit boundaries; authenticated custody is supplied.

These cases do not run native tools, acquire scientific evidence, authenticate
the supplied receipt bodies, or establish a complete scientific workflow.
"""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a101 import native_blast_results as blast
from gene_annotation_episode.episodic_workflow.root.a101 import native_hmmer_results as hmmer


@pytest.fixture(params=["blast", "hmmer"])
def selected(request, tmp_path):
    backend = request.param
    module = blast if backend == "blast" else hmmer
    cls = module.NativeBLASTResults if backend == "blast" else module.NativeHMMERResults
    context = SimpleNamespace(run_id="run", episode_id="episode", role="results",
                              assignment={"selected": "assignment"}, scope={}, request={})
    row = {"source_ref": "source-a", "record_key": "row-a", "reference_refs": ["source-a"],
           "search_key": {"artifact_key": "artifact-a", "search_pointer": "search-a"}}
    body = {"assignment": {"selector": {"projection": {"family": "pairwise_hsp"}}},
            "target": {"assignment": {"requested_job": {"native_hmmer": {"program": "hmmsearch"}}}},
            "capture": {"complete": True, "bundle_validated": True, "bundle_artifact_ref": "bundle"},
            "observation": {"state": "completed", "returncode": 0},
            "record_refs": ["record-a", "record-b"], "rows": [row], "complete": True,
            "operation_key": "original:1", "tool_name": "execution.results.collect", "arguments": {}}
    bundle = {"returncode": 0, "failures": []}
    calls = []
    action = {"result": {"actual": "result"}}
    def original_action(*args):
        calls.append(args)
        return action
    host = object.__new__(cls)
    host.owner = SimpleNamespace(acquired_record_unit=2.5, handoff_unit=7,
                                 _selected_result_action=original_action,
                                 _selection=lambda ctx: {"known_record_refs": ["record-a"]})
    host.store = SimpleNamespace(get_artifact=lambda ref: json.dumps(bundle).encode(),
                                  get=lambda ref: {"record_type": "source"})
    host.directory = tmp_path / "index"
    host.directory.mkdir()
    bodies = [body]
    host._own_bodies = lambda ctx: iter(bodies)
    host.applies = lambda ctx: ctx.role == "results"
    host.read_result = lambda reference, scope, **kwargs: body
    host.result_identity = lambda reference, scope: {"record-a": "stable-a", "record-b": "stable-b",
                                                     "inherited-a": "stable-a"}[reference]
    return SimpleNamespace(backend=backend, module=module, host=host, context=context,
                           body=body, bodies=bodies, bundle=bundle, action=action, calls=calls)


@pytest.mark.parametrize("requested", [False, True])
def test_requested_rows_deduplicate_witnesses_and_keep_complete_reference_set(selected, requested):
    s = selected
    source = "execution_blast_pairwise_hsp_rows" if s.backend == "blast" else "execution_hmmer_domain_rows"
    s.context.request = {"report_contract": {"measurements": {"schema": {"properties":
        {"rows": {"x-source": source}} if requested else {}}}}}
    s.body["rows"].append(deepcopy(s.body["rows"][0]))
    s.bodies.append(deepcopy(s.body))
    before = deepcopy(s.bodies)
    result = s.host.facts(s.context)
    assert result["execution_result_refs"] == ["record-a", "record-b"]
    expected_rows = [s.body["rows"][0]] if requested else []
    assert result[source] == expected_rows
    assert result["execution_completed"] is True
    assert s.bodies == before
    assert result["execution_result_origin"] == s.module.ORIGIN
    assert result["execution_result_origin"] is not s.module.ORIGIN


@pytest.mark.parametrize("change", ["incomplete", "failed_state", "failed_observation", "unvalidated", "failed_bundle", "bundle_diagnostics"])
def test_backend_specific_origin_qualification_is_preserved(selected, change):
    s = selected
    if change == "incomplete": s.body["capture"]["complete"] = False
    elif change == "failed_state": s.body["observation"]["state"] = "failed"
    elif change == "failed_observation": s.body["observation"]["returncode"] = 1
    elif change == "unvalidated": s.body["capture"]["bundle_validated"] = False
    elif change == "failed_bundle": s.bundle["returncode"] = 1
    else: s.bundle["failures"] = ["retained_failure"]
    result = s.host.facts(s.context)
    expected_origin = s.module.ORIGIN if s.backend == "hmmer" and change != "incomplete" else None
    assert result["execution_result_origin"] == expected_origin
    assert result["execution_result_refs"] == ["record-a", "record-b"]


def test_credit_counts_new_stable_identities_and_keeps_original_units(selected):
    s = selected
    selection = {"known_record_refs": ["record-a", "record-b", "inherited-a"],
                 "initial_known_record_refs": ["inherited-a"]}
    result = s.host.credit_view(s.context, selection)
    assert result["credit"] == result["operational_credit"] == 2.5
    assert result["new_acquired_record_count"] == 1 and result["new_handoff_count"] == 0
    assert result["operational_credit_binding"] == {
        "version": s.module.VERSION, "handoff_unit": 7, "acquired_record_unit": 2.5,
        "scientific_credit": False, "monitoring_credit": False}


def test_initial_unknown_reference_is_rejected_before_identity_reads(selected):
    s = selected
    def forbidden(*args):
        pytest.fail("identity read preceded selection validation")
    s.host.result_identity = forbidden
    with pytest.raises(s.module.ContractError, match="initial_references_must_be_known"):
        s.host.credit_view(s.context, {"known_record_refs": ["record-a"],
                                      "initial_known_record_refs": ["unselected"]})


@pytest.mark.parametrize("error_type", [ValueError, KeyError, OSError, TypeError])
def test_inherited_identity_failure_retains_original_exception_boundary(selected, error_type):
    s = selected
    def identity(reference, scope):
        if reference == "inherited-a": raise error_type("unavailable inherited record")
        return reference
    s.host.result_identity = identity
    selection = {"known_record_refs": ["record-a", "record-b", "inherited-a"],
                 "initial_known_record_refs": ["inherited-a"]}
    if error_type is TypeError:
        with pytest.raises(TypeError, match="unavailable inherited record"):
            s.host.credit_view(s.context, selection)
    else:
        result = s.host.credit_view(s.context, selection)
        assert result["new_acquired_record_count"] == 2
        assert result["credit"] == result["operational_credit"] == 5.0


@pytest.mark.parametrize("state", ["incomplete", "unreturned", "returned", "empty_result"])
def test_completion_requires_complete_capture_and_actual_selected_action_result(selected, state):
    s = selected
    s.body["complete"] = state != "incomplete"
    s.action["result"] = None if state == "unreturned" else {"actual": "result"}
    if state == "empty_result": s.action["result"] = {}
    result = s.host.completion(s.context)
    if state in {"incomplete", "unreturned"}:
        assert result is None
    else:
        assert result == {"version": "practical_completion_v1", "run_id": "run", "episode_id": "episode",
            "assignment_sha256": s.module.digest(s.context.assignment), "endpoint": "usable_handoff",
            "operation_key": "original:1", "receipt_sha256": s.module.digest(s.body),
            "validation_keys": ["original_native_attempt", "complete_sealed_bundle_acquisition",
                                "requested_native_numerical_projection"]}
    assert s.calls == ([] if state == "incomplete" else
                       [("episode", "original:1", "execution.results.collect", {})])


def test_received_context_resolution_keeps_backend_distinction(selected):
    s = selected
    s.context.role = "scientific"
    (s.host.directory / s.module.digest("record-a")).mkdir()
    namespace = "native_blast_pairwise_row" if s.backend == "blast" else "native_hmmer_row"
    assert s.host.resolve(s.context, "row-a", namespace) is (s.backend == "hmmer")
    assert s.host.resolve(s.context, "record-a", "execution_result") is (s.backend == "hmmer")
    assert s.host.resolve(s.context, "record-a", "unsupported") is False


def test_own_row_resolution_and_source_type_are_preserved(selected):
    s = selected
    namespace = "native_blast_pairwise_row" if s.backend == "blast" else "native_hmmer_row"
    assert s.host.resolve(s.context, "row-a", namespace) is True
    assert s.host.resolve(s.context, "missing-row", namespace) is False
    assert s.host.resolve(s.context, "record-a", "source") is True
    s.host.store.get = lambda reference: {"record_type": "observation"}
    assert s.host.resolve(s.context, "record-a", "source") is False
