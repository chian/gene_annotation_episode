"""Authenticate selected own restriction results for requested typed returns.

Native execution, numerical calculations and projection remain with their
existing owners. This reader only joins original records and copies saved data.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .communication import plain
from .domain import canonical, identity
from .episode_return_records import EpisodeReturnRecords
from .restriction_mapping_bound_contracts import validate_restriction_alias_arguments
from .restriction_mapping_returns import requested_restriction_projections


SOURCE = "restriction_mapping_results"
_TOOLS = ("find_restriction_sites", "find_restriction_enzymes")


class RestrictionMappingActionRecords(EpisodeReturnRecords):
    def __init__(self, store, run_id):
        super().__init__(store, run_id, failure_prefix="restriction_mapping_return_")

    def _context(self, context):
        self.authenticate(context)
        self._require(context.role == "scientific_process", "scientific_owner_required")

    def _requested(self, context):
        request = plain(context.request)
        return requested_restriction_projections(request["report_contract"]["measurements"]["schema"])

    def _query(self, context, *, after, sequence_ref=None, limit=None,
            before_decision_index=None, through_receipt_index=None):
        arguments = [self.run_id, context.episode_id, -1 if after is None else after, *_TOOLS]
        operations = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='tool_operations'").fetchone() is not None
        columns = ("t.operation_key,t.id,t.name,t.arguments,t.scope,t.result AS tool_result"
            if operations else "NULL AS operation_key,NULL AS id,NULL AS name,"
                "NULL AS arguments,NULL AS scope,NULL AS tool_result")
        join = (" LEFT JOIN tool_operations t ON "
            "t.operation_key=a.run_id||':'||a.episode_id||':'||a.decision_index" if operations else "")
        query = f"""SELECT a.decision_index,a.action,a.result AS runtime_result,{columns}
            FROM runtime_actions a{join}
            WHERE a.run_id=? AND a.episode_id=? AND a.decision_index>?
              AND json_extract(a.action,'$.kind')='tool'
              AND json_extract(a.action,'$.tool') IN (?,?)
              AND json_extract(a.result,'$.status') IN ('completed','partial')"""
        if sequence_ref is not None and operations:
            # Native selections expose the operand in arguments; saved ones
            # retain it in their original outcome. Neither selects latest data.
            query += " AND (json_extract(a.action,'$.arguments.sequence_ref')=? OR " \
                "json_extract(t.result,'$.result.sequence_ref')=?)"
            arguments.extend((sequence_ref, sequence_ref))
        if before_decision_index is not None:
            # A selected earlier action may finish after a child was built.
            # Both its decision and actual own-source delivery must precede
            # that child's original commission/receipt boundaries.
            query += " AND a.decision_index<? AND EXISTS (SELECT 1 FROM runtime_record_receipts r " \
                "WHERE r.run_id=a.run_id AND r.episode_id=a.episode_id " \
                "AND r.record_ref=json_extract(a.result,'$.result.source_ref') " \
                "AND r.receipt_kind='own_action' AND r.source_index=a.decision_index " \
                "AND r.receipt_index<=?)"
            arguments.extend((before_decision_index, through_receipt_index))
        query += " ORDER BY a.decision_index"
        if limit is not None:
            query += " LIMIT ?"
            arguments.append(limit)
        return query, arguments

    def own_action_results(self, context, *, selection, after_decision_index, limit):
        self._context(context)
        requested = self._requested(context)
        self._require(SOURCE in requested, "requested_source_required")
        self._require(self._equal(selection, requested[SOURCE]["selection"]), "selection_conflict")
        self._require(type(limit) is int and 1 <= limit <= 256
            and (after_decision_index is None or type(after_decision_index) is int
                 and after_decision_index >= 0), "explicit_page_required")
        query, arguments = self._query(context, after=after_decision_index,
            sequence_ref=selection["sequence_ref"], limit=limit + 1)
        with self.store.read_snapshot():
            rows = list(self.db.execute(query, arguments))
            records = [self._authenticated(context, row)[0] for row in rows[:limit]]
            self._require(all(selection["sequence_ref"] is None
                or record["sequence_ref"] == selection["sequence_ref"] for record in records),
                "selection_conflict")
        return {"records": records, "next_after_decision_index":
            records[-1]["decision_index"] if len(rows) > limit else None}

    def _authenticated(self, context, row):
        self._require(row["tool_result"] is not None, "completed_operation_missing")
        action, actual, saved = (json.loads(row[name]) for name in
            ("action", "runtime_result", "tool_result"))
        self._require(type(row["decision_index"]) is int and row["decision_index"] >= 0
            and action.get("kind") == "tool" and action.get("tool") in _TOOLS,
            "operation_identity_conflict")
        try:
            arguments = validate_restriction_alias_arguments(action["tool"], action["arguments"])
            scope = self.store.validate_scope(json.loads(row["scope"]))
        except ValueError as error:
            raise ValueError(self.failure_prefix + "operation_identity_conflict") from error
        key = f'{self.run_id}:{context.episode_id}:{row["decision_index"]}'
        operation_ref = identity("operation", {"key": key, "name": action["tool"], "arguments": arguments})
        self._require(row["operation_key"] == key and row["id"] == operation_ref
            and row["name"] == action["tool"] and actual.get("operation_ref") == operation_ref
            and saved.get("operation_ref") == operation_ref
            and saved.get("status") in ("completed", "partial")
            and self._equal(json.loads(row["arguments"]), arguments)
            and self._equal(scope,
                self.store.validate_scope(plain(context.scope))), "operation_identity_conflict")
        self._require(self._equal({key: value for key, value in actual.items()
            if key != "pending_work_after_action"}, saved), "operation_outcome_conflict")
        from .restriction_mapping_jobs import RestrictionMappingJobs
        from .restriction_mapping_publication import read_published_restriction_result
        try:
            state = RestrictionMappingJobs(self.store).publication_state(key)
        except ValueError as error:
            raise ValueError(self.failure_prefix + "operation_authority_invalid") from error
        self._require(state["published_outcome"] is not None
            and self._equal(state["published_outcome"], saved), "operation_authority_conflict")
        result = saved["result"]
        self._require(type(result) is dict and result.get("source_ref") == state["published_source_ref"],
            "operation_source_conflict")
        try:
            original = read_published_restriction_result(self.store, result["source_ref"],
                scope=plain(context.scope))
        except ValueError as error:
            raise ValueError(self.failure_prefix + "published_authority_invalid") from error
        body, binding = original["body"], original["sequence_binding"]
        self._require(body["operation_key"] == key and body["operation_ref"] == operation_ref
            and body["tool_name"] == action["tool"] and body["status"] == saved["status"]
            and self._equal(body["arguments"], arguments)
            and self._equal(body["scope"], self.store.validate_scope(plain(context.scope)))
            and binding["sequence_ref"] == result["sequence_ref"]
            and binding["namespace"] == result["namespace"]
            and binding["source_ref"] == result["input_source_ref"] == body["input_source_ref"]
            and result["work_mode"] == arguments["mode"] == body["work_mode"], "published_binding_conflict")
        self._require(self._received_before(context.episode_id, binding["sequence_ref"],
            row["decision_index"]), "original_sequence_receipt_required")
        if arguments["mode"] == "saved":
            self._require(body["prior_result_source_ref"] == arguments["result_source_ref"]
                and self._received_before(context.episode_id, arguments["result_source_ref"],
                    row["decision_index"]), "original_saved_source_receipt_required")
        else:
            self._require(arguments["sequence_ref"] == binding["sequence_ref"], "published_binding_conflict")
        mapping, native = original["mapping"], original["native"]
        for role, value in (("native", native), ("mapping", mapping)):
            file = body["files"][role]
            expected = None if value is None else file["artifact_ref"]
            self._require(result[role + "_artifact_ref"] == expected, "published_artifact_conflict")
        self._require((mapping is None and body["failure_code"] in
            ("native_unavailable", "reader_unavailable", "mapping_invalid"))
            or mapping is not None and body["failure_code"] is None, "published_availability_conflict")
        record = {"decision_index": row["decision_index"], "operation_ref": operation_ref,
            "tool_name": action["tool"], "work_mode": body["work_mode"],
            "operation_status": saved["status"], "sequence_ref": binding["sequence_ref"],
            "namespace": binding["namespace"], "input_source_ref": body["input_source_ref"],
            "source_ref": original["source"]["id"], "native_artifact_ref": result["native_artifact_ref"],
            "mapping_artifact_ref": result["mapping_artifact_ref"], "mapping": deepcopy(mapping),
            "failure_code": body["failure_code"]}
        canonical(record)
        return record, original

    def frozen_facts(self, context, *, sources):
        self._context(context)
        requested = self._requested(context)
        self._require(type(sources) in (tuple, list) and all(type(source) is str for source in sources)
            and len(sources) == len(set(sources))
            and all(source == SOURCE and source in requested for source in sources), "requested_source_required")
        if not sources:
            return {}
        row = self.db.execute("SELECT json_type(facts,?) AS source_type,json_extract(facts,?) AS value "
            "FROM runtime_forms WHERE run_id=? AND episode_id=?",
            ("$." + SOURCE, "$." + SOURCE, self.run_id, context.episode_id)).fetchone()
        self._require(row is not None, "frozen_state_required")
        if row["source_type"] is None:
            return {}
        self._require(row["source_type"] == "array", "frozen_source_invalid")
        result = {SOURCE: json.loads(row["value"])}
        canonical(result)
        return result

    def own_enzyme_reference(self, context, reference, *, before_decision_index=None,
            through_receipt_index=None):
        self._context(context)
        if type(reference) is not str or not reference:
            return False
        bounded = before_decision_index is not None or through_receipt_index is not None
        if bounded:
            self._require(type(before_decision_index) is int and before_decision_index >= 0
                and type(through_receipt_index) is int and through_receipt_index >= 0,
                "explicit_catalog_cutoff_required")
            self._require(self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_record_receipts'").fetchone() is not None, "receipt_history_unbound")
        query, arguments = self._query(context, after=None,
            before_decision_index=before_decision_index, through_receipt_index=through_receipt_index)
        with self.store.read_snapshot():
            for row in self.db.execute(query, arguments):
                _, original = self._authenticated(context, row)
                # A separate catalog-file loss need not erase the validated
                # catalog retained inside the original complete native record.
                catalog = original["catalog"]
                if catalog is None and original["native"] is not None:
                    catalog = original["native"]["catalog"]
                if catalog is not None and any(enzyme["name"] == reference for enzyme in catalog["enzymes"]):
                    return True
        return False


__all__ = ["RestrictionMappingActionRecords"]
