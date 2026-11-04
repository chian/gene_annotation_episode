"""Current completed-action delivery facts, read before controller observation.

The packet names the actual supplied unit and the frozen original action. It
does not decide whether a delivered reference is new, project credit, admit a
return, or read scientific bodies. C4 timing uses the single original-return
reader; C8 bodies use only the scoped immutable progress reader.
"""
from __future__ import annotations

import json
import math
from datetime import datetime

from method_loop import ClosedRecord
from method_loop.durable import canonical, content_digest
from method_loop.identities import EpisodeRef, UnitRef

from .domain import ContractError, validate_schema
from .episode_monitoring import _SNAPSHOT
from .local_return_history import LocalReturnHistory
from .progress_records import validate_job_status


VERSION = "completed_action_evidence_v1"
_CHILD_KINDS = {"child", "job_child", "episode_child"}
_KINDS = {"tool", "reason", "wait", *_CHILD_KINDS}
_FIELDS = {"version", "run_id", "episode_id", "unit_ref", "original_decision_index",
    "action_kind", "received_record_refs", "received_progress_refs", "progress_records",
    "child_return", "unavailable_reasons"}
_RETURN_FIELDS = {"child_handle", "return_id", "admission_id", "admission_state",
    "commission_sha256", "report_contract_sha256", "selected_at", "returned_at",
    "selection_to_return"}


def _text(value):
    return isinstance(value, str) and bool(value)


def _index(value):
    return type(value) is int and value >= 0


def _invalid():
    raise ValueError("invalid_completion_evidence")


def _conflict():
    raise ValueError("completion_evidence_identity_conflict")


