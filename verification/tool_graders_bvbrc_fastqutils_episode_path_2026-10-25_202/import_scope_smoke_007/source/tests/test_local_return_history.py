"""Actual saved C1/C3/C4/F2/C6 records and standard signed controller steps.

The child forms, credit units and event deliveries are engineering fixtures.
No scientific model, child worker or native scientific job is run here.
"""
import asyncio
from copy import deepcopy
from dataclasses import dataclass
import json

import pytest

from method_loop import ClosedRecord
from method_loop.archive import JsonArchive
from method_loop.durable import DurableExecutionStore, canonical, content_digest
from method_loop.identities import EpisodeRef, UnitRef

from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_commissions import CommissionCoordinator
from gene_annotation_episode.episode_completion import CompletionLedger
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import FIELDS, ProgressProvider
from gene_annotation_episode.local_return_history import LocalReturnHistory, VERSION
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.runtime import TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.waiting import WaitStore, estimate_wait
from test_episode_commissions import setup_case


STAMP = "2026-10-21T12:00:00+00:00"
LATER = "2026-10-21T12:00:12.125000+00:00"
BINDING = {"version": "caller_fixture_units_v1", "unit": "received_contribution"}


@dataclass(frozen=True)
class Value(ClosedRecord):
    value: dict

    def as_record(self):
        return self.value


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


SCHEMA = obj({"records": {"type": "array", "items": {"type": "string", "format": "reference"}},
    "updates": {"type": "array", "items": obj({"ref": {"type": "string",
        "format": "reference", "x-reference-namespace": "episode_progress"}})},
    "other": {"type": "string", "format": "identifier"}})


class Case:
    def __init__(self, tmp_path):
        self.store, self.journal, backend, self.base, self.receipts = setup_case(tmp_path)
        self.backend = backend.durable
        self.coordinator = CommissionCoordinator(self.store, self.journal, self.backend)
        self.ledger = CompletionLedger(self.store, self.journal)
        self.progress = ProgressProvider(self.store, self.backend, run_id=self.journal.run_id)
        WaitStore(self.store, self.journal.run_id)
        self.controller = YieldController("fixture-epoch", 0, 0)
        self.archive = JsonArchive(tmp_path / "archives")
        self.parent = self.base["parent"]["episode_id"]

    def child(self, index, *, role="improvement", selected_at=STAMP, returned_at=LATER,
              credit=5.25, state="admitted", progress=False, defer_admission=False):
        values = deepcopy(self.base)
        values.update(original_decision_index=index, selected_at=selected_at)
        key = "child_" + str(index)
        path = values["parent"]["path"] + [[role, key]]
        child_id = EpisodeRef(self.journal.run_id, path).episode_id
        contract = TypedReportContract("Return selected information", deepcopy(SCHEMA),
            lambda ref, namespace=None: True)
        child = values["child"]
        child.update(episode_id=child_id, role=role, key=key, path=path)
        child["request"]["report_contract"] = contract.as_record()
        child["request"]["message"]["initial_report"] = {"records": [], "updates": [], "other": "unknown"}
        child["request"]["message"]["knowledge_inheritance"] = self.receipts.bind(child_id, self.parent)
        self.journal.save("runtime_episodes", {"episode_id": child_id, "path": canonical(path),
            "request": canonical(child["request"]), "initial_credit": 0, "state": "yielded",
            "completion": None, "archive": None})
        spec = self.coordinator.select(**values)
        self.backend.commission(spec)
        # Register this fixture process as the recorded owner, without starting
        # a worker or invoking the selected reconstruction factory.
        with self.backend._connect() as db:
            token = db.execute("SELECT execution_token FROM commissions WHERE handle=?",
                (spec["handle"],)).fetchone()[0]
        assert self.backend._claim(spec["handle"], token)
        update = (self.progress.observe(spec["handle"], list(FIELDS), child["scope"],
            operation_key="original-observation:" + str(index)) if progress else None)
        source = self.base["input_versions"][0]["reference"]
        form = {"records": [source], "updates": [] if update is None else [{"ref": update["progress_ref"]}],
                "other": "progress_undeclared_value"}
        returned = {"version": "returned_episode_v1", "handle": spec["handle"],
            "return_id": "", "commission_sha256": content_digest(spec), "returned_at": returned_at,
            "outcome": "closed", "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 17},
            "episode_archive": self.archive.store({"private_child_history": ["must not hydrate"]}).descriptor(),
            "result_archive": self.archive.store({"private_child_result": "must not hydrate"}).descriptor(),
            "facts_archive": None, "form": deepcopy(form), "pending_handles": [], "failure": None}
        if state == "delivery_failed":
            returned["form"]["records"] = "invalid_not_an_array"
        elif state == "execution_failed":
            returned.update(outcome="execution_failed", completion=None, episode_archive=None,
                result_archive=None, form=None, failure={"code": "execution_failed",
                    "affected_refs": [spec["handle"]], "diagnostic_ref": None,
                    "partial_record_refs": [source]})
        returned["return_id"] = content_digest({k: v for k, v in returned.items() if k != "return_id"})
        self.backend.publish_return(spec["handle"], token, returned)

        def receive(report):
            self.receipts.receive(self.parent, report["records"], kind="child_form", source_index=index)
            self.progress.receive_form(self.parent, report, SCHEMA, child["scope"], "return:" + str(index))
            return report["records"]

        def project():
            if state in {"execution_failed", "receiver_closed"}:
                raise AssertionError("unobserved failure must not project")
            return credit

        receiver = ReceiverBindingV1(self.store, self.journal, index, contract, lambda form: None,
            receive, project, lambda decision, score: Value({"credit": score,
                "estimation_action_index": decision, "original_context": {"unknown_queue_wait": None}}))
        if state == "receiver_closed":
            self.store.db.execute("UPDATE runtime_episodes SET state='yielded' WHERE run_id=? AND episode_id=?",
                (self.journal.run_id, self.parent))
        admission = None if defer_admission else admit_return(spec, returned, receiver)
        if admission is not None:
            assert admission["state"] == state
        return spec, returned, admission, receiver

    def stage(self, admission, *, observe=True):
        slot = self.ledger.stage(self.parent, admission["original_decision_index"],
            label="child:" + str(admission["original_decision_index"]), kind="child_return",
            controller_input=Value(admission["controller_input"]),
            child_return={key: admission[key] for key in ("handle", "return_id", "admission_id")})
        if observe:
            step = self.controller.observe(slot["label"], Value(slot["controller_input"]), is_root=True)
            self.ledger.confirm_observed(self.parent, slot["sequence"], {"label": slot["label"],
                "credit": slot["controller_input"], "step": step.as_record(),
                "unit_ref": UnitRef(self.parent, slot["sequence"]).as_record(),
                "decision_index": admission["original_decision_index"]})
        return slot

    def capture(self):
        return LocalReturnHistory(self.store, self.journal, self.backend).capture(self.parent,
            credit_kind="scientific", credit_binding=BINDING)


