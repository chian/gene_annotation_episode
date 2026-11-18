"""Preserve the original explicitly global factory for untagged callers."""
from ...communication import plain
from ...execution_contracts import checked
from ...local_file_capture_results import is_file_source_selector
from ..execution_result_contract import RESULTS_SCHEMA
from .presentation import resource_information
from .presentation import (received_api_information, annotation_blast_information,
    scientific_blast_information, received_rna_information)

def initial_information(context, readers):
    if context.role == 'results' and is_file_source_selector(plain(context.assignment).get('selector')):
        assignment = checked(context.assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        target = readers.job_progress_provider.targets.read_target(assignment['handoff_ref'], context.scope)
        return {'execution_resource_capabilities': [{'resource_id': target['resource_id'],
            'resource_kind': 'local'}], 'execution_initial_information': {}}
    value = resource_information(readers)
    value.update(received_api_information(context, readers))
    if context.role == 'annotation':
        value.update(annotation_blast_information(context, readers))
        value.update(received_rna_information(context, readers))
    elif context.role == 'partner_presence_evidence':
        value.update(scientific_blast_information(context, readers))
        value.update(received_rna_information(context, readers))
    return value
