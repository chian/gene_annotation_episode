"""Negative Enrichr File restrictions from committed publication metadata.

This reader needs no configured API resource. It neither grants references nor
imports another run's scientific facts.
"""
from __future__ import annotations

from .domain import identity


def _require(condition, code):
    if not condition:
        raise ValueError("enrichr_" + code)


def validated_enrichr_source(store, reference):
    source = store.get(reference)
    payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    _require(source.get("record_type") == "source" and source.get("provider") == "enrichr"
        and source.get("origin") == "external"
        and reference == identity("source", {"origin": "external", "record": payload}), "source_snapshot_conflict")
    return source


def matching_enrichr_publications(store, reference, *, current_run_id=None):
    """Prefilter one exact reference, retaining original SQL row identities.

    Only an explicit current owner may inspect its not-yet-committed rows. The
    resource-independent restriction below always selects committed rows only.
    """
    if not isinstance(reference, str):
        return []
    tables = {row[0] for row in store._db.execute("SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('records','tool_operations','runtime_actions')")}
    if tables != {"records", "tool_operations", "runtime_actions"}:
        return []  # No selected publication chain exists in a fresh non-runtime Store.
    if current_run_id is None:
        condition, parameters = "action.result IS NOT NULL", []
    else:
        _require(type(current_run_id) is str and bool(current_run_id), "original_context_conflict")
        condition, parameters = "(action.run_id=? OR action.result IS NOT NULL)", [current_run_id]
    return list(store._db.execute("SELECT DISTINCT source.id,source.data,action.run_id AS publication_run_id,"
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


def enrichr_reference_restriction(store, context, reference, namespace, *, initial_record_refs=(), private_only=False):
    """Return a negative verdict or defer; this function never grants access.

    The committed-chain classifier that separated raw from private Enrichr
    Files belonged to the deleted root publication records, so every reference
    of a committed Enrichr publication is denied.
    """
    _require(type(private_only) is bool, "original_context_conflict")
    _require(type(initial_record_refs) in (list, tuple)
        and all(type(reference) is str for reference in initial_record_refs), "original_context_conflict")
    return False if matching_enrichr_publications(store, reference) else None


__all__ = ["validated_enrichr_source", "matching_enrichr_publications",
    "enrichr_reference_restriction"]
