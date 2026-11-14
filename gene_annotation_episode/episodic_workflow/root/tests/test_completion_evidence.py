"""Read actual saved completion/return/delivery records under read-only guards.

The forms, credit operands and process ownership are engineering fixtures. No
model, scientific interpretation, worker or native scientific job is executed.
"""
from copy import deepcopy
import json

import pytest

from method_loop.durable import canonical
from method_loop.identities import UnitRef

from gene_annotation_episode.completion_evidence import (
    CompletionEvidence, VERSION, validate_completion_evidence)
from gene_annotation_episode.episode_completion import observes_action_outcome
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import FIELDS, read_progress
from gene_annotation_episode.local_return_history import LocalReturnHistory
from gene_annotation_episode.state import Store
from test_local_return_history import Case, SCHEMA, Value, forbidden, read_only


@pytest.fixture
def case(tmp_path):
    case = Case(tmp_path)
    try:
        yield case
    finally:
        case.store.close()


def capture(case, index, *, sequence=0, body=None, provider=...):
    if body is None:
        body = {"credit": case.journal.row("runtime_actions", case.parent, index)["credit"],
                "estimation_action_index": index}
    return CompletionEvidence(case.store, case.journal, case.backend,
        case.progress if provider is ... else provider).capture(case.parent,
            original_decision_index=index, unit_ref=UnitRef(case.parent, sequence),
            controller_input=Value(body))


def own(case, index, *, result=None, selection=None, credit=1.25, stage=True):
    selection = selection or {"kind": "tool", "tool": "progress.observe", "arguments": {}}
    result = result or {"status": "completed", "record_refs": [], "changed_record_refs": []}
    case.journal.save("runtime_actions", {"episode_id": case.parent, "decision_index": index,
        "action": canonical(selection), "result": canonical(result), "credit": credit})
    body = {"credit": credit, "estimation_action_index": index}
    if stage and observes_action_outcome(selection["kind"], result["status"]):
        return case.ledger.stage(case.parent, index, label="own:" + str(index),
            kind="own_action", controller_input=Value(body), child_return=None)


def actual_form_delivery(case, index, admission):
    return case.progress.receive_form(case.parent, admission["report"], SCHEMA,
        case.base["child"]["scope"], f"{case.journal.run_id}:{case.parent}:{index}:typed_form")


def guards(case, monkeypatch):
    read_only(case, monkeypatch)
    for name in ("observe", "expose", "receive_form", "receive_outcome", "received_progress_refs",
                 "direct_dependencies", "observation_identity", "resolve", "flush_notifications"):
        monkeypatch.setattr(case.progress, name, forbidden)
    monkeypatch.setattr(LocalReturnHistory, "capture", forbidden)
    monkeypatch.setattr(LocalReturnHistory, "_link_waits", forbidden)


def test_current_return_is_read_before_observation_without_loading_other_history(case, monkeypatch):
    child = case.child(9, progress=True)
    delivered = actual_form_delivery(case, 9, child[2])
    slot = case.stage(child[2], observe=False)
    # Another original return is deliberately corrupt. Current capture must
    # neither capture full E2 history nor read a different C4/C3 sample.
    other = case.child(2)
    case.store.db.execute("UPDATE runtime_return_admissions SET admission='{}' "
        "WHERE original_decision_index=2")
    body = deepcopy(child[2]["controller_input"])
    before = case.store.db.total_changes
    reads, c3_reads = [], []
    public_read, original_return = case.progress.read_progress, case.backend.load_return

    def reader(reference, scope):
        reads.append((reference, deepcopy(scope)))
        return public_read(reference, scope)

    def returned(handle, return_id):
        c3_reads.append((handle, return_id))
        return original_return(handle, return_id)

    monkeypatch.setattr(case.progress, "read_progress", reader)
    monkeypatch.setattr(case.backend, "load_return", returned)
    guards(case, monkeypatch)
    packet = capture(case, 9, sequence=slot["sequence"], body=body)
    assert packet["version"] == VERSION
    assert packet["unit_ref"] == UnitRef(case.parent, 0).as_record()
    assert packet["received_record_refs"] == child[2]["received_record_refs"]
    assert packet["received_progress_refs"] == delivered
    assert packet["progress_records"] == [public_read(delivered[0], case.base["child"]["scope"])]
    assert reads == [(delivered[0], case.base["child"]["scope"])]
    assert c3_reads == [(child[0]["handle"], child[1]["return_id"])]
    returned_packet = packet["child_return"]
    assert returned_packet["admission_id"] == child[2]["admission_id"]
    assert returned_packet["selection_to_return"] == {"seconds": 12.125,
        "measure": "utc_timestamp_difference", "unavailable_reason": None}
    assert set(returned_packet) == {"child_handle", "return_id", "admission_id", "admission_state",
        "commission_sha256", "report_contract_sha256", "selected_at", "returned_at", "selection_to_return"}
    assert case.journal.row("runtime_observations", case.parent, 0) is None
    assert case.store.db.total_changes == before
    assert body == child[2]["controller_input"]
    assert other[2]["admission_id"] != returned_packet["admission_id"]


