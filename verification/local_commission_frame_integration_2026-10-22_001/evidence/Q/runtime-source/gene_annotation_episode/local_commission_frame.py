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


__all__ = ["LocalCommissionFrame", "validate_local_commission_frame", "VERSION"]


def _fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names.split()):
        _invalid()


def _texts(value):
    if not isinstance(value, list) or any(not _text(item) or not item.strip() for item in value):
        _invalid()


def _digest(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        _invalid()


def _read_interval(value):
    _fields(value, "started_at finished_at")
    if _utc(value["started_at"]) > _utc(value["finished_at"]):
        _invalid()


def _credit(value):
    if value is not None:
        _fields(value, "credit_kind credit_binding")
        if (not _text(value["credit_kind"])
                or value["credit_kind"] not in {"scientific", "monitoring", "operational"}
                or not isinstance(value["credit_binding"], dict) or not value["credit_binding"]):
            _invalid()


def validate_local_commission_frame(value, *, run_id, episode_id, pending,
                                    controller_credit) -> dict:
    """Copy saved C1/C3/E2 facts and validate only their available relationships.

    No capture, Store, backend, clock, projection or controller participates.
    In particular original selection scope/assignment may precede producer
    normalization/preparation: only unchanged typed mirrors are checked here.
    JSON cannot authenticate the original reads or prove historical coverage.
    """
    try:
        value, pending, credit = _copy(value), _copy(pending), _copy(controller_credit)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError("local_commission_frame_invalid_input") from error
    if not _text(run_id) or not _text(episode_id):
        _invalid()
    _fields(value, "version run_id episode_id parent_state_at_store_read controller_credit "
        "pending_captured_at store_read_interval population_status population_count commissions "
        "return_scan unmatched_admission_refs unavailable_reasons")
    if (value["version"] != VERSION or not _text(value["run_id"])
            or not _text(value["episode_id"]) or not _text(value["parent_state_at_store_read"])
            or not isinstance(value["commissions"], list)
            or not _text(value["population_status"])
            or value["population_status"] not in {"complete", "unavailable"}):
        _invalid()
    if value["run_id"] != run_id or value["episode_id"] != episode_id:
        _conflict()
    _read_interval(value["store_read_interval"])
    _credit(credit)
    _credit(value["controller_credit"])
    if canonical(value["controller_credit"]) != canonical(credit):
        _conflict()
    _texts(value["unavailable_reasons"])
    _texts(value["unmatched_admission_refs"])
    reasons = value["unavailable_reasons"]
    unmatched = value["unmatched_admission_refs"]
    if len(set(unmatched)) != len(unmatched):
        _conflict()
    for reference in unmatched:
        if not reference.startswith("admission_"):
            _invalid()
        _digest(reference[len("admission_"):])
    if bool(unmatched) != ("unmatched_admissions" in reasons):
        _conflict()
    if (credit is None) != ("controller_credit_binding_unavailable" in reasons):
        _conflict()
    if (pending is None) != ("pending_snapshot_unavailable" in reasons):
        _conflict()
    if pending is not None:
        try:
            pending = validate_pending(pending)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("local_commission_frame_invalid_input") from error
        if value["pending_captured_at"] != pending["captured_at"]:
            _conflict()
    elif value["pending_captured_at"] is not None:
        _conflict()
    facts = {} if pending is None else {item["handle"]: item for item in pending["items"]}
    if value["pending_captured_at"] is not None:
        _utc(value["pending_captured_at"])
    rows = value["commissions"]
    if value["population_status"] == "complete":
        if not _index(value["population_count"]):
            _invalid()
        if value["population_count"] != len(rows):
            _conflict()
        if "commission_population_unavailable" in reasons:
            _conflict()
    elif (value["population_count"] is not None or rows
            or "commission_population_unavailable" not in reasons):
        _conflict()

    scan = value["return_scan"]
    _fields(scan, "status next_cursor exhausted reads")
    if (not _text(scan["status"]) or scan["status"] not in {"complete", "incomplete", "unavailable"}
            or type(scan["exhausted"]) is not bool or not isinstance(scan["reads"], list)
            or scan["next_cursor"] is not None and not _index(scan["next_cursor"])):
        _invalid()
    cursor, failed, successful_reads = 0, False, []
    for position, read in enumerate(scan["reads"]):
        _fields(read, "after_cursor next_cursor started_at finished_at")
        _read_interval({key: read[key] for key in ("started_at", "finished_at")})
        if not _index(read["after_cursor"]) or read["next_cursor"] is not None and not _index(read["next_cursor"]):
            _invalid()
        if read["after_cursor"] != cursor:
            _conflict()
        if read["next_cursor"] is None:
            if position != len(scan["reads"])-1:
                _conflict()
            failed = True
        else:
            if read["next_cursor"] < cursor or (read["next_cursor"] == cursor and position != len(scan["reads"])-1):
                _conflict()
            successful_reads.append(read)
            cursor = read["next_cursor"]
    if value["population_status"] == "unavailable":
        if (scan != {"status": "unavailable", "next_cursor": None, "exhausted": False, "reads": []}
                or "return_scan_unavailable" not in reasons):
            _conflict()
    else:
        if scan["next_cursor"] != cursor:
            _conflict()
        exhausted = bool(successful_reads and successful_reads[-1]["next_cursor"] == successful_reads[-1]["after_cursor"])
        if scan["exhausted"] != exhausted:
            _conflict()
        if scan["status"] == "complete":
            if failed or "return_scan_unavailable" in reasons or "return_outside_commission_snapshot" in reasons:
                _conflict()
            if rows and not scan["reads"]:
                _conflict()
        elif scan["status"] == "unavailable":
            if not failed or len(scan["reads"]) != 1 or cursor != 0 or scan["exhausted"]:
                _conflict()
        elif (scan["exhausted"] or not scan["reads"] or
                (not failed and "return_outside_commission_snapshot" not in reasons)
                or failed and not successful_reads):
            _conflict()
        if failed != ("return_scan_unavailable" in reasons):
            _conflict()
        if not rows and scan != {"status": "complete", "next_cursor": 0, "exhausted": False, "reads": []}:
            _conflict()

    handles, operations, children, sample_ids, units, sequences, metadata_cursors = (set() for _ in range(7))
    previous, parent_identity, attempt_indices = -1, None, {}
    for row in rows:
        _fields(row, "original_decision_index handle operation_key commission_sha256 commission "
            "selection selected_at accounting_status pending_status_fact return_presence return_metadata "
            "admission_evidence representation_attempts unavailable_reasons")
        if (not _index(row["original_decision_index"])
                or any(not _text(row[key]) for key in ("handle", "operation_key"))
                or not isinstance(row["selection"], dict)
                or row["accounting_status"] is not None and not _text(row["accounting_status"])
                or not _text(row["return_presence"])
                or row["return_presence"] not in {"observed", "not_observed_in_completed_scan", "unknown"}
                or not isinstance(row["representation_attempts"], list)):
            _invalid()
        _digest(row["commission_sha256"])
        _utc(row["selected_at"])
        _texts(row["unavailable_reasons"])
        index = row["original_decision_index"]
        if index <= previous:
            _conflict()
        previous = index
        try:
            spec = validate_commission(row["commission"])
        except RuntimeError as error:
            raise ValueError("local_commission_frame_identity_conflict") from error
        except (TypeError, ValueError, KeyError, OverflowError) as error:
            raise ValueError("local_commission_frame_invalid_input") from error
        child = spec["child"]
        expected = content_digest({"run_id": run_id, "parent_episode_id": episode_id,
                                   "original_decision_index": index})
        if (spec["run_id"] != run_id or spec["parent"]["episode_id"] != episode_id
                or row["handle"] != spec["handle"] or row["handle"] != "execution_"+expected
                or row["operation_key"] != spec["operation_key"] or row["operation_key"] != "commission_"+expected
                or row["commission_sha256"] != content_digest(spec)
                or canonical(child["scope"]) != canonical(child["request"]["message"].get("scope"))):
            _conflict()
        current_parent = canonical(spec["parent"])
        if parent_identity is not None and current_parent != parent_identity:
            _conflict()
        parent_identity = current_parent
        for seen, identity in ((handles, row["handle"]), (operations, row["operation_key"]),
                               (children, child["episode_id"])):
            if identity in seen:
                _conflict()
            seen.add(identity)
        selection = row["selection"]
        if not _text(selection.get("kind")) or selection["kind"] not in {"child", "job_child", "episode_child"}:
            _invalid()
        if ("role" in selection and selection["role"] != child["role"]
                or "goal" in selection and canonical(selection["goal"]) != canonical(child["request"]["goal"]["objective"])
                or "purpose" in selection and canonical(selection["purpose"]) != canonical(child["request"]["report_contract"]["decision"])):
            _conflict()
        fact = facts.get(row["handle"])
        if canonical(row["pending_status_fact"]) != canonical(fact):
            _conflict()
        if fact is not None and (fact["role"] != child["role"] or fact["selected_at"] != row["selected_at"]
                or canonical(fact["resource_selection"]) != canonical(spec["resource_selection"])
                or canonical(fact["expectation_snapshot_refs"]) != canonical(spec["expectation_snapshot_refs"])):
            _conflict()
        contract_digest = content_digest(child["request"]["report_contract"])
        sample = None
        if row["admission_evidence"] is not None:
            from .wait_estimation_inputs import validate_local_return_evidence
            try:
                evidence = validate_local_return_evidence(row["admission_evidence"], run_id=run_id,
                    episode_id=episode_id, original_decision_index=index)
            except (TypeError, ValueError) as error:
                if str(error) == "local_return_evidence_identity_conflict":
                    _conflict()
                _invalid()
            sample = evidence["sample"]
            if (sample["child_handle"] != row["handle"] or sample["child_role"] != child["role"]
                    or sample["commission_sha256"] != row["commission_sha256"]
                    or sample["report_contract_sha256"] != contract_digest
                    or sample["selected_at"] != row["selected_at"]
                    or sample["sample_ref"] in sample_ids or sample["sample_ref"] in unmatched):
                _conflict()
            sample_ids.add(sample["sample_ref"])
            for key, seen in (("completion_sequence", sequences), ("unit_ref", units)):
                identity = sample[key] if key == "completion_sequence" else (
                    None if sample[key] is None else sample[key]["unit_id"])
                if identity is not None:
                    if identity in seen:
                        _conflict()
                    seen.add(identity)
        metadata = row["return_metadata"]
        if (row["return_presence"] == "observed") != (metadata is not None):
            _conflict()
        if scan["status"] == "complete":
            if row["return_presence"] == "unknown":
                _conflict()
        elif row["return_presence"] == "not_observed_in_completed_scan":
            _conflict()
        if metadata is not None:
            _fields(metadata, "return_id cursor returned_at outcome failure_code read_interval")
            if (not _text(metadata["return_id"]) or not _index(metadata["cursor"]) or metadata["cursor"] == 0
                    or metadata["outcome"] is not None and (not _text(metadata["outcome"])
                        or metadata["outcome"] not in {"closed", "execution_failed", "interrupted"})
                    or metadata["failure_code"] is not None and not _text(metadata["failure_code"])):
                _invalid()
            _utc(metadata["returned_at"])
            _read_interval(metadata["read_interval"])
            matching = [read for read in successful_reads
                if read["after_cursor"] < metadata["cursor"] <= read["next_cursor"]]
            if (metadata["cursor"] in metadata_cursors or len(matching) != 1
                    or canonical(metadata["read_interval"]) != canonical({key: matching[0][key]
                        for key in ("started_at", "finished_at")})):
                _conflict()
            metadata_cursors.add(metadata["cursor"])
            if metadata["outcome"] is None:
                if metadata["failure_code"] is not None or "return_envelope_unavailable" not in row["unavailable_reasons"]:
                    _conflict()
            elif ("return_envelope_unavailable" in row["unavailable_reasons"]
                    or metadata["outcome"] != "closed" and metadata["failure_code"] is None):
                _conflict()
            if sample is not None and (sample["return_id"] != metadata["return_id"]
                    or sample["returned_at"] is not None and sample["returned_at"] != metadata["returned_at"]
                    or metadata["outcome"] is not None and (
                        sample["admission_state"] in {"admitted", "delivery_failed"} and metadata["outcome"] != "closed"
                        or sample["admission_state"] == "execution_failed" and metadata["outcome"] == "closed")):
                _conflict()
        last_attempt = -1
        delivery = "delivery_" + content_digest({"run": run_id, "parent": episode_id, "index": index})[:24]
        for attempt in row["representation_attempts"]:
            _fields(attempt, "decision_index delivery_ref child_episode_id report_contract_sha256 form_recorded failure")
            if (not _index(attempt["decision_index"]) or not _text(attempt["delivery_ref"])
                    or not _text(attempt["child_episode_id"]) or type(attempt["form_recorded"]) is not bool
                    or attempt["failure"] is not None and not isinstance(attempt["failure"], dict)):
                _invalid()
            _digest(attempt["report_contract_sha256"])
            at = attempt["decision_index"]
            if (at < index or at <= last_attempt or at in attempt_indices
                    or attempt["delivery_ref"] != delivery or attempt["child_episode_id"] != child["episode_id"]
                    or at == index and attempt["report_contract_sha256"] != contract_digest):
                _conflict()
            attempt_indices[at] = index
            last_attempt = at
    if value["population_status"] == "complete" and not set(facts) <= handles:
        _conflict()
    if any(at in {row["original_decision_index"] for row in rows} and at != owner
           for at, owner in attempt_indices.items()):
        _conflict()
    if (value["population_status"] == "complete" and scan["status"] == "complete"
            and not scan["exhausted"] and any(row["return_presence"] != "observed" for row in rows)):
        _conflict()
    return value
