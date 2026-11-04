"""Finite ordinary-publication reference restrictions from retained metadata.

This preserves the native publication policies and the explicit external
Ensembl Source policy. It neither reads scientific/private artifact bytes
nor validates a native producer, grants references or imports scientific facts.
"""
import json

from .episode_bindings import BindingContext
from .episode_receipts import EpisodeReceipts
from .episode_return_records import EpisodeReturnRecords


_PROFILES = {
    'detect_and_annotate_somatic_mutations': ('ordinary_somatic_variant_result_v1', True, 'tool',
        'detect_and_annotate_somatic_mutations', ('completed', 'partial')),
    'generate_gene_embeddings_with_ESM_models': ('esm_gene_embedding_result_v1', True, 'tool',
        'generate_gene_embeddings_with_ESM_models', ('completed', 'partial')),
    # version, Source-only auxiliaries, origin, producing operation(s), statuses
    "result.variants.vcf": ("ordinary_vcf_result_v1", True, "tool",
        "result.variants.vcf", ("completed", "partial")),
    "analyze_itc_binding_thermodynamics": ("ordinary_itc_result_v1", False, "tool",
        "analyze_itc_binding_thermodynamics", ("completed", "partial")),
    "liftover_coordinates": ("ordinary_liftover_result_v1", True, "tool",
        "liftover_coordinates", ("completed", "partial")),
    "analyze_circular_dichroism_spectra": ("ordinary_cd_result_v1", True, "tool",
        "analyze_circular_dichroism_spectra", ("completed", "partial")),
    "perform_flux_balance_analysis": ("ordinary_flux_balance_result_v1", True, "tool",
        "perform_flux_balance_analysis", ("completed", "partial")),
    "annotate_open_reading_frames": ("ordinary_orf_result_v1", True, "tool",
        "annotate_open_reading_frames", ("completed", "partial")),
    "find_n_glycosylation_motifs": ("ordinary_n_glycosylation_result_v1", True, "tool",
        "find_n_glycosylation_motifs", ("completed", "partial")),
    "predict_o_glycosylation_hotspots": ("ordinary_o_glycosylation_result_v1", True, "tool",
        "predict_o_glycosylation_hotspots", ("completed", "partial")),
    "analyze_cas9_mutation_outcomes": ("ordinary_reference_edit_outcome_result_v1", True, "tool",
        "analyze_cas9_mutation_outcomes", ("completed", "partial")),
    "result.macs2.peaks": ("ordinary_macs2_peak_result_v1", True, "tool",
        "result.macs2.peaks", ("completed", "partial")),
    "find_enriched_motifs_with_homer": ("ordinary_homer_motif_result_v1", True, "tool",
        "find_enriched_motifs_with_homer", ("completed", "partial")),
    "identify_transcription_factor_binding_sites": ("ordinary_tf_binding_result_v1", True, "tool",
        "identify_transcription_factor_binding_sites", ("completed", "partial")),
    "analyze_protease_kinetics": ("ordinary_protease_kinetics_result_v1", True, "tool",
        "analyze_protease_kinetics", ("completed", "partial")),
    "analyze_arsenic_speciation_hplc_icpms": ("ordinary_arsenic_speciation_result_v1", True, "tool",
        "analyze_arsenic_speciation_hplc_icpms", ("completed", "partial")),
    "predict_protein_disorder_regions": ("ordinary_protein_disorder_result_v1", True, "tool",
        "predict_protein_disorder_regions", ("completed", "partial")),
    "align_sequences": ("ordinary_primer_placement_result_v1", True, "tool",
        "align_sequences", ("completed", "partial")),
    "analyze_protein_conservation": ("ordinary_protein_conservation_result_v1", True, "tool",
        "analyze_protein_conservation", ("completed", "partial")),
    "analyze_protein_phylogeny": ("ordinary_protein_phylogeny_result_v1", True, "tool",
        "analyze_protein_phylogeny", ("completed", "partial")),
    "ensembl": (None, True, "external", "public.ensembl.request", ("completed", "partial", "failed")),
    "alphafold": (None, True, "external",
        ("public.alphafold.prediction", "public.alphafold.file"), ("completed", "partial", "failed")),
    "emdb": (None, True, "external", "public.emdb.entry", ("completed", "partial", "failed")),
    "rcsb_pdb": (None, True, "external",
        ("public.rcsb.entry", "public.rcsb.file"), ("completed", "partial", "failed")),
    "string": (None, True, "external", "public.string.network", ("completed", "partial", "failed")),
    "kegg": (None, True, "external", "public.kegg.reaction", ("completed", "partial", "failed")),
    "reactome": (None, True, "external", "public.reactome.record", ("completed", "partial", "failed")),
    "quickgo": (None, True, "external", "public.quickgo.term", ("completed", "partial", "failed")),
    "pubchem": (None, True, "external", "public.pubchem.compound", ("completed", "partial", "failed")),
    "hpa": (None, True, "external", "public.hpa.gene", ("completed", "partial", "failed")),
    "ucsc": (None, True, "external", "public.ucsc.request", ("completed", "partial", "failed")),
    "eva": (None, True, "external", "public.eva.request", ("completed", "partial", "failed")),
    "gnomad": (None, True, "external", "public.gnomad.request", ("completed", "partial", "failed")),
    # Retained internal publications keep their custody policy after rerouting.
    "bvbrc_minhash": (None, True, "external",
        "internal.api_service.api.bvbrc.minhash.result", ("completed", "partial")),
    "public.ncbi.entrez": (None, True, "external",
        ("public.ncbi.entrez", "internal.api_service.public.ncbi.entrez"), ("completed", "partial", "failed")),
    "public.ncbi.geo": (None, True, "external",
        ("public.ncbi.geo", "internal.api_service.public.ncbi.geo"), ("completed", "partial", "failed")),
    "public.ncbi.sra.file": (None, True, "external", "public.ncbi.sra.file", ("completed", "partial", "failed")),
    "public.jaspar": (None, True, "external", "public.jaspar", ("completed", "partial", "failed")),
    "public.encode": (None, True, "external", "public.encode", ("completed", "partial", "failed")),
    "public.screen": (None, True, "external", "public.screen", ("completed", "partial", "failed")),
}