def _copy(value):
    try:
        return json.loads(canonical(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("invalid_completion_evidence") from error


def _load(value):
    try:
        return _copy(json.loads(value))
    except (TypeError, ValueError) as error:
        raise ValueError("completion_evidence_invalid_saved_json") from error


def _refs(value):
    return isinstance(value, list) and all(_text(ref) for ref in value)


def _utc(value):
    if not _text(value):
        _invalid()
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            _invalid()
        return stamp
    except (ValueError, OverflowError) as error:
        raise ValueError("invalid_completion_evidence") from error


def _unit(value):
    try:
        return UnitRef.from_record(value)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid_completion_evidence") from error


def _progress(snapshot):
    try:
        validate_schema(snapshot, _SNAPSHOT)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid_completion_evidence") from error
    if snapshot["target_handle"] != snapshot["execution_status"]["handle"]:
        _invalid()
    status = snapshot["execution_status"]
    if snapshot["result_available"] != status.get("result_available", status.get("return_available")):
        _invalid()
    if status["version"] == "job_execution_status_v1":
        validate_job_status(status)
    elif (status["return_available"] != (status["return_id"] is not None)
            or status["return_available"] != (status["lifecycle_state"] in {"returned", "admitted"})
            or (status["acknowledgment_id"] is not None) != (status["lifecycle_state"] == "admitted")):
        _invalid()
    _utc(snapshot["observed_at"])
    _utc(status["observed_at"])
    for field, stamp in (("measurements", "measured_at"), ("dependencies", "observed_at"),
                         ("log_windows", "observed_at")):
        for record in snapshot[field]:
            _utc(record[stamp])
    for record in snapshot["log_windows"]:
        if record["end_byte"] < record["start_byte"]:
            _invalid()


def validate_completion_evidence(value, *, run_id=None, episode_id=None,
        original_decision_index=None, unit_ref=None) -> dict:
    """Validate/copy an existing finite packet, without consulting any service."""
    value = _copy(value)
    if (not isinstance(value, dict) or set(value) != _FIELDS
            or value["version"] != VERSION or not _text(value["run_id"])
            or not _text(value["episode_id"]) or not _index(value["original_decision_index"])
            or not _text(value["action_kind"]) or value["action_kind"] not in _KINDS
            or not _refs(value["received_record_refs"]) or not _refs(value["received_progress_refs"])
            or not _refs(value["unavailable_reasons"]) or not isinstance(value["progress_records"], list)
            or len(set(value["received_progress_refs"])) != len(value["received_progress_refs"])):
        _invalid()
    actual = _unit(value["unit_ref"])
    if (actual.episode_id != value["episode_id"]
            or run_id is not None and value["run_id"] != run_id
            or episode_id is not None and value["episode_id"] != episode_id
            or original_decision_index is not None and (not _index(original_decision_index)
                or value["original_decision_index"] != original_decision_index)
            or unit_ref is not None and (not isinstance(unit_ref, UnitRef) or actual != unit_ref)):
        _conflict()
    bodies = set()
    for snapshot in value["progress_records"]:
        _progress(snapshot)
        reference = snapshot["progress_ref"]
        if reference not in value["received_progress_refs"] or reference in bodies:
            _invalid()
        bodies.add(reference)
    for reference in value["received_progress_refs"]:
        if reference not in bodies and not any(reason in value["unavailable_reasons"] for reason in (
                "progress_reader_unavailable:" + reference, "progress_body_unavailable:" + reference)):
            _invalid()
    child = value["child_return"]
    if value["action_kind"] not in _CHILD_KINDS:
        if child is not None or "original_return_admission_unavailable" in value["unavailable_reasons"]:
            _invalid()
    elif child is None:
        if "original_return_admission_unavailable" not in value["unavailable_reasons"]:
            _invalid()
    else:
        if (not isinstance(child, dict) or set(child) != _RETURN_FIELDS
                or any(not _text(child[key]) for key in ("child_handle", "return_id", "admission_id",
                    "commission_sha256", "admission_state"))
                or child["admission_state"] not in {"admitted", "delivery_failed"}
                or child["report_contract_sha256"] is not None and not _text(child["report_contract_sha256"])
                or "original_return_admission_unavailable" in value["unavailable_reasons"]):
            _invalid()
        expected_admission = "admission_" + content_digest({"run_id": value["run_id"],
            "parent_episode_id": value["episode_id"],
            "original_decision_index": value["original_decision_index"], "return_id": child["return_id"]})
        if child["admission_id"] != expected_admission:
            _conflict()
        if child["admission_state"] == "delivery_failed" and (
                value["received_record_refs"] or value["received_progress_refs"] or value["progress_records"]):
            _invalid()
        stamps = {key: None if child[key] is None else _utc(child[key])
                  for key in ("selected_at", "returned_at")}
        timing = child["selection_to_return"]
        if (not isinstance(timing, dict) or set(timing) != {"seconds", "measure", "unavailable_reason"}
                or timing["measure"] != "utc_timestamp_difference"):
            _invalid()
        seconds, reason = None, None
        if stamps["selected_at"] is None:
            reason = "selected_at_unavailable"
        elif stamps["returned_at"] is None:
            reason = "returned_at_unavailable"
        else:
            seconds = (stamps["returned_at"] - stamps["selected_at"]).total_seconds()
            if seconds < 0:
                seconds, reason = None, "negative_selection_to_return"
        if (timing["seconds"] != seconds or timing["unavailable_reason"] != reason
                or seconds is not None and type(timing["seconds"]) not in (int, float)
                or reason is not None and reason not in value["unavailable_reasons"]):
            _invalid()
    return value


class CompletionEvidence:
    """Read exactly one completing action and its recorded delivery channels."""

    def __init__(self, store, journal, backend, progress_provider):
        if journal.db is not store.db:
            raise ValueError("completion_evidence_journal_requires_same_store_connection")
        if not _text(journal.run_id):
            raise ValueError("completion_evidence_run_identity_required")
        if getattr(progress_provider, "run_id", journal.run_id) != journal.run_id:
            _conflict()
        self.store, self.journal = store, journal
        self.returns = LocalReturnHistory(store, journal, backend)
        self.progress_provider = progress_provider

    def capture(self, episode_id, *, original_decision_index, unit_ref: UnitRef,
                controller_input: ClosedRecord) -> dict:
        if not _text(episode_id) or not _index(original_decision_index):
            raise ValueError("completion_evidence_original_identity_required")
        if not isinstance(unit_ref, UnitRef) or unit_ref.episode_id != episode_id:
            _conflict()
        if not isinstance(controller_input, ClosedRecord):
            raise TypeError("completion_evidence_closed_controller_input_required")
        body = _copy(controller_input.as_record())
        if (not isinstance(body, dict) or type(body.get("credit")) not in (int, float)
                or not math.isfinite(body["credit"])):
            raise ValueError("completion_evidence_finite_credit_required")
        if "estimation_action_index" in body and (not _index(body["estimation_action_index"])
                or body["estimation_action_index"] != original_decision_index):
            _conflict()
        reasons = []
        with self.store.read_snapshot():
            tables = {row[0] for row in self.store.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "runtime_episodes" not in tables:
                raise ValueError("completion_evidence_episode_unavailable")
            episode = self.store.db.execute("SELECT path,json_extract(request,'$.message.scope') AS scope "
                "FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.journal.run_id, episode_id)).fetchone()
            if episode is None:
                raise ValueError("completion_evidence_episode_unavailable")
            try:
                saved_episode = EpisodeRef(self.journal.run_id, _load(episode["path"]))
            except (TypeError, ValueError) as error:
                raise ValueError("completion_evidence_identity_conflict") from error
            if saved_episode.episode_id != episode_id:
                _conflict()
            scope = None if episode["scope"] is None else _load(episode["scope"])
            if not isinstance(scope, dict):
                raise ValueError("completion_evidence_saved_scope_required")
            action = (self.store.db.execute("SELECT credit,json_extract(action,'$.kind') AS kind, "
                "json_extract(action,'$.tool') AS tool, "
                "json_extract(result,'$.status') AS status,json_extract(result,'$.record_refs') AS refs, "
                "json_extract(result,'$.progress_refs') AS progress, "
                "json_extract(result,'$.native_execution_refs') AS native_refs FROM runtime_actions "
                "WHERE run_id=? AND episode_id=? AND decision_index=?",
                (self.journal.run_id, episode_id, original_decision_index)).fetchone()
                if "runtime_actions" in tables else None)
            if (action is None or action["status"] not in {"completed", "partial"}
                    or type(action["credit"]) not in (int, float) or not math.isfinite(action["credit"])):
                raise ValueError("completion_evidence_requires_completed_outcome_and_credit")
            if action["kind"] not in _KINDS or action["credit"] != body["credit"]:
                _conflict()
            refs = None if action["refs"] is None else _load(action["refs"])
            progress = [] if action["progress"] is None else _load(action["progress"])
            if not _refs(refs) or not _refs(progress):
                _conflict()
            if action["kind"] not in _CHILD_KINDS:
                native_refs = [] if action["native_refs"] is None else _load(action["native_refs"])
                if not _refs(native_refs):
                    _conflict()
                refs.extend(native_refs)
                # These are the two explicit returned-record positions consumed
                # by receive_outcome/receive_native_outcome, never a transitive
                # reference scan or scientific-body read.
                records = self.store.db.execute("SELECT json_extract(CASE WHEN r.type='object' "
                    "THEN r.value ELSE '{}' END,'$.id') AS reference "
                    "FROM runtime_actions a JOIN json_each(a.result,'$.result.records') r "
                    "WHERE a.run_id=? AND a.episode_id=? AND a.decision_index=? AND r.type='object' AND "
                    "((?='tool' AND ?='state.query') OR (json_extract(CASE WHEN r.type='object' "
                    "THEN r.value ELSE '{}' END,'$.record_type')='native_execution' AND "
                    "json_type(CASE WHEN r.type='object' THEN r.value ELSE '{}' END,'$.measurement') "
                    "IS NOT NULL)) ORDER BY r.key",
                    (self.journal.run_id, episode_id, original_decision_index, action["kind"], action["tool"]))
                refs.extend(row["reference"] for row in records)
                if not _refs(refs):
                    _conflict()
                refs = list(dict.fromkeys(refs))
            slot = self._slot(episode_id, original_decision_index, unit_ref, body, tables)
            self._observation(episode_id, original_decision_index, unit_ref, body, slot, tables)
            evidence = (self.returns.read_return(episode_id, original_decision_index)
                        if action["kind"] in _CHILD_KINDS else None)
            sample = None if evidence is None else evidence["sample"]
            child = None
            if sample is not None:
                if (sample["admission_state"] not in {"admitted", "delivery_failed"}
                        or sample["received_record_refs"] != refs
                        or canonical(sample["controller_input"]) != canonical(body)
                        or sample["completion_sequence"] is not None
                            and sample["completion_sequence"] != unit_ref.unit_index
                        or sample["unit_ref"] is not None and sample["unit_ref"] != unit_ref.as_record()):
                    _conflict()
                child = {key: sample[key] for key in _RETURN_FIELDS}
                reasons.extend(evidence["unavailable_reasons"])
            elif action["kind"] in _CHILD_KINDS:
                reasons.append("original_return_admission_unavailable")
            if slot is not None:
                if (slot["kind"] == "child_return") != (action["kind"] in _CHILD_KINDS):
                    _conflict()
                if (slot["kind"] == "child_return") != (sample is not None):
                    _conflict()
                if sample is not None and slot["child_return"] != {
                        "handle": sample["child_handle"], "return_id": sample["return_id"],
                        "admission_id": sample["admission_id"]}:
                    _conflict()
            for channel in ("own_progress", "typed_form"):
                delivered = self._delivery(episode_id, original_decision_index, channel, tables)
                if delivered is None:
                    # The original admitted form itself records requested C8
                    # references, including legacy runs without this ledger.
                    # Its declaration is delivery information, not novelty.
                    if channel == "typed_form" and sample is not None:
                        progress.extend(sample["received_progress_refs"])
                    continue
                if (channel == "own_progress" and delivered != list(dict.fromkeys(progress))
                        or channel == "typed_form" and sample is not None
                            and delivered != sample["received_progress_refs"]):
                    _conflict()
                progress.extend(delivered)
            progress = list(dict.fromkeys(progress))
            records = []
            reader = getattr(self.progress_provider, "read_progress", None)
            for reference in progress:
                if not callable(reader):
                    reasons.append("progress_reader_unavailable:" + reference)
                    continue
                try:
                    snapshot = reader(reference, scope)
                except ContractError as error:
                    if str(error) == "progress_reference_outside_scope":
                        _conflict()
                    reasons.append("progress_body_unavailable:" + reference)
                    continue
                except (KeyError, OSError, ValueError):
                    reasons.append("progress_body_unavailable:" + reference)
                    continue
                if snapshot is None:
                    reasons.append("progress_body_unavailable:" + reference)
                    continue
                snapshot = _copy(snapshot)
                if (not isinstance(snapshot, dict) or snapshot.get("version") != "progress_snapshot_v1"
                        or snapshot.get("progress_ref") != reference):
                    _conflict()
                records.append(snapshot)
            return validate_completion_evidence({"version": VERSION, "run_id": self.journal.run_id,
                "episode_id": episode_id, "unit_ref": unit_ref.as_record(),
                "original_decision_index": original_decision_index, "action_kind": action["kind"],
                "received_record_refs": refs, "received_progress_refs": progress,
                "progress_records": records, "child_return": child,
                "unavailable_reasons": list(dict.fromkeys(reasons))}, run_id=self.journal.run_id,
                episode_id=episode_id, original_decision_index=original_decision_index, unit_ref=unit_ref)

    def _slot(self, episode_id, index, unit, body, tables):
        if "runtime_completion_slots" not in tables:
            return None
        rows = self.store.db.execute("SELECT sequence,slot FROM runtime_completion_slots "
            "WHERE run_id=? AND episode_id=? AND (original_decision_index=? OR sequence=?)",
            (self.journal.run_id, episode_id, index, unit.unit_index)).fetchall()
        if not rows:
            return None
        if len(rows) != 1:
            _conflict()
        row, slot = rows[0], _load(rows[0]["slot"])
        if (not isinstance(slot, dict) or set(slot) != {"version", "episode_id", "sequence",
                "original_decision_index", "label", "kind", "controller_input", "child_return"}
                or slot["version"] != "episode_completion_slot_v1" or slot["episode_id"] != episode_id
                or not _index(slot["sequence"]) or row["sequence"] != unit.unit_index
                or slot["sequence"] != unit.unit_index or not _index(slot["original_decision_index"])
                or slot["original_decision_index"] != index
                or not _text(slot["label"]) or slot["kind"] not in {"own_action", "child_return"}
                or slot["kind"] == "own_action" and slot["child_return"] is not None
                or canonical(slot["controller_input"]) != canonical(body)):
            _conflict()
        return slot

    def _observation(self, episode_id, index, unit, body, slot, tables):
        if "runtime_observations" not in tables:
            return
        rows = self.store.db.execute("SELECT unit_index,observation FROM runtime_observations "
            "WHERE run_id=? AND episode_id=? AND (json_extract(observation,'$.decision_index')=? "
            "OR unit_index=?)", (self.journal.run_id, episode_id, index, unit.unit_index)).fetchall()
        if len(rows) > 1:
            _conflict()
        for row in rows:
            observed = _load(row["observation"])
            if (not isinstance(observed, dict) or row["unit_index"] != unit.unit_index
                    or not _index(observed.get("decision_index")) or observed["decision_index"] != index
                    or canonical(observed.get("credit")) != canonical(body)
                    or not _text(observed.get("label"))
                    or observed.get("unit_ref") is not None and observed["unit_ref"] != unit.as_record()
                    or slot is not None and observed.get("label") != slot["label"]):
                _conflict()
            step = observed.get("step")
            if isinstance(step, dict) and (
                    "unit_label" in step and step["unit_label"] != observed["label"]
                    or "credit" in step and step["credit"] != body["credit"]):
                _conflict()

    def _delivery(self, episode_id, index, channel, tables):
        if "runtime_progress_deliveries" not in tables:
            return None
        row = self.store.db.execute("SELECT progress_refs FROM runtime_progress_deliveries "
            "WHERE run_id=? AND episode_id=? AND operation_key=?", (self.journal.run_id, episode_id,
            f"{self.journal.run_id}:{episode_id}:{index}:{channel}")).fetchone()
        if row is None:
            return None
        refs = _load(row["progress_refs"])
        if not _refs(refs) or len(set(refs)) != len(refs):
            _conflict()
        return refs


__all__ = ["CompletionEvidence", "validate_completion_evidence", "VERSION"]
