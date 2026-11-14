from __future__ import annotations
'binding record for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.receiving_context_sources import receiving_context_source_bytes
from gene_annotation_episode.episodic_workflow.root.a108.shared_infrastructure_sources import shared_infrastructure_source_bytes
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_contracts import VERSION, _AXIS_DIRECTORY, _binding_source_bytes, deepcopy, hashlib

from gene_annotation_episode.episodic_workflow.root.a108.runtime_assets import binding_runtime_asset_bytes

class LiteratureBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes() + b''.join((path.read_bytes() for path in sorted(_AXIS_DIRECTORY.glob('*.py')))) + binding_runtime_asset_bytes() + receiving_context_source_bytes() + shared_infrastructure_source_bytes()
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.private_yield_binding:
            configuration['private_yield_binding'] = True
            configuration['yield_bindings'] = deepcopy(self._yield_bindings)
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': configuration}
