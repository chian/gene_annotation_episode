"""Freeze an episode's selected child before publishing it for execution.

The Store intent and original pending action are one transaction. Publication
uses only that frozen intent, outside the transaction, through the public C2
backend. This boundary owns no child loop, receipt, credit or controller step.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import sqlite3

from method_loop.durable import (DurableExecutionError, DurableExecutionStore,
                                 canonical, content_digest, validate_commission)

from .domain import ContractError
from .episode_journal import Journal, WorkflowError
from .episode_receipts import EpisodeReceipts
from .state import Store


VERSION = "episode_commission_v1"
FAILURE_CODES = frozenset({"identity_conflict", "invalid_commission",
                           "unavailable_binding", "storage_failure"})


class CommissionError(WorkflowError):
    def __init__(self, code, *, affected_refs=()):
        if code not in FAILURE_CODES:
            raise ValueError("undeclared_commission_failure_code")
        self.failure = {"code": code, "affected_refs": list(affected_refs),
                        "diagnostic_ref": None, "partial_record_refs": []}
        super().__init__(code)


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("selected_at_must_be_utc_text")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        raise ValueError("selected_at_must_be_utc_text")


def _conflict(*references):
    raise CommissionError("identity_conflict", affected_refs=references)


class CommissionCoordinator:
    def __init__(self, store: Store, journal: Journal, backend: DurableExecutionStore):
        if journal.db is not store.db:
            raise ValueError("commission_journal_requires_same_store_connection")
        if not isinstance(journal.run_id, str) or not journal.run_id:
            raise ValueError("commission_run_identity_required")
        self.store, self.journal, self.backend = store, journal, backend
        with store.transaction():
            store.db.execute("""CREATE TABLE IF NOT EXISTS runtime_commission_intents (
                run_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL,
                original_decision_index INTEGER NOT NULL, handle TEXT NOT NULL,
                operation_key TEXT NOT NULL, commission_sha256 TEXT NOT NULL,
                spec TEXT NOT NULL, selection TEXT NOT NULL, selected_at TEXT NOT NULL,
                PRIMARY KEY(run_id,parent_episode_id,original_decision_index),
                UNIQUE(run_id,handle), UNIQUE(run_id,operation_key))""")

    def select(self, *, parent: dict, child: dict, original_decision_index: int,
               selection: dict, runtime_binding: dict, input_versions: list,
               constraints: dict, resource_selection: dict | None,
               expectation_snapshot_refs: list, selected_at: str) -> dict:
        """Commit the exact C1 assignment and its original pending action."""
        if type(original_decision_index) is not int or original_decision_index < 0:
            raise ValueError("original_decision_index_required")
        _timestamp(selected_at)
        if not isinstance(selection, dict):
            raise ValueError("commission_selection_must_be_json_object")
        # Identity does not depend on assignment content: changing a selection
        # at this original decision is a conflict rather than another execution.
        identity = {"run_id": self.journal.run_id,
                    "parent_episode_id": parent["episode_id"],
                    "original_decision_index": original_decision_index}
        digest = content_digest(identity)
        handle, operation_key = "execution_" + digest, "commission_" + digest
        try:
            spec = validate_commission({"version": VERSION, "handle": handle,
                "operation_key": operation_key, "run_id": self.journal.run_id,
                "parent": parent, "child": child, "input_versions": input_versions,
                "runtime_binding": runtime_binding, "constraints": constraints,
                "resource_selection": resource_selection,
                "expectation_snapshot_refs": expectation_snapshot_refs})
            serialized_selection = canonical(selection)
        except DurableExecutionError as error:
            raise CommissionError(error.failure["code"],
                                  affected_refs=error.failure["affected_refs"]) from error
        except (ValueError, TypeError, KeyError) as error:
            raise CommissionError("invalid_commission", affected_refs=[handle]) from error
        key = (self.journal.run_id, parent["episode_id"], original_decision_index)
        try:
            with self.store.transaction():
                old = self.store.db.execute("SELECT * FROM runtime_commission_intents "
                    "WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?", key).fetchone()
                action = self.journal.row("runtime_actions", parent["episode_id"], original_decision_index)
                if old is not None:
                    original = self._spec(old)
                    if (old["spec"] != canonical(spec) or old["selection"] != serialized_selection
                            or old["selected_at"] != selected_at or action is None
                            or canonical(json.loads(action["action"])) != serialized_selection):
                        _conflict(handle)
                    # Completed action/credit and original timing remain intact.
                    return original
                self._validate_assignment(spec)
                pending = {"status": "pending", "pending_handle": handle,
                           "selected_at": selected_at}
                if action is not None and (
                        canonical(json.loads(action["action"])) != serialized_selection
                        or action["credit"] is not None
                        or (action["result"] is not None and json.loads(action["result"]) != pending)):
                    _conflict(handle)
                self.store.db.execute("INSERT INTO runtime_commission_intents VALUES(?,?,?,?,?,?,?,?,?)",
                    (*key, handle, operation_key, content_digest(spec), canonical(spec),
                     serialized_selection, selected_at))
                self.journal.save("runtime_actions", {"episode_id": parent["episode_id"],
                    "decision_index": original_decision_index, "action": serialized_selection,
                    "result": canonical(pending), "credit": None})
                return spec
        except sqlite3.Error as error:
            raise CommissionError("storage_failure", affected_refs=[handle]) from error

    def _validate_assignment(self, spec):
        """Check frozen producer operands against authoritative local records."""
        parent, child = spec["parent"], spec["child"]
        parent_row = self.journal.row("runtime_episodes", parent["episode_id"])
        child_row = self.journal.row("runtime_episodes", child["episode_id"])
        if parent_row is None or child_row is None:
            raise CommissionError("unavailable_binding", affected_refs=[spec["handle"]])
        parent_request = json.loads(parent_row["request"])
        if (json.loads(parent_row["path"]) != parent["path"]
                or parent_request["goal"]["goal_id"] != parent["goal_id"]
                or json.loads(child_row["path"]) != child["path"]
                or json.loads(child_row["request"]) != child["request"]):
            _conflict(spec["handle"])
        try:
            scope = self.store.validate_scope(child["scope"], parent_request["message"]["scope"])
            if scope != child["scope"] or scope != child["request"]["message"].get("scope"):
                _conflict(spec["handle"])
            for operand in spec["input_versions"]:
                ref = operand["reference"]
                record = self.store.get(ref)
                version = record.get("version")
                if (operand["version"] is not None
                        and operand["version"] != (str(version) if version is not None else None)):
                    _conflict(ref)
                if operand["content_sha256"] is not None:
                    actual = (hashlib.sha256(self.store.get_artifact(ref)).hexdigest()
                              if record["record_type"] == "artifact" else content_digest(record))
                    if actual != operand["content_sha256"]:
                        _conflict(ref)
        except (ContractError, ValueError, KeyError) as error:
            raise CommissionError("invalid_commission", affected_refs=[spec["handle"]]) from error
        # Read the already frozen inheritance. Binding or receiving information
        # here would change the original scientific assignment.
        inheritance = child["request"]["message"].get("knowledge_inheritance")
        try:
            expected = EpisodeReceipts.read_manifest(self.store.db, self.journal.run_id,
                                                     child["episode_id"])
        except ValueError as error:
            if str(error) != 'episode_receipts_not_bound':
                _conflict(spec["handle"])
            expected = None
        if inheritance is not None or expected is not None:
            if (inheritance != expected or expected is None
                    or expected['parent_episode_id'] != parent["episode_id"]):
                _conflict(spec["handle"])

    def _spec(self, row):
        spec = validate_commission(json.loads(row["spec"]))
        if (content_digest(spec) != row["commission_sha256"]
                or spec["run_id"] != self.journal.run_id
                or spec["parent"]["episode_id"] != row["parent_episode_id"]
                or spec["handle"] != row["handle"] or spec["operation_key"] != row["operation_key"]):
            _conflict(row["handle"])
        return spec

    def _intent(self, handle):
        row = self.store.db.execute("SELECT * FROM runtime_commission_intents "
            "WHERE run_id=? AND handle=?", (self.journal.run_id, handle)).fetchone()
        if row is None:
            raise KeyError(handle)
        return row

    @staticmethod
    def _check_status(status, spec):
        if (status["handle"] != spec["handle"]
                or status["commission_sha256"] != content_digest(spec)):
            _conflict(spec["handle"])
        return status

    def dispatch(self, handle: str) -> dict:
        """Publish saved work once through the backend's identity-safe start."""
        if self.store.db.in_transaction:
            raise WorkflowError("commission_dispatch_requires_committed_store_transaction")
        spec = self._spec(self._intent(handle))
        receipt = self.backend.commission(spec)
        if (receipt["handle"] != handle
                or receipt["commission_sha256"] != content_digest(spec)):
            _conflict(handle)
        return self._check_status(self.backend.start(handle), spec)

    def recover_selected(self, parent_episode_id: str) -> list[dict]:
        """Read this parent's saved selections without publishing or rebinding."""
        rows = self.store.db.execute("SELECT * FROM runtime_commission_intents "
            "WHERE run_id=? AND parent_episode_id=? ORDER BY original_decision_index",
            (self.journal.run_id, parent_episode_id))
        return [self._spec(row) for row in rows]

    def pending(self, parent_episode_id: str) -> dict:
        """Expose commitments and public execution facts, without child archives."""
        captured = datetime.now(timezone.utc).isoformat()
        rows = self.store.db.execute("SELECT intents.*,actions.result,actions.credit "
            "FROM runtime_commission_intents intents JOIN runtime_actions actions "
            "ON actions.run_id=intents.run_id AND actions.episode_id=intents.parent_episode_id "
            "AND actions.decision_index=intents.original_decision_index "
            "WHERE intents.run_id=? AND intents.parent_episode_id=? "
            "AND json_extract(actions.result,'$.status')='pending' ORDER BY original_decision_index",
            (self.journal.run_id, parent_episode_id)).fetchall()
        items = []
        for row in rows:
            spec = self._spec(row)
            result = json.loads(row["result"])
            if (result.get("pending_handle") != spec["handle"]
                    or result.get("selected_at") != row["selected_at"] or row["credit"] is not None):
                _conflict(spec["handle"])
            try:
                status = self.backend.status(spec["handle"])
            except KeyError:
                # Timestamp this lookup of an unpublished intent, asserting no
                # physical execution identity or measured duration.
                status = {"lifecycle_state": "pending", "observed_at": captured,
                          "return_available": False}
            else:
                self._check_status(status, spec)
            items.append({"handle": spec["handle"], "role": spec["child"]["role"],
                "lifecycle_state": status["lifecycle_state"], "selected_at": row["selected_at"],
                "observed_at": status["observed_at"], "resource_selection": spec["resource_selection"],
                "expectation_snapshot_refs": spec["expectation_snapshot_refs"],
                "latest_progress_ref": None, "return_available": status["return_available"]})
        return {"version": "pending_work_v1", "captured_at": captured, "items": items}


__all__ = ["CommissionCoordinator", "CommissionError", "VERSION", "FAILURE_CODES"]
