"""Read the original local commission population without receiving child work.

C1 defines the population; C3 supplies return metadata, while the existing E2
reader supplies original admission/payoff evidence.  Store and backend reads
have separate provenance and do not constitute an atomic cross-database view.
This adapter installs nothing and has no execution, admission or credit role.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from collections.abc import Mapping

from method_loop import EpisodeGoal
from method_loop.communication import ReportContract
from method_loop.durable import canonical, content_digest, validate_commission, validate_return
from method_loop.identities import EpisodeRef

from .local_return_history import LocalReturnHistory
from .waiting import validate_pending


VERSION = "local_commission_frame_v1"


def _invalid():
    raise ValueError("local_commission_frame_invalid_input")


def _conflict():
    raise ValueError("local_commission_frame_identity_conflict")


def _text(value):
    return isinstance(value, str) and bool(value)


def _index(value):
    return type(value) is int and value >= 0


def _copy(value):
    return json.loads(canonical(value))


def _saved(value):
    try:
        return _copy(json.loads(value))
    except (TypeError, ValueError, OverflowError):
        _conflict()


def _utc(value):
    if not _text(value):
        _invalid()
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        _invalid()
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        _invalid()
    return stamp


def _now():
    return datetime.now(timezone.utc).isoformat()


def _interval(started_at, finished_at):
    if _utc(finished_at) < _utc(started_at):
        raise ValueError("local_commission_frame_clock_order_failure")
    return {"started_at": started_at, "finished_at": finished_at}


def _reason(reasons, reason):
    if reason not in reasons:
        reasons.append(reason)


class LocalCommissionFrame:
    """A read-only projection scoped to the Journal's original run identity."""

    def __init__(self, store, journal, backend):
        if (getattr(journal, "db", None) is None
                or getattr(journal, "db", None) is not getattr(store, "db", None)
                or not _text(getattr(journal, "run_id", None))):
            _invalid()
        self.store, self.journal, self.backend = store, journal, backend
        self.returns = LocalReturnHistory(store, journal, backend)

    def capture(self, episode_id, *, pending, controller_credit, page_size):
        if not _text(episode_id) or type(page_size) is not int or page_size <= 0:
            _invalid()
        try:
            pending = None if pending is None else validate_pending(pending)
            credit = None if controller_credit is None else _copy(controller_credit)
        except (TypeError, ValueError, OverflowError):
            _invalid()
        if credit is not None and (
                not isinstance(credit, dict)
                or set(credit) != {"credit_kind", "credit_binding"}
                or not _text(credit["credit_kind"])
                or credit["credit_kind"] not in {"scientific", "monitoring", "operational"}
                or not isinstance(credit["credit_binding"], dict)
                or not credit["credit_binding"]):
            _invalid()
        reasons = []
        if credit is None:
            reasons.append("controller_credit_binding_unavailable")
        if pending is None:
            reasons.append("pending_snapshot_unavailable")
        started = _now()
        with self.store.read_snapshot():
            tables = {row[0] for row in self.store.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            parent = self._parent(episode_id, tables)
            rows = []
            population_status, population_count = "unavailable", None
            if "runtime_commission_intents" not in tables:
                reasons.append("commission_population_unavailable")
            else:
                originals = self.store.db.execute(
                    "SELECT * FROM runtime_commission_intents WHERE run_id=? "
                    "AND parent_episode_id=? ORDER BY original_decision_index",
                    (self.journal.run_id, episode_id)).fetchall()
                rows = [self._commission(row, episode_id, parent, tables)
                        for row in originals]
                population_status, population_count = "complete", len(rows)
            by_handle = {row["handle"]: row for row in rows}
            if len(by_handle) != len(rows):
                _conflict()
            by_index = {row["original_decision_index"]: row for row in rows}
            if pending is not None:
                for item in pending["items"]:
                    row = by_handle.get(item["handle"])
                    if row is None:
                        if population_status == "complete":
                            _conflict()
                        continue
                    if (item["role"] != row["commission"]["child"]["role"]
                            or item["selected_at"] != row["selected_at"]
                            or canonical(item["resource_selection"])
                                != canonical(row["commission"]["resource_selection"])
                            or canonical(item["expectation_snapshot_refs"])
                                != canonical(row["commission"]["expectation_snapshot_refs"])):
                        _conflict()
                    row["pending_status_fact"] = _copy(item)
            unmatched = self._admissions(episode_id, by_index, tables, reasons)
            self._attempts(episode_id, rows, tables, reasons)
            if population_status == "complete":
                scan = self._scan(episode_id, by_handle, page_size, reasons)
            else:
                scan = {"status": "unavailable", "next_cursor": None,
                        "exhausted": False, "reads": []}
                _reason(reasons, "return_scan_unavailable")
        finished = _now()
        return _copy({"version": VERSION, "run_id": self.journal.run_id,
            "episode_id": episode_id, "parent_state_at_store_read": parent["state"],
            "controller_credit": credit,
            "pending_captured_at": None if pending is None else pending["captured_at"],
            "store_read_interval": _interval(started, finished),
            "population_status": population_status, "population_count": population_count,
            "commissions": rows, "return_scan": scan,
            "unmatched_admission_refs": unmatched, "unavailable_reasons": reasons})

    def _parent(self, episode_id, tables):
        if "runtime_episodes" not in tables:
            _invalid()
        row = self.store.db.execute(
            "SELECT path,state,json_extract(request,'$.goal') AS goal "
            "FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.journal.run_id, episode_id)).fetchone()
        if row is None:
            _invalid()
        path, goal = _saved(row["path"]), _saved(row["goal"])
        try:
            reference = EpisodeRef(self.journal.run_id, path)
            EpisodeGoal.from_record(goal)
        except (TypeError, ValueError):
            _conflict()
        if reference.episode_id != episode_id or not _text(row["state"]):
            _conflict()
        return {"path": path, "goal": goal, "state": row["state"]}

    def _commission(self, original, episode_id, parent, tables):
        index = original["original_decision_index"]
        if not _index(index):
            _conflict()
        selection = _saved(original["selection"])
        try:
            spec = validate_commission(_saved(original["spec"]))
            _utc(original["selected_at"])
        except (TypeError, ValueError, RuntimeError):
            _conflict()
        if (not isinstance(selection, dict)
                or spec["run_id"] != self.journal.run_id
                or spec["parent"]["episode_id"] != episode_id
                or spec["parent"]["path"] != parent["path"]
                or spec["parent"]["goal_id"] != parent["goal"]["goal_id"]
                or spec["handle"] != original["handle"]
                or spec["operation_key"] != original["operation_key"]
                or content_digest(spec) != original["commission_sha256"]):
            _conflict()
        action = (self.journal.row("runtime_actions", episode_id, index)
                  if "runtime_actions" in tables else None)
        status, reasons = None, []
        child = self.store.db.execute(
            "SELECT path,request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.journal.run_id, spec["child"]["episode_id"])).fetchone()
        if child is None:
            reasons.append("child_record_unavailable")
        elif (canonical(_saved(child["path"])) != canonical(spec["child"]["path"])
                or canonical(_saved(child["request"])) != canonical(spec["child"]["request"])):
            _conflict()
        if action is None:
            reasons.append("original_action_unavailable")
        else:
            if canonical(_saved(action["action"])) != canonical(selection):
                _conflict()
            if action["result"] is not None:
                outcome = _saved(action["result"])
                if not isinstance(outcome, dict) or not _text(outcome.get("status")):
                    _conflict()
                status = outcome["status"]
                if status == "pending" and (
                        outcome.get("pending_handle") != spec["handle"]
                        or outcome.get("selected_at") != original["selected_at"]
                        or action["credit"] is not None):
                    _conflict()
        return {"original_decision_index": index, "handle": spec["handle"],
            "operation_key": spec["operation_key"],
            "commission_sha256": original["commission_sha256"], "commission": spec,
            "selection": selection, "selected_at": original["selected_at"],
            "accounting_status": status, "pending_status_fact": None,
            "return_presence": "unknown", "return_metadata": None,
            "admission_evidence": None, "representation_attempts": [],
            "unavailable_reasons": reasons}

    def _admissions(self, episode_id, by_index, tables, reasons):
        if "runtime_return_admissions" not in tables:
            _reason(reasons, "return_admissions_unavailable")
            return []
        originals = self.store.db.execute(
            "SELECT run_id,parent_episode_id,original_decision_index,handle,return_id,"
            "json_extract(admission,'$.version') AS body_version,"
            "json_extract(admission,'$.admission_id') AS admission_id,"
            "json_extract(admission,'$.parent_episode_id') AS body_parent_episode_id,"
            "json_extract(admission,'$.original_decision_index') AS body_decision_index,"
            "json_type(admission,'$.original_decision_index') AS body_index_type,"
            "json_extract(admission,'$.handle') AS body_handle,"
            "json_extract(admission,'$.return_id') AS body_return_id "
            "FROM runtime_return_admissions WHERE run_id=? AND parent_episode_id=? "
            "ORDER BY original_decision_index", (self.journal.run_id, episode_id))
        unmatched = []
        for original in originals:
            if (not _index(original["original_decision_index"])
                    or any(not _text(original[key]) for key in
                           ("handle", "return_id", "admission_id"))
                    or original["run_id"] != self.journal.run_id
                    or original["parent_episode_id"] != episode_id
                    or original["body_version"] != "episode_admission_v1"
                    or original["body_parent_episode_id"] != episode_id
                    or original["body_index_type"] != "integer"
                    or original["body_decision_index"] != original["original_decision_index"]
                    or original["body_handle"] != original["handle"]
                    or original["body_return_id"] != original["return_id"]):
                _conflict()
            expected = "admission_" + content_digest({"run_id": self.journal.run_id,
                "parent_episode_id": episode_id,
                "original_decision_index": original["original_decision_index"],
                "return_id": original["return_id"]})
            if original["admission_id"] != expected:
                _conflict()
            row = by_index.get(original["original_decision_index"])
            if row is None:
                unmatched.append(original["admission_id"])
                continue
            if row["handle"] != original["handle"]:
                _conflict()
            try:
                evidence = self.returns.read_return(episode_id, row["original_decision_index"])
            except (TypeError, ValueError):
                _conflict()
            if evidence is None:
                _conflict()
            sample = evidence["sample"]
            if (sample["child_handle"] != row["handle"]
                    or sample["commission_sha256"] != row["commission_sha256"]
                    or sample["return_id"] != original["return_id"]
                    or sample["admission_id"] != original["admission_id"]):
                _conflict()
            row["admission_evidence"] = _copy(evidence)
        if unmatched:
            _reason(reasons, "unmatched_admissions")
        return unmatched

    def _attempts(self, episode_id, rows, tables, reasons):
        if "runtime_report_attempts" not in tables:
            _reason(reasons, "report_attempts_unavailable")
            for row in rows:
                _reason(row["unavailable_reasons"], "report_attempts_unavailable")
            return
        by_child, by_delivery, by_index = {}, {}, {}
        for row in rows:
            child = row["commission"]["child"]["episode_id"]
            delivery = "delivery_" + content_digest({"run": self.journal.run_id,
                "parent": episode_id, "index": row["original_decision_index"]})[:24]
            if child in by_child or delivery in by_delivery:
                _conflict()
            by_child[child] = by_delivery[delivery] = row
            by_index[row["original_decision_index"]] = row
        attempts = self.store.db.execute(
            "SELECT decision_index,delivery_ref,child_episode_id,contract,"
            "form IS NOT NULL AS form_recorded,failure FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? ORDER BY decision_index",
            (self.journal.run_id, episode_id))
        for attempt in attempts:
            index, delivery, child = (attempt[key] for key in
                ("decision_index", "delivery_ref", "child_episode_id"))
            if not _index(index) or not _text(delivery) or not _text(child):
                _conflict()
            candidates = [row for row in (by_delivery.get(delivery), by_child.get(child),
                                          by_index.get(index)) if row is not None]
            if not candidates:
                continue
            row = candidates[0]
            if (any(candidate is not row for candidate in candidates)
                    or by_child.get(child) is not row or by_delivery.get(delivery) is not row):
                _conflict()
            contract = _saved(attempt["contract"])
            try:
                ReportContract.from_record(contract)
            except (TypeError, ValueError, KeyError):
                _conflict()
            if (index == row["original_decision_index"]
                    and canonical(contract)
                        != canonical(row["commission"]["child"]["request"]["report_contract"])):
                _conflict()
            failure = None if attempt["failure"] is None else _saved(attempt["failure"])
            if failure is not None and not isinstance(failure, dict):
                _conflict()
            row["representation_attempts"].append({"decision_index": index,
                "delivery_ref": delivery, "child_episode_id": child,
                "report_contract_sha256": content_digest(contract),
                "form_recorded": bool(attempt["form_recorded"]), "failure": failure})

    def _scan(self, episode_id, by_handle, page_size, reasons):
        scan = {"status": "complete", "next_cursor": 0, "exhausted": False, "reads": []}
        seen = set()
        while len(seen) < len(by_handle):
            cursor = scan["next_cursor"]
            limit = min(page_size, len(by_handle) - len(seen))
            started = _now()
            try:
                page = self.backend.return_page(episode_id, cursor, limit)
            except Exception:
                finished = _now()
                span = _interval(started, finished)
                scan["reads"].append({"after_cursor": cursor, "next_cursor": None, **span})
                scan["status"] = "incomplete" if len(scan["reads"]) > 1 else "unavailable"
                _reason(reasons, "return_scan_unavailable")
                break
            finished = _now()
            span = _interval(started, finished)
            page = self._page(page, cursor, limit)
            scan["reads"].append({"after_cursor": cursor,
                                  "next_cursor": page["next_cursor"], **span})
            scan["next_cursor"] = page["next_cursor"]
            if not page["items"]:
                scan["exhausted"] = True
                break
            outside = False
            for item in page["items"]:
                if item["handle"] in seen:
                    _conflict()
                seen.add(item["handle"])
                row = by_handle.get(item["handle"])
                if row is None:
                    outside = True
                    _reason(reasons, "return_outside_commission_snapshot")
                    continue
                row["return_presence"] = "observed"
                row["return_metadata"] = self._metadata(row, item, span)
            if outside:
                scan["status"] = "incomplete"
                break
        if scan["status"] == "complete":
            for row in by_handle.values():
                if row["return_presence"] != "observed":
                    row["return_presence"] = "not_observed_in_completed_scan"
        else:
            for row in by_handle.values():
                if row["return_presence"] == "unknown":
                    _reason(row["unavailable_reasons"], "return_scan_unavailable"
                        if "return_scan_unavailable" in reasons else "return_outside_commission_snapshot")
        return scan

    @staticmethod
    def _page(page, cursor, limit):
        try:
            page = _copy(page)
        except (TypeError, ValueError, OverflowError):
            _invalid()
        if (not isinstance(page, dict)
                or set(page) != {"version", "after_cursor", "next_cursor", "items"}
                or page["version"] != "return_page_v1" or page["after_cursor"] != cursor
                or not _index(page["after_cursor"]) or not _index(page["next_cursor"])
                or not isinstance(page["items"], list) or len(page["items"]) > limit):
            _invalid()
        previous, handles = cursor, set()
        for item in page["items"]:
            if (not isinstance(item, dict)
                    or set(item) != {"cursor", "handle", "return_id", "returned_at"}
                    or not _index(item["cursor"]) or item["cursor"] == 0
                    or not _text(item["handle"]) or not _text(item["return_id"])):
                _invalid()
            _utc(item["returned_at"])
            if item["cursor"] <= previous or item["handle"] in handles:
                _conflict()
            previous = item["cursor"]
            handles.add(item["handle"])
        if page["next_cursor"] != previous:
            _conflict()
        return page

    def _metadata(self, row, item, span):
        metadata = {"return_id": item["return_id"], "cursor": item["cursor"],
            "returned_at": item["returned_at"], "outcome": None, "failure_code": None,
            "read_interval": _copy(span)}
        evidence = row["admission_evidence"]
        if evidence is not None:
            sample = evidence["sample"]
            if (sample["return_id"] != item["return_id"]
                    or sample["returned_at"] is not None
                        and sample["returned_at"] != item["returned_at"]):
                _conflict()
        try:
            returned = self.backend.load_return(row["handle"], item["return_id"])
        except Exception:
            _reason(row["unavailable_reasons"], "return_envelope_unavailable")
            return metadata
        if (not isinstance(returned, Mapping) or returned.get("handle") != row["handle"]
                or returned.get("return_id") != item["return_id"]
                or returned.get("commission_sha256") != row["commission_sha256"]
                or returned.get("returned_at") != item["returned_at"]):
            _conflict()
        try:
            returned = validate_return(returned, spec=row["commission"],
                                       commission_sha256=row["commission_sha256"])
        except (TypeError, ValueError, RuntimeError):
            _invalid()
        metadata["outcome"] = returned["outcome"]
        metadata["failure_code"] = (None if returned["failure"] is None
                                    else returned["failure"]["code"])
        return metadata


__all__ = ["LocalCommissionFrame", "VERSION"]
