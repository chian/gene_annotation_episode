"""Private A106 literature_targeted binding record."""
from __future__ import annotations
from .source_contracts import VERSION, _AXIS_DIRECTORY, deepcopy, hashlib

class LiteratureBindingRecord:

    def as_record(self):
        from pathlib import Path as _context_source_path
        directory = _AXIS_DIRECTORY
        digest = hashlib.sha256()
        for path in sorted(directory.rglob('*')):
            if 'tests' in path.relative_to(directory).parts or not path.is_file():
                continue
            if path.suffix not in {'.py', '.json'}:
                continue
            digest.update(path.relative_to(directory).as_posix().encode('utf8'))
            digest.update(path.read_bytes())
        for _context_source_key in ('gene_annotation_episode/__init__.py', 'gene_annotation_episode/episodic_workflow/__init__.py', 'gene_annotation_episode/episodic_workflow/root/__init__.py', 'gene_annotation_episode/episodic_workflow/root/receiving_context.py'):
            digest.update(_context_source_key.encode('utf8'))
            digest.update((_context_source_path(__file__).resolve().parents[9] / _context_source_key).read_bytes())
        configuration = {'outcome_page_size': self.outcome_page_size}
        for name in ('private_yield_binding', 'ratio_source_population', 'controlled_response_population', 'gel_population', 'completion_time_population', 'product_partition_population', 'active_site_population', 'parent_depletion_population', 'stoichiometric_balance_population', 'compiled_assay_population', 'channel_population', 'ion_discrimination_population'):
            if getattr(self, name):
                configuration[name] = True
        if self.private_yield_binding:
            configuration['yield_bindings'] = deepcopy(self._yield_bindings)
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        if self.ratio_source_population:
            configuration['ratio_source_evidence_origin'] = self.ratio_source_evidence_origin
        if self.controlled_response_population:
            configuration['controlled_response_descriptor'] = deepcopy(self._controlled_response_descriptor)
            configuration['controlled_response_evidence_origin'] = self.controlled_response_evidence_origin
        if self.gel_population:
            configuration['gel_descriptor'] = deepcopy(self._gel_descriptor)
            configuration['gel_evidence_origin'] = self.gel_evidence_origin
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction', 'implementation_sha256': digest.hexdigest(), 'configuration': configuration}