def test_single_return_api_is_scoped_and_does_not_link_waits(case, monkeypatch):
    child = case.child(3)
    slot = case.stage(child[2], observe=False)
    guards(case, monkeypatch)
    reader = LocalReturnHistory(case.store, case.journal, case.backend)
    value = reader.read_return(case.parent, 3)
    assert value["version"] == "local_return_evidence_v1"
    assert value["sample"]["admission_id"] == child[2]["admission_id"]
    assert value["sample"]["completion_sequence"] == slot["sequence"]
    assert value["sample"]["observation_state"] == "unobserved"
    assert value["sample"]["linked_waits"] == []
    assert reader.read_return(case.parent, 4) is None
    with pytest.raises(ValueError, match="episode_unavailable"):
        reader.read_return("foreign", 3)
    for index in (-1, True, 1.5):
        with pytest.raises(ValueError, match="decision_index_required"):
            reader.read_return(case.parent, index)


@pytest.mark.parametrize("status", ["partial", "failed", "unavailable"])
def test_own_retained_and_repeated_progress_are_delivery_facts(case, monkeypatch, status):
    child = case.child(8, progress=True)
    snapshot = case.progress.read_progress(child[2]["report"]["updates"][0]["ref"],
        case.base["child"]["scope"])
    reference = snapshot["progress_ref"]
    source = case.base["input_versions"][0]["reference"]
    outcome = {"status": status, "record_refs": [source], "changed_record_refs": [],
        "progress_refs": [reference, reference], "feedback": {"code": "retained_partial"}}
    for index in (10, 12):
        own(case, index, result=outcome)
        case.progress.receive_outcome(case.parent, outcome, case.base["child"]["scope"],
            f"{case.journal.run_id}:{case.parent}:{index}:own_progress")
    # A later, unselected snapshot and another operation key are excluded.
    case.progress.expose(child[0]["handle"], operation_key="later",
        provenance_refs=[source])
    newer = case.progress.observe(child[0]["handle"], list(FIELDS), case.base["child"]["scope"])
    case.progress.receive_outcome(case.parent, {**outcome, "progress_refs": [newer["progress_ref"]]},
        case.base["child"]["scope"], f"{case.journal.run_id}:{case.parent}:999:own_progress")
    before = case.store.db.total_changes
    guards(case, monkeypatch)
    first, repeated = capture(case, 10), capture(case, 12, sequence=1)
    for packet in (first, repeated):
        assert packet["received_record_refs"] == [source]
        assert packet["received_progress_refs"] == [reference]
        assert packet["progress_records"] == [snapshot]
        assert packet["child_return"] is None
        assert "original_return_admission_unavailable" not in packet["unavailable_reasons"]
        assert not {"score", "raw_controller_delta", "novelty_count", "controller_step"} & packet.keys()
    assert case.store.db.total_changes == before


@pytest.mark.parametrize("kind", ["reason", "wait", "tool"])
def test_ordinary_actions_do_not_capture_return_history(case, monkeypatch, kind):
    own(case, 2, selection={"kind": kind})
    guards(case, monkeypatch)
    monkeypatch.setattr(LocalReturnHistory, "read_return", forbidden)
    packet = capture(case, 2)
    assert packet["action_kind"] == kind
    assert packet["child_return"] is None


