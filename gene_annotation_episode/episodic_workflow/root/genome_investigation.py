"""Saved configuration for the unsupported combined genome workflow.

Each evidence axis needs its own private caller binding before this combined
entry point can be restored.
"""
from dataclasses import dataclass

from .library.record_values import plain


@dataclass(frozen=True)
class GenomeEvidenceServices:
    source_directory: str
    execution_configuration: dict
    tool_retrieval: dict
    literature_configuration: dict
    scientific_yield_bindings: dict | None = None

    def as_record(self):
        return {'version': 'genome_existing_evidence_services_v1',
            'source_directory': self.source_directory,
            'execution_configuration': plain(self.execution_configuration),
            'tool_retrieval': plain(self.tool_retrieval),
            'literature_configuration': plain(self.literature_configuration),
            'scientific_yield_bindings': plain(self.scientific_yield_bindings)}

    def __call__(self, store, *, run_id, directory, tool_catalog, tool_registry,
                 job_episodes=None, resource_estimator=None):
        raise ValueError('combined_literature_requires_axis_private_bindings')
