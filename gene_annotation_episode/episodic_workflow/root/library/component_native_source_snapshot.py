"""Retain actual component scientific sources at their current package paths.

The operation map and each scientific implementation are predefined. This
changes source packaging after relocation; it creates no scientific algorithm,
module alias or replacement implementation. Missing code remains an error.
"""
from pathlib import Path


def snapshot_component_sources(axis, names):
    from ..a107.native_driver_runtime import _source_closure
    packages = {
        'A107': 'gene_annotation_episode.episodic_workflow.root.a107',
        'A110': 'gene_annotation_episode.episodic_workflow.root.a110',
    }
    selected = packages[axis]
    modules = [selected + '.' + name.removesuffix('.py').replace('/', '.') for name in names]
    modules.extend((
        'gene_annotation_episode.episodic_workflow.root.library.component_native_tool_contracts',
        'gene_annotation_episode.episodic_workflow.root.library.component_native_profiles',
    ))
    implementation = _source_closure(Path(__file__).resolve().parents[4], modules)
    return {name.replace('.', '/') + '.py': source.read_text()
        for name, source in implementation.items()}
