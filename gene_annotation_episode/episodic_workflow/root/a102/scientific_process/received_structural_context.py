"""Original own-A102 Scientific received_structural_context."""
from ..domain import ContractError
from ..a102_structural_evidence import is_merged_entry
from ..a102_structural_report import received_reports


def received_structural_context(binding, context, workflow):
    axis = next((row['option_ref'] for row in binding.library.headers()
        if row['option_ref']['option_id'] == 'A102'), None)
    if axis is None or not is_merged_entry(binding.library.resolve(axis)):
        return {}
    if workflow is None:
        raise ContractError('a102_report_store_required')
    from ..literature_structure_storage import LiteratureStructureRepository
    return {'received_structural_evidence': received_reports(workflow.store,
        context=context, structure_repository=LiteratureStructureRepository(workflow.store, workflow.run_id),
        axis_reference=axis)}
