from __future__ import annotations

def bind_adapters(configured):
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_homology_bundle_adapter as homology
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_gene_tree_bundle_adapter as gene_tree
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_codon_tree_bundle_adapter as codon_tree
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_msa_bundle_adapter as msa
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_metacats_bundle_adapter as metacats
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_genome_alignment_bundle_adapter as genome_alignment
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_bundle_adapter as proteome
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_proteome_bundle_adapter_v2 as proteome_v2
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_bundle_adapter as comparative_systems
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_fastqutils_bundle_adapter as fastqutils
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_annotation_bundle_adapter as annotation
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_assembly_bundle_adapter as assembly
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_variation_bundle_adapter as variation
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_influenza_ha_bundle_adapter as influenza_ha
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_subspecies_bundle_adapter as subspecies
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_tnseq_bundle_adapter as tnseq
    import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_rnaseq_bundle_adapter as rnaseq
    installed = {(module.ADAPTER_ID, module.ADAPTER_VERSION): module for module in (homology, gene_tree, codon_tree, msa, metacats, genome_alignment, proteome, proteome_v2, comparative_systems, fastqutils, annotation, assembly, variation, influenza_ha, subspecies, tnseq, rnaseq)}
    bound, seen = ({}, set())
    for row in configured:
        key = (row['adapter_id'], row['adapter_version'])
        if key in seen:
            raise ValueError('appservice_adapter_configuration_conflict')
        seen.add(key)
        implementation = installed.get(key)
        if implementation is None:
            continue
        bound[key] = implementation
    return bound

def selected_adapter(service, selection):
    if selection is None:
        return None
    return service.scientific_adapters.get((selection['adapter_id'], selection['adapter_version']))
