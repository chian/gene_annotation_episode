"""Root retained-publication readers for the original finite producer domain.

The original shared public reader remains unchanged. Current Root callers use
their actual domain validators and private publication owners, preserving the
original saved values, source-only versus source-and-file admission, custody
checks, error order and generic multi-producer routing.
"""
import json
from gene_annotation_episode.domain import ContractError, canonical
from .molecular_action_custody import (
    ITC_TOOL, _publication_profile, _recorded_molecular_producer_details,
)
from .molecular_publication_custody import _publication_bytes


def read_retained_molecular_publication(registry, context, reader, source_ref, *, tool_name):
    """Read an admitted producer's saved values without delivering its Files.

    ITC preserves its existing dual Source/File admission. Source-only producers
    authenticate metadata and the original selected action before any private
    native, control or grading bytes are opened. The shared association checks
    do not calculate measurements, grant receipts or invoke native software.
    """
    with registry.store.read_snapshot():
        return _read_retained_molecular_publication(registry, context, reader, source_ref,
            tool_name=tool_name)

def _read_retained_molecular_publication(registry, context, reader, source_ref, *, tool_name):
    """The common read within one metadata snapshot; no additional admission."""
    if tool_name == "generate_gene_embeddings_with_ESM_models":
        from .esm_gene_embedding_publication import _read
        return _read(registry, context, reader, source_ref)
    if tool_name == "detect_and_annotate_somatic_mutations":
        from .somatic_variant_publication import _read_somatic_variant_publication
        return _read_somatic_variant_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_protein_phylogeny":
        from .protein_phylogeny_publication import _read_protein_phylogeny_publication
        return _read_protein_phylogeny_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_protein_conservation":
        from gene_annotation_episode.episodic_workflow.root.library.protein_conservation_publication import _read_protein_conservation_publication
        return _read_protein_conservation_publication(registry, context, reader, source_ref)
    if tool_name == "predict_protein_disorder_regions":
        from .protein_disorder_tools import read_protein_disorder_publication
        return read_protein_disorder_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_arsenic_speciation_hplc_icpms":
        from .arsenic_speciation_tools import read_arsenic_speciation_publication
        return read_arsenic_speciation_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_protease_kinetics":
        from .protease_kinetics_tools import _read_protease_kinetics_publication
        return _read_protease_kinetics_publication(registry, context, reader, source_ref)
    if tool_name == "result.variants.vcf":
        from .vcf_result_tools import read_retained_vcf_publication
        return read_retained_vcf_publication(registry, context, reader, source_ref)
    if tool_name in {"find_n_glycosylation_motifs", "predict_o_glycosylation_hotspots", "align_sequences"}:
        return registry.molecular_sequence_results_for(context.run_id).read_ordinary_molecular_sequence_publication(
            context, source_ref, operation=tool_name, read_received=reader)
    if tool_name == "identify_transcription_factor_binding_sites":
        from .tf_binding_tools import _read_tf_binding_publication
        return _read_tf_binding_publication(registry, context, reader, source_ref)
    if tool_name == "find_enriched_motifs_with_homer":
        from .homer_motif_tools import _read_homer_publication
        return _read_homer_publication(registry, context, reader, source_ref)
    if tool_name == "result.macs2.peaks":
        from .macs2_peak_tools import _read_publication
        return _read_publication(registry, context, reader, source_ref)
    if tool_name == "analyze_cas9_mutation_outcomes":
        from .reference_edit_outcome_tools import _read_reference_edit_outcome_publication
        return _read_reference_edit_outcome_publication(registry, context, reader, source_ref)
    if tool_name == ITC_TOOL:
        from .itc_tools import _read_retained_itc_publication
        return _read_retained_itc_publication(registry, context, reader, source_ref)
    result_version, control_version, _, prefix = _publication_profile(tool_name)
    tool_name == ITC_TOOL
    admitted = reader(context, source_ref, "source", source_metadata_only=True)
    if admitted["failure"] is not None:
        raise ContractError("molecular_tool_" + admitted["failure"]["code"])
    item = admitted["input"]
    source = item["witness"]["record"]
    if (source.get("origin") != "tool" or source.get("provider") != tool_name
            or source.get("version") != result_version):
        raise ContractError(prefix + "producer_required")
    details = _recorded_molecular_producer_details(registry, source_ref, tool_name)
    arguments, invocation = details["arguments"], details["invocation"]
    tool_name == ITC_TOOL
    if tool_name == "analyze_circular_dichroism_spectra":
        from .circular_dichroism_contracts import validate_circular_dichroism_tool_result
        value = validate_circular_dichroism_tool_result(json.loads(_publication_bytes(registry.store, source["artifact_ref"])))
    else:
        from .liftover_measurements import validate_liftover_tool_result
        value = validate_liftover_tool_result(json.loads(_publication_bytes(registry.store, source["artifact_ref"])))
    control = json.loads(_publication_bytes(registry.store, source["request_ref"]))
    if (type(control) is not dict or set(control) != {"version", "request", "native_artifact_ref",
            "execution_selection", "native_handle", "execution"}
            or control["version"] != control_version
            or control["native_artifact_ref"] != source["artifact_ref"]):
        raise ContractError(prefix + "publication_conflict")
    request = control["request"]
    if tool_name in {"liftover_coordinates", "analyze_circular_dichroism_spectra"} and (
            type(request) is not dict or set(request) != {
                "version", "arguments", "invocation", "received_input", "request"}
            or request["version"] != ("ordinary_liftover_request_v1" if tool_name == "liftover_coordinates"
                else "ordinary_cd_request_v1")):
        raise ContractError(prefix + "publication_conflict")
    tool_name == ITC_TOOL
    expected = request["request"]
    witness = request["received_input"]["witness"]
    if tool_name == "liftover_coordinates" and (
            canonical(expected["chain"]["file"]) != canonical(request["received_input"]["file"])
            or expected["chain"]["source_ref"] != (
                witness["reference"] if witness["namespace"] == "source" else None)
            or canonical(arguments.get("input")) != canonical(
                dict(namespace=witness["namespace"], reference=witness["reference"]))
            or arguments.get("chain_format") != expected["chain"]["file"]["format"]
            or canonical(arguments.get("point")) != canonical(expected["point"])):
        raise ContractError(prefix + "publication_conflict")
    if tool_name == "analyze_circular_dichroism_spectra" and (
            canonical(expected["input_file"]) != canonical(request["received_input"]["file"])
            or canonical(arguments.get("input")) != canonical(
                dict(namespace=witness["namespace"], reference=witness["reference"]))):
        raise ContractError(prefix + "publication_conflict")
    if (canonical(expected) != canonical(value["request"])
            or canonical(request["arguments"]) != canonical(arguments)
            or canonical(request["invocation"]) != canonical(invocation)
            or "operand_refs" in source or source.get("parent_source_refs") != (
                [witness["reference"]] if witness["namespace"] == "source" else [])):
        raise ContractError(prefix + "publication_conflict")
    from .tool_grading_artifacts import MEDIA_TYPE, source_tool_grading_entries
    from gene_annotation_episode.native_file_capture import _metadata
    for reference in source.get("auxiliary_artifact_refs", ()):
        if _metadata(registry.store, reference)["media_type"] == MEDIA_TYPE:
            _publication_bytes(registry.store, reference)
    entries = source_tool_grading_entries(registry.store, source_ref)
    if (len(entries) != 1 or canonical(entries[0]["grading"]) != canonical(
            dict(sheet=value["sheet"], scores=value["components"]))):
        raise ContractError(prefix + "publication_conflict")
    tool_name == ITC_TOOL
    return dict(admission_kind="source_only",
        received_input=item, source=source, stored=value, control=control,
        grading_ref=entries[0]["artifact_ref"])
