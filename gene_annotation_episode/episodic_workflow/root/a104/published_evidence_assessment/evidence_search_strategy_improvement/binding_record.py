"""Private A104 binding record."""
from __future__ import annotations
from .contracts import VERSION, _AXIS_DIRECTORY, _binding_source_bytes, deepcopy, hashlib, json

class LiteratureBindingRecord:

    def as_record(self):
        """Record only A104's own literature binding and retained local files."""
        from gene_annotation_episode.episodic_workflow.root.a104.library.source_descriptor_inputs import implementation_bytes
        implementation = implementation_bytes(self.binding_path)
        configuration = {'outcome_page_size': self.outcome_page_size}
        for name in ('rate_population', 'compiled_assay_population', 'assay_grading_population'):
            if getattr(self, name):
                configuration[name] = True
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self.private_yield_binding:
            configuration['private_yield_binding'] = True
            configuration['yield_bindings'] = deepcopy(self._yield_bindings)
        if self.ion_discrimination_population:
            configuration['ion_discrimination_population'] = True
        if self.channel_population:
            configuration['channel_population'] = True
        if self.completion_time_population:
            configuration['completion_time_population'] = True
        if self.active_site_population:
            configuration['active_site_population'] = True
        if self.parent_depletion_population:
            configuration['parent_depletion_population'] = True
        if self.stoichiometric_balance_population:
            configuration['stoichiometric_balance_population'] = True
        if self.product_partition_population:
            configuration['product_partition_population'] = True
        if self.ratio_source_population:
            configuration.update(ratio_source_population=True, ratio_source_evidence_origin=self.ratio_source_evidence_origin)
        if self.controlled_response_population:
            configuration.update(controlled_response_population=True, controlled_response_descriptor=deepcopy(self._controlled_response_descriptor), controlled_response_evidence_origin=self.controlled_response_evidence_origin)
            implementation += json.dumps(self._controlled_response_descriptor, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
        if self.gel_population:
            configuration.update(gel_population=True, gel_descriptor=deepcopy(self._gel_descriptor), gel_evidence_origin=self.gel_evidence_origin)
            implementation += json.dumps(self._gel_descriptor, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment/evidence_search_strategy_improvement', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': configuration}
