"""What the commissioning parent gives: the handoff row of the job (in custody), the requested results and the job's
directory. The only place an assignment is read.

The handoff arrives as a record reference: ``handoff_ref`` names the one handoff row the job service wrote at the
launch (a row of the job ledger), passed in custody. ``workspace`` is the job's directory (the handoff row's
``detail['native']['directory']``): the requested paths lie inside it, and the job service names each result file by
its path inside that directory (``result_names``). ``resource_kind`` names the yield profile of the acquisition.

This episode acquires plain file results: requested paths and byte intervals of a local or HPC job. A selector of
another kind does not fit the selector schema and the commission fails with that error."""
from pathlib import Path

from method_loop import ChoiceField, DeclaredField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.practical_execution_operations import (
    confined)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import (
    obj, validate_schema)

RESULTS_VERSION = 'execution_results_assignment'
_TEXT = {'type': 'string', 'minLength': 1}
NATIVE_SELECTOR_SCHEMA = obj({'paths': {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': _TEXT},
                              'path': _TEXT, 'offset': {'type': 'integer', 'minimum': 0},
                              'limit': {'type': 'integer', 'minimum': 1}}, [])

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The results assignment contract version', RESULTS_VERSION),
    'handoff_ref': Field('record_refs', 'The one handoff row of the job whose results are acquired (the job ledger '
                         'row the job service wrote at the launch), passed in custody'),
    'selector': Field('record', 'The requested results: paths, or one path with offset and limit, inside the '
                      'job\'s directory'),
    'resource_kind': ChoiceField('text', 'The kind of the resource the job ran on; it names the yield profile of '
                                 'the acquisition', ('local', 'hpc')),
    'workspace': Field('text', 'The job\'s directory (the handoff row\'s native directory); the requested paths '
                       'are confined to it'),
    'acquired_record_unit': Field('number', 'The credit of a fully acquired original selector (positive)'),
    'initial_result_refs': Field('record_refs', 'Earlier result acquisitions of this job that the parent holds '
                                 '(each an episode.execution_result source record); the byte positions they cover '
                                 'earn no credit', required=False),
    'initial_result_artifact_refs': Field('record_refs', 'The information artifact of each record named in '
                                          'initial_result_refs and the fetched files their windows lie in (a '
                                          'passed record does not bring the records it names)', required=False),
})


def native_windows(selector):
    """The requested ``{path: [offset, limit or None]}`` of a plain file selector (``None``: to the end of the
    file)."""
    value = dict(selector)
    validate_schema(value, NATIVE_SELECTOR_SCHEMA)
    paths = list(value.get('paths', []))
    if 'path' in value:
        if value['path'] in paths:
            raise ValueError('ambiguous_execution_results_selector')
        paths.append(value['path'])
    if not paths or (('offset' in value or 'limit' in value) and 'path' not in value):
        raise ValueError('execution_results_paths_required')
    windows = {path: [0, None] for path in value.get('paths', [])}
    if 'path' in value:
        windows[value['path']] = [value.get('offset', 0), value.get('limit')]
    return windows


def result_names(workspace, requested):
    """The job service's name of each requested path: its path inside the job's directory, which is how a route
    lists the result files of a job. A path outside the directory raises."""
    directory = Path(workspace).resolve()
    return {path: confined(path, directory).relative_to(directory).as_posix() for path in requested}


def read_from_parent(assignment, message):
    """The parent input: the assignment (the handoff row's reference, the selector, the kind and the job's
    directory), the requested byte intervals with the job service's name of each path, the credit unit and the
    earlier results passed."""
    handoff_ref, = assignment['handoff_ref']
    unit = assignment['acquired_record_unit']
    if unit <= 0:
        raise ValueError('explicit_positive_operational_credit_units_required')
    requested = native_windows(assignment['selector'])
    return {'assignment': {'version': assignment['version'], 'handoff_ref': handoff_ref,
                           'selector': assignment['selector'], 'resource_kind': assignment['resource_kind'],
                           'workspace': assignment['workspace']},
            'requested': requested, 'result_names': result_names(assignment['workspace'], requested),
            'acquired_record_unit': unit,
            'initial_result_refs': list(assignment.get('initial_result_refs', []))}
