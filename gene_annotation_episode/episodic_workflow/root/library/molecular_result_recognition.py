"""Original molecular result recognition for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping


def _selected_molecular_packet(value):
    """Recognize only a complete registered selected-value packet."""
    if isinstance(value, Mapping) and value.get("version") == "ordinary_somatic_variant_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.somatic_variant_contracts import validate_somatic_return
        from gene_annotation_episode.episodic_workflow.root.communication import plain
        try:
            return validate_somatic_return(plain(value))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "esm_gene_embedding_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.esm_gene_embedding_contracts import validate_esm_embedding_return
        from gene_annotation_episode.episodic_workflow.root.communication import plain
        try:
            return validate_esm_embedding_return(plain(value))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protein_phylogeny_values_v1":
        from gene_annotation_episode.protein_phylogeny_result_views import select_protein_phylogeny_values
        return select_protein_phylogeny_values(value)
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protein_conservation_values_v1":
        from gene_annotation_episode.protein_conservation_result_views import select_protein_conservation_values
        return select_protein_conservation_values(value)
    if isinstance(value, Mapping) and value.get("version") == "ordinary_primer_placement_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.primer_placement_result_contracts import validate_ordinary_primer_placement_return
        try:
            return validate_ordinary_primer_placement_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protein_disorder_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.protein_disorder_result_contracts import validate_ordinary_disorder_return
        try:
            return validate_ordinary_disorder_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_arsenic_speciation_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.arsenic_speciation_result_contracts import validate_ordinary_arsenic_return
        try:
            return validate_ordinary_arsenic_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "vcf_result_return_v1":
        from gene_annotation_episode.episodic_workflow.root.library.vcf_result_measurements import validate_vcf_return
        try:
            return validate_vcf_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") in (
            "ordinary_itc_values_v1", "ordinary_itc_partial_values_v1", "itc_parameter_return_v1"):
        from gene_annotation_episode.itc_binding_presentation import select_itc_binding_result
        return select_itc_binding_result(value)
    if isinstance(value, Mapping) and value.get("version") == "ordinary_o_glycosylation_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        try:
            return validate_ordinary_molecular_sequence_return(value,
                operation="predict_o_glycosylation_hotspots")
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_n_glycosylation_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
        try:
            return validate_ordinary_molecular_sequence_return(value,
                operation="find_n_glycosylation_motifs")
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "tf_binding_return_v1":
        from gene_annotation_episode.episodic_workflow.root.library.tf_binding_result_contracts import validate_tf_binding_return
        try:
            return validate_tf_binding_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_protease_kinetics_values_v1":
        from gene_annotation_episode.episodic_workflow.root.library.protease_kinetics_result_contracts import validate_ordinary_protease_kinetics_return
        try:
            return validate_ordinary_protease_kinetics_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "homer_motif_return_v1":
        from gene_annotation_episode.episodic_workflow.root.library.homer_motif_result_contracts import validate_homer_motif_return
        try:
            return validate_homer_motif_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if isinstance(value, Mapping) and value.get("version") == "ordinary_macs2_peak_result_v1":
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_result_contracts import validate_macs2_peak_return
        try:
            return validate_macs2_peak_return(value)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError):
            return None
    if not isinstance(value, Mapping) or value.get("version") != "ordinary_orf_values_v1":
        return None
    from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import validate_ordinary_orf_return
    try:
        # This delegates to the common selected-value validator. It performs
        # no custody lookup, File read, native work or scientific calculation.
        return validate_ordinary_orf_return(value)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError):
        return None