def forbidden(*args, **kwargs):
    raise AssertionError("capture must only read original evidence")


def read_only(case, monkeypatch):
    for name in ("status", "start", "commission", "acknowledge", "publish_return", "return_page",
                 "load_commission", "record_progress", "_claim"):
        monkeypatch.setattr(case.backend, name, forbidden)
    for name in ("save", "measure", "elapsed_view", "commission_returned"):
        monkeypatch.setattr(case.journal, name, forbidden)
    for name in ("transaction", "artifact", "put", "get", "get_artifact"):
        monkeypatch.setattr(case.store, name, forbidden)
    monkeypatch.setattr(case.controller, "observe", forbidden)
    monkeypatch.setattr(case.archive, "load", forbidden, raising=False)
    case.store.db.execute("PRAGMA query_only=ON")


def test_real_saved_original_returns_signed_steps_order_and_replay(tmp_path, monkeypatch):
    case = Case(tmp_path)
    try:
        # Selection order and actual completion observation order differ.
        second = case.child(1, credit=2.0, defer_admission=True)
        third = case.child(4, credit=2.125, defer_admission=True)
        first = case.child(9, credit=5.25, progress=True, defer_admission=True)
        completed = []
        for item in (first, second, third):
            admitted = admit_return(item[0], item[1], item[3])
            completed.append((item[0], item[1], admitted, item[3]))
        first, second, third = completed
        slots = [case.stage(item[2]) for item in (first, second, third)]
        assert [slot["sequence"] for slot in slots] == [0, 1, 2]
        # Re-admission and restaging retain the original durable contribution.
        assert admit_return(first[0], first[1], first[3]) == first[2]
        assert case.stage(first[2], observe=False) == slots[0]
        before = case.store.db.total_changes
        read_only(case, monkeypatch)
        reader = LocalReturnHistory(case.store, case.journal, case.backend)
        value = reader.capture(case.parent, credit_kind="scientific", credit_binding=BINDING)
        assert value["version"] == VERSION and value["unavailable_reasons"] == []
        assert [s["original_decision_index"] for s in value["samples"]] == [9, 1, 4]
        assert [s["completion_sequence"] for s in value["samples"]] == [0, 1, 2]
        assert [s["raw_controller_delta"] for s in value["samples"]] == [5.25, -3.25, 0.125]
        for sample, item, slot in zip(value["samples"], (first, second, third), slots):
            assert sample["sample_ref"] == sample["admission_id"] == item[2]["admission_id"]
            assert sample["unit_ref"] == UnitRef(case.parent, slot["sequence"]).as_record()
            assert sample["child_handle"] == item[0]["handle"]
            assert sample["commission_sha256"] == content_digest(item[0])
            assert sample["report_contract_sha256"] == content_digest(item[0]["child"]["request"]["report_contract"])
            assert sample["controller_input"] == item[2]["controller_input"]
            assert sample["selection_to_return"] == {"seconds": 12.125,
                "measure": "utc_timestamp_difference", "unavailable_reason": None}
            assert sample["selected_at"] == STAMP and sample["returned_at"] == LATER
            assert sample["received_record_refs"] == item[2]["received_record_refs"]
        assert value["samples"][0]["received_progress_refs"] == [first[2]["report"]["updates"][0]["ref"]]
        assert all(not sample["linked_waits"] for sample in value["samples"])
        assert reader.capture(case.parent, credit_kind="scientific", credit_binding=BINDING) == value
        assert case.store.db.total_changes == before
        run_id, parent = case.journal.run_id, case.parent
    finally:
        case.store.close()
    # Fresh adapters read the same records without invoking a reconstruction
    # factory, credit projector, old child archive or current source bodies.
    with Store(tmp_path / "workspace") as reopened:
        journal = Journal(reopened, run_id)
        reopened.db.execute("PRAGMA query_only=ON")
        restored = LocalReturnHistory(reopened, journal, DurableExecutionStore(tmp_path / "backend"))
        assert restored.capture(parent, credit_kind="scientific", credit_binding=BINDING) == value


