"""Negative Enrichr File restrictions from committed publication metadata.

This reader needs no configured API resource. It neither grants references nor
imports another run's scientific facts. A Source-like record is insufficient:
classification authenticates its original selected publication and receipt.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from .api_enrichr import PROTOCOL_VERSION, WIRE_PROFILE, _prepared as validate_prepared_enrichr
from .communication import ReportBoundaryError, plain
from .domain import identity, canonical as domain_canonical
from .enrichr_contracts import validate_enrichr_selector
from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import digest


def _boundary(code):
    return ReportBoundaryError("enrichr_" + code, code="enrichr_" + code)


def _require(condition, code):
    if not condition:
        raise _boundary(code)


def validated_enrichr_source(store, reference):
    source = store.get(reference)
    payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    _require(source.get("record_type") == "source" and source.get("provider") == "enrichr"
        and source.get("origin") == "external"
        and reference == identity("source", {"origin": "external", "record": payload}), "source_snapshot_conflict")
    return source


def normalized_enrichr_outcome(value):
    value = deepcopy(value)
    if isinstance(value, dict) and "pending_work_after_action" in value:
        from .waiting import validate_pending
        validate_pending(value.pop("pending_work_after_action"))
    return value


def matching_enrichr_publications(store, reference, *, current_run_id=None):
    """Prefilter one exact reference, retaining original SQL row identities.

    Only an explicit current owner may inspect its not-yet-committed rows. The
    resource-independent restriction below always selects committed rows only.
    """
    if not isinstance(reference, str):
        return []
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('records','tool_operations','runtime_actions')")}
    if tables != {"records", "tool_operations", "runtime_actions"}:
        return []  # No selected publication chain exists in a fresh non-runtime Store.
    if current_run_id is None:
        condition, parameters = "action.result IS NOT NULL", []
    else:
        _require(type(current_run_id) is str and bool(current_run_id), "original_context_conflict")
        condition, parameters = "(action.run_id=? OR action.result IS NOT NULL)", [current_run_id]
    return list(store.db.execute("SELECT DISTINCT source.id,source.data,action.run_id AS publication_run_id,"
        "action.episode_id,action.decision_index,action.action AS selected_action,action.result AS selected_result,"
        "operation.operation_key,operation.id AS operation_id,operation.arguments AS operation_arguments,"
        "operation.scope AS operation_scope,operation.result AS operation_result "
        "FROM records source JOIN tool_operations operation ON operation.name='internal.api_service.enrichr.result' "
        "JOIN runtime_actions action ON operation.operation_key=action.run_id||':'||action.episode_id||':'||action.decision_index||':publication' "
        "WHERE " + condition + " AND source.record_type='source' "
        "AND json_extract(source.data,'$.provider')='enrichr' "
        "AND json_extract(operation.result,'$.status') IN ('completed','partial') "
        "AND EXISTS(SELECT 1 FROM json_each(operation.result,'$.record_refs') WHERE value=source.id) "
        "AND (source.id=? OR json_extract(source.data,'$.artifact_ref')=? OR json_extract(source.data,'$.request_ref')=? "
        "OR EXISTS(SELECT 1 FROM json_each(source.data,'$.auxiliary_artifact_refs') WHERE value=?) "
        "OR EXISTS(SELECT 1 FROM json_each(CASE WHEN json_valid(operation.arguments) THEN operation.arguments ELSE '{}' END,"
        "'$.transport.enrichr_protocol.stages') stage WHERE json_extract(stage.value,'$.snapshot.content_ref')=?))",
        (*parameters, reference, reference, reference, reference, reference)))


def committed_enrichr_reference_kind(store, row, reference):
    """The original committed-chain classifier; never read API paths or bytes."""
    try:
        run_id, key = row["publication_run_id"], row["operation_key"].removesuffix(":publication")
        records = EpisodeReturnRecords(store, run_id, failure_prefix="enrichr_foreign_")
        context = records.context(row["episode_id"])
        _require(context.role == "results" and type(row["decision_index"]) is int
            and row["decision_index"] >= 0 and key == f"{run_id}:{context.episode_id}:{row['decision_index']}",
            "foreign_publication_conflict")
        _require(_same(json.loads(row["selected_action"]), {"kind": "tool",
            "tool": "api.enrichr.result", "arguments": {}}), "foreign_publication_conflict")
        action = normalized_enrichr_outcome(json.loads(row["selected_result"]))
        original = json.loads(row["operation_result"])
        operands = json.loads(row["operation_arguments"])
        assignment = plain(context.assignment)
        selector = validate_enrichr_selector(assignment["selector"])
        _require(assignment["version"] == "execution_results_assignment_v1"
            and _same(json.loads(row["operation_scope"]), context.scope)
            and original["status"] in {"completed", "partial"}
            and original["record_refs"] == [row["id"]]
            and original["result"]["source_ref"] == row["id"]
            and original["operation_ref"] == row["operation_id"] == identity("operation", {
                "key": row["operation_key"], "name": "internal.api_service.enrichr.result", "arguments": operands}),
            "foreign_publication_conflict")
        source = validated_enrichr_source(store, row["id"])
        receipt = action["result"]["acquisition_receipt"]
        _require(receipt["version"] == "api_service_acquisition_v1"
            and receipt["run_id"] == run_id and receipt["episode_id"] == context.episode_id
            and receipt["operation_key"] == key and receipt["name"] == "api.enrichr.result"
            and receipt["arguments"] == {} and receipt["assignment_sha256"] == digest(assignment)
            and receipt["handoff_ref"] == assignment["handoff_ref"]
            and _same(receipt["selector"], selector) and receipt["source_ref"] == source["id"]
            and receipt["record_refs"] == original["record_refs"]
            and _same(operands["arguments"]["selector"], selector)
            and source["artifact_ref"] == "artifact_" + operands["snapshot_sha256"]
            and receipt["snapshot_sha256"] == operands["snapshot_sha256"], "foreign_publication_conflict")
        expected = deepcopy(original)
        expected["operation_ref"] = identity("api_operation", {"key": key})
        expected["result"].update(acquisition_receipt=receipt, handoff_ref=assignment["handoff_ref"])
        _require(_same(action, expected), "foreign_publication_conflict")
        transport = operands["transport"]
        protocol = transport["enrichr_protocol"]
        prepared = validate_prepared_enrichr(protocol["prepared"], query_only=True)
        _require(protocol["version"] == PROTOCOL_VERSION and protocol["wire_profile"] == WIRE_PROFILE
            and _same(prepared["request"], operands["arguments"]["request"])
            and source["request_ref"] == "artifact_" + hashlib.sha256(domain_canonical({
                "request": operands["request"], "transport": transport}).encode()).hexdigest(),
            "foreign_publication_conflict")
        stages = protocol["stages"]
        _require(type(stages) is list and len(stages) == (
            3 if prepared["request"]["background"]["policy"] == "supplied" else 2), "foreign_publication_conflict")
        stage_refs = []
        for ordinal, stage in enumerate(stages):
            _require(type(stage) is dict and set(stage) == {"ordinal", "stage_code", "snapshot"}
                and type(stage["ordinal"]) is int and stage["ordinal"] == ordinal
                and type(stage["snapshot"]) is dict and stage["snapshot"]["service"] == "enrichr"
                and type(stage["snapshot"]["content_ref"]) is str
                and re.fullmatch(r"artifact_[a-f0-9]{64}", stage["snapshot"]["content_ref"]), "foreign_publication_conflict")
            stage_refs.append(stage["snapshot"]["content_ref"])
        final = stages[-1]["snapshot"]
        bare_transport = deepcopy(transport)
        bare_transport.pop("enrichr_protocol")
        _require(stage_refs[-1] == source["artifact_ref"] and source["uri"] == final["url"]
            and source["retrieved_at"] == final["retrieved_at"]
            and _same(operands["request"], final["request"])
            and _same(bare_transport, final["transport"]), "foreign_publication_conflict")
        if reference == source["id"]:
            return "source"
        if reference == source["artifact_ref"]:
            return "raw"
        _require(reference == source["request_ref"] or reference in source.get("auxiliary_artifact_refs", [])
            or reference in stage_refs, "foreign_publication_conflict")
        return "private"
    except ReportBoundaryError:
        raise
    except (ValueError, TypeError, KeyError, IndexError) as error:
        raise _boundary("foreign_publication_conflict") from error


def enrichr_reference_restriction(store, context, reference, namespace, *, initial_record_refs=(), private_only=False):
    """Return a negative verdict or defer; this function never grants access.

    ``initial_record_refs`` comes only from the caller's original root input
    selection. A Source seed is never expanded into an implicit File seed.
    Contextless scope checks can request private-only restrictions so they do
    not overturn File authority already established by a context-aware caller.
    """
    _require(type(private_only) is bool, "original_context_conflict")
    _require(type(initial_record_refs) in (list, tuple)
        and all(type(reference) is str for reference in initial_record_refs), "original_context_conflict")
    kinds = {committed_enrichr_reference_kind(store, row, reference)
        for row in matching_enrichr_publications(store, reference)}
    if "private" in kinds:
        return False
    if "raw" not in kinds or private_only:
        return None
    if namespace not in {None, "artifact"} or not isinstance(context, BindingContext):
        return False
    try:
        EpisodeReturnRecords(store, context.run_id, failure_prefix="enrichr_reference_").authenticate(
            context, allow_unsaved=True)
        if len(context.path) == 1 and reference in initial_record_refs:
            return None
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
        return None if reference in set(receipts.known(context.episode_id)) else False
    except (ValueError, TypeError, KeyError):
        return False


__all__ = ["validated_enrichr_source", "normalized_enrichr_outcome", "matching_enrichr_publications",
    "committed_enrichr_reference_kind", "enrichr_reference_restriction"]