@pytest.mark.parametrize("mode", ["query", "native_refs", "native_rows"])
def test_explicit_own_host_delivery_positions_are_retained_without_body_hydration(case, monkeypatch, mode):
    source = case.store.get(case.base["input_versions"][0]["reference"])
    result = {"status": "completed", "record_refs": [], "changed_record_refs": []}
    selection = {"kind": "tool", "tool": "fixture.tool"}
    if mode == "query":
        selection["tool"] = "state.query"
        result["result"] = {"records": [source, "bare-record-reference", 5, None, False, source]}
    elif mode == "native_refs":
        result["native_execution_refs"] = [source["id"], source["id"]]
    else:
        result["result"] = {"records": ["bare-record-reference", 5, None, False,
            {"id": source["id"], "record_type": "native_execution",
            "measurement": {"unknown_queue_wait": None}},
            {"id": "not_received", "record_type": "native_execution"},
            {"id": "not_received_either", "record_type": "source", "measurement": {}}]}
    result["arbitrary_reference"] = "not_delivered"
    own(case, 2, result=result, selection=selection)
    guards(case, monkeypatch)
    assert capture(case, 2)["received_record_refs"] == [source["id"]]


def test_blocking_child_has_its_saved_form_delivery_without_inventing_c4(case, monkeypatch):
    child = case.child(3, progress=True)
    actual_form_delivery(case, 3, child[2])
    case.store.db.execute("DROP TABLE runtime_return_admissions")
    guards(case, monkeypatch)
    monkeypatch.setattr(case.backend, "load_return", forbidden)
    packet = capture(case, 3, body=child[2]["controller_input"])
    assert packet["child_return"] is None
    assert packet["received_record_refs"] == child[2]["received_record_refs"]
    assert packet["received_progress_refs"] == [child[2]["report"]["updates"][0]["ref"]]
    assert "original_return_admission_unavailable" in packet["unavailable_reasons"]


@pytest.mark.parametrize("missing", ["row", "table", "provider"])
def test_original_admitted_form_keeps_progress_without_delivery_ledger(case, monkeypatch, missing):
    child = case.child(3, progress=True)
    actual_form_delivery(case, 3, child[2])
    case.stage(child[2], observe=False)
    if missing == "row":
        case.store.db.execute("DELETE FROM runtime_progress_deliveries WHERE operation_key=?",
            (f"{case.journal.run_id}:{case.parent}:3:typed_form",))
    elif missing == "table":
        case.store.db.execute("DROP TABLE runtime_progress_deliveries")
    guards(case, monkeypatch)
    packet = capture(case, 3, body=child[2]["controller_input"],
        provider=None if missing == "provider" else case.progress)
    reference = child[2]["report"]["updates"][0]["ref"]
    assert packet["received_progress_refs"] == [reference]
    if missing == "provider":
        assert packet["progress_records"] == []
        assert "progress_reader_unavailable:" + reference in packet["unavailable_reasons"]
    else:
        assert [row["progress_ref"] for row in packet["progress_records"]] == [reference]


def test_failed_form_is_completed_action_with_empty_received_information(case, monkeypatch):
    child = case.child(3, state="delivery_failed", progress=True)
    slot = case.stage(child[2], observe=False)
    guards(case, monkeypatch)
    packet = capture(case, 3, sequence=slot["sequence"], body=child[2]["controller_input"])
    assert packet["child_return"]["admission_state"] == "delivery_failed"
    assert packet["received_record_refs"] == packet["received_progress_refs"] == packet["progress_records"] == []
    assert case.journal.row("runtime_observations", case.parent, slot["sequence"]) is None


@pytest.mark.parametrize("child_failure", [False, True])
def test_unobserved_child_failure_or_rejected_request_has_no_completion_packet(case, monkeypatch, child_failure):
    if child_failure:
        case.child(3, state="execution_failed")
    else:
        own(case, 3, result={"status": "invalid", "record_refs": [], "changed_record_refs": []}, stage=False)
    guards(case, monkeypatch)
    with pytest.raises(ValueError, match="requires_completed_outcome_and_credit"):
        capture(case, 3, body={"credit": 0, "estimation_action_index": 3})
    assert case.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("support", ["missing_reader", "missing_body", "missing_c1", "unreadable_return"])