def test_unobserved_and_failed_admissions_follow_observed_samples(tmp_path):
    case = Case(tmp_path)
    try:
        staged = case.child(2, credit=1)
        slot = case.stage(staged[2], observe=False)
        delivered = case.child(5, credit=0, state="delivery_failed", progress=True)
        case.stage(delivered[2])
        failed = case.child(0, state="execution_failed")
        closed = case.child(7, state="receiver_closed")
        value = case.capture()
        assert [s["original_decision_index"] for s in value["samples"]] == [5, 0, 2, 7]
        observed, execution, pending_observation, receiver_closed = value["samples"]
        assert observed["admission_state"] == "delivery_failed" and observed["raw_controller_delta"] == 0
        assert observed["received_progress_refs"] == observed["received_record_refs"] == []
        assert pending_observation["controller_input"] == staged[2]["controller_input"]
        assert pending_observation["completion_sequence"] == slot["sequence"]
        assert pending_observation["observation_state"] == "unobserved"
        for sample in (execution, receiver_closed):
            assert sample["observation_state"] == "unobserved"
            assert sample["controller_input"] is sample["controller_step"] is sample["raw_controller_delta"] is None
            assert sample["unit_ref"] is sample["completion_sequence"] is None
            assert sample["received_record_refs"] == sample["received_progress_refs"] == []
        assert failed[2]["admission_id"] == execution["admission_id"]
        assert closed[2]["admission_id"] == receiver_closed["admission_id"]
    finally:
        case.store.close()


