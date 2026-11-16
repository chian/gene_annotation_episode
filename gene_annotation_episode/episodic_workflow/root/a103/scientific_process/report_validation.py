"""Validate A103 gene-context returns with their original report contract."""

from ..communication import plain
from ..domain import ContractError
from ..a103_investigation import measurement_report_schema, resolve_measurement_report


def validate_axis_report(binding, context, form, schema):
    axis = plain(context.assignment).get('selection', {}).get('evidence_axis', {}).get('option_id')
    if axis != 'A103':
        return
    fields = set(plain(schema).get('properties', {}))
    if fields == set(measurement_report_schema()['properties']):
        workflow = getattr(binding.services, 'workflow', None)
        if workflow is None:
            raise ContractError('a103_report_store_required')
        resolve_measurement_report(workflow.store, plain(form), scope=plain(context.scope))