def test_unavailable_support_keeps_original_identity_and_unknown_timing(case, monkeypatch, support):
    child = case.child(3, progress=True)
    actual_form_delivery(case, 3, child[2])
    case.stage(child[2], observe=False)
    reference = child[2]["report"]["updates"][0]["ref"]
    provider = case.progress
    if support == "missing_reader":
        provider = None
    elif support == "missing_body":
        case.store.db.execute("DELETE FROM runtime_progress_observations")
    elif support == "missing_c1":
        case.store.db.execute("DROP TABLE runtime_commission_intents")
        monkeypatch.setattr(case.backend, "load_return", forbidden)
    else:
        def unavailable(*args):
            raise OSError("original backend unavailable")
        monkeypatch.setattr(case.backend, "load_return", unavailable)
    guards(case, monkeypatch)
    packet = capture(case, 3, body=child[2]["controller_input"], provider=provider)
    assert packet["child_return"]["admission_id"] == child[2]["admission_id"]
    assert packet["received_progress_refs"] == [reference]
    if support in {"missing_reader", "missing_body"}:
        assert packet["progress_records"] == []
        assert ("progress_reader_unavailable:" if support == "missing_reader" else
                "progress_body_unavailable:") + reference in packet["unavailable_reasons"]
    else:
        assert packet["child_return"]["selection_to_return"]["seconds"] is None
        assert packet["child_return"]["returned_at"] is None


@pytest.mark.parametrize("conflict,reason", [("handle", "original_return_identity_conflict"),
    ("digest", "original_return_invalid"), ("admission", "original_return_admission_conflict")])
def test_conflicting_auxiliary_c3_timing_never_replaces_committed_admission(case, monkeypatch, conflict, reason):
    child = case.child(3)
    case.stage(child[2], observe=False)
    if conflict == "admission":
        admission = deepcopy(child[2])
        admission["report"]["other"] = "changed-original-form"
        case.store.db.execute("UPDATE runtime_return_admissions SET admission=?", (canonical(admission),))
        case.store.db.execute("UPDATE runtime_report_attempts SET form=?", (canonical(admission["report"]),))
    else:
        returned = deepcopy(child[1])
        if conflict == "handle":
            returned["handle"] = "foreign"
        else:
            returned["returned_at"] = "2099-01-01T00:00:00Z"
        monkeypatch.setattr(case.backend, "load_return", lambda *args: returned)
    guards(case, monkeypatch)
    packet = capture(case, 3, body=child[2]["controller_input"])
    assert packet["child_return"]["admission_id"] == child[2]["admission_id"]
    assert packet["child_return"]["return_id"] == child[1]["return_id"]
    assert packet["child_return"]["returned_at"] is None
    assert packet["child_return"]["selection_to_return"] == {"seconds": None,
        "measure": "utc_timestamp_difference", "unavailable_reason": "returned_at_unavailable"}
    assert reason in packet["unavailable_reasons"]


@pytest.mark.parametrize("mutation", ["version", "identity", "target", "outside_scope"])
def test_returned_progress_identity_conflicts_are_rejected(case, monkeypatch, mutation):
    child = case.child(3, progress=True)
    reference = child[2]["report"]["updates"][0]["ref"]
    outcome = {"status": "completed", "record_refs": [], "changed_record_refs": [], "progress_refs": [reference]}
    own(case, 8, result=outcome)
    snapshot = case.progress.read_progress(reference, case.base["child"]["scope"])
    if mutation == "version":
        snapshot["version"] = "future_snapshot"
    elif mutation == "identity":
        snapshot["progress_ref"] = "foreign"
    elif mutation == "target":
        snapshot["target_handle"] = "foreign"
    else:
        request = json.loads(case.journal.row("runtime_episodes", case.parent)["request"])
        request["message"]["scope"]["segments"] = [{"target_ref": request["message"]["scope"]["subject_refs"][0],
            "start": 0, "end": 1, "unit": "nt"}]
        case.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
            (canonical(request), case.parent))
    if mutation != "outside_scope":
        monkeypatch.setattr(case.progress, "read_progress", lambda *args: snapshot)
    guards(case, monkeypatch)
    with pytest.raises(ValueError, match="completion_evidence"):
        capture(case, 8)


@pytest.mark.parametrize("mismatch", ["credit", "action_index", "unit_episode", "unit_position",
    "slot_input", "slot_index", "observation_input", "observation_identity", "c4_refs", "delivery_refs"])
