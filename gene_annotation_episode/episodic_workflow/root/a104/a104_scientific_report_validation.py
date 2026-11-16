"""Validate A104 evolutionary report claims against native placements."""

from .communication import ReportBoundaryError, plain
from .domain import ContractError
from .a104_investigation import report_schema, resolve_report


def validate_axis_report(binding, context, form, schema):
    axis = plain(context.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id')
    if axis != 'A104' or set(plain(schema).get('properties', {})) != set(report_schema()['properties']):
        return
    workflow = getattr(binding.services, 'workflow', None)
    if workflow is None:
        raise ContractError('a104_report_store_required')
    try:
        resolve_report(workflow.store, plain(form), scope=plain(context.scope))
    except ContractError as error:
        fields = {'a104_report_numeric_credit_conflict': 'phylogenetic_credit'}
        if str(error) not in fields:
            raise
        raise ReportBoundaryError('A104 interpretation requires the particular native evidence and attribution',
            code=str(error), field=fields[str(error)]) from error
