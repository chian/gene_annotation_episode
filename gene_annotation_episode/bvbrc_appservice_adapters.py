"""Explicit installed scientific implementations for AppService publications.

This registry performs no scientific I/O and never chooses an implementation.
The caller pins an implementation; the results assignment selects it and its
parameters. Unknown implementations remain unavailable without losing bytes.
"""
from __future__ import annotations


def bind_adapters(configured):
    from . import bvbrc_homology_bundle_adapter as homology
    from . import bvbrc_gene_tree_bundle_adapter as gene_tree
    from . import bvbrc_codon_tree_bundle_adapter as codon_tree
    from . import bvbrc_msa_bundle_adapter as msa
    from . import bvbrc_metacats_bundle_adapter as metacats
    from . import bvbrc_genome_alignment_bundle_adapter as genome_alignment
    from . import bvbrc_proteome_bundle_adapter as proteome
    from . import bvbrc_proteome_bundle_adapter_v2 as proteome_v2
    from . import bvbrc_comparative_systems_bundle_adapter as comparative_systems
    from . import bvbrc_fastqutils_bundle_adapter as fastqutils
    from . import bvbrc_annotation_bundle_adapter as annotation
    from . import bvbrc_assembly_bundle_adapter as assembly
    from . import bvbrc_variation_bundle_adapter as variation
    from . import bvbrc_influenza_ha_bundle_adapter as influenza_ha
    from . import bvbrc_subspecies_bundle_adapter as subspecies
    from . import bvbrc_tnseq_bundle_adapter as tnseq
    from . import bvbrc_rnaseq_bundle_adapter as rnaseq

    installed = {(module.ADAPTER_ID, module.ADAPTER_VERSION): module
        for module in (homology, gene_tree, codon_tree, msa, metacats, genome_alignment, proteome, proteome_v2, comparative_systems, fastqutils, annotation, assembly, variation, influenza_ha, subspecies, tnseq, rnaseq)}
    bound, seen = {}, set()
    for row in configured:
        key = row['adapter_id'], row['adapter_version']
        if key in seen:
            raise ValueError('appservice_adapter_configuration_conflict')
        seen.add(key)
        implementation = installed.get(key)
        if implementation is None:
            continue
        if implementation.implementation_sha256() != row['implementation_sha256']:
            raise ValueError('appservice_adapter_implementation_conflict')
        bound[key] = (implementation, row['implementation_sha256'])
    return bound


def selected_adapter(service, selection):
    if selection is None:
        return None
    return service.scientific_adapters.get((selection['adapter_id'], selection['adapter_version']))


__all__ = ['bind_adapters', 'selected_adapter']