def test_saved_identity_credit_and_completion_alignment_mismatches(case, monkeypatch, mismatch):
    child = case.child(3, progress=True)
    actual_form_delivery(case, 3, child[2])
    case.stage(child[2], observe=mismatch.startswith("observation"))
    body = deepcopy(child[2]["controller_input"])
    unit = UnitRef(case.parent, 0)
    if mismatch == "credit":
        body["credit"] += 1
    elif mismatch == "action_index":
        body["estimation_action_index"] = 99
    elif mismatch == "unit_episode":
        unit = UnitRef("foreign", 0)
    elif mismatch == "unit_position":
        unit = UnitRef(case.parent, 4)
    elif mismatch.startswith("slot"):
        slot = case.ledger.slot(case.parent, 0)
        if mismatch == "slot_input":
            slot["controller_input"]["extra"] = "different"
        else:
            slot["original_decision_index"] = 99
        case.store.db.execute("UPDATE runtime_completion_slots SET slot=?", (canonical(slot),))
    elif mismatch.startswith("observation"):
        observed = json.loads(case.journal.row("runtime_observations", case.parent, 0)["observation"])
        if mismatch == "observation_input":
            observed["credit"]["extra"] = "different"
        else:
            observed["unit_ref"] = UnitRef("foreign", 0).as_record()
        case.store.db.execute("UPDATE runtime_observations SET observation=?", (canonical(observed),))
    elif mismatch == "c4_refs":
        result = json.loads(case.journal.row("runtime_actions", case.parent, 3)["result"])
        result["record_refs"] = []
        case.store.db.execute("UPDATE runtime_actions SET result=? WHERE decision_index=3", (canonical(result),))
    else:
        case.store.db.execute("UPDATE runtime_progress_deliveries SET progress_refs='[]' WHERE operation_key=?",
            (f"{case.journal.run_id}:{case.parent}:3:typed_form",))
    guards(case, monkeypatch)
    with pytest.raises(ValueError, match="identity_conflict"):
        CompletionEvidence(case.store, case.journal, case.backend, case.progress).capture(case.parent,
            original_decision_index=3, unit_ref=unit, controller_input=Value(body))


def test_present_observation_is_checked_without_being_copied(case, monkeypatch):
    child = case.child(3)
    case.stage(child[2])
    saved = deepcopy(case.journal.row("runtime_observations", case.parent, 0))
    guards(case, monkeypatch)
    packet = capture(case, 3, body=child[2]["controller_input"])
    assert packet["child_return"]["admission_id"] == child[2]["admission_id"]
    assert not {"controller_step", "raw_controller_delta", "observation_state"} & packet["child_return"].keys()
    assert case.journal.row("runtime_observations", case.parent, 0) == saved


@pytest.mark.parametrize("field", ["slot", "observation", "admission"])
def test_saved_boolean_decision_identity_is_not_an_integer_index(case, monkeypatch, field):
    child = case.child(1)
    case.stage(child[2], observe=field == "observation")
    if field == "slot":
        value = case.ledger.slot(case.parent, 0)
        value["original_decision_index"] = True
        case.store.db.execute("UPDATE runtime_completion_slots SET slot=?", (canonical(value),))
    elif field == "observation":
        value = json.loads(case.journal.row("runtime_observations", case.parent, 0)["observation"])
        value["decision_index"] = True
        case.store.db.execute("UPDATE runtime_observations SET observation=?", (canonical(value),))
    else:
        value = deepcopy(child[2])
        value["original_decision_index"] = True
        case.store.db.execute("UPDATE runtime_return_admissions SET admission=?", (canonical(value),))
    guards(case, monkeypatch)
    with pytest.raises(ValueError, match="identity_conflict"):
        capture(case, 1, body=child[2]["controller_input"])


