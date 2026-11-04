"""Factual C1 population and public C3 reads, using real isolated records.

The contents and execution ownership are synthetic fixtures. No worker,
scientific model, native job, network operation or controller is run by capture.
The contract is LOCAL_COMMISSION_FRAME_SCOPE_2026-10-22_001 and its permanent
clarifications; assertions describe that contract rather than implementation
helpers or statistical assumptions.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from method_loop.archive import ArchivedRecord, JsonArchive
from method_loop.durable import canonical, content_digest
from method_loop.identities import EpisodeRef, UnitRef

from gene_annotation_episode.episode_admission import admit_return
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.local_commission_frame import (LocalCommissionFrame,
    validate_local_commission_frame)
from gene_annotation_episode import local_commission_frame as frame_module
from gene_annotation_episode.local_return_history import LocalReturnHistory
from gene_annotation_episode.state import Store
from test_local_return_history import BINDING, Case, LATER, STAMP


CREDIT = {"credit_kind": "scientific", "credit_binding": BINDING}
TOP_FIELDS = set("version run_id episode_id parent_state_at_store_read controller_credit "
    "pending_captured_at store_read_interval population_status population_count commissions "
    "return_scan unmatched_admission_refs unavailable_reasons".split())
ROW_FIELDS = set("original_decision_index handle operation_key commission_sha256 commission "
    "selection selected_at accounting_status pending_status_fact return_presence return_metadata "
    "admission_evidence representation_attempts unavailable_reasons".split())
METADATA_FIELDS = set("return_id cursor returned_at outcome failure_code read_interval".split())
ATTEMPT_FIELDS = set("decision_index delivery_ref child_episode_id report_contract_sha256 "
    "form_recorded failure".split())
INVALID = "^local_commission_frame_invalid_input$"
CONFLICT = "^local_commission_frame_identity_conflict$"


@pytest.fixture
def case(tmp_path):
    fixture = Case(tmp_path)
    try:
        yield fixture
    finally:
        fixture.store.close()


def selected(case, index, *, publish=False, executing=False):
    """Real C1 selection; optional immutable publication and simulated claim."""
    values = deepcopy(case.base)
    values.update(original_decision_index=index, selected_at=STAMP)
    child = values["child"]
    child["key"] = "child_" + str(index)
    child["path"] = values["parent"]["path"] + [[child["role"], child["key"]]]
    child["episode_id"] = EpisodeRef(case.journal.run_id, child["path"]).episode_id
    child["request"]["message"]["knowledge_inheritance"] = case.receipts.bind(
        child["episode_id"], case.parent)
    case.journal.save("runtime_episodes", {"episode_id": child["episode_id"],
        "path": canonical(child["path"]), "request": canonical(child["request"]),
        "initial_credit": 0, "state": "active", "completion": None, "archive": None})
    spec = case.coordinator.select(**values)
    if publish or executing:
        case.backend.commission(spec)
    if executing:
        with case.backend._connect() as db:
            token = db.execute("SELECT execution_token FROM commissions WHERE handle=?",
                (spec["handle"],)).fetchone()[0]
        assert case.backend._claim(spec["handle"], token)
    return spec


def publish_private_return(case, spec, *, outcome="closed"):
    """Publish actual C3 with private unadmitted payloads, without execution."""
    with case.backend._connect() as db:
        token = db.execute("SELECT execution_token FROM commissions WHERE handle=?",
            (spec["handle"],)).fetchone()[0]
    payload = {"version": "returned_episode_v1", "handle": spec["handle"],
        "return_id": "", "commission_sha256": content_digest(spec), "returned_at": LATER,
        "outcome": outcome, "completion": None, "episode_archive": None,
        "result_archive": None, "facts_archive": None, "form": None,
        "pending_handles": ["private_pending_descendant"], "failure": None}
    if outcome == "closed":
        payload.update(completion={"ended_by": "yield_stop", "end_reason": "",
            "units_consumed": 919191}, form={"finding": "private_unadmitted_finding"},
            episode_archive=case.archive.store({"private_child_history": ["private_archive_body"]}).descriptor(),
            result_archive=case.archive.store({"child_credit": 838383,
                "records": ["private_unadmitted_record_ref"]}).descriptor(),
            facts_archive=case.archive.store({"private_facts_body": True}).descriptor())
    else:
        payload["failure"] = {"code": "execution_failed" if outcome == "execution_failed"
            else "interrupted_execution", "affected_refs": [spec["handle"]],
            "diagnostic_ref": "private_unadmitted_diagnostic_ref",
            "partial_record_refs": ["private_unadmitted_record_ref"]}
    payload["return_id"] = content_digest({k: v for k, v in payload.items() if k != "return_id"})
    receipt = case.backend.publish_return(spec["handle"], token, payload)
    return payload, receipt


class ReturnPort:
    """Expose precisely the two permitted public C3 readers, recording calls."""
    def __init__(self, backend, *, page=None, envelope=None):
        self.backend, self.page_override, self.envelope_override = backend, page, envelope
        self.pages, self.loads = [], []

    def return_page(self, episode_id, after_cursor, limit):
        self.pages.append((episode_id, after_cursor, limit))
        if self.page_override is not None:
            return self.page_override(episode_id, after_cursor, limit)
        return self.backend.return_page(episode_id, after_cursor, limit)

    def load_return(self, handle, return_id):
        self.loads.append((handle, return_id))
        if self.envelope_override is not None:
            return self.envelope_override(handle, return_id)
        return self.backend.load_return(handle, return_id)

    def __getattr__(self, name):
        raise AssertionError("non-C3 backend access: " + name)


def capture(case, *, pending=None, credit=CREDIT, page_size=2, backend=None):
    value = LocalCommissionFrame(case.store, case.journal,
        case.backend if backend is None else backend).capture(case.parent,
            pending=pending, controller_credit=credit, page_size=page_size)
    checked = validate_local_commission_frame(value, run_id=case.journal.run_id,
        episode_id=case.parent, pending=pending, controller_credit=credit)
    assert canonical(checked) == canonical(value) and checked is not value
    return value


def bracket(value):
    assert set(value) == {"started_at", "finished_at"}
    stamps = [datetime.fromisoformat(value[key].replace("Z", "+00:00"))
        for key in ("started_at", "finished_at")]
    assert all(stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0 for stamp in stamps)
    assert stamps[1] >= stamps[0]


def shape(value):
    assert set(value) == TOP_FIELDS
    assert value["version"] == "local_commission_frame_v1"
    assert json.loads(canonical(value)) == value  # Detached, finite JSON.
    bracket(value["store_read_interval"])
    scan = value["return_scan"]
    assert set(scan) == {"status", "next_cursor", "exhausted", "reads"}
    for read in scan["reads"]:
        assert set(read) == {"after_cursor", "next_cursor", "started_at", "finished_at"}
        bracket({key: read[key] for key in ("started_at", "finished_at")})
    for row in value["commissions"]:
        assert set(row) == ROW_FIELDS
        for attempt in row["representation_attempts"]:
            assert set(attempt) == ATTEMPT_FIELDS
        if row["return_metadata"] is not None:
            assert set(row["return_metadata"]) == METADATA_FIELDS
            bracket(row["return_metadata"]["read_interval"])
    return {row["original_decision_index"]: row for row in value["commissions"]}


def read_only(case, monkeypatch):
    """Fail even if a forbidden attempted read/write is caught by capture."""
    blocked = []
    def deny(*args, **kwargs):
        blocked.append((args, kwargs))
        raise AssertionError("capture attempted a forbidden side effect or archive/source hydration")
    for name in ("status", "start", "commission", "acknowledge", "publish_return",
                 "load_commission", "record_progress", "_claim", "wait_events"):
        monkeypatch.setattr(case.backend, name, deny)
    for name in ("save", "measure", "elapsed_view", "commission_returned"):
        monkeypatch.setattr(case.journal, name, deny)
    for name in ("transaction", "artifact", "put", "get", "get_artifact"):
        monkeypatch.setattr(case.store, name, deny)
    monkeypatch.setattr(case.controller, "observe", deny)
    monkeypatch.setattr(JsonArchive, "store", deny)
    monkeypatch.setattr(ArchivedRecord, "load", deny)
    monkeypatch.setattr(ArchivedRecord, "iter_json", deny)
    case.store.db.execute("PRAGMA query_only=ON")
    return blocked


def test_population_includes_every_commission_and_closed_parent_without_side_effects(case, monkeypatch):
    unpublished = selected(case, 0)
    running = selected(case, 2, executing=True)
    unadmitted = selected(case, 5, executing=True)
    unadmitted_return, unadmitted_receipt = publish_private_return(case, unadmitted)
    admitted = case.child(8, credit=3.5, progress=True)
    case.stage(admitted[2])
    failed = case.child(11, state="execution_failed")
    frozen = case.coordinator.pending(case.parent)
    closed = case.child(14, state="receiver_closed")
    original_evidence = {index: LocalReturnHistory(case.store, case.journal,
        case.backend).read_return(case.parent, index) for index in (8, 11, 14)}
    with case.backend._connect() as db:
        backend_before = list(db.iterdump())
    store_before = case.store.db.total_changes
    schema_before = list(case.store.db.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
    blocked = read_only(case, monkeypatch)
    port = ReturnPort(case.backend)
    before_time = datetime.now(timezone.utc)
    value = capture(case, pending=frozen, backend=port, page_size=1)
    after_time = datetime.now(timezone.utc)
    rows = shape(value)
    assert list(rows) == [0, 2, 5, 8, 11, 14]
    assert value["population_status"] == "complete" and value["population_count"] == 6
    assert value["parent_state_at_store_read"] == "yielded"
    assert value["run_id"] == case.journal.run_id and value["episode_id"] == case.parent
    assert value["controller_credit"] == CREDIT and value["pending_captured_at"] == frozen["captured_at"]
    facts = {item["handle"]: item for item in frozen["items"]}
    for index, spec in ((0, unpublished), (2, running), (5, unadmitted),
                        (8, admitted[0]), (11, failed[0]), (14, closed[0])):
        row = rows[index]
        assert row["commission"] == spec and row["commission_sha256"] == content_digest(spec)
        assert row["handle"] == spec["handle"] and row["operation_key"] == spec["operation_key"]
        assert row["selection"] == case.base["selection"] and row["selected_at"] == STAMP
        assert row["pending_status_fact"] == facts.get(spec["handle"])
        if index in (0, 2):
            assert row["accounting_status"] == "pending"
            assert row["return_presence"] == "not_observed_in_completed_scan"
            assert row["return_metadata"] is row["admission_evidence"] is None
        elif index == 5:
            assert row["accounting_status"] == "pending" and row["admission_evidence"] is None
            assert row["return_metadata"]["return_id"] == unadmitted_return["return_id"]
            assert row["return_metadata"]["cursor"] == unadmitted_receipt["cursor"]
        else:
            assert row["admission_evidence"] == original_evidence[index]
            assert row["return_presence"] == "observed"
    assert rows[11]["accounting_status"] == "failed"
    assert rows[11]["return_metadata"]["outcome"] == "execution_failed"
    assert rows[11]["return_metadata"]["failure_code"] == "execution_failed"
    assert rows[14]["accounting_status"] == "pending"
    assert value["return_scan"]["status"] == "complete" and value["return_scan"]["exhausted"]
    assert len(port.pages) == 5 and all(limit == 1 for _, _, limit in port.pages)
    assert len(value["return_scan"]["reads"]) == len(port.pages)
    for key in ("started_at", "finished_at"):
        assert before_time <= datetime.fromisoformat(value["store_read_interval"][key]) <= after_time
    text = canonical(value)
    for private in ("private_unadmitted_finding", "private_archive_body",
                    "private_unadmitted_record_ref", "private_pending_descendant", "child_credit",
                    "episode_archive", "result_archive", "facts_archive", "919191", "838383"):
        assert private not in text
    assert value["unmatched_admission_refs"] == [] and blocked == []
    assert case.store.db.total_changes == store_before
    assert list(case.store.db.execute("SELECT name,sql FROM sqlite_master ORDER BY name")) == schema_before
    with case.backend._connect() as db:
        assert list(db.iterdump()) == backend_before


def test_original_signed_payoff_and_completion_order_are_kept_inside_e2(case, monkeypatch):
    items = [case.child(i, credit=credit, defer_admission=True)
        for i, credit in ((1, 2.0), (4, 2.125), (9, 5.25))]
    for item in (items[2], items[0], items[1]):
        admission = admit_return(item[0], item[1], item[3])
        case.stage(admission)
    expected = {i: LocalReturnHistory(case.store, case.journal, case.backend).read_return(case.parent, i)
        for i in (1, 4, 9)}
    blocked = read_only(case, monkeypatch)
    rows = shape(capture(case, page_size=10))
    assert list(rows) == [1, 4, 9]
    assert [rows[i]["admission_evidence"] for i in rows] == [expected[i] for i in rows]
    samples = [rows[i]["admission_evidence"]["sample"] for i in (9, 1, 4)]
    assert [s["raw_controller_delta"] for s in samples] == [5.25, -3.25, 0.125]
    assert [s["completion_sequence"] for s in samples] == [0, 1, 2]
    assert [s["unit_ref"] for s in samples] == [UnitRef(case.parent, i).as_record() for i in range(3)]
    assert len({s["sample_ref"] for s in samples}) == 3 and blocked == []


def test_nonstandard_saved_step_retains_specific_e2_reason_without_deriving_gain(case):
    child = case.child(1)
    case.stage(child[2])
    saved = json.loads(case.journal.row("runtime_observations", case.parent, 0)["observation"])
    saved["step"] = {"delta": -123.5, "completed_count": 1}
    case.journal.save("runtime_observations", {"episode_id": case.parent, "unit_index": 0,
        "observation": canonical(saved)})
    evidence = shape(capture(case))[1]["admission_evidence"]
    assert evidence == LocalReturnHistory(case.store, case.journal, case.backend).read_return(case.parent, 1)
    assert evidence["sample"]["raw_controller_delta"] is None
    assert evidence["sample"]["controller_step"] == saved["step"]
    assert "standard_controller_marginal_credit_unavailable" in evidence["unavailable_reasons"]


def test_pending_facts_and_credit_binding_are_frozen_detached_inputs(case):
    spec = selected(case, 3, executing=True)
    pending = case.coordinator.pending(case.parent)
    assert pending["items"][0]["lifecycle_state"] == "executing"
    credit = deepcopy(CREDIT)
    original_pending, original_credit = deepcopy(pending), deepcopy(credit)
    publish_private_return(case, spec)
    first = capture(case, pending=pending, credit=credit)
    row = shape(first)[3]
    assert row["pending_status_fact"] == original_pending["items"][0]
    assert row["return_presence"] == "observed"
    pending["items"][0]["resource_selection"]["allocation"]["cpu"] = 99
    credit["credit_binding"]["unit"] = "changed-after-capture"
    assert row["pending_status_fact"] == original_pending["items"][0]
    assert first["controller_credit"] == original_credit
    row["commission"]["constraints"]["caller_cpu"] = 99
    row["pending_status_fact"]["expectation_snapshot_refs"].append("mutated-output")
    second = capture(case, pending=original_pending, credit=original_credit)
    assert shape(second)[3]["commission"] == spec
    assert shape(second)[3]["pending_status_fact"] == original_pending["items"][0]


def test_null_inputs_remain_unknown_without_inferred_units_or_status(case):
    selected(case, 2)
    value = capture(case, pending=None, credit=None)
    row = shape(value)[2]
    assert value["controller_credit"] is value["pending_captured_at"] is None
    assert row["pending_status_fact"] is None
    assert {"pending_snapshot_unavailable", "controller_credit_binding_unavailable"} <= set(value["unavailable_reasons"])


@pytest.mark.parametrize("missing", ["row", "table"])
def test_known_c1_survives_missing_original_action_support(case, missing):
    spec = selected(case, 2)
    case.store.db.execute("DROP TABLE runtime_actions" if missing == "table"
        else "DELETE FROM runtime_actions WHERE decision_index=2")
    value = capture(case)
    row = shape(value)[2]
    assert value["population_status"] == "complete" and value["population_count"] == 1
    assert row["commission"] == spec and row["accounting_status"] is None
    assert "original_action_unavailable" in row["unavailable_reasons"]


def test_existing_empty_population_is_complete_without_backend_reads(case):
    port = ReturnPort(case.backend)
    value = capture(case, backend=port)
    shape(value)
    assert value["population_status"] == "complete" and value["population_count"] == 0
    assert value["commissions"] == [] and port.pages == port.loads == []
    assert value["return_scan"] == {"status": "complete", "next_cursor": 0,
        "exhausted": False, "reads": []}


def test_absent_population_does_not_fabricate_empty_support_or_backend_scan(case, monkeypatch):
    case.store.db.execute("DROP TABLE runtime_commission_intents")
    before = case.store.db.total_changes
    blocked = read_only(case, monkeypatch)
    port = ReturnPort(case.backend)
    value = capture(case, backend=port)
    shape(value)
    assert value["population_status"] == "unavailable" and value["population_count"] is None
    assert value["commissions"] == [] and "commission_population_unavailable" in value["unavailable_reasons"]
    assert value["return_scan"]["status"] == "unavailable" and not value["return_scan"]["exhausted"]
    assert port.pages == port.loads == [] and blocked == []
    assert case.store.db.total_changes == before


def test_unmatched_admission_is_a_diagnostic_and_never_an_invented_commission(case):
    orphan = case.child(2)
    case.stage(orphan[2])
    case.store.db.execute("DELETE FROM runtime_commission_intents WHERE original_decision_index=2")
    value = capture(case)
    assert shape(value) == {} and value["population_count"] == 0
    assert value["unmatched_admission_refs"] == [orphan[2]["admission_id"]]
    assert "unmatched_admissions" in value["unavailable_reasons"]


@pytest.mark.parametrize("identity", ["parent_episode_id", "original_decision_index", "handle", "return_id", "admission_id"])
def test_unmatched_admission_body_still_must_agree_with_its_physical_c4_row(case, identity):
    orphan = case.child(2)
    case.store.db.execute("DELETE FROM runtime_commission_intents WHERE original_decision_index=2")
    altered = deepcopy(orphan[2])
    altered[identity] = 19 if identity == "original_decision_index" else "foreign-identity"
    case.store.db.execute("UPDATE runtime_return_admissions SET admission=?", (canonical(altered),))
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case)


def test_page_window_is_not_population_cap_and_stops_when_all_returns_are_seen(case):
    for i in range(5):
        publish_private_return(case, selected(case, i, executing=True))
    port = ReturnPort(case.backend)
    value = capture(case, page_size=2, backend=port)
    rows = shape(value)
    assert value["population_count"] == len(rows) == 5
    assert [limit for _, _, limit in port.pages] == [2, 2, 1]
    assert [after for _, after, _ in port.pages] == [0] + [
        read["next_cursor"] for read in value["return_scan"]["reads"][:-1]]
    assert value["return_scan"]["status"] == "complete" and not value["return_scan"]["exhausted"]
    assert all(row["return_presence"] == "observed" and row["admission_evidence"] is None for row in rows.values())
    assert all(read["next_cursor"] > read["after_cursor"] for read in value["return_scan"]["reads"])
    for row in rows.values():
        metadata = row["return_metadata"]
        observing_read = next(read for read in value["return_scan"]["reads"]
            if read["after_cursor"] < metadata["cursor"] <= read["next_cursor"])
        assert metadata["read_interval"] == {key: observing_read[key]
            for key in ("started_at", "finished_at")}
        assert metadata["returned_at"] == LATER


@pytest.mark.parametrize("successful_pages", [0, 1])
def test_page_failure_preserves_known_returns_and_truthful_unknown_presence(case, successful_pages):
    for i in (1, 2):
        publish_private_return(case, selected(case, i, executing=True))
    selected(case, 3)
    calls = []
    def flaky(parent, after, limit):
        calls.append(after)
        if len(calls) > successful_pages:
            raise OSError("synthetic page read unavailable")
        return case.backend.return_page(parent, after, limit)
    port = ReturnPort(case.backend, page=flaky)
    value = capture(case, backend=port, page_size=1)
    rows = shape(value)
    scan = value["return_scan"]
    assert scan["status"] == ("incomplete" if successful_pages else "unavailable")
    assert not scan["exhausted"] and "return_scan_unavailable" in value["unavailable_reasons"]
    assert scan["reads"][-1]["next_cursor"] is None
    assert scan["reads"][-1]["after_cursor"] == scan["next_cursor"]
    assert scan["next_cursor"] == (0 if not successful_pages else scan["reads"][0]["next_cursor"])
    assert len(scan["reads"]) == successful_pages + 1
    for index, row in rows.items():
        observed = successful_pages and index == 1
        assert row["return_presence"] == ("observed" if observed else "unknown")
        assert (row["return_metadata"] is not None) == bool(observed)


@pytest.mark.parametrize("failure", [KeyError("gone"), OSError("offline"), ValueError("unreadable")])
def test_envelope_read_failure_keeps_page_identity_timestamp_and_interval(case, failure):
    spec = selected(case, 1, executing=True)
    payload, receipt = publish_private_return(case, spec)
    def unavailable(handle, return_id):
        raise failure
    port = ReturnPort(case.backend, envelope=unavailable)
    value = capture(case, backend=port)
    row = shape(value)[1]
    assert value["return_scan"]["status"] == "complete" and row["return_presence"] == "observed"
    assert row["return_metadata"] == {"return_id": payload["return_id"], "cursor": receipt["cursor"],
        "returned_at": LATER, "outcome": None, "failure_code": None,
        "read_interval": {key: value["return_scan"]["reads"][0][key]
            for key in ("started_at", "finished_at")}}
    assert row["admission_evidence"] is None and "return_envelope_unavailable" in row["unavailable_reasons"]
    assert port.loads == [(spec["handle"], payload["return_id"])]


def test_c3_read_failure_retains_original_observed_payoff_and_e2_specific_reason(case):
    child = case.child(1, credit=2.75)
    case.stage(child[2])
    def unavailable(handle, return_id):
        raise OSError("original immutable return currently unavailable")
    value = capture(case, backend=ReturnPort(case.backend, envelope=unavailable))
    row = shape(value)[1]
    evidence = row["admission_evidence"]
    assert evidence["sample"]["admission_id"] == child[2]["admission_id"]
    assert evidence["sample"]["raw_controller_delta"] == 2.75
    assert evidence["sample"]["returned_at"] is None
    assert "original_return_read_unavailable" in evidence["unavailable_reasons"]
    assert row["return_presence"] == "observed" and row["return_metadata"]["returned_at"] == LATER
    assert row["return_metadata"]["outcome"] is row["return_metadata"]["failure_code"] is None
    assert "return_envelope_unavailable" in row["unavailable_reasons"]


def test_return_outside_c1_snapshot_is_incomplete_and_gets_no_invented_row(case):
    outside = selected(case, 8, executing=True)
    outside_return, _ = publish_private_return(case, outside)
    inside = selected(case, 2, executing=True)
    publish_private_return(case, inside)
    case.store.db.execute("DELETE FROM runtime_commission_intents WHERE original_decision_index=8")
    port = ReturnPort(case.backend)
    value = capture(case, backend=port, page_size=1)
    rows = shape(value)
    assert list(rows) == [2] and value["population_count"] == 1
    assert rows[2]["return_presence"] == "unknown" and rows[2]["return_metadata"] is None
    assert value["return_scan"]["status"] == "incomplete"
    assert "return_outside_commission_snapshot" in value["unavailable_reasons"]
    assert outside_return["return_id"] not in canonical(value)
    assert (outside["handle"], outside_return["return_id"]) not in port.loads
    assert [limit for _, _, limit in port.pages] == [1]


def test_outside_snapshot_page_retains_same_page_known_metadata_and_stops(case):
    outside = selected(case, 8, executing=True)
    publish_private_return(case, outside)
    inside = selected(case, 2, executing=True)
    payload, receipt = publish_private_return(case, inside)
    selected(case, 3)
    case.store.db.execute("DELETE FROM runtime_commission_intents WHERE original_decision_index=8")
    port = ReturnPort(case.backend)
    value = capture(case, backend=port, page_size=20)
    rows = shape(value)
    assert list(rows) == [2, 3] and value["population_count"] == 2
    assert rows[2]["return_presence"] == "observed"
    assert rows[2]["return_metadata"]["return_id"] == payload["return_id"]
    assert rows[2]["return_metadata"]["cursor"] == receipt["cursor"]
    assert rows[3]["return_presence"] == "unknown" and rows[3]["return_metadata"] is None
    assert value["return_scan"]["status"] == "incomplete" and not value["return_scan"]["exhausted"]
    assert [limit for _, _, limit in port.pages] == [2]
    assert port.loads == [(inside["handle"], payload["return_id"])]


def test_original_failed_delivery_and_signed_delta_survive_later_repair_attempts(case):
    failed = case.child(2, state="delivery_failed", credit=1.5)
    case.stage(failed[2])
    saved = dict(case.store.db.execute("SELECT * FROM runtime_report_attempts WHERE decision_index=2").fetchone())
    changed_contract = deepcopy(failed[0]["child"]["request"]["report_contract"])
    changed_contract["decision"] = "Later repaired requested representation"
    later_failure = {"kind": "report_delivery_failure", "delivery_ref": saved["delivery_ref"],
        "reason": "recorded_interpretation_unavailable", "field": "other"}
    for index, form, failure in ((7, None, later_failure),
        (12, {"records": ["private_repaired_record"], "updates": [], "other": "private_repaired_form"}, None)):
        case.journal.save("runtime_report_attempts", {"parent_episode_id": case.parent,
            "decision_index": index, "delivery_ref": saved["delivery_ref"],
            "child_episode_id": failed[0]["child"]["episode_id"], "contract": canonical(changed_contract),
            "form": None if form is None else canonical(form),
            "failure": None if failure is None else canonical(failure)})
    original = LocalReturnHistory(case.store, case.journal, case.backend).read_return(case.parent, 2)
    value = capture(case)
    row = shape(value)[2]
    assert row["admission_evidence"] == original
    assert original["sample"]["admission_state"] == "delivery_failed"
    assert original["sample"]["raw_controller_delta"] == 1.5
    assert original["sample"]["received_record_refs"] == []
    assert [attempt["decision_index"] for attempt in row["representation_attempts"]] == [2, 7, 12]
    assert [attempt["form_recorded"] for attempt in row["representation_attempts"]] == [False, False, True]
    assert [attempt["failure"] for attempt in row["representation_attempts"]] == [
        json.loads(saved["failure"]), later_failure, None]
    assert [attempt["report_contract_sha256"] for attempt in row["representation_attempts"]] == [
        content_digest(json.loads(saved["contract"])), content_digest(changed_contract), content_digest(changed_contract)]
    assert all(attempt["delivery_ref"] == saved["delivery_ref"] and attempt["child_episode_id"] ==
        failed[0]["child"]["episode_id"] for attempt in row["representation_attempts"])
    assert "private_repaired_form" not in canonical(value) and "private_repaired_record" not in canonical(value)


def test_missing_report_attempt_table_is_explicit_and_preserves_c1(case):
    selected(case, 1)
    case.store.db.execute("DROP TABLE runtime_report_attempts")
    row = shape(capture(case))[1]
    assert row["representation_attempts"] == [] and "report_attempts_unavailable" in row["unavailable_reasons"]


def test_missing_saved_child_record_preserves_original_c1_with_specific_support_reason(case):
    spec = selected(case, 1)
    case.store.db.execute("DELETE FROM runtime_episodes WHERE episode_id=?", (spec["child"]["episode_id"],))
    value = capture(case)
    row = shape(value)[1]
    assert value["population_status"] == "complete" and value["population_count"] == 1
    assert row["commission"] == spec and "child_record_unavailable" in row["unavailable_reasons"]


def test_capture_joins_existing_store_snapshot_without_committing_it(case):
    spec = selected(case, 1)
    with case.store.read_snapshot():
        case.store.db.execute("SELECT state FROM runtime_episodes WHERE episode_id=?", (case.parent,)).fetchone()
        with Store(case.store.path) as concurrent:
            concurrent.db.execute("UPDATE runtime_episodes SET state='yielded' WHERE episode_id=?", (case.parent,))
            concurrent.db.execute("DELETE FROM runtime_actions WHERE episode_id=?", (case.parent,))
        first = capture(case)
        assert case.store.db.in_transaction
        assert first["parent_state_at_store_read"] == "active"
        assert shape(first)[1]["accounting_status"] == "pending"
    second = capture(case)
    assert second["parent_state_at_store_read"] == "yielded"
    assert shape(second)[1]["commission"] == spec
    assert shape(second)[1]["accounting_status"] is None


@pytest.mark.parametrize("change", ["digest", "handle", "operation", "run", "parent_goal",
    "parent_path", "child_path", "child_request", "selection", "pending_action_handle"])
def test_present_saved_identity_conflicts_raise_component_error_without_writes(case, monkeypatch, change):
    spec = selected(case, 1)
    if change in {"digest", "handle", "operation"}:
        field = {"digest": "commission_sha256", "handle": "handle", "operation": "operation_key"}[change]
        case.store.db.execute("UPDATE runtime_commission_intents SET " + field + "=?", ("c" * 64,))
    elif change == "run":
        altered = deepcopy(spec)
        altered["run_id"] = "foreign-run"
        case.store.db.execute("UPDATE runtime_commission_intents SET spec=?,commission_sha256=?",
            (canonical(altered), content_digest(altered)))
    elif change in {"parent_goal", "child_request"}:
        episode = case.parent if change == "parent_goal" else spec["child"]["episode_id"]
        request = json.loads(case.journal.row("runtime_episodes", episode)["request"])
        if change == "parent_goal":
            request["goal"]["goal_id"] = "foreign-goal"
        else:
            request["message"]["initial_report"] = {"finding": "qualified"}
        case.store.db.execute("UPDATE runtime_episodes SET request=? WHERE episode_id=?", (canonical(request), episode))
    elif change in {"parent_path", "child_path"}:
        episode = case.parent if change == "parent_path" else spec["child"]["episode_id"]
        case.store.db.execute("UPDATE runtime_episodes SET path=? WHERE episode_id=?",
            (canonical([["annotation", "foreign"]]), episode))
    elif change == "selection":
        case.store.db.execute("UPDATE runtime_actions SET action=?", (canonical({"kind": "child", "goal": "foreign"}),))
    else:
        case.store.db.execute("UPDATE runtime_actions SET result=?", (canonical({"status": "pending",
            "pending_handle": "foreign-handle", "selected_at": STAMP}),))
    before = case.store.db.total_changes
    blocked = read_only(case, monkeypatch)
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case)
    assert blocked == [] and case.store.db.total_changes == before


@pytest.mark.parametrize("change", ["handle", "return_id", "digest", "timestamp"])
def test_return_envelope_must_match_page_and_original_commission(case, change):
    spec = selected(case, 1, executing=True)
    returned, _ = publish_private_return(case, spec)
    altered = deepcopy(returned)
    if change == "timestamp":
        altered["returned_at"] = "2026-10-21T12:00:13+00:00"
        altered["return_id"] = content_digest({key: item for key, item in altered.items() if key != "return_id"})
        def changed_page(parent, after, limit):
            page = case.backend.return_page(parent, after, limit)
            for item in page["items"]:
                item["return_id"] = altered["return_id"]
            return page
    else:
        altered[{"handle": "handle", "return_id": "return_id", "digest": "commission_sha256"}[change]] = "d" * 64
        changed_page = None
    port = ReturnPort(case.backend, page=changed_page, envelope=lambda handle, return_id: altered)
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case, backend=port)


@pytest.mark.parametrize("change", ["duplicate_handle", "duplicate_cursor", "nonadvancing", "wrong_after",
    "empty_advances", "extra_page_field", "invalid_timestamp", "too_many"])
def test_malformed_or_conflicting_pages_are_errors_instead_of_false_absence(case, change):
    for index in (1, 2):
        publish_private_return(case, selected(case, index, executing=True))
    def malformed(parent, after, limit):
        page = case.backend.return_page(parent, after, limit)
        if change == "duplicate_handle":
            page["items"][1]["handle"] = page["items"][0]["handle"]
        elif change == "duplicate_cursor":
            page["items"][1]["cursor"] = page["items"][0]["cursor"]
            page["next_cursor"] = page["items"][-1]["cursor"]
        elif change == "nonadvancing":
            page["next_cursor"] = after
        elif change == "wrong_after":
            page["after_cursor"] = after + 1
        elif change == "empty_advances":
            page["items"] = []
            page["next_cursor"] = after + 1
        elif change == "extra_page_field":
            page["observed_at"] = LATER
        elif change == "invalid_timestamp":
            page["items"][0]["returned_at"] = "2026-10-21T12:00:00-05:00"
        else:
            page["items"].append(deepcopy(page["items"][-1]))
        return page
    with pytest.raises(ValueError, match="^local_commission_frame_(identity_conflict|invalid_input)$"):
        capture(case, backend=ReturnPort(case.backend, page=malformed), page_size=2)


@pytest.mark.parametrize("page_size", [0, -1, True, 1.5, "2", None])
def test_page_size_is_explicit_positive_integer(case, page_size):
    with pytest.raises(ValueError, match=INVALID):
        capture(case, page_size=page_size)


@pytest.mark.parametrize("credit", [{}, [], {"credit_kind": "scientific"},
    {"credit_kind": "job_monitor", "credit_binding": BINDING},
    {"credit_kind": "scientific", "credit_binding": {}},
    {"credit_kind": "scientific", "credit_binding": {"nonfinite": float("inf")}},
    {"credit_kind": "scientific", "credit_binding": BINDING, "inferred_units": True}])
def test_controller_credit_requires_exact_existing_finite_binding_shape(case, credit):
    with pytest.raises(ValueError, match=INVALID):
        capture(case, credit=credit)


def test_connection_run_and_episode_input_validation_uses_declared_error(case, tmp_path):
    with Store(tmp_path / "other") as other:
        with pytest.raises(ValueError, match=INVALID):
            LocalCommissionFrame(other, case.journal, case.backend)
    journal = Journal(case.store, "")
    with pytest.raises(ValueError, match=INVALID):
        LocalCommissionFrame(case.store, journal, case.backend)
    reader = LocalCommissionFrame(case.store, case.journal, case.backend)
    for episode_id in (None, "", "not-an-actual-parent"):
        with pytest.raises(ValueError, match=INVALID):
            reader.capture(episode_id, pending=None, controller_credit=CREDIT, page_size=1)


@pytest.mark.parametrize("change", ["shape", "duplicate", "foreign_handle", "role", "selected_at", "resource"])
def test_pending_input_shape_or_present_identity_conflict_is_rejected(case, change):
    selected(case, 1)
    pending = case.coordinator.pending(case.parent)
    if change == "shape":
        pending["invented"] = True
    elif change == "duplicate":
        pending["items"].append(deepcopy(pending["items"][0]))
    elif change == "foreign_handle":
        pending["items"][0]["handle"] = "foreign-handle"
    elif change == "role":
        pending["items"][0]["role"] = "job_monitor"
    elif change == "selected_at":
        pending["items"][0]["selected_at"] = LATER
    else:
        pending["items"][0]["resource_selection"]["allocation"]["cpu"] = 19
    with pytest.raises(ValueError, match="^local_commission_frame_(identity_conflict|invalid_input)$"):
        capture(case, pending=pending)


@pytest.mark.parametrize("replacement", [True, 1.0])
def test_original_action_json_identity_does_not_coerce_boolean_or_float_to_integer(case, replacement):
    case.base["selection"]["fixture_original_operand"] = 1
    selected(case, 1)
    altered = deepcopy(case.base["selection"])
    altered["fixture_original_operand"] = replacement
    assert altered == case.base["selection"]  # Python equality would erase the change.
    assert canonical(altered) != canonical(case.base["selection"])
    case.store.db.execute("UPDATE runtime_actions SET action=?", (canonical(altered),))
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case)


def test_original_pending_resource_json_identity_does_not_coerce_number_shape(case):
    case.base["resource_selection"]["allocation"]["wall_seconds"] = 1
    selected(case, 1)
    pending = case.coordinator.pending(case.parent)
    pending["items"][0]["resource_selection"]["allocation"]["wall_seconds"] = 1.0
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case, pending=pending)


@pytest.mark.parametrize("replacement", [True, 1.0])
def test_original_attempt_contract_digest_distinguishes_json_numeric_identity(case, replacement):
    case.base["child"]["request"]["report_contract"]["measurements"]["fixture_original_operand"] = 1
    spec = selected(case, 1)
    altered = deepcopy(spec["child"]["request"]["report_contract"])
    altered["measurements"]["fixture_original_operand"] = replacement
    delivery = "delivery_" + content_digest({"run": case.journal.run_id, "parent": case.parent, "index": 1})[:24]
    case.journal.save("runtime_report_attempts", {"parent_episode_id": case.parent,
        "decision_index": 1, "delivery_ref": delivery, "child_episode_id": spec["child"]["episode_id"],
        "contract": canonical(altered), "form": None,
        "failure": canonical({"kind": "report_delivery_failure", "delivery_ref": delivery,
            "reason": "recorded_interpretation_unavailable", "field": "finding"})})
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case)


@pytest.mark.parametrize("location", ["store", "page"])
def test_backward_utc_read_bracket_is_specific_clock_order_failure(case, monkeypatch, location):
    earlier = "2026-10-21T11:59:59+00:00"
    if location == "page":
        selected(case, 1)
        stamps = iter([STAMP, STAMP, earlier])
    else:
        stamps = iter([STAMP, earlier])
    monkeypatch.setattr(frame_module, "_now", lambda: next(stamps))
    with pytest.raises(ValueError, match="^local_commission_frame_clock_order_failure$"):
        capture(case)


def test_repeated_handle_across_validly_advancing_pages_is_an_identity_error(case):
    spec = selected(case, 1, executing=True)
    returned, receipt = publish_private_return(case, spec)
    selected(case, 2)
    def repeated(parent, after, limit):
        if after == 0:
            return case.backend.return_page(parent, after, limit)
        cursor = after + 1
        return {"version": "return_page_v1", "after_cursor": after, "next_cursor": cursor,
            "items": [{"cursor": cursor, "handle": spec["handle"],
                "return_id": returned["return_id"], "returned_at": LATER}]}
    with pytest.raises(ValueError, match=CONFLICT):
        capture(case, backend=ReturnPort(case.backend, page=repeated), page_size=1)


@pytest.fixture(scope="module")
def saved_frame(tmp_path_factory):
    directory = tmp_path_factory.mktemp("actual-frame-validation")
    fixture = Case(directory)
    try:
        for index, credit in ((0, 5.0), (2, 2.0)):
            item = fixture.child(index, credit=credit)
            fixture.stage(item[2])
        spec = selected(fixture, 4, executing=True)
        publish_private_return(fixture, spec)
        selected(fixture, 6)
        pending = fixture.coordinator.pending(fixture.parent)
        value = capture(fixture, pending=pending, page_size=2)
        (directory / "original-frame.json").write_text(json.dumps(value, indent=2)+"\n")
        yield value, {"run_id": fixture.journal.run_id, "episode_id": fixture.parent,
                      "pending": pending, "controller_credit": deepcopy(CREDIT)}
    finally:
        fixture.store.close()


def test_pure_saved_frame_validates_without_capture_clock_or_backend(saved_frame, monkeypatch):
    value, arguments = saved_frame
    def forbidden(*args, **kwargs):
        raise AssertionError("pure validation obtained newer facts")
    monkeypatch.setattr(frame_module, "_now", forbidden)
    monkeypatch.setattr(LocalCommissionFrame, "capture", forbidden)
    original = canonical(value)
    checked = validate_local_commission_frame(value, **arguments)
    assert canonical(checked) == original
    assert checked["commissions"][1]["admission_evidence"]["sample"]["raw_controller_delta"] == -3.0
    checked["commissions"][0]["commission"]["constraints"]["caller_cpu"] = 987
    checked["controller_credit"]["credit_binding"]["unit"] = "changed-copy"
    assert canonical(value) == original
    assert arguments["controller_credit"] == CREDIT


def alter(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


@pytest.mark.parametrize("path,replacement,error", [
    (("version",), "unknown", INVALID),
    (("extra",), None, INVALID),
    (("population_count",), True, INVALID),
    (("population_count",), 99, CONFLICT),
    (("run_id",), "foreign-run", CONFLICT),
    (("pending_captured_at",), LATER, CONFLICT),
    (("controller_credit", "credit_binding", "unit"), "another-unit", CONFLICT),
    (("controller_credit", "credit_binding", 7), "non-string-key", INVALID),
    (("controller_credit", "credit_binding", "bad"), float("nan"), INVALID),
    (("store_read_interval", "started_at"), "not-a-time", INVALID),
    (("store_read_interval", "finished_at"), STAMP, INVALID),
    (("commissions", 0, "original_decision_index"), False, INVALID),
    (("commissions", 0, "commission_sha256"), "c"*64, CONFLICT),
    (("commissions", 0, "handle"), "foreign-execution", CONFLICT),
    (("commissions", 0, "operation_key"), "foreign-operation", CONFLICT),
    (("commissions", 0, "selection", "kind"), "tool", INVALID),
    (("commissions", 0, "selection", "goal"), "foreign goal", CONFLICT),
    (("commissions", 0, "selection", "role"), "foreign_role", CONFLICT),
    (("commissions", 0, "return_presence"), "not_observed_in_completed_scan", CONFLICT),
    (("commissions", 0, "return_metadata", "outcome"), {}, INVALID),
    (("commissions", 0, "return_metadata", "read_interval", "finished_at"), LATER, INVALID),
    (("commissions", 0, "return_metadata", "returned_at"), STAMP, CONFLICT),
    (("commissions", 0, "return_metadata", "cursor"), True, INVALID),
    (("commissions", 0, "return_metadata", "cursor"), 999, CONFLICT),
    (("commissions", 0, "admission_evidence", "sample", "admission_id"), "admission_"+"f"*64, CONFLICT),
    (("commissions", 0, "admission_evidence", "sample", "raw_controller_delta"), 999, CONFLICT),
    (("commissions", 0, "admission_evidence", "sample", "completion_sequence"), 91, CONFLICT),
    (("commissions", 0, "representation_attempts", 0, "delivery_ref"), "foreign", CONFLICT),
    (("commissions", 0, "representation_attempts", 0, "report_contract_sha256"), "d"*64, CONFLICT),
    (("commissions", 0, "representation_attempts", 0, "form_recorded"), 1, INVALID),
    (("commissions", 2, "pending_status_fact"), None, CONFLICT),
    (("return_scan", "next_cursor"), 999, CONFLICT),
    (("return_scan", "reads", 0, "after_cursor"), 1, CONFLICT),
    (("return_scan", "reads", 0, "next_cursor"), None, CONFLICT),
    (("return_scan", "exhausted"), 1, INVALID),
    (("return_scan", "status"), "incomplete", CONFLICT),
])
def test_saved_frame_rejects_malformed_shapes_and_available_identity_conflicts(saved_frame, path, replacement, error):
    original, arguments = saved_frame
    value = deepcopy(original)
    alter(value, path, replacement)
    with pytest.raises(ValueError, match=error):
        validate_local_commission_frame(value, **arguments)


def test_saved_frame_order_uniqueness_and_repair_failure_object_are_exact(saved_frame):
    original, arguments = saved_frame
    swapped = deepcopy(original)
    swapped["commissions"][0:2] = reversed(swapped["commissions"][0:2])
    with pytest.raises(ValueError, match=CONFLICT):
        validate_local_commission_frame(swapped, **arguments)
    value = deepcopy(original)
    attempt = deepcopy(value["commissions"][0]["representation_attempts"][0])
    attempt.update(decision_index=19, form_recorded=False,
        failure={"arbitrary_original_diagnostic": {"precise": [-12.5, None, False]}, "other": "retained"})
    value["commissions"][0]["representation_attempts"].append(attempt)
    assert validate_local_commission_frame(value, **arguments) == value
    value["commissions"][0]["representation_attempts"].append(deepcopy(attempt))
    with pytest.raises(ValueError, match=CONFLICT):
        validate_local_commission_frame(value, **arguments)


def test_saved_frame_never_treats_unknown_pending_as_an_empty_snapshot(saved_frame):
    original, arguments = saved_frame
    with pytest.raises(ValueError, match=CONFLICT):
        validate_local_commission_frame(original, **{**arguments, "pending": None})
    value = deepcopy(original)
    value["pending_captured_at"] = None
    value["unavailable_reasons"].append("pending_snapshot_unavailable")
    for row in value["commissions"]:
        row["pending_status_fact"] = None
    assert validate_local_commission_frame(value, **{**arguments, "pending": None}) == value