@pytest.mark.parametrize("missing_contract", [False, True])
def test_legacy_missing_support_is_explicit_and_does_not_invent_references(tmp_path, monkeypatch, missing_contract):
    case = Case(tmp_path)
    try:
        child = case.child(3, progress=True)
        case.stage(child[2])
        case.store.db.execute("DROP TABLE runtime_completion_slots")
        case.store.db.execute("DROP TABLE runtime_commission_intents")
        if missing_contract:
            case.store.db.execute("DROP TABLE runtime_report_attempts")
        read_only(case, monkeypatch)
        monkeypatch.setattr(case.backend, "load_return", forbidden)
        value = case.capture()
        sample = value["samples"][0]
        assert sample["observation_state"] == "observed" and sample["raw_controller_delta"] == 5.25
        assert sample["unit_ref"] == UnitRef(case.parent, 0).as_record()
        assert sample["completion_sequence"] is sample["child_role"] is sample["selected_at"] is sample["returned_at"] is None
        assert sample["selection_to_return"]["seconds"] is None
        assert {"original_commission_unavailable", "completion_slot_unavailable",
                "original_return_commission_unavailable", "selected_at_unavailable"} <= set(value["unavailable_reasons"])
        if missing_contract:
            assert sample["report_contract_sha256"] is None and sample["received_progress_refs"] == []
            assert "admitted_progress_schema_unavailable" in value["unavailable_reasons"]
        else:
            assert sample["report_contract_sha256"] == content_digest(child[0]["child"]["request"]["report_contract"])
            assert sample["received_progress_refs"] == [child[2]["report"]["updates"][0]["ref"]]
    finally:
        case.store.close()


