"""Private A110 binding record."""
from __future__ import annotations
from .contracts import VERSION, _AXIS_DIRECTORY, _binding_source_bytes, hashlib

class LiteratureBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes()
        for name in ('library/literature_component_binding.py', 'library/reaction_source_selection.py', 'library/literature_reaction_inputs.py', 'library/literature_reaction_calculations.py', 'literature_reaction_storage.py', 'literature_sheet_updates.py', 'library/literature_source_presentation.py', 'library/literature_reference_parent_presentation.py', 'library/reaction_population.py', 'library/reaction_population_contracts.py', 'library/literature_reaction_instructions.py', 'library/scientific_decision_presentation.py', 'library/scientific_instruction_text.py', 'library/literature_experiment_assessments.py', 'library/literature_reaction_meanings.py', 'library/literature_reaction_native_inputs.py', 'library/literature_reaction_prompt.py', 'library/literature_reaction_types.py', 'library/literature_task_selection.py', 'library/reaction_native_observations.py', 'library/reaction_report_contracts.py', 'literature_reaction_native_storage.py'):
            implementation += (_AXIS_DIRECTORY / name).read_bytes()
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        return {'version': VERSION, 'binding_id': 'published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': configuration}