_CAPTURE_PROFILES = {
    "detect_and_annotate_somatic_mutations": ("ordinary_somatic_variant_native_capture_v1", "somatic_variant_"),
    "find_enriched_motifs_with_homer": ("ordinary_homer_motif_native_capture_v1", "homer_motif_"),
    "identify_transcription_factor_binding_sites": ("ordinary_tf_binding_native_capture_v1", "tf_binding_"),
    "analyze_protein_conservation": ("ordinary_protein_conservation_native_capture_v1", "protein_conservation_"),
    "analyze_protein_phylogeny": ("ordinary_protein_phylogeny_native_capture_v1", "protein_phylogeny_"),
}


def molecular_capture_reference_restriction(store, context, reference, namespace, *, provider):
    """Deny a selected action's private capture without revoking input Files.

    The Source marker is only a candidate. The shared action owner verifies its
    accession against the actual selected tool and full arguments. No private
    bytes are read, and this classification never grants a reference.
    """
    from types import SimpleNamespace
    from .alignment_site_native import immutable_record
    from .materials import source_window_selection
    from .molecular_measurement_tools import _recorded_molecular_capture_action
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
            if provider == "find_enriched_motifs_with_homer":
                from .homer_motif_tools import _arguments
            elif provider == "detect_and_annotate_somatic_mutations":
                from .somatic_variant_contracts import validate_somatic_arguments as _arguments
            elif provider == "analyze_protein_phylogeny":
                from .protein_phylogeny_result_contracts import validate_phylogeny_arguments as _arguments
            elif provider == "analyze_protein_conservation":
                from .protein_conservation_result_contracts import validate_conservation_arguments as _arguments
            else:
                from .tf_binding_tools import _arguments
            arguments = _arguments(selected["arguments"])
            if arguments["mode"] != "run_native" or selected["operation_ref"] != capture.get("accession"):
                continue
            original_inputs = []
            for item in ([arguments["input"]] if provider in {"analyze_protein_conservation", "analyze_protein_phylogeny"} else arguments["inputs"]):
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


def molecular_reference_restriction(store, context, reference, namespace, *, private_only=False, providers=None):
    """Return the existing owner verdict, or defer for unrelated references.

    Private controls and diagnostics always deny. Source-only auxiliaries are
    private too, except genuine explicitly published FBA sheet/model Files.
    Public Source/native/ITC-grading/FBA-File handles need the receiving
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
    for provider, (_, prefix) in _CAPTURE_PROFILES.items():
        if provider not in selected:
            continue
        if provider == "find_enriched_motifs_with_homer":
            from .homer_motif_tools import homer_capture_reference_restriction
            capture_verdict = homer_capture_reference_restriction(store, context, reference, namespace)
        else:
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
    if private_auxiliary and (any(source["provider"] != "perform_flux_balance_analysis" for source in private_auxiliary)
            or not _published_fba_file(store, reference)):
        return False
    if private_only:
        return None
    kind = "source" if any(source["id"] == reference for source in sources) else "artifact"
    minhash_result_source = (kind == "source" and namespace == "execution_result"
        and any(source["id"] == reference and source["provider"] == "bvbrc_minhash"
            for source in sources))
    if (namespace not in (None, kind) and not minhash_result_source
            or not isinstance(context, BindingContext)):
        return False
    try:
        EpisodeReturnRecords(store, context.run_id, failure_prefix="molecular_reference_").authenticate(context)
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, context.run_id
        return reference in set(receipts.known(context.episode_id))
    except (ValueError, TypeError, KeyError):
        return False


__all__ = ["molecular_reference_restriction", "molecular_capture_reference_restriction"]
