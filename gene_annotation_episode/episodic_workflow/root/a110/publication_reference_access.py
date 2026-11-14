"""Finite ordinary-publication reference restrictions from retained metadata.

This preserves the native publication policies and the explicit external
A110 Source policy. It neither reads scientific/private artifact bytes
nor validates a native producer, grants references or imports scientific facts.
"""
import json

from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords


_PROFILES = {
    "perform_flux_balance_analysis": ("ordinary_flux_balance_result_v1", True, "tool",
        "perform_flux_balance_analysis", ("completed", "partial")),
    "kegg": (None, True, "external", "public.kegg.reaction", ("completed", "partial", "failed")),
    "reactome": (None, True, "external", "public.reactome.record", ("completed", "partial", "failed")),
    "pubchem": (None, True, "external", "public.pubchem.compound", ("completed", "partial", "failed")),
    "public.ncbi.entrez": (None, True, "external", ("public.ncbi.entrez", "internal.api_service.public.ncbi.entrez"), ("completed", "partial", "failed")),
}

def _providers(value):
    if value is None:
        return tuple(_PROFILES)
    if (type(value) is not tuple or any(type(name) is not str or name not in _PROFILES for name in value)
            or len(value) != len(set(value))):
        raise ValueError("molecular_reference_providers_invalid")
    return value


def _published_fba_file(store, reference):
    """An explicit File publication is public metadata, never a receipt grant."""
    from .flux_balance_contracts import validate_flux_balance_record
    from .native_file_capture import NativeFileCaptureError, _metadata
    for field, modes, formats in (("saved_sheets", ("solve", "calculate_saved"), {"flux_balance_sheet_v1"}),
            ("edited_models", ("edit",), {"sbml", "cobra_json"})):
        rows = store.db.execute("""SELECT output.value FROM tool_operations operation
            JOIN records source ON source.id=json_extract(operation.result,'$.result.source_ref')
            JOIN json_each(operation.result, ?) output
            WHERE operation.name='perform_flux_balance_analysis'
              AND source.record_type='source' AND source.origin='tool'
              AND json_extract(source.data,'$.provider')='perform_flux_balance_analysis'
              AND json_extract(source.data,'$.version')='ordinary_flux_balance_result_v1'
              AND json_extract(operation.result,'$.result.version')='ordinary_flux_balance_result_v1'
              AND json_extract(operation.result,'$.status') IN ('completed','partial')
              AND json_extract(operation.arguments,'$.mode') IN (SELECT value FROM json_each(?))
              AND json_extract(operation.result,'$.result.mode')=json_extract(operation.arguments,'$.mode')
              AND output.type='object' AND json_extract(output.value,'$.artifact_ref')=?
              AND EXISTS(SELECT 1 FROM json_each(operation.result,'$.record_refs') item WHERE item.value=source.id)
              AND EXISTS(SELECT 1 FROM json_each(operation.result,'$.record_refs') item WHERE item.value=?)""",
            ("$.result." + field, json.dumps(modes), reference, reference))
        for row in rows:
            try:
                file = validate_flux_balance_record("File", json.loads(row[0]))
                metadata = _metadata(store, reference)
                if (file["format"] in formats and file["artifact_ref"] == reference == "artifact_" + file["sha256"]
                        and metadata["sha256"] == file["sha256"] and metadata["size"] == file["size_bytes"]):
                    return True
            except (ValueError, TypeError, KeyError, NativeFileCaptureError):
                continue
    return False


def publication_reference_restriction(store, context, reference, namespace, *, private_only=False, providers=None):
    """Return the existing publication verdict, or defer for unrelated references.

    Private controls and diagnostics always deny. Source-only auxiliaries are
    private too, except genuine explicitly published FBA sheet/model Files.
    Public Source/native/FBA-File handles need the receiving
    context's actual semantic receipt; Store membership is insufficient. A
    private-only caller defers public handles so a prior context-aware verdict
    is not overturned. Neither path creates a receipt or traverses Source refs.
    """
    if type(private_only) is not bool:
        raise ValueError("molecular_reference_private_only_invalid")
    selected = _providers(providers)
    if not isinstance(reference, str) or not selected:
        return None
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('records','tool_operations')")}
    if "tool_operations" not in tables:
        return None  # A fresh Store has no ordinary publication or diagnostic.
    if store.db.execute("""SELECT 1 FROM tool_operations
        WHERE name IN (SELECT value FROM json_each(?))
          AND json_extract(result,'$.feedback.diagnostic_ref')=? LIMIT 1""",
            (json.dumps([operation for name in selected
                for operation in ((_PROFILES[name][3],) if isinstance(_PROFILES[name][3], str)
                                  else _PROFILES[name][3])]), reference)).fetchone():
        return False
    if "records" not in tables:
        return None
    profiles = [dict(provider=name, version=_PROFILES[name][0], origin=_PROFILES[name][2],
        operation=operation, statuses=_PROFILES[name][4]) for name in selected
        for operation in ((_PROFILES[name][3],) if isinstance(_PROFILES[name][3], str)
                          else _PROFILES[name][3])]
    rows = store.db.execute("""SELECT source.data FROM records source, json_each(?) profile
        WHERE source.record_type='source' AND source.origin=json_extract(profile.value,'$.origin')
          AND json_extract(source.data,'$.provider')=json_extract(profile.value,'$.provider')
          AND json_extract(source.data,'$.version') IS json_extract(profile.value,'$.version')
          AND (source.id=? OR json_extract(source.data,'$.artifact_ref')=?
            OR json_extract(source.data,'$.request_ref')=? OR EXISTS(
                SELECT 1 FROM json_each(source.data,'$.auxiliary_artifact_refs') artifact WHERE artifact.value=?))
          AND EXISTS(SELECT 1 FROM tool_operations operation, json_each(operation.result,'$.record_refs') published
            WHERE operation.name=json_extract(profile.value,'$.operation') AND published.value=source.id
              AND json_extract(operation.result,'$.status') IN (
                SELECT value FROM json_each(json_extract(profile.value,'$.statuses'))))""",
        (json.dumps(profiles), reference, reference, reference, reference))
    sources = [json.loads(row[0]) for row in rows]
    if not sources:
        return None
    if any(source.get("request_ref") == reference for source in sources):
        return False
    private_auxiliary = [source for source in sources if _PROFILES[source["provider"]][1]
        and reference in source.get("auxiliary_artifact_refs", ())]
    if private_auxiliary and (any(source["provider"] != "perform_flux_balance_analysis" for source in private_auxiliary)
            or not _published_fba_file(store, reference)):
        return False
    if private_only:
        return None
    kind = "source" if any(source["id"] == reference for source in sources) else "artifact"
    if (namespace not in (None, kind)
            or not isinstance(context, BindingContext)):
        return False
    try:
        EpisodeReturnRecords(store, context.run_id, failure_prefix="molecular_reference_").authenticate(context)
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
        return reference in set(receipts.known(context.episode_id))
    except (ValueError, TypeError, KeyError):
        return False


__all__ = ["publication_reference_restriction"]