def test_missing_admissions_empty_support_and_constructor_do_not_install_tables(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        journal = Journal(store, "legacy")
        journal.save("runtime_episodes", {"episode_id": "legacy-parent", "path": "[]", "request": "{}",
            "state": "yielded", "initial_credit": 0})
        before = store.db.total_changes
        tables = list(store.db.execute("SELECT name FROM sqlite_master ORDER BY name"))
        store.db.execute("PRAGMA query_only=ON")
        reader = LocalReturnHistory(store, journal, object())
        result = reader.capture("legacy-parent", credit_kind="monitoring", credit_binding=BINDING)
        assert result["samples"] == [] and result["unavailable_reasons"] == ["return_admissions_unavailable"]
        assert result["credit_kind"] == "monitoring"
        assert list(store.db.execute("SELECT name FROM sqlite_master ORDER BY name")) == tables
        assert store.db.total_changes == before


@pytest.mark.parametrize("failure", [KeyError("missing"), OSError("unavailable"), ValueError("bad saved return")])
def test_original_return_read_failure_retains_sample_without_restarting(tmp_path, monkeypatch, failure):
    case = Case(tmp_path)
    try:
        child = case.child(3)
        case.stage(child[2])
        reads = []
        def unavailable(handle, return_id):
            reads.append((handle, return_id))
            raise failure
        read_only(case, monkeypatch)
        monkeypatch.setattr(case.backend, "load_return", unavailable)
        value = case.capture()
        sample = value["samples"][0]
        assert reads == [(child[0]["handle"], child[1]["return_id"])]
        assert sample["sample_ref"] == child[2]["admission_id"] and sample["raw_controller_delta"] == 5.25
        assert sample["returned_at"] is None and sample["selection_to_return"]["seconds"] is None
        assert "original_return_read_unavailable" in value["unavailable_reasons"]
    finally:
        case.store.close()


@pytest.mark.parametrize("selected_at,returned_at,seconds,reason", [
    ("2026-10-21T12:00:00Z", LATER, 12.125, None),
    (STAMP, "2026-10-21T11:59:59+00:00", None, "negative_selection_to_return"),
    (None, LATER, None, "selected_at_unavailable"),
    ("invalid", LATER, None, "selected_at_unavailable"),
    ("2026-10-21T12:00:00-05:00", LATER, None, "selected_at_unavailable"),
    ("2026-10-21T12:00:00", LATER, None, "selected_at_unavailable"),
])
def test_only_original_utc_timestamp_difference_is_exposed(tmp_path, selected_at, returned_at, seconds, reason):
    case = Case(tmp_path)
    try:
        child = case.child(1, returned_at=returned_at)
        case.stage(child[2])
        if selected_at is None:
            # A nullable timestamp cannot be stored by current C1; absent legacy
            # C1 support remains unknown instead of adopting action timing.
            case.store.db.execute("DELETE FROM runtime_commission_intents")
        else:
            case.store.db.execute("UPDATE runtime_commission_intents SET selected_at=?", (selected_at,))
        case.store.db.execute("UPDATE runtime_actions SET timing=? WHERE run_id=? AND episode_id=? AND decision_index=1",
            (canonical({"measured_elapsed_seconds": 999999, "queue_wait": 42}), case.journal.run_id, case.parent))
        sample = case.capture()["samples"][0]
        assert sample["selection_to_return"] == {"seconds": seconds, "measure": "utc_timestamp_difference",
                                               "unavailable_reason": reason}
    finally:
        case.store.close()


@pytest.mark.parametrize("change,reason", [("timestamp", "returned_at_invalid"),
    ("timezone", "returned_at_invalid"), ("handle", "original_return_identity_conflict"),
    ("digest", "original_return_invalid")])
def test_malformed_original_return_support_does_not_escape_as_valid_timing(tmp_path, monkeypatch, change, reason):
    case = Case(tmp_path)
    try:
        child = case.child(1)
        case.stage(child[2])
        returned = deepcopy(child[1])
        if change == "timestamp":
            returned["returned_at"] = "not-a-timestamp"
        elif change == "timezone":
            returned["returned_at"] = "2026-10-21T12:00:00-05:00"
        elif change == "handle":
            returned["handle"] = "foreign-handle"
        else:
            returned["pending_handles"] = ["changed-saved-content"]
        monkeypatch.setattr(case.backend, "load_return", lambda handle, return_id: returned)
        value = case.capture()
        assert value["samples"][0]["returned_at"] is None
        assert value["samples"][0]["selection_to_return"]["seconds"] is None
        assert reason in value["unavailable_reasons"]
    finally:
        case.store.close()


def test_nonstandard_controller_fields_are_preserved_without_guessing_delta(tmp_path):
    case = Case(tmp_path)
    try:
        child = case.child(1)
        case.stage(child[2])
        row = case.journal.row("runtime_observations", case.parent, 0)
        saved = json.loads(row["observation"])
        saved["step"] = {"delta": -7.5, "raw_gain": -8.5, "completed_count": 1}
        case.journal.save("runtime_observations", {"episode_id": case.parent, "unit_index": 0,
            "observation": canonical(saved)})
        value = case.capture()
        assert value["samples"][0]["controller_step"] == saved["step"]
        assert value["samples"][0]["raw_controller_delta"] is None
        assert "standard_controller_marginal_credit_unavailable" in value["unavailable_reasons"]
    finally:
        case.store.close()


@pytest.mark.parametrize("changed", ["admission_handle", "admission_id", "commission", "selection",
    "completion_return", "observation_unit", "observation_decision", "observation_credit"])
def test_malformed_durable_cross_references_are_rejected_without_writes(tmp_path, monkeypatch, changed):
    case = Case(tmp_path)
    try:
        child = case.child(1)
        case.stage(child[2])
        if changed.startswith("admission"):
            value = deepcopy(child[2])
            value["handle" if changed == "admission_handle" else "admission_id"] = "foreign"
            case.store.db.execute("UPDATE runtime_return_admissions SET admission=?", (canonical(value),))
        elif changed == "commission":
            case.store.db.execute("UPDATE runtime_commission_intents SET commission_sha256=?", ("c" * 64,))
        elif changed == "selection":
            case.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=1",
                (canonical({"kind": "child", "changed": True}), case.journal.run_id, case.parent))
        elif changed == "completion_return":
            value = case.ledger.slot(case.parent, 0)
            value["child_return"]["return_id"] = "foreign"
            case.store.db.execute("UPDATE runtime_completion_slots SET slot=?", (canonical(value),))
        else:
            value = json.loads(case.journal.row("runtime_observations", case.parent, 0)["observation"])
            if changed == "observation_unit":
                value["unit_ref"] = UnitRef("foreign-episode", 0).as_record()
            elif changed == "observation_decision":
                value["decision_index"] = 2
            else:
                value["credit"]["credit"] = 999
            case.journal.save("runtime_observations", {"episode_id": case.parent, "unit_index": 0,
                "observation": canonical(value)})
        before = case.store.db.total_changes
        read_only(case, monkeypatch)
        with pytest.raises(ValueError, match="local_return_history_identity_conflict"):
            case.capture()
        assert case.store.db.total_changes == before
    finally:
        case.store.close()


