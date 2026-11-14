"""Explicit installed scientific implementations for AppService publications.

This registry performs no scientific I/O and never chooses an implementation.
The caller pins an implementation; the results assignment selects it and its
parameters. Unknown implementations remain unavailable without losing bytes.
"""
from __future__ import annotations


def bind_adapters(configured):
    from .library import bvbrc_homology_bundle_adapter as homology
    from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_adapter as proteome
    from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_bundle_adapter_v2 as proteome_v2
    installed = {(module.ADAPTER_ID, module.ADAPTER_VERSION): module
        for module in (homology, proteome, proteome_v2)}
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
