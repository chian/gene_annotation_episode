"""Private A107 binding record."""
from __future__ import annotations
from .contracts import VERSION, _AXIS_DIRECTORY, _binding_source_bytes, hashlib

class LiteratureBindingRecord:

    def as_record(self):
        implementation = _binding_source_bytes()
        for name in ('library/partner_source_contracts.py', 'library/literature_partner_native_inputs.py', 'library/literature_partner_inputs.py', 'library/literature_partner_calculations.py', 'literature_partner_storage.py', 'library/literature_sheet_updates.py', 'library/literature_source_presentation.py', 'library/partner_source_task.py', 'library/literature_partner_sheet_records.py', 'library/literature_partner_sheet_population.py', 'library/scientific_instruction_text.py', 'library/literature_assay_inputs.py', 'library/literature_assets.py', 'library/literature_current_results.py', 'library/literature_experiment_assessments.py', 'library/literature_partner_defined_units.py', 'library/literature_partner_models.py', 'library/literature_partner_operand_information.py', 'library/literature_partner_saved_validation.py', 'library/literature_partner_source_fields.py', 'library/literature_source_operand_information.py', 'library/literature_source_origin.py', 'library/literature_work_results.py', 'library/partner_source_instruction_text.py', 'library/partner_source_task_selection.py', 'literature_contract_error.py'):
            implementation += (_AXIS_DIRECTORY / name).read_bytes()
        configuration = {'outcome_page_size': self.outcome_page_size}
        if self.reference_parent_sources is not None:
            configuration['reference_parent_sources'] = list(self.reference_parent_sources)
        if self._contract_information_profile is not None:
            configuration['contract_information_profile'] = self._contract_information_profile
        return {'version': VERSION, 'binding_id': 'scientific_process/published_evidence_assessment/evidence_search_strategy_improvement', 'implementation_sha256': hashlib.sha256(implementation).hexdigest(), 'configuration': configuration}
