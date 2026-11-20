"""What the parent gives: the results assignment (``execution_results_assignment_v1``: ``handoff_ref`` and
``selector``) and the records it passes.

This is the only place the assignment is read. The handoff arrives as a record reference: ``handoff_ref`` names the
handoff row the job service wrote at the launch (a row of the job ledger), and the commissioner passes that row in
custody in ``record_refs``. The commissioner also copies the execution target the handoff names into the assignment
(``target``); for a plain file result its ``assignment.workspace`` is the job's directory (the handoff row's
``detail['native']['directory']``), and the selector is validated here against it. A wrong commission fails with its
error.

The family of the target decides which branch of this episode applies. Placed: the plain file results of a job
(``native_bytes``: requested paths and byte intervals inside the job's directory), the BLAST database grader return
(``blast_graded``) and the local phmmer return (``phmmer_graded``). The other families are named here and raise
where their old class would have been called (``unplaced``): their classes are in no place now."""
import math
from pathlib import Path

from method_loop import ChoiceField, Field, DeclaredField, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.native_blast_masking_acquisition import (
    is_native_blast_masking_target)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_acquisition import (
    is_native_hmmer_preparation_target)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_analysis_kind import (
    ANALYSIS_KINDS, checked_analysis_kind)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.blast_return_contracts import (
    BLAST_GRADED_REQUEST_SCHEMA, BLAST_GRADED_REQUEST_VERSION, BLAST_PAIRWISE_GRADED_REQUEST_SCHEMA,
    BLAST_PAIRWISE_GRADED_REQUEST_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import (
    TEXT, checked, obj, validate_target)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_homology_evidence.practical_execution_operations import (
    confined)
from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.sequence_homology_evidence.hmmer_preparation_result_views import (
    validate_preparation_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_result_views import (
    validate_masking_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.hmmer_native_result_views import (
    validate_native_hmmer_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.native_blast_database_result_views import (
    validate_native_blast_database_result_selector)
from gene_annotation_episode.episodic_workflow.episode_support.readers.similarity_search.sequence_homology_evidence.native_blast_standard_database_result_views import (
    validate_standard_blast_database_selector)

RESULTS_VERSION = 'execution_results_assignment_v1'
LOCAL_FILE_SOURCE_VERSION = 'local_file_source_selector_v1'
OFFSET = {'type': 'integer', 'minimum': 0}
LIMIT = {'type': 'integer', 'minimum': 1}
RESULTS_SCHEMA = obj({'version': {'const': RESULTS_VERSION}, 'handoff_ref': TEXT, 'selector': {'type': 'object'}})
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': TEXT},
                              'path': TEXT, 'offset': OFFSET, 'limit': LIMIT}, [])
MASKING_SELECTOR_VERSION = 'native_blast_masking_result_selector_v1'

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The assignment version', RESULTS_VERSION),
    'handoff_ref': Field('text', 'The reference of the handoff row of the job whose results are acquired; the row '
                                 'itself is passed in record_refs'),
    'selector': Field('record', 'The requested results: plain file results (paths, or one path with offset and '
                                'limit, inside the job\'s directory), a graded return request, or a typed native '
                                'result selector'),
    'target': Field('record', 'The execution target the handoff names (execution_target_v1); the commissioner '
                              'builds it from the handoff row'),
    'analysis_kind': ChoiceField('text', 'The declared analysis kind of the BLAST job whose result is acquired '
                                         '(pairwise: one query sequence against one subject sequence). The kind is '
                                         'derived again from the job itself and the two must agree; it is required '
                                         'for a pairwise BLAST target and not allowed for any other', ANALYSIS_KINDS,
                                 required=False),
    'acquired_record_unit': Field('number', 'The credit of one fully acquired requested selector'),
    'record_refs': Field('record_refs', 'Every record the code reads, passed in custody: the handoff row, the job '
                                        'rows and result artifacts of an earlier acquisition, and the records the '
                                        'selected native inputs name', required=False),
    'initial_result_refs': Field('record_refs', 'The earlier result acquisitions of this handoff that the parent '
                                                'holds; the artifacts they name are in record_refs',
                                 required=False),
})


def _jobs(target):
    return target['assignment'].get('requested_job', {}) if isinstance(target.get('assignment'), dict) else {}


def family(target, selector):
    """The family of the original ``_selector`` branches, in the old order. The BLAST database grader return
    (``blast_graded``) is the API BLAST result whose return is its graded sheet."""
    if selector.get('version') == BLAST_GRADED_REQUEST_VERSION:
        return 'blast_graded'
    if selector.get('version') == BLAST_PAIRWISE_GRADED_REQUEST_VERSION:
        return 'blast_pairwise'
    if selector.get('version') == LOCAL_FILE_SOURCE_VERSION:
        return 'local_file_source'
    if selector.get('version') == MASKING_SELECTOR_VERSION or is_native_blast_masking_target(target):
        return 'native_blast_masking'
    if target['resource_kind'] == 'api':
        return 'api'
    jobs = _jobs(target) if target['resource_kind'] != 'api' else {}
    if 'native_blast_standard_database' in jobs:
        return 'native_blast_standard_database'
    if 'native_blast_database' in jobs:
        return 'native_blast_database'
    if is_native_hmmer_preparation_target(target):
        return 'native_hmmer_preparation'
    if 'native_hmmer' in jobs:
        # A local phmmer search is graded into the HMMER search sheet by this episode (``phmmer_grade``).
        return 'phmmer_graded' if jobs['native_hmmer']['program'] == 'phmmer' else 'native_hmmer'
    return 'native_bytes'


