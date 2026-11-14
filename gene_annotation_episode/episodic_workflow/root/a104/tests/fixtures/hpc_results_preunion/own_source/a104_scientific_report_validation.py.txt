"""Validate A104 evolutionary report claims against native placements."""

from .communication import ReportBoundaryError, plain
from .domain import ContractError
from .a104_investigation import report_schema, legacy_report_schema, resolve_report


def validate_axis_report(binding, context, form, schema):
    axis = plain(context.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id')
    if axis != 'A104' or set(plain(schema).get('properties', {})) not in (
            set(report_schema()['properties']), set(legacy_report_schema()['properties'])):
        return
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a104_report_store_required')
    try:
        resolve_report(workflow.store, plain(form), scope=plain(context.scope))
    except ContractError as error:
        fields = {
            'a104_report_numeric_credit_conflict': 'phylogenetic_credit',
            'a104_native_tree_statement_requires_received_original_execution': 'phylogeny_status',
            'a104_placement_statement_requires_native_measurement': 'phylogeny_status',
            'a104_history_statement_requires_actual_two_tree_comparison': 'phylogeny_status',
            'a104_history_agreement_requires_supported_native_comparison': 'history_interpretation',
            'a104_discordance_statement_requires_native_comparison': 'history_interpretation',
            'a104_function_clade_requires_exact_characterized_reference_links': 'function_scope',
            'a104_mixed_function_statement_requires_characterized_members': 'function_scope',
            'a104_function_statement_requires_explicit_hypothesis_and_assessment': 'function_scope',
            'a104_function_hypothesis_requires_original_target': 'hypothesis_refs',
            'a104_function_statement_requires_corresponding_assessment_relation': 'assessment_refs'}
        if str(error) not in fields:
            raise
        raise ReportBoundaryError('A104 interpretation requires the particular native evidence and attribution',
            code=str(error), field=fields[str(error)]) from error
