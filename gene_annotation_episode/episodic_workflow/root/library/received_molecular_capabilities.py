"""Original received molecular capabilities for supplied decision information."""
from __future__ import annotations
from collections.abc import Mapping
from gene_annotation_episode.schema_information_text import schema_fingerprint


def has_molecular_receiver_context(context):
    """Recognize registered capabilities and exact interval return channels.

    Empty initial values need no synthetic received group or native deployment.
    Molecular capabilities require their exact supplied declarations. Interval
    returns additionally use their existing closed Projection validators in
    declared outcome/report slots; arbitrary input records remain opaque.
    """
    if not isinstance(context, Mapping):
        return False
    sources = context.get("available_report_facts", {})
    sources = sources if isinstance(sources, Mapping) else {}
    from gene_annotation_episode.episodic_workflow.root.library.molecular_result_facts import molecular_fact_sources
    for name, registered in molecular_fact_sources().items():
        supplied = sources.get(name)
        if not isinstance(supplied, Mapping):
            continue
        try:
            if schema_fingerprint(supplied) == schema_fingerprint(registered):
                return True
        except (ValueError, TypeError, KeyError, RecursionError):
            continue
    from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_return_views import genomic_overlap_fact_sources
    from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_return_views import chromatin_fact_sources
    from gene_annotation_episode.episodic_workflow.root.library.atac_differential_return_views import atac_fact_sources
    from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_return_views import expression_nmf_fact_sources
    for registered_sources in (genomic_overlap_fact_sources(), chromatin_fact_sources(),
            atac_fact_sources(), expression_nmf_fact_sources()):
        for name, registered in registered_sources.items():
            supplied = sources.get(name)
            if not isinstance(supplied, Mapping):
                continue
            try:
                if schema_fingerprint(supplied) == schema_fingerprint(registered):
                    return True
            except (ValueError, TypeError, KeyError, RecursionError):
                continue
    from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_presentation import select_genomic_overlap_presentation
    from gene_annotation_episode.episodic_workflow.root.library.chromatin_interaction_presentation import select_chromatin_presentation
    from gene_annotation_episode.episodic_workflow.root.library.atac_differential_presentation import select_atac_presentation
    from gene_annotation_episode.episodic_workflow.root.library.expression_nmf_presentation import select_expression_nmf_presentation
    from gene_annotation_episode.episodic_workflow.root.library.native_profile_presentation import has_native_profile_receiver_context
    return bool(select_genomic_overlap_presentation(context)['projections']
        or select_chromatin_presentation(context)['projections']
        or select_atac_presentation(context)['projections']
        or select_expression_nmf_presentation(context)['projections']
        or has_native_profile_receiver_context(context))


