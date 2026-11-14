"""Finite ordinary-publication reference restrictions from retained metadata.

This preserves A104 conservation and phylogeny publication policies.
It neither reads scientific/private artifact bytes
nor validates a native producer, grants references or imports scientific facts.
"""
import json

from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords


_PROFILES = {
    "analyze_protein_conservation": ("ordinary_protein_conservation_result_v1", True, "tool",
        "analyze_protein_conservation", ("completed", "partial")),
    "analyze_protein_phylogeny": ("ordinary_protein_phylogeny_result_v1", True, "tool",
        "analyze_protein_phylogeny", ("completed", "partial")),
}


_CAPTURE_PROFILES = {
    "analyze_protein_conservation": ("ordinary_protein_conservation_native_capture_v1", "protein_conservation_"),
    "analyze_protein_phylogeny": ("ordinary_protein_phylogeny_native_capture_v1", "protein_phylogeny_"),
}


def molecular_capture_reference_restriction(store, context, reference, namespace, *, provider):
    """Deny a selected action's private capture without revoking input Files.

    The Source marker is only a candidate. The private action reader verifies its
    accession against the actual selected tool and full arguments. No private
    bytes are read, and this classification never grants a reference.
    """
    from types import SimpleNamespace
    from .alignment_site_native import immutable_record
    from .source_representation import source_window_selection
    from .a104_action_custody import _recorded_molecular_capture_action
    if provider not in _CAPTURE_PROFILES:
        raise ValueError("molecular_capture_provider_invalid")
    if type(reference) is not str:
        return None
    tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"records", "runtime_actions", "runtime_episodes"} <= tables:
        return None
    capture_version, _ = _CAPTURE_PROFILES[provider]
    rows = store.db.execute("""SELECT data FROM records WHERE record_type='source' AND origin='tool'
        AND json_extract(data,'$.provider')=? AND json_extract(data,'$.version')=?
        AND (id=? OR json_extract(data,'$.artifact_ref')=? OR json_extract(data,'$.request_ref')=?
          OR EXISTS(SELECT 1 FROM json_each(data,'$.auxiliary_artifact_refs') a WHERE a.value=?))""",
        (provider, capture_version, reference, reference, reference, reference))
    registry = SimpleNamespace(store=store)
    for row in rows:
        capture = json.loads(row[0])
        try:
            immutable_record(capture)
            selected = _recorded_molecular_capture_action(registry, capture.get("accession"), provider)
            if provider == "analyze_protein_phylogeny":
                from .protein_phylogeny_result_contracts import validate_phylogeny_arguments as _arguments
            else:
                from .protein_conservation_result_contracts import validate_conservation_arguments as _arguments
            arguments = _arguments(selected["arguments"])
            if arguments["mode"] != "run_native" or selected["operation_ref"] != capture.get("accession"):
                continue
            original_inputs = []
            for item in [arguments["input"]]:
                original_inputs.append(item["reference"] if item["namespace"] == "artifact" else
                    source_window_selection(store.get(item["reference"]), "original")[0])
            if reference in original_inputs:
                continue
            return False
        except (ValueError, TypeError, KeyError):
            continue
    return None


def _providers(value):
    if value is None:
        return tuple(_PROFILES)
    if (type(value) is not tuple or any(type(name) is not str or name not in _PROFILES for name in value)
            or len(value) != len(set(value))):
        raise ValueError("molecular_reference_providers_invalid")
    return value


def molecular_reference_restriction(store, context, reference, namespace, *, private_only=False, providers=None):
    """Preserve private capture, control and auxiliary custody and actual receipts."""
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
    for provider, (_, prefix) in _CAPTURE_PROFILES.items():
        if provider not in selected:
            continue
        capture_verdict = molecular_capture_reference_restriction(
            store, context, reference, namespace, provider=provider)
        if capture_verdict is not None:
            if capture_verdict is not False:
                raise ValueError(prefix + "private_capture_verdict_invalid")
            return False
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
    if private_auxiliary:
        return False
    if private_only:
        return None
    kind = "source" if any(source["id"] == reference for source in sources) else "artifact"
    if namespace not in (None, kind) or not isinstance(context, BindingContext):
        return False
    try:
        EpisodeReturnRecords(store, context.run_id, failure_prefix="molecular_reference_").authenticate(context)
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
        return reference in set(receipts.known(context.episode_id))
    except (ValueError, TypeError, KeyError):
        return False


__all__ = ["molecular_reference_restriction", "molecular_capture_reference_restriction"]
