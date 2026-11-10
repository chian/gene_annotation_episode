"""Admit one immutable child return into its original parent's information.

Receipt, form attempt, completed action and cumulative credit are one Store
transaction. The execution backend acknowledges that commit separately. This
module never advances a controller or turns collection into a second action.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import math
import sqlite3

from method_loop import ClosedRecord
from method_loop.communication import ReportContract
from method_loop.durable import (DurableExecutionError, canonical, content_digest,
                                 validate_commission, validate_return)

from .communication import ReportBoundaryError, plain, validate_closed_schema
from .domain import ContractError
from .episode_journal import Journal, WorkflowError
from .episode_source_failure import child_completion_status
from .numerical import validate_task_credit


VERSION = "episode_admission_v1"
FAILURE_CODES = frozenset({"identity_conflict", "unavailable_binding",
    "unavailable_resource", "invalid_return", "storage_failure",
    "interrupted_execution", "execution_failed", "report_delivery_failed"})


class AdmissionError(WorkflowError):
    """An envelope/ownership failure, without changing child contributions."""
    def __init__(self, code, *, affected_refs=()):
        if code not in FAILURE_CODES:
            raise ValueError("undeclared_admission_failure_code")
        self.failure = {"code": code, "affected_refs": list(affected_refs),
                        "diagnostic_ref": None, "partial_record_refs": []}
        super().__init__(code)


@dataclass(frozen=True)
class ReceiverBindingV1:
    store: object
    journal: Journal
    original_decision_index: int
    original_contract: ReportContract
    validate_semantics: Callable
    receive_references: Callable
    project_received_credit: Callable
    make_controller_input: Callable
    defer_failed_delivery: bool = True

    def __post_init__(self):
        if self.journal.db is not self.store.db:
            raise ValueError("receiver_journal_requires_same_store_connection")
        if type(self.original_decision_index) is not int or self.original_decision_index < 0:
            raise ValueError("original_decision_index_required")
        if not isinstance(self.original_contract, ReportContract):
            raise TypeError("original_report_contract_required")
        if self.defer_failed_delivery is not True:
            raise ValueError("parent_owned_delivery_resolution_required")
        for name in ("validate_semantics", "receive_references",
                     "project_received_credit", "make_controller_input"):
            if not callable(getattr(self, name)):
                raise TypeError("receiver_callbacks_required")


def _install(db):
    # execute(), unlike executescript(), preserves an existing Store transaction.
    db.execute("""CREATE TABLE IF NOT EXISTS runtime_return_admissions (
        run_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL,
        original_decision_index INTEGER NOT NULL, handle TEXT NOT NULL,
        return_id TEXT NOT NULL, commission_sha256 TEXT NOT NULL,
        selection_sha256 TEXT NOT NULL, expectation_snapshot_refs TEXT NOT NULL,
        credit_snapshot REAL, admission TEXT NOT NULL,
        PRIMARY KEY(run_id,return_id), UNIQUE(run_id,handle),
        UNIQUE(run_id,parent_episode_id,original_decision_index))""")
    db.execute("""CREATE TABLE IF NOT EXISTS runtime_return_delivery_resolutions (
        run_id TEXT NOT NULL, return_id TEXT NOT NULL,
        original_admission_sha256 TEXT NOT NULL, repair_decision_index INTEGER NOT NULL,
        delivery_contract TEXT NOT NULL, admission TEXT NOT NULL,
        PRIMARY KEY(run_id,return_id))""")


def load_return_admission(store, run_id, return_id):
    """Read the original admission and its immutable delivery resolution, if any."""
    row = store.db.execute("SELECT admission FROM runtime_return_admissions "
        "WHERE run_id=? AND return_id=?", (run_id, return_id)).fetchone()
    if row is None:
        raise AdmissionError("unavailable_binding", affected_refs=[return_id])
    original = json.loads(row[0])
    installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='runtime_return_delivery_resolutions'").fetchone()
    resolution = (store.db.execute("SELECT * FROM runtime_return_delivery_resolutions "
        "WHERE run_id=? AND return_id=?", (run_id, return_id)).fetchone()
        if installed else None)
    if resolution is None:
        return original
    resolved = json.loads(resolution["admission"])
    if (original["state"] != "delivery_pending"
            or resolution["original_admission_sha256"] != content_digest(original)
            or any(resolved[name] != original[name] for name in
                ("version", "admission_id", "handle", "return_id", "parent_episode_id",
                 "original_decision_index"))
            or resolved["state"] != "admitted"
            or resolved["repair_decision_index"] != resolution["repair_decision_index"]
            or canonical(resolved["delivery_contract"]) != resolution["delivery_contract"]):
        _conflict(original["handle"])
    return resolved


def _conflict(handle):
    raise AdmissionError("identity_conflict", affected_refs=[handle])


def _delivery_ref(spec, index):
    return "delivery_" + content_digest({"run": spec["run_id"],
        "parent": spec["parent"]["episode_id"], "index": index})[:24]


def _save_attempt(receiver, spec, delivery_ref, *, report=None, failure=None):
    values = {"parent_episode_id": spec["parent"]["episode_id"],
        "decision_index": receiver.original_decision_index,
        "delivery_ref": delivery_ref, "child_episode_id": spec["child"]["episode_id"],
        "contract": canonical(receiver.original_contract.as_record()),
        "form": None if report is None else canonical(report),
        "failure": None if failure is None else canonical(failure)}
    old = receiver.store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? "
        "AND parent_episode_id=? AND decision_index=?", (spec["run_id"],
        spec["parent"]["episode_id"], receiver.original_decision_index)).fetchone()
    if old is not None:
        if any(old[key] != value for key, value in values.items()):
            _conflict(spec["handle"])
    else:
        receiver.journal.save("runtime_report_attempts", values)


def _validate_original(receiver, spec):
    """Validate the frozen assignment; never reconstruct identity from a key."""
    journal = receiver.journal
    if journal.run_id != spec["run_id"]:
        _conflict(spec["handle"])
    contract = receiver.original_contract.as_record()
    if canonical(contract) != canonical(spec["child"]["request"]["report_contract"]):
        _conflict(spec["handle"])
    parent = journal.row("runtime_episodes", spec["parent"]["episode_id"])
    if parent is None:
        raise AdmissionError("unavailable_binding", affected_refs=[spec["handle"]])
    parent_request = json.loads(parent["request"])
    if (json.loads(parent["path"]) != spec["parent"]["path"]
            or parent_request["goal"]["goal_id"] != spec["parent"]["goal_id"]):
        _conflict(spec["handle"])
    scope = receiver.store.validate_scope(spec["child"]["scope"],
        parent_request["message"].get("scope"))
    if scope != spec["child"]["scope"]:
        _conflict(spec["handle"])
    child = journal.row("runtime_episodes", spec["child"]["episode_id"])
    if child is not None and (json.loads(child["path"]) != spec["child"]["path"]
            or json.loads(child["request"]) != spec["child"]["request"]):
        _conflict(spec["handle"])
    action = journal.row("runtime_actions", spec["parent"]["episode_id"],
                         receiver.original_decision_index)
    if action is None:
        raise AdmissionError("unavailable_binding", affected_refs=[spec["handle"]])
    if action["result"] is not None:
        result = json.loads(action["result"])
        if result.get("status") != "pending" or result.get("pending_handle") != spec["handle"]:
            _conflict(spec["handle"])
    if action["credit"] is not None:
        _conflict(spec["handle"])
    return parent, action


def _admit_form(receiver, spec, returned):
    form = returned["form"]
    if returned["outcome"] != "closed" or form is None:
        raise ReportBoundaryError("Closed scientific form unavailable", code="form_unavailable")
    schema = receiver.original_contract.measurements.get("schema")
    if schema is None:
        raise ReportBoundaryError("Typed original form unavailable", code="invalid_schema")
    schema = validate_closed_schema(schema)
    # Recorded fields are frozen by the original child, never recomposed now.
    sourced = {name: node["x-source"] for name, node in schema["properties"].items()
               if "x-source" in node}
    if sourced:
        saved = receiver.journal.row("runtime_forms", spec["child"]["episode_id"])
        facts = {} if saved is None else json.loads(saved["facts"])
        for name, fact in sourced.items():
            if fact not in facts or name not in form or canonical(form[name]) != canonical(facts[fact]):
                raise ReportBoundaryError("Return differs from recorded child fact",
                                          code="recorded_fact_mismatch", field=name)
    admitted = receiver.original_contract.admit(form, audit_identifiers=(
        spec["child"]["episode_id"], spec["child"]["request"]["goal"]["goal_id"]))
    report = plain(admitted.as_record())
    receiver.validate_semantics(report)
    return report


def admit_return(spec, returned, receiver: ReceiverBindingV1):
    """Admit C3 through C4, translating storage failures after rollback."""
    try:
        return _admit_return(spec, returned, receiver)
    except sqlite3.Error as error:
        handle = spec.get("handle", "unknown") if isinstance(spec, Mapping) else "unknown"
        raise AdmissionError("storage_failure", affected_refs=[handle]) from error


def _admit_return(spec, returned, receiver: ReceiverBindingV1):
    """Return AdmissionV1, replaying its original credit and controller input.

    The caller owns delivery of this single completed original commission to
    method_loop and the backend acknowledgment. Callback exceptions indicating
    storage/interruption abort the entire transaction; typed form failures
    persist an actionable delivery attempt while preserving committed child work.
    """
    if not isinstance(receiver, ReceiverBindingV1):
        raise TypeError("receiver_binding_required")
    supplied_handle = spec.get("handle", "unknown") if isinstance(spec, Mapping) else "unknown"
    try:
        spec = validate_commission(spec)
        commission_sha256 = content_digest(spec)
        returned = validate_return(returned, spec=spec, commission_sha256=commission_sha256)
    except DurableExecutionError as error:
        raise AdmissionError(error.failure["code"],
                             affected_refs=error.failure["affected_refs"]) from error
    except (ValueError, TypeError, KeyError) as error:
        raise AdmissionError("invalid_return", affected_refs=[supplied_handle]) from error
    db, journal = receiver.store.db, receiver.journal
    index, parent_id = receiver.original_decision_index, spec["parent"]["episode_id"]
    with receiver.store.transaction():
        _install(db)
        old = db.execute("SELECT * FROM runtime_return_admissions WHERE run_id=? AND "
            "(return_id=? OR handle=? OR (parent_episode_id=? AND original_decision_index=?))",
            (spec["run_id"], returned["return_id"], spec["handle"], parent_id, index)).fetchone()
        if old is not None:
            original_action = journal.row("runtime_actions", parent_id, index)
            if (old["return_id"] != returned["return_id"] or old["handle"] != spec["handle"]
                    or old["commission_sha256"] != commission_sha256
                    or old["parent_episode_id"] != parent_id
                    or old["original_decision_index"] != index
                    or journal.run_id != spec["run_id"]
                    or original_action is None
                    or content_digest(json.loads(original_action["action"])) != old["selection_sha256"]
                    or canonical(receiver.original_contract.as_record()) != canonical(
                        spec["child"]["request"]["report_contract"])):
                _conflict(spec["handle"])
            return load_return_admission(receiver.store, spec["run_id"], returned["return_id"])
        parent, action = _validate_original(receiver, spec)
        admission_id = "admission_" + content_digest({"run_id": spec["run_id"],
            "parent_episode_id": parent_id, "original_decision_index": index,
            "return_id": returned["return_id"]})
        result = {"version": VERSION, "admission_id": admission_id,
            "handle": spec["handle"], "return_id": returned["return_id"],
            "parent_episode_id": parent_id, "original_decision_index": index,
            "state": "receiver_closed", "received_record_refs": [],
            "controller_input": None, "report": None, "delivery_failure": None}
        credit = None
        if parent["state"] == "active" and returned["outcome"] != "closed":
            failure = returned["failure"]
            result.update(state="execution_failed", delivery_failure=failure)
            if receiver.defer_failed_delivery:
                # A definitive failed invocation is still completed work for
                # its assigning iterator. No child-private result is admitted.
                credit = receiver.project_received_credit()
                validate_task_credit(credit)
                controller = receiver.make_controller_input(index, credit)
                if not isinstance(controller, ClosedRecord):
                    raise TypeError("admission_controller_input_requires_closed_record")
                result["controller_input"] = plain(controller.as_record())
            journal.save("runtime_actions", {"episode_id": parent_id,
                "decision_index": index, "action": action["action"], "credit": credit,
                "result": canonical({"status": ("interrupted" if returned["outcome"] == "interrupted"
                                               else "failed"),
                    "record_refs": [], "changed_record_refs": [], "feedback": failure})})
        elif parent["state"] == "active":
            delivery_ref = _delivery_ref(spec, index)
            try:
                report = _admit_form(receiver, spec, returned)
            except (ReportBoundaryError, ContractError, ValueError) as error:
                diagnostic = getattr(error, "diagnostic", {})
                feedback = {"kind": "report_delivery_failure", "delivery_ref": delivery_ref,
                    "reason": diagnostic.get("code", "invalid_return"),
                    "field": diagnostic.get("field")}
                _save_attempt(receiver, spec, delivery_ref, failure=feedback)
                failure = {"code": "report_delivery_failed", "affected_refs": [delivery_ref],
                    "diagnostic_ref": None, "partial_record_refs": list(
                        (returned.get("failure") or {}).get("partial_record_refs", []))}
                result.update(state=("delivery_pending" if receiver.defer_failed_delivery
                                     else "delivery_failed"), delivery_failure=failure)
                if receiver.defer_failed_delivery:
                    pending = ({'status': 'pending', 'pending_handle': spec['handle']}
                        if action['result'] is None else json.loads(action['result']))
                    if pending.get('status') != 'pending' or pending.get('pending_handle') != spec['handle']:
                        _conflict(spec['handle'])
                    pending.update(delivery_ref=delivery_ref, feedback=feedback)
                    pending['child_completion'] = child_completion_status(receiver.store,
                        spec['run_id'], spec['child']['episode_id'], returned['completion'], delivery='pending')
                    journal.save("runtime_actions", {"episode_id": parent_id,
                        "decision_index": index, "action": action["action"],
                        "result": canonical(pending), "credit": None})
            else:
                _save_attempt(receiver, spec, delivery_ref, report=report)
                references = receiver.receive_references(report)
                if isinstance(references, (str, bytes)):
                    raise TypeError("received_references_must_be_semantic_reference_iterable")
                references = list(dict.fromkeys(references))
                if any(not isinstance(ref, str) or not ref for ref in references):
                    raise TypeError("received_references_must_be_semantic_reference_iterable")
                result.update(state="admitted", received_record_refs=references, report=report)
            # Failure conveys no unreturned work. Projection is still the
            # parent's cumulative received information, never child credit.
            if result["state"] == "delivery_pending":
                # Child execution is closed, but its original parent acquisition
                # has no admitted return yet. Its one observation belongs after
                # resolution, not to an unrelated later action.
                db.execute("INSERT INTO runtime_return_admissions VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (spec["run_id"], parent_id, index, spec["handle"], returned["return_id"],
                     commission_sha256, content_digest(json.loads(action["action"])),
                     canonical(spec["expectation_snapshot_refs"]), None, canonical(result)))
                return result
            credit = receiver.project_received_credit()
            validate_task_credit(credit)
            controller_input = receiver.make_controller_input(index, credit)
            if not isinstance(controller_input, ClosedRecord):
                raise TypeError("admission_controller_input_requires_closed_record")
            controller_value = controller_input.as_record()
            if not isinstance(controller_value, Mapping):
                raise TypeError("admission_controller_input_requires_json_object")
            result["controller_input"] = json.loads(canonical(controller_value))
            child_form = journal.row("runtime_forms", spec["child"]["episode_id"])
            child_changed = set(() if child_form is None else
                json.loads(child_form["facts"]).get("changed_record_refs", []))
            outcome = {"status": "completed", "record_refs": result["received_record_refs"],
                "changed_record_refs": [ref for ref in result["received_record_refs"]
                                        if ref in child_changed]}
            outcome['child_completion'] = child_completion_status(receiver.store, spec['run_id'],
                spec['child']['episode_id'], returned['completion'], delivery=result['state'])
            if result["delivery_failure"] is not None:
                outcome["feedback"] = feedback
            journal.save("runtime_actions", {"episode_id": parent_id,
                "decision_index": index, "result": canonical(outcome), "credit": credit,
                "action": action["action"]})
        db.execute("INSERT INTO runtime_return_admissions VALUES(?,?,?,?,?,?,?,?,?,?)",
            (spec["run_id"], parent_id, index, spec["handle"], returned["return_id"],
             commission_sha256, content_digest(json.loads(action["action"])),
             canonical(spec["expectation_snapshot_refs"]), credit, canonical(result)))
        return result


def resolve_return_delivery(spec, returned, receiver: ReceiverBindingV1, *,
                            repair_decision_index, delivery_contract: ReportContract):
    """Finish one still-owned child acquisition through a saved revised form.

    The failed original attempt and immutable returned envelope are retained.
    Receipt, parent credit, resolution and the original completion slot commit
    together. A replay reads that resolution without receiving or repricing it.
    """
    if not isinstance(receiver, ReceiverBindingV1) or not receiver.defer_failed_delivery:
        raise TypeError("deferred_delivery_receiver_required")
    if (type(repair_decision_index) is not int
            or repair_decision_index <= receiver.original_decision_index
            or not isinstance(delivery_contract, ReportContract)):
        raise ValueError("original_delivery_repair_required")
    spec = validate_commission(spec)
    returned = validate_return(returned, spec=spec, commission_sha256=content_digest(spec))
    index, parent_id = receiver.original_decision_index, spec["parent"]["episode_id"]
    try:
        with receiver.store.transaction():
            _install(receiver.store.db)
            original_row = receiver.store.db.execute(
                "SELECT admission FROM runtime_return_admissions WHERE run_id=? AND return_id=?",
                (spec["run_id"], returned["return_id"])).fetchone()
            if original_row is None:
                raise AdmissionError("unavailable_binding", affected_refs=[spec["handle"]])
            original = json.loads(original_row[0])
            effective = load_return_admission(receiver.store, spec["run_id"], returned["return_id"])
            if effective["state"] == "admitted":
                if (effective.get("repair_decision_index") != repair_decision_index
                        or canonical(effective.get("delivery_contract")) != canonical(delivery_contract.as_record())):
                    _conflict(spec["handle"])
                return effective
            parent, action = _validate_original(receiver, spec)
            if (parent["state"] != "active" or original["state"] != "delivery_pending"
                    or original["original_decision_index"] != index
                    or original["parent_episode_id"] != parent_id
                    or original["handle"] != spec["handle"]
                    or original["return_id"] != returned["return_id"]
                    or returned["outcome"] != "closed"):
                _conflict(spec["handle"])
            attempt = receiver.store.db.execute("SELECT * FROM runtime_report_attempts "
                "WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
                (spec["run_id"], parent_id, repair_decision_index)).fetchone()
            if (attempt is None or attempt["failure"] is not None or attempt["form"] is None
                    or attempt["delivery_ref"] != _delivery_ref(spec, index)
                    or attempt["child_episode_id"] != spec["child"]["episode_id"]
                    or attempt["contract"] != canonical(delivery_contract.as_record())):
                _conflict(spec["handle"])
            report = plain(delivery_contract.admit(json.loads(attempt["form"]),
                audit_identifiers=(spec["child"]["episode_id"],
                    spec["child"]["request"]["goal"]["goal_id"])).as_record())
            receiver.validate_semantics(report)
            references = receiver.receive_references(report)
            if isinstance(references, (str, bytes)):
                raise TypeError("received_references_must_be_semantic_reference_iterable")
            references = list(dict.fromkeys(references))
            if any(not isinstance(ref, str) or not ref for ref in references):
                raise TypeError("received_references_must_be_semantic_reference_iterable")
            credit = receiver.project_received_credit()
            validate_task_credit(credit)
            controller_input = receiver.make_controller_input(index, credit)
            if not isinstance(controller_input, ClosedRecord):
                raise TypeError("admission_controller_input_requires_closed_record")
            controller_value = controller_input.as_record()
            if not isinstance(controller_value, Mapping):
                raise TypeError("admission_controller_input_requires_json_object")
            resolved = {**original, "state": "admitted", "received_record_refs": references,
                "report": report, "controller_input": json.loads(canonical(controller_value)),
                "delivery_failure": None, "repair_decision_index": repair_decision_index,
                "delivery_contract": plain(delivery_contract.as_record()), "credit_snapshot": credit}
            child_form = receiver.journal.row("runtime_forms", spec["child"]["episode_id"])
            changed = set(() if child_form is None else
                json.loads(child_form["facts"]).get("changed_record_refs", []))
            receiver.journal.save("runtime_actions", {"episode_id": parent_id,
                "decision_index": index, "action": action["action"], "credit": credit,
                "result": canonical({"status": "completed", "record_refs": references,
                    "changed_record_refs": [ref for ref in references if ref in changed],
                    'child_completion': child_completion_status(receiver.store, spec['run_id'],
                        spec['child']['episode_id'], returned['completion'], delivery='admitted')})})
            receiver.store.db.execute("INSERT INTO runtime_return_delivery_resolutions VALUES(?,?,?,?,?,?)",
                (spec["run_id"], returned["return_id"], content_digest(original), repair_decision_index,
                 canonical(delivery_contract.as_record()), canonical(resolved)))
            from .episode_completion import CompletionLedger
            CompletionLedger(receiver.store, receiver.journal).stage(parent_id, index,
                label=spec["child"]["key"], kind="child_return", controller_input=controller_input,
                child_return={name: resolved[name] for name in ("handle", "return_id", "admission_id")})
            return resolved
    except sqlite3.Error as error:
        raise AdmissionError("storage_failure", affected_refs=[spec["handle"]]) from error