def test_pure_validation_is_detached_finite_and_rejects_extra_or_incoherent_values(case):
    child = case.child(3, progress=True)
    actual_form_delivery(case, 3, child[2])
    case.stage(child[2], observe=False)
    packet = capture(case, 3, body=child[2]["controller_input"])
    copy = validate_completion_evidence(packet, run_id=case.journal.run_id,
        episode_id=case.parent, original_decision_index=3, unit_ref=UnitRef(case.parent, 0))
    assert copy == packet and copy is not packet
    copy["progress_records"][0]["provenance_refs"].append("changed")
    assert copy != packet
    mutations = [lambda p: p.update(score=1),
        lambda p: p["child_return"].update(controller_step={}),
        lambda p: p["child_return"]["selection_to_return"].update(seconds=999),
        lambda p: p["child_return"].update(admission_id="foreign"),
        lambda p: p["child_return"].update(admission_state="delivery_failed"),
        lambda p: p["progress_records"][0]["measurements"].append({"value": float("nan")}),
        lambda p: p["progress_records"][0].update(undeclared=True),
        lambda p: p["progress_records"][0].update(progress_ref="foreign"),
        lambda p: p.update(progress_records=[])]
    for mutate in mutations:
        invalid = deepcopy(packet)
        mutate(invalid)
        with pytest.raises(ValueError, match="completion_evidence"):
            validate_completion_evidence(invalid)
    for expected in ({"run_id": "foreign"}, {"episode_id": "foreign"},
                     {"original_decision_index": 4}, {"unit_ref": UnitRef(case.parent, 4)}):
        with pytest.raises(ValueError, match="identity_conflict"):
            validate_completion_evidence(packet, **expected)


def test_construction_and_absent_legacy_c4_install_no_tables(tmp_path):
    with Store(tmp_path) as store:
        journal = Journal(store, "legacy")
        journal.save("runtime_episodes", {"episode_id": "legacy-parent", "path": "[]", "request": "{}",
            "state": "yielded", "initial_credit": 0})
        before = store.db.total_changes
        tables = list(store.db.execute("SELECT name FROM sqlite_master ORDER BY name"))
        store.db.execute("PRAGMA query_only=ON")
        CompletionEvidence(store, journal, object(), None)
        assert LocalReturnHistory(store, journal, object()).read_return("legacy-parent", 0) is None
        assert list(store.db.execute("SELECT name FROM sqlite_master ORDER BY name")) == tables
        assert store.db.total_changes == before


def test_present_progress_provider_identity_must_agree(case):
    class ForeignReader:
        run_id = "foreign"

        def read_progress(self, reference, scope):
            raise AssertionError("conflicting service must not be consulted")
    with pytest.raises(ValueError, match="identity_conflict"):
        CompletionEvidence(case.store, case.journal, case.backend, ForeignReader())


@pytest.mark.parametrize("field", ["path", "goal"])
def test_original_saved_episode_must_agree_with_current_return(case, monkeypatch, field):
    child = case.child(3)
    case.stage(child[2], observe=False)
    if field == "path":
        case.store.db.execute("UPDATE runtime_episodes SET path='[]' WHERE episode_id=?", (case.parent,))
    else:
        request = json.loads(case.journal.row("runtime_episodes", case.parent)["request"])
        request["goal"]["goal_id"] = "foreign"
        case.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?",
            (canonical(request), case.parent))
    guards(case, monkeypatch)
    with pytest.raises(ValueError, match="identity_conflict"):
        capture(case, 3, body=child[2]["controller_input"])


def test_read_return_and_completion_join_the_same_read_snapshot(case, monkeypatch):
    child = case.child(3)
    case.stage(child[2], observe=False)
    calls = []
    reader = case.store.read_snapshot

    def snapshot():
        calls.append("snapshot")
        return reader()

    monkeypatch.setattr(case.store, "read_snapshot", snapshot)
    guards(case, monkeypatch)
    capture(case, 3, body=child[2]["controller_input"])
    assert calls == ["snapshot"]


def test_reopen_reads_same_original_packet_without_live_child_state(case):
    child = case.child(3, progress=True)
    actual_form_delivery(case, 3, child[2])
    case.stage(child[2], observe=False)
    packet = capture(case, 3, body=child[2]["controller_input"])
    with Store(case.store.path) as reopened:
        journal = Journal(reopened, case.journal.run_id)
        reopened.db.execute("PRAGMA query_only=ON")
        class ImmutableReader:
            def read_progress(self, reference, scope):
                return read_progress(reopened, journal.run_id, reference, scope)
        restored = CompletionEvidence(reopened, journal, case.backend, ImmutableReader()).capture(case.parent,
            original_decision_index=3, unit_ref=UnitRef(case.parent, 0),
            controller_input=Value(child[2]["controller_input"]))
        assert restored == packet
