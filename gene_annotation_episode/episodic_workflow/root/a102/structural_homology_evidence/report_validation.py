"""Validate A102 reports against the actual received structural evidence."""

from dataclasses import replace

from ..communication import ReportBoundaryError, plain
from ..domain import ContractError
from ..structural_homology_evidence_records import selection_fields
from ..a102_structural_evidence import is_merged_entry
from ..a102_structural_report import is_structural_report_schema, resolve_report


def validate_structural_report(binding, context, form, schema):
    if not is_structural_report_schema(schema):
        return
    axis = binding.library.reference('A102')
    if not is_merged_entry(binding.library.resolve(axis)):
        raise ContractError('a102_merged_structural_evidence_catalog_required')
    if context.role == 'structural_homology_evidence':
        selection = binding._original_selection(context)
        if selection[selection_fields(selection)[0]] != axis:
            raise ContractError('a102_structural_report_requires_merged_axis')
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a102_report_store_required')
    selected = binding.services.record_selection(context)
    if selected.get('run_id') != context.run_id or selected.get('episode_id') != context.episode_id:
        raise ContractError('a102_report_receiver_mismatch')
    current = replace(context, received_record_refs=tuple(selected['known_record_refs']))
    try:
        from ..literature_structure_storage import LiteratureStructureRepository
        resolve_report(workflow.store, plain(form), context=current,
            structure_repository=LiteratureStructureRepository(workflow.store, workflow.run_id))
    except ContractError as error:
        fields = {'a102_comparative_status_differs_from_delivered_evidence': 'comparative_status',
            'a102_experimental_status_differs_from_delivered_evidence': 'experimental_status'}
        if str(error) not in fields:
            raise
        raise ReportBoundaryError('A102 interpretation requires its delivered structural evidence',
            code=str(error), field=fields[str(error)]) from error


def validate_investigation_report(binding, context, form, schema):
    from ..a102_investigation import report_schema, resolve_report
    if plain(schema) != report_schema():
        return
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a102_report_store_required')
    resolve_report(workflow.store, plain(form), scope=plain(context.scope))
