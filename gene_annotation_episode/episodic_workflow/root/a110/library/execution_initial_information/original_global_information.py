"""Preserve the original explicitly global factory for untagged callers."""
from ...communication import plain
from ...execution_contracts import checked
from ...local_file_capture_results import is_file_source_selector
from ..execution_result_contract import RESULTS_SCHEMA
from .presentation import resource_information

def initial_information(context, readers):
    if context.role == 'results' and is_file_source_selector(plain(context.assignment).get('selector')):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = readers.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)
        return {'execution_resource_capabilities': [{'resource_id': target['resource_id'],
            'resource_kind': 'local'}], 'execution_initial_information': {}}
    value = resource_information(readers)
    return value
