"""Actual retained request custody under controlled native transport.

Store, Journal, preparation, submission, native-source retention, TaskHandoff and
custody are real. Only the remote RPC transport is controlled; no live service,
model decisions or scientific execution is claimed.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.bvbrc_appservice_custody import AppServiceCustodyError
from gene_annotation_episode.bvbrc_appservice_receipt_values import build_appservice_receipt
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.state import Store
from test_bvbrc_appservice_host import ProductionDriver
from test_bvbrc_appservice_custody import request, selector


PARAMETER_POINTER = "/prepared/native_operands/call/rpc_request/params/1"


def retained_submission(directory):
    """Open a real host fixture; the caller owns closing its Store."""
    store = Store(directory / "state")
    d = ProductionDriver(store, directory)
    query = request()
    query.update(required_application_id="GenomeComparison", parameters={
        "genome_ids": [], "user_genomes": ["/synthetic/work/unused.faa",
            "/synthetic/work/ref.faa", "/synthetic/work/subject.faa"],
        "user_feature_groups": [], "reference_genome_index": 2,
        "min_ident": .1, "min_seq_cov": .3, "min_positives": .2,
        "max_e_val": 1e-5, "output_path": "/synthetic/work/output", "output_file": "comparison"})
    context = d.tree(query)
    preparation = d.call("prepare", {"definition": {"kind": "packaged", "required_application_id": "GenomeComparison"}})
    # This equal-valued native echo is retained, but never supplies parameters.
    d.client.value = {"id": "123", "application_id": "GenomeComparison", "state_code": "Q",
                      "parameters": deepcopy(query["parameters"])}
    args = {"preparation_receipt_ref": preparation["source_ref"], "input_evidence_refs": []}
    handoff = d.call("submit", args)
    task = handoff["value"]["original_task"]
    source = store.get(task["submission_source_ref"])
    raw = store.get_artifact(source["request_ref"])
    binding = {"source_ref": source["id"], "artifact_field": "request_ref", "artifact_ref": source["request_ref"],
               "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
    evidence = {"content": binding, "pointer": PARAMETER_POINTER}
    action_dir = d.api._manifest(context) / "actions" / digest(task["submission_operation_key"])
    target = d.api.read_target(handoff["source_ref"], context.scope)
    return SimpleNamespace(driver=d, store=store, context=context, query=query, handoff=handoff,
        task=task, source=source, raw=raw, binding=binding, evidence=evidence, action_dir=action_dir,
        retained=json.loads(raw), snapshot=d.api._submission_snapshot(target), arguments=args)


@pytest.fixture(scope="module")
def submitted(tmp_path_factory):
    value = retained_submission(tmp_path_factory.mktemp("actual-submitted-content"))
    try:
        yield value
    finally:
        value.store.close()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("request-content verification attempted live transport")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)


def test_actual_retention_handoff_and_custody_have_original_parameter_pointer(submitted):
    s = submitted
    d = s.driver
    assert set(s.retained) == {"version", "origin", "snapshot", "prepared"}
    assert s.raw == canonical(s.retained).encode()
    assert d.records.read(s.handoff["source_ref"]) == s.handoff
    assert d.api.appservice.read_handoff(s.handoff["source_ref"])["task_handoff"] == s.handoff["value"]
    binding = d.records.retain_snapshot(s.context, s.retained["prepared"], s.snapshot,
                                       operation_key=s.task["submission_operation_key"])
    assert binding == s.handoff["value"]["receipt"]["snapshot"]
    assert d.custody.content(s.context, s.binding) == s.raw
    assert d.custody.evidence(s.context, s.evidence) == s.task["submitted_parameters"]
    assert s.binding["source_ref"] == s.task["submission_source_ref"]
    assert s.binding["artifact_ref"] != s.source["artifact_ref"]
    assert s.task["effective_parameters"] is None
    assert s.retained["prepared"]["native_operands"]["call"]["rpc_request"]["params"][1] == s.query["parameters"]
    assert len(d.client.calls) == 1
    assert s.store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("change", ["source", "digest", "length", "field", "artifact"])
def test_actual_custody_rejects_changed_content_bindings(submitted, change):
    binding = deepcopy(submitted.binding)
    if change == "source":
        binding["source_ref"] = submitted.handoff["source_ref"]
    elif change == "digest":
        binding["sha256"] = "0" * 64
    elif change == "length":
        binding["byte_count"] += 1
    elif change == "field":
        binding["artifact_field"] = "artifact_ref"
    else:
        binding["artifact_ref"] = submitted.source["artifact_ref"]
    with pytest.raises(AppServiceCustodyError):
        submitted.driver.custody.content(submitted.context, binding)


def test_actual_custody_requires_source_possession_and_exact_pointer(submitted):
    s = submitted
    with pytest.raises(AppServiceCustodyError, match="input_not_possessed"):
        s.driver.custody.content(s.driver.saved.root, s.binding)
    with pytest.raises(AppServiceCustodyError, match="evidence_pointer_unavailable"):
        s.driver.custody.evidence(s.context, {"content": s.binding, "pointer": "/parameters"})


@pytest.mark.parametrize("change", ["event_task", "effect_task"])
def test_real_receipt_builder_correlates_task_id_with_retained_native_response(submitted, change):
    s = submitted
    event = _read(s.action_dir / "event.json")
    common = deepcopy(s.handoff["value"]["receipt"])
    effects = [s.driver.api.selected_effects.read(ref, original_job_owner=s.handoff["value"]["original_job_owner"])
               for ref in common["effect_receipt_refs"]]
    actual = build_appservice_receipt(s.retained["prepared"], event, s.snapshot,
                                     common_receipt=common, effect_receipts=effects)
    assert actual["contract"] == "TaskHandoff" and actual["value"]["original_task"] == s.task
    if change == "event_task":
        event["native_handle"]["task_id"] = "456"
    else:
        effects[0]["native_effect_identifiers"]["task_id"] = "456"
    rejected = build_appservice_receipt(s.retained["prepared"], event, s.snapshot,
                                      common_receipt=common, effect_receipts=effects)
    assert rejected["contract"] == "CommonReceipt" and rejected["value"]["status"] == "failed"
    assert "submission_handoff_unconfirmed" in {d["code"] for d in rejected["diagnostics"]}
    assert s.driver.records.read(s.handoff["source_ref"])["value"]["original_task"]["task_id"] == "123"
    assert len(s.driver.client.calls) == 1


def test_host_rejects_wrong_task_after_real_record_authentication(submitted, monkeypatch):
    s = submitted
    read = s.driver.records.read
    def corrupt_after_authentication(reference, **kwargs):
        actual = read(reference, **kwargs)
        actual["value"]["original_task"]["task_id"] = "456"
        return actual
    monkeypatch.setattr(s.driver.records, "read", corrupt_after_authentication)
    with pytest.raises(ValueError, match="appservice_original_submission_unconfirmed"):
        s.driver.api.appservice.read_handoff(s.handoff["source_ref"])


def test_replay_retains_request_original_actions_and_no_new_transport(submitted):
    s = submitted
    before = s.store.db.execute("SELECT COUNT(*) FROM runtime_actions").fetchone()[0]
    result = s.driver.invoke(s.context, "submit", s.arguments, s.task["submission_operation_key"])
    assert result["result"]["handoff_ref"] == s.handoff["source_ref"]
    assert s.store.get_artifact(s.source["request_ref"]) == s.raw
    assert len(s.driver.client.calls) == 1
    assert s.store.db.execute("SELECT COUNT(*) FROM runtime_actions").fetchone()[0] == before


def test_request_source_crosses_declared_returns_and_results_assignment(tmp_path):
    s = retained_submission(tmp_path)
    try:
        d, refs = s.driver, [s.handoff["source_ref"], s.task["submission_source_ref"]]
        def admit(parent, child):
            # SavedRecords' helper delivers one ref. Retain the same original
            # declared refs-array contract while delivering both actual refs.
            d.saved.admit(parent, child, refs[0])
            form = {"refs": refs}
            d.saved.journal.save("runtime_forms", {"episode_id": child.episode_id,
                "facts": canonical({"committed_record_refs": refs}), "form": canonical(form)})
            index = int(child.path[-1][1][6:])
            old = dict(s.store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? "
                "AND parent_episode_id=? AND decision_index=?", (d.saved.run_id, parent.episode_id, index)).fetchone())
            d.saved.journal.save("runtime_report_attempts", {**old, "form": canonical(form)})
            d.saved.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        admit(d.launch, s.context)
        admit(d.saved.root, d.launch)
        selected = selector()
        selected.update(supplied_contents=[s.binding], supplied_metadata=[s.evidence])
        receiving = d.saved.child(d.saved.root, "results", {"version": "execution_results_assignment_v1",
            "handoff_ref": s.handoff["source_ref"], "selector": selected}, 3)
        d.api.initialize(receiving)
        assert d.api.appservice.initial_references(receiving) == refs
        assert d.custody.content(receiving, s.binding) == s.raw
        assert d.custody.evidence(receiving, s.evidence) == s.task["submitted_parameters"]
        # Compose the real receiving custody bytes with the existing synthetic
        # scientific-output fixture. The real provider and B1 constructor run;
        # production adapter registry/publication binding is a separate task.
        from test_bvbrc_proteome_submitted_parameters import submitted_case, assert_native_means
        from test_bvbrc_proteome_bundle_resolution import consume
        case = submitted_case(s)
        case["artifact_bytes"][s.binding["artifact_ref"]] = d.custody.content(receiving, s.binding)
        result = consume(case)
        assert result["sheet"]["input_index_result"]["value"]["reference_original_index"] == 2
        assert_native_means(result)
        assert len(d.client.calls) == 1
    finally:
        s.store.close()
