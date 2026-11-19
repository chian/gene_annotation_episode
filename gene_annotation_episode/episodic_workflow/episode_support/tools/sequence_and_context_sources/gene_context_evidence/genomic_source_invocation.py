"""A103 genomic source acquisition is bound to the host's current selected tool action.

The host (an A103 episode's decision source on ``episode_runtime``) records the
selected action through its ``EpisodeRecorder`` and opens
``ToolRegistry.current_invocation`` around exactly that action. This check
requires that binding and that it names this very operation.
"""
import json

from gene_annotation_episode.episodic_workflow.episode_support.forms.gene_context_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, canonical


def authenticate_genomic_source_invocation(registry, name, arguments, scope, operation_key):
    """The current host action, which must be this exact selected tool call."""
    invocation = registry._current_invocation.get()
    if invocation is None:
        raise ContractError("a103_genomic_source_current_invocation_required")
    context, reader, selected_name, selected_arguments, selected_key = invocation
    prefix = f"{context.run_id}:{context.episode_id}:"
    suffix = operation_key[len(prefix):] if isinstance(operation_key, str) and operation_key.startswith(prefix) else ""
    if (not suffix.isdecimal() or str(int(suffix)) != suffix or selected_name != name
            or canonical(selected_arguments) != canonical(arguments) or selected_key != operation_key
            or canonical(plain(context.scope)) != canonical(scope) or not callable(reader)):
        raise ContractError("a103_genomic_source_selected_action_conflict")
    return context, reader


_PROFILES = {
    "ensembl": (None, True, "external", "public.ensembl.request", ("completed", "partial", "failed")),
    "string": (None, True, "external", "public.string.network", ("completed", "partial", "failed")),
    "ucsc": (None, True, "external", "public.ucsc.request", ("completed", "partial", "failed")),
    "public.ncbi.entrez": (None, True, "external",
        ("public.ncbi.entrez", "internal.api_service.public.ncbi.entrez"), ("completed", "partial", "failed")),
    "bvbrc_minhash": (None, True, "external",
        "internal.api_service.api.bvbrc.minhash.result", ("completed", "partial")),
}

def _providers(value):
    if value is None:
        return tuple(_PROFILES)
    if (type(value) is not tuple or any(type(name) is not str or name not in _PROFILES for name in value)
            or len(value) != len(set(value))):
        raise ValueError("molecular_reference_providers_invalid")
    return value


def source_reference_restriction(store, context, reference, namespace, *, private_only=False, providers=None):
    """Resolve the current invocation's receipt of an A103 source, or defer for unrelated references.

    Private controls and diagnostics always deny. Source-only auxiliaries are
    private too.
    Public Source/native File handles need the receiving
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
    if private_auxiliary:
        return False
    if private_only:
        return None
    kind = "source" if any(source["id"] == reference for source in sources) else "artifact"
    minhash_result_source = (kind == "source" and namespace == "execution_result"
        and any(source["id"] == reference and source["provider"] == "bvbrc_minhash"
            for source in sources))
    if (namespace not in (None, kind) and not minhash_result_source
            or context is None):
        return False
    # The receiving episode's own received records (``A103Invocation``) are the receipt.
    return reference in context.received_record_refs
