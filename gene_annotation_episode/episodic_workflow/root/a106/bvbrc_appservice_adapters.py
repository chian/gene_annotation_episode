"""Explicit installed scientific implementations for AppService publications.

This registry performs no scientific I/O and never chooses an implementation.
The caller pins an implementation; the results assignment selects it and its
parameters. Unknown implementations remain unavailable without losing bytes.
"""
from __future__ import annotations


def bind_adapters(configured):
    from . import bvbrc_tnseq_bundle_adapter as tnseq
    from . import bvbrc_rnaseq_bundle_adapter as rnaseq
    installed = {(module.ADAPTER_ID, module.ADAPTER_VERSION): module
        for module in (tnseq, rnaseq)}
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