def test_wait_links_use_only_actual_return_wake_same_handle_and_do_not_duplicate_credit(tmp_path, monkeypatch):
    case = Case(tmp_path)
    try:
        child = case.child(1)
        other = case.child(2, credit=5.25)
        case.stage(child[2])
        # Save actual C6 operations through the public wait boundary. Events
        # are scripted; their original returned records and measured intervals
        # are stored by WaitStore, not fabricated by the evidence collector.
        waits = WaitStore(case.store, case.journal.run_id)
        pending = {"version": "pending_work_v1", "captured_at": STAMP, "items": []}
        outcomes = []
        for decision, item, event in ((3, child, "returned"), (4, child, "progress_committed"),
                                      (5, other, "returned")):
            condition = {"version": "event_condition_v1", "events": [{"handle": item[0]["handle"],
                "event": event, "after_cursor": 0}], "reconsider_at": None}
            request = {"version": "wait_request_v1", "wait_id": "wait:" + str(decision),
                "parent_episode_id": case.parent, "original_decision_index": decision,
                "condition": condition, "estimate_snapshot": estimate_wait(condition, pending, [], [], [])}
            class Provider:
                async def wait_events(self, selected):
                    return {"version": "event_wake_v1", "reason": event, "observed_at": STAMP,
                        "events": [{"cursor": decision, "handle": item[0]["handle"], "event": event,
                                    "record_ref": item[1]["return_id"]}], "reconsider_at": None}
            if decision == 3:
                class Interrupted:
                    async def wait_events(self, selected):
                        raise RuntimeError("fixture interruption")
                with pytest.raises(RuntimeError, match="fixture interruption"):
                    asyncio.run(waits.perform_wait(request, Interrupted()))
            outcome = asyncio.run(waits.perform_wait(request, Provider()))
            outcomes.append(outcome)
            # A completed selected wait has its own standard zero-gain step.
            case.journal.save("runtime_actions", {"episode_id": case.parent, "decision_index": decision,
                "action": canonical({"kind": "wait", "wait_id": request["wait_id"]}),
                "result": canonical({"status": "completed", "wait_outcome": outcome}), "credit": 5.25})
            slot = case.ledger.stage(case.parent, decision, label="wait:" + str(decision), kind="own_action",
                controller_input=Value({"credit": 5.25}), child_return=None)
            step = case.controller.observe(slot["label"], Value(slot["controller_input"]), is_root=True)
            assert step.marginal_credit == 0
            case.ledger.confirm_observed(case.parent, slot["sequence"], {"label": slot["label"],
                "credit": slot["controller_input"], "step": step.as_record(),
                "unit_ref": UnitRef(case.parent, slot["sequence"]).as_record(), "decision_index": decision})
        assert outcomes[0]["unmeasured_interruption"] is True
        original_outcome = canonical(outcomes[0])
        malformed = deepcopy(outcomes[0])
        malformed["condition_sha256"] = "f" * 64
        case.store.db.execute("UPDATE episode_waits SET outcome=? WHERE wait_id='wait:3'", (canonical(malformed),))
        with pytest.raises(ValueError, match="local_return_history_wait_identity_conflict"):
            case.capture()
        case.store.db.execute("UPDATE episode_waits SET outcome=? WHERE wait_id='wait:3'", (original_outcome,))
        read_only(case, monkeypatch)
        value = case.capture()
        original, unobserved = value["samples"]
        assert original["raw_controller_delta"] == 5.25 and unobserved["raw_controller_delta"] is None
        assert [s["sample_ref"] for s in value["samples"]] == [child[2]["admission_id"], other[2]["admission_id"]]
        assert original["linked_waits"] == [{key: outcomes[0][key] for key in ("wait_id", "condition_sha256",
            "measured_duration_seconds", "duration_measure", "unmeasured_interruption")}]
        assert unobserved["linked_waits"][0]["wait_id"] == "wait:5"
        assert all("credit" not in wait and "raw_controller_delta" not in wait
                   for sample in value["samples"] for wait in sample["linked_waits"])
    finally:
        case.store.close()


def test_capture_validates_caller_owned_channel_binding_and_connection(tmp_path):
    case = Case(tmp_path)
    try:
        reader = LocalReturnHistory(case.store, case.journal, case.backend)
        for binding in ({}, [], {"nonfinite": float("inf")}, {1: "not-a-string-key"}):
            with pytest.raises(ValueError):
                reader.capture(case.parent, credit_kind="operational", credit_binding=binding)
        for channel in ("job_monitor", None, ""):
            with pytest.raises(ValueError, match="credit_kind_required"):
                reader.capture(case.parent, credit_kind=channel, credit_binding=BINDING)
        with Store(tmp_path / "different") as other:
            with pytest.raises(ValueError, match="same_store_connection"):
                LocalReturnHistory(other, case.journal, case.backend)
        with pytest.raises(ValueError, match="episode_unavailable"):
            reader.capture("missing", credit_kind="scientific", credit_binding=BINDING)
    finally:
        case.store.close()