def windows(selector):
    """The requested byte interval of each path as ``[offset, limit or None]`` (``None``: to the end of the
    file)."""
    values = {path: [0, None] for path in selector.get('paths', [])}
    if 'path' in selector:
        values[selector['path']] = [selector.get('offset', 0), selector.get('limit')]
    return values


def result_names(target, requested):
    """The job service's name of each requested path: its path inside the job's directory, which is how a route
    lists the result files of a job."""
    workspace = Path(target['assignment']['workspace']).resolve()
    return {path: confined(path, workspace).relative_to(workspace).as_posix() for path in requested}


def validated_selector(target, selector, kind):
    """The old ``_selector`` of this role over the family ``kind``."""
    jobs = _jobs(target)
    if kind == 'blast_graded':
        # The original query operand is a required result identity, not a prewritten service command.
        value = checked(selector, BLAST_GRADED_REQUEST_SCHEMA, 'blast_database_grader_return_request_invalid')
        if target['resource_kind'] != 'api' or value['resource_id'] != target['resource_id']:
            raise ValueError('blast_database_grader_resource_conflict')
        return value
    if kind == 'blast_pairwise':
        # The graded return of A101's pairwise BLAST job: the request names the resource and the sheet it wants.
        value = checked(selector, BLAST_PAIRWISE_GRADED_REQUEST_SCHEMA, 'blast_pairwise_grader_return_request_invalid')
        if target['resource_kind'] != 'local' or value['resource_id'] != target['resource_id']:
            raise ValueError('blast_pairwise_grader_resource_conflict')
        return value
    if kind == 'local_file_source':
        raise NotImplementedError('unplaced:LocalFileSourceResults.selector')
    if kind == 'native_blast_masking':
        return validate_masking_result_selector(selector, operation=jobs['native_blast_masking']['operation'])
    if kind == 'api':
        raise NotImplementedError('unplaced:api_execution.validate_result_selector')
    if kind == 'native_blast_standard_database':
        return validate_standard_blast_database_selector(
            selector, program=jobs['native_blast_standard_database']['program'])
    if kind == 'native_blast_database':
        return validate_native_blast_database_result_selector(selector, program=jobs['native_blast_database']['program'])
    if kind == 'native_hmmer_preparation':
        job = jobs['native_hmmer_preparation']
        return validate_preparation_result_selector(selector, program=job['program'], mode=job['mode'])
    if kind in ('native_hmmer', 'phmmer_graded'):
        return validate_native_hmmer_result_selector(selector, program=jobs['native_hmmer']['program'])
    value = checked(selector, NATIVE_SELECTOR_SCHEMA, 'invalid_execution_native_selector')
    paths = list(value.get('paths', []))
    if 'path' in value:
        if value['path'] in paths:
            raise ValueError('ambiguous_execution_results_selector')
        paths.append(value['path'])
    if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
        raise ValueError('execution_results_paths_required')
    for path in paths:
        confined(path, target['assignment']['workspace'])
    return value


def read_from_parent(assignment, message):
    """The validated results assignment as the parent input: the assignment, its target, its family and validated
    selector, the requested byte intervals of a plain file result with the job service's name of each path, the
    credit unit and the records passed."""
    own = {name: assignment[name] for name in ('version', 'handoff_ref', 'selector')}
    own = checked(own, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
    target = validate_target(assignment['target'])
    if target['handle'] != own['handoff_ref']:
        raise ValueError('execution_result_target_conflict')
    unit = assignment['acquired_record_unit']
    if not math.isfinite(unit) or unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    kind = family(target, own['selector'])
    declared = assignment.get('analysis_kind')
    if kind == 'blast_pairwise':
        # The declared kind of the commission and the kind derived from the job itself must agree (no fallback).
        analysis_kind = checked_analysis_kind(declared, _jobs(target))
    elif declared is not None:
        raise ValueError('analysis_kind_not_applicable_to_family:' + kind)
    else:
        analysis_kind = None
    selector = validated_selector(target, own['selector'], kind)
    requested = windows(selector) if kind == 'native_bytes' else {}
    parent_input = {'assignment': own, 'target': target, 'family': kind, 'selector': selector,
                    'requested': requested,
                    'result_names': result_names(target, requested) if kind == 'native_bytes' else {},
                    'analysis_kind': analysis_kind, 'acquired_record_unit': unit,
                    'record_refs': list(assignment.get('record_refs', [])),
                    'initial_result_refs': list(assignment.get('initial_result_refs', []))}
    if kind == 'blast_pairwise':
        parent_input['report_name'] = _jobs(target)['blast_pairwise']['report']['relative_path']
    if kind == 'phmmer_graded':
        # The original query operand: the one subject bound to the job's query sequence.
        queries = [binding['subject_ref'] for binding in target['assignment']['requested_job']['native_hmmer'][
            'operand_bindings'] if binding['operand_role'] == 'query_sequence']
        if len(queries) != 1 or not queries[0]:
            raise ValueError('phmmer_query_subject_binding_required')
        parent_input['query_ref'] = queries[0]
    return parent_input
